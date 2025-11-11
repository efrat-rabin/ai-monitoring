#!/usr/bin/env python3
"""
Apply Suggested Logs Action - Patch-based approach
"""

import os
import sys
import argparse
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Import patch validation utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "analyze-pr-code"))
try:
    from validate_patch import fix_patch_format, normalize_patch_newlines
    PATCH_VALIDATION_AVAILABLE = True
except ImportError:
    PATCH_VALIDATION_AVAILABLE = False
    print("Warning: Patch validation module not available")


class PatchApplier:
    """Applies logging improvements using unified diffs."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
        if self.verbose:
            print(f"[DEBUG] PatchApplier initialized")
    
    def verify_file_unchanged(self, file_path: str, expected_hash: str) -> bool:
        """Verify file hasn't changed since analysis."""
        if not os.path.exists(file_path):
            return False
        
        with open(file_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        
        if self.verbose:
            print(f"[DEBUG] File hash verification:")
            print(f"  Expected: {expected_hash}")
            print(f"  Current:  {current_hash}")
            print(f"  Match: {current_hash == expected_hash}")
        
        return current_hash == expected_hash
    
    def _show_file_changes(self, file_path: str):
        """Show recent changes to the file to help understand why patch failed."""
        try:
            print(f"\n📋 Recent changes to {file_path}:")
            
            # Try to get the last commit that modified this file
            result = subprocess.run(
                ['git', 'log', '--oneline', '-n', '3', '--', file_path],
                capture_output=True,
                text=True,
                cwd='.'
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print("\nLast commits affecting this file:")
                print(result.stdout.strip())
                
                # Show the diff from the most recent commit
                print(f"\nChanges in the last commit:")
                diff_result = subprocess.run(
                    ['git', 'diff', 'HEAD~1', 'HEAD', '--', file_path],
                    capture_output=True,
                    text=True,
                    cwd='.'
                )
                
                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    # Show first 30 lines of diff
                    diff_lines = diff_result.stdout.split('\n')[:30]
                    print('\n'.join(diff_lines))
                    if len(diff_result.stdout.split('\n')) > 30:
                        print("\n... (diff truncated)")
                else:
                    print("(No diff available)")
            else:
                print("(No git history found for this file)")
                
        except Exception as e:
            if self.verbose:
                print(f"[DEBUG] Could not show file changes: {e}")
    
    def _validate_patch_format(self, patch_content: str) -> tuple[bool, str]:
        """Validate that patch has correct unified diff format.
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        lines = patch_content.split('\n')
        
        if not lines:
            return False, "Patch is empty"
        
        # Check if patch has @@ header
        has_header = False
        for line in lines:
            if line.startswith('@@'):
                has_header = True
                break
        
        if not has_header:
            return False, "Patch is missing @@ hunk header"
        
        # Check for identical +/- pairs (no-op changes that corrupt patches)
        # This happens when AI removes and adds the exact same line
        i = 0
        while i < len(lines) - 1:
            if lines[i].startswith('-') and lines[i+1].startswith('+'):
                # Check if the content after the prefix is identical
                removed_content = lines[i][1:]  # Everything after the -
                added_content = lines[i+1][1:]   # Everything after the +
                
                if removed_content == added_content:
                    return False, (
                        f"Patch contains no-op change at lines {i+1}-{i+2}:\n"
                        f"  Removes: {repr(lines[i][:60])}\n"
                        f"  Adds:    {repr(lines[i+1][:60])}\n"
                        f"\n❌ These lines are identical! This creates a corrupt patch.\n"
                        f"💡 The AI generated a patch that removes and re-adds the same line.\n"
                        f"   Please re-run analysis to get a corrected patch."
                    )
            i += 1
        
        return True, ""
    
    def apply_patch(self, file_path: str, patch_content: str, file_hash: Optional[str] = None) -> bool:
        """Apply a unified diff patch to a file."""
        print(f"Applying patch to: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"ERROR: File not found: {file_path}")
            return False
        
        # Always show patch content for debugging
        print(f"\n📝 Patch content from analysis:")
        print("=" * 60)
        print(patch_content)
        print("=" * 60)
        
        # Show first character of each line to help diagnose missing prefixes
        print(f"\n🔍 First character of each patch line (for diagnosis):")
        patch_lines = patch_content.split('\n')
        print(f"Total lines in patch: {len(patch_lines)}")
        for i, line in enumerate(patch_lines, 1):  # Show ALL lines
            if not line:
                print(f"  Line {i}: (empty line)")
            elif line.startswith('@@'):
                print(f"  Line {i}: @@ (hunk header)")
            else:
                first_char_repr = repr(line[0])
                print(f"  Line {i}: {first_char_repr} | {line[:40]}")
        
        if self.verbose:
            print(f"\n[DEBUG] Raw patch content (repr):")
            print(repr(patch_content))
        
        # Validate patch format before attempting to apply
        print("\n🔍 Validating patch format...")
        is_valid, error_msg = self._validate_patch_format(patch_content)
        if not is_valid:
            print(f"\n❌ PATCH FORMAT ERROR:")
            print(error_msg)
            print("\n💡 This patch was generated incorrectly by the AI.")
            print("   Please re-run the analysis to generate a new patch with correct format.")
            return False
        print("✓ Patch format is valid")
        
        # Create a proper unified diff with file headers
        # The patch should already be in unified diff format from analysis
        full_patch = patch_content
        
        # If patch doesn't have file headers, add them
        if not patch_content.startswith('---'):
            full_patch = f"--- a/{file_path}\n+++ b/{file_path}\n{patch_content}"
            print(f"\n📋 Full patch with headers:")
            print("=" * 60)
            print(full_patch)
            print("=" * 60)
        
        if self.verbose:
            print(f"[DEBUG] Full patch (repr):")
            print(repr(full_patch))
        
        # Write patch to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as tmp:
            tmp.write(full_patch)
            tmp_patch_file = tmp.name
        
        try:
            # Try to apply patch using git apply
            # Use --ignore-whitespace to be more forgiving with whitespace differences
            # Use --whitespace=fix to automatically fix whitespace issues
            result = subprocess.run(
                ['git', 'apply', '--ignore-whitespace', '--whitespace=fix', '--verbose', tmp_patch_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path) or '.'
            )
            
            if self.verbose:
                print(f"[DEBUG] git apply result:")
                print(f"  Return code: {result.returncode}")
                print(f"  Stdout: {result.stdout}")
                print(f"  Stderr: {result.stderr}")
            
            if result.returncode == 0:
                print(f"✓ Patch applied successfully to {file_path}")
                return True
            else:
                print(f"ERROR: Failed to apply patch to {file_path}")
                print(f"Git apply error: {result.stderr}")
                
                # Try to extract line number from error
                if "does not match" in result.stderr or "does not apply" in result.stderr:
                    print("\nThis usually means the code context has changed.")
                    print("Please re-run analysis to generate updated patches.")
                    
                    # Show what changed in the file
                    self._show_file_changes(file_path)
                
                return False
                
        except FileNotFoundError:
            print("ERROR: git command not found. Please ensure git is installed.")
            return False
        except Exception as e:
            print(f"ERROR: Exception while applying patch: {e}")
            return False
        finally:
            # Clean up temporary patch file
            try:
                os.unlink(tmp_patch_file)
            except:
                pass

   
def parse_issue_from_comment(comment_body: str) -> Optional[Dict[str, Any]]:
    """Parse issue details from a comment body."""
    import re
    
    # Try to extract from hidden JSON metadata
    json_match = re.search(r'<!-- ISSUE_DATA: (.+?) -->', comment_body, re.DOTALL)
    
    if not json_match:
        print("⚠️  No JSON metadata found in comment - cannot determine file path")
        return None
    
    try:
        metadata = json.loads(json_match.group(1))
        
        # Validate required fields
        if 'file' not in metadata:
            print("ERROR: Missing 'file' field in metadata")
            return None
        
        if 'patch' not in metadata:
            print("ERROR: Missing 'patch' field in metadata")
            print("This workflow requires analysis to generate unified diff patches.")
            return None
        
        return {
            'file': metadata['file'],
            'patch': metadata['patch'],
            'file_hash': metadata.get('file_hash'),
            'severity': metadata.get('severity', 'MEDIUM'),
            'category': metadata.get('category', 'logging'),
            'method': metadata.get('method', 'N/A'),
            'line': metadata.get('line', 0),
            'description': metadata.get('description', ''),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Failed to parse JSON metadata: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Apply suggested logs from review comment using patches')
    parser.add_argument('--pr-number', type=str, required=True)
    parser.add_argument('--repository', type=str, required=True)
    parser.add_argument('--comment-body', type=str,
                       help='Review comment body with hidden JSON metadata')
    parser.add_argument('--comment-body-file', type=str,
                       help='File containing review comment body')
    parser.add_argument('--comment-id', type=str)
    
    args = parser.parse_args()
    
    # Use GitHub Actions' native debug mode
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running apply-suggested-logs/main.py (patch-based) with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
    
    # Get comment body from file or argument
    if args.comment_body_file:
        if verbose:
            print(f"[DEBUG] Reading comment body from file: {args.comment_body_file}")
        with open(args.comment_body_file, 'r') as f:
            comment_body = f.read()
        if verbose:
            print(f"[DEBUG] Comment body length: {len(comment_body)} chars")
    elif args.comment_body:
        comment_body = args.comment_body
        if verbose:
            print(f"[DEBUG] Using comment body from argument: {len(comment_body)} chars")
    else:
        print("ERROR: Either --comment-body or --comment-body-file is required")
        return 1
    
    # Initialize applier
    applier = PatchApplier(verbose=verbose)
    
    # Parse issue from comment body
    print("Parsing issue from comment...")
    
    # Debug: Show the comment body structure
    print(f"\n🔍 DEBUG: Comment body info:")
    print(f"  Total length: {len(comment_body)} characters")
    print(f"  Contains ISSUE_DATA: {'ISSUE_DATA' in comment_body}")
    if 'ISSUE_DATA' in comment_body:
        import re
        json_match = re.search(r'<!-- ISSUE_DATA: (.+?) -->', comment_body, re.DOTALL)
        if json_match:
            raw_json = json_match.group(1)
            print(f"  JSON metadata length: {len(raw_json)} characters")
            print(f"\n📋 Full ISSUE_DATA JSON:")
            print("=" * 80)
            try:
                # Pretty print the JSON for readability
                parsed_json = json.loads(raw_json)
                print(json.dumps(parsed_json, indent=2))
            except:
                # If can't parse, just show raw
                print(raw_json)
            print("=" * 80)
    
    issue = parse_issue_from_comment(comment_body)
    
    if not issue:
        print("ERROR: Could not parse issue from comment")
        print("Make sure the comment includes hidden JSON metadata with 'patch' field: <!-- ISSUE_DATA: {...} -->")
        return 1
    
    if verbose:
        print(f"[DEBUG] Parsed issue: {json.dumps({k: v for k, v in issue.items() if k != 'patch'}, indent=2)}")
        print(f"[DEBUG] Patch present: {bool(issue.get('patch'))}")
    
    file_path = issue['file']
    patch_content = issue['patch']
    file_hash = issue.get('file_hash')
    
    # Validate and fix patch format if validation is available
    if PATCH_VALIDATION_AVAILABLE:
        if verbose:
            print(f"[DEBUG] Validating and fixing patch format...")
        original_patch = patch_content
        patch_content = normalize_patch_newlines(patch_content)
        patch_content = fix_patch_format(patch_content)
        if patch_content != original_patch:
            print(f"✓ Patch format corrected (newlines normalized, hunk headers fixed)")
        elif verbose:
            print(f"[DEBUG] Patch format already valid")
    
    # Debug: Show raw patch content to diagnose any corruption
    print(f"\n🔍 DEBUG: Raw patch content from JSON:")
    print(f"  Patch type: {type(patch_content)}")
    print(f"  Patch length: {len(patch_content)} characters")
    has_escaped_newlines = '\\n' in repr(patch_content)
    print(f"  Has \\n escape sequences: {has_escaped_newlines}")
    print(f"  Number of actual newlines: {patch_content.count(chr(10))}")
    print(f"\n  Raw patch (repr, first 300 chars):")
    print(f"  {repr(patch_content[:300])}")
    print(f"\n  Decoded patch (first 10 lines):")
    for i, line in enumerate(patch_content.split('\n')[:10], 1):
        print(f"    {i}: {repr(line[:60])}")
    
    print(f"\nApplying patch to {file_path}")
    if file_hash:
        print(f"✓ File hash from analysis: {file_hash[:16]}...")
    else:
        print("⚠️  No file hash in metadata - cannot verify file hasn't changed")
        print("   This comment was created before file hash tracking was added")
        print("   Proceeding anyway, but patch may fail if file changed")
    
    if applier.apply_patch(file_path, patch_content, file_hash):
        print(f"\n✓ Successfully applied patch to {file_path}")
        
        # Output commit message for the workflow to use
        commit_message = parsed_json.get('commit_message')
        
        # Debug: show what we got
        print(f"[DEBUG] commit_message key exists: {'commit_message' in parsed_json}")
        print(f"[DEBUG] commit_message value: {repr(parsed_json)}")
        print(f"[DEBUG] commit_message type: {type(parsed_json)}")
        
        if commit_message and commit_message.strip():
            # Set GitHub Actions output
            github_output = os.getenv('GITHUB_OUTPUT')
            if github_output:
                # Escape newlines and special characters for GitHub Actions output
                escaped_message = commit_message.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
                with open(github_output, 'a') as f:
                    f.write(f"commit_message={escaped_message}\n")
                print(f"✓ Commit message set as output: {commit_message}")
            else:
                print(f"⚠️  GITHUB_OUTPUT not available, commit message not set")
        else:
            print(f"⚠️  No commit_message in issue metadata or it's empty")
            if verbose:
                print(f"[DEBUG] Issue keys: {list(issue.keys())}")
        
        if verbose:
            print(f"[DEBUG] Successfully completed apply-suggested-logs/main.py")
        return 0
    else:
        print(f"\n✗ Failed to apply patch")
        return 1


if __name__ == '__main__':
    sys.exit(main())
