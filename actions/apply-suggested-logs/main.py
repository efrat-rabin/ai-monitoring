#!/usr/bin/env python3
"""
Apply Suggested Logs Action
"""

import os
import sys
import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

def parse_issue_from_comment(comment_body: str) -> Optional[Dict[str, Any]]:
    """Parse issue details from a comment body, including the fixed_content to apply."""
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
            'fixed_content': metadata.get('fixed_content', ''),
            'impact': metadata.get('impact', '')
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Failed to parse JSON metadata: {e}")
        return None


def apply_fixed_content(file_path: str, fixed_content: str, verbose: bool = False) -> bool:
    """Apply the fixed content directly to the file without calling AI."""
    print(f"Applying improvements to: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    if not fixed_content:
        print(f"❌ No fixed_content provided - cannot apply changes")
        return False
    
    # Read current file content for comparison
    with open(file_path, 'r') as f:
        original_content = f.read()
    
    if verbose:
        print(f"[DEBUG] Original file size: {len(original_content)} chars")
        print(f"[DEBUG] Fixed content size: {len(fixed_content)} chars")
    
    # Check if content is actually different
    if fixed_content == original_content:
        print(f"ℹ️  No changes needed for {file_path} (content is identical)")
        return False
    
    # Write the fixed content directly to the file
    try:
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        
        print(f"✅ Applied changes to {file_path}")
        if verbose:
            print(f"[DEBUG] Successfully wrote {len(fixed_content)} chars to {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to write file {file_path}: {e}")
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
        print(f"[DEBUG] Has fixed_content: {bool(issue.get('fixed_content'))}")
        if issue.get('fixed_content'):
            print(f"[DEBUG] Fixed content size: {len(issue['fixed_content'])} chars")
    
    file_path = issue.get('file')
    fixed_content = issue.get('fixed_content')
    
    if not file_path:
        print("ERROR: No file path found in issue metadata")
        return 1
    
    if not fixed_content:
        print("ERROR: No fixed_content found in issue metadata")
        print("The PR comment may have been created with an older version of the analyzer.")
        print("Please re-run the analysis to generate updated comments with fixed_content.")
        return 1
    
    print(f"Applying changes to {file_path}")
    
    if apply_fixed_content(file_path, fixed_content, verbose=verbose):
        print(f"\n✅ Successfully applied changes to {file_path}")
        if verbose:
            print(f"[DEBUG] Successfully completed apply-suggested-logs/main.py")
        return 0
    else:
        print(f"\n❌ Failed to apply changes")
        return 1


if __name__ == '__main__':
    sys.exit(main())

