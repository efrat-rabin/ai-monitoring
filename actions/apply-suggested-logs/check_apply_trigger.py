#!/usr/bin/env python3
"""Get parent review comment for /apply-logs trigger"""

import os
import sys
import argparse
import json
import requests


def get_comment_by_id(github_token: str, repository: str, pr_number: int, comment_id: int):
    """Get a specific review comment by ID."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


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
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    # Get the parent comment directly by ID
    print(f"Getting parent comment #{args.in_reply_to_id}")
    try:
        parent_comment = get_comment_by_id(github_token, args.repository, int(args.pr_number), int(args.in_reply_to_id))
        trigger_comment = get_comment_by_id(github_token, args.repository, int(args.pr_number), int(args.comment_id))
    except Exception as e:
        print(f"ERROR: Failed to get comments: {e}")
        return 1
    
    # Write result
    result = {
        "triggered": True,
        "comment_id": trigger_comment.get('id'),
        "comment_author": trigger_comment.get('user', {}).get('login'),
        "parent_comment_id": parent_comment.get('id'),
        "parent_comment_body": parent_comment.get('body', '')
    }
    
    with open(args.output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ Got parent comment #{result['parent_comment_id']}")
    print(f"  Triggered by comment #{result['comment_id']} from {result['comment_author']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

