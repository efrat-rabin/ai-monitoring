#!/usr/bin/env python3
"""Get parent review comment for /apply-logs trigger"""

import os
import sys
import argparse
import json
import requests


def get_comment_by_id(github_token: str, repository: str, pr_number: int, comment_id: int, verbose: bool = False):
    """Get a specific review comment by ID."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    if verbose:
        print(f"[DEBUG] API Request: GET {url}")
        print(f"[DEBUG] Headers: Authorization=Bearer *****, Accept={headers['Accept']}")
    
    response = requests.get(url, headers=headers)
    
    if verbose:
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response size: {len(response.content)} bytes")
    
    response.raise_for_status()
    data = response.json()
    
    if verbose:
        print(f"[DEBUG] Comment data keys: {list(data.keys())}")
        print(f"[DEBUG] Comment ID: {data.get('id')}")
        print(f"[DEBUG] Comment author: {data.get('user', {}).get('login')}")
        print(f"[DEBUG] Body length: {len(data.get('body', ''))} chars")
    
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True, 
                       help="The comment that triggered the workflow")
    parser.add_argument("--in-reply-to-id", type=str, required=True,
                       help="The parent comment ID (from GitHub event)")
    parser.add_argument("--output-file", type=str, default="apply-trigger.json")
    args = parser.parse_args()
    
    # Use GitHub Actions' native debug mode
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running check_apply_trigger.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Trigger comment ID: {args.comment_id}")
        print(f"[DEBUG] Parent comment ID: {args.in_reply_to_id}")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    # Get the parent comment directly by ID
    print(f"Getting parent comment #{args.in_reply_to_id}")
    try:
        parent_comment = get_comment_by_id(github_token, args.repository, int(args.pr_number), int(args.in_reply_to_id), verbose=verbose)
        trigger_comment = get_comment_by_id(github_token, args.repository, int(args.pr_number), int(args.comment_id), verbose=verbose)
    except Exception as e:
        print(f"ERROR: Failed to get comments: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    # Write result
    result = {
        "triggered": True,
        "comment_id": trigger_comment.get('id'),
        "comment_author": trigger_comment.get('user', {}).get('login'),
        "parent_comment_id": parent_comment.get('id'),
        "parent_comment_body": parent_comment.get('body', '')
    }
    
    if verbose:
        print(f"[DEBUG] Writing result to {args.output_file}")
        print(f"[DEBUG] Result keys: {list(result.keys())}")
        print(f"[DEBUG] Parent comment body preview: {result['parent_comment_body'][:200]}...")
    
    with open(args.output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ Got parent comment #{result['parent_comment_id']}")
    print(f"  Triggered by comment #{result['comment_id']} from {result['comment_author']}")
    
    if verbose:
        print(f"[DEBUG] Successfully completed check_apply_trigger.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

