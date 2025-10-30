#!/usr/bin/env python3
"""
Apply Suggested Logs Action - Using Git Patch Format
"""

import os
import sys
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

def parse_issue_from_comment(comment_body: str) -> Optional[Dict[str, Any]]:
    """Parse issue details from a comment body, including the patch to apply."""
    # Try to extract from hidden JSON metadata
    json_match = re.search(r'<!-- ISSUE_DATA: (.+?) -->', comment_body, re.DOTALL)
    
    if not json_match:
        print("⚠️  No JSON metadata found in comment - cannot determine file path")
        return None
    
    try:
        metadata = json.loads(json_match.group(1))
        return {
            'file': metadata['file'],
            'severity': metadata.get('severity', 'MEDIUM'),
            'category': metadata.get('category', 'logging'),
            'method': metadata.get('method', 'N/A'),
            'line': metadata.get('line', 0),
            'description': metadata.get('description', ''),
            'recommendation': metadata.get('recommendation', ''),
            'patch': metadata.get('patch', ''),
            'impact': metadata.get('impact', '')
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Failed to parse JSON metadata: {e}")
        return None


def apply_patch(file_path: str, patch_content: str, verbose: bool = False) -> bool:
    """Apply a git patch to the specified file."""
    print(f"Applying patch to: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    if not patch_content:
        print(f"❌ No patch provided - cannot apply changes")
        return False
    
    # Ensure patch has proper newlines (JSON may have escaped them)
    # Replace literal \n with actual newlines if needed
    if '\\n' in patch_content and '\n' not in patch_content:
        patch_content = patch_content.replace('\\n', '\n')
        if verbose:
            print(f"[DEBUG] Unescaped newlines in patch")
    
    # Ensure patch ends with newline
    if not patch_content.endswith('\n'):
        patch_content += '\n'
    
    if verbose:
        print(f"[DEBUG] Patch content ({len(patch_content)} chars):")
        print(patch_content[:500])
        if len(patch_content) > 500:
            print("... (truncated)")
    
    # Write patch to temporary file
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            patch_file = f.name
            f.write(patch_content)
        
        if verbose:
            print(f"[DEBUG] Wrote patch to temp file: {patch_file}")
        
        # Try to apply the patch using git apply
        try:
            result = subprocess.run(
                ['git', 'apply', '--verbose', patch_file],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                print(f"✅ Successfully applied patch to {file_path}")
                if verbose and result.stdout:
                    print(f"[DEBUG] git apply output: {result.stdout}")
                return True
            else:
                print(f"❌ Failed to apply patch with git apply")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                
                # Try with patch command as fallback
                if verbose:
                    print(f"[DEBUG] Trying fallback with patch command...")
                
                result = subprocess.run(
                    ['patch', '-p1', '-i', patch_file],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    print(f"✅ Successfully applied patch to {file_path} (using patch command)")
                    if verbose and result.stdout:
                        print(f"[DEBUG] patch output: {result.stdout}")
                    return True
                else:
                    print(f"❌ Failed to apply patch with patch command")
                    if result.stderr:
                        print(f"Error: {result.stderr}")
                    
                    # Show the patch content for debugging
                    print(f"\n⚠️  Patch content that failed to apply:")
                    print("=" * 60)
                    print(patch_content)
                    print("=" * 60)
                    return False
        
        finally:
            # Clean up temp file
            if os.path.exists(patch_file):
                os.unlink(patch_file)
                if verbose:
                    print(f"[DEBUG] Cleaned up temp patch file")
    
    except Exception as e:
        print(f"❌ Exception while applying patch: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Apply suggested logs from review comment')
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
        print(f"[DEBUG] Running apply-suggested-logs/main.py with verbose mode")
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
    
    # Parse issue from comment body
    print("Parsing issue from comment...")
    issue = parse_issue_from_comment(comment_body)
    
    if not issue:
        print("ERROR: Could not parse issue from comment")
        print("Make sure the comment includes hidden JSON metadata: <!-- ISSUE_DATA: {...} -->")
        return 1
    
    if verbose:
        print(f"[DEBUG] Parsed issue for file: {issue.get('file')}")
        print(f"[DEBUG] Has patch: {bool(issue.get('patch'))}")
        if issue.get('patch'):
            print(f"[DEBUG] Patch size: {len(issue['patch'])} chars")
    
    file_path = issue.get('file')
    patch = issue.get('patch')
    
    if not file_path:
        print("ERROR: No file path found in issue metadata")
        return 1
    
    if not patch:
        print("ERROR: No patch found in issue metadata")
        print("The PR comment may have been created with an older version of the analyzer.")
        print("Please re-run the analysis to generate updated comments with patch data.")
        return 1
    
    print(f"Applying patch to {file_path}")
    
    if apply_patch(file_path, patch, verbose=verbose):
        print(f"\n✅ Successfully applied patch to {file_path}")
        if verbose:
            print(f"[DEBUG] Successfully completed apply-suggested-logs/main.py")
        return 0
    else:
        print(f"\n❌ Failed to apply patch")
        return 1


if __name__ == '__main__':
    sys.exit(main())

