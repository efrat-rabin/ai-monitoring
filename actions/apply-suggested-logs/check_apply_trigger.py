#!/usr/bin/env python3
"""Check if /apply-logs trigger is present in PR comments"""

import os
import sys
import argparse
import json
import requests


def get_pr_comments(github_token: str, repository: str, pr_number: int):
    """Get comments on a PR."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def check_for_trigger(comments, analysis_comment_id=None):
    """Check if any comment contains /apply-logs trigger."""
    for comment in comments:
        body = comment.get('body', '').strip().lower()
        
        if '/apply-logs' in body:
            # If checking for replies, ensure it's after the analysis comment
            if analysis_comment_id and comment.get('id', 0) > analysis_comment_id:
                return comment
            elif not analysis_comment_id:
                return comment
    
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--analysis-comment-id", type=str)
    parser.add_argument("--output-file", type=str, default="apply-trigger.json")
    args = parser.parse_args()
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    comments = get_pr_comments(github_token, args.repository, int(args.pr_number))
    analysis_comment_id = int(args.analysis_comment_id) if args.analysis_comment_id else None
    trigger_comment = check_for_trigger(comments, analysis_comment_id)
    
    result = {
        "triggered": trigger_comment is not None,
        "comment_id": trigger_comment.get('id') if trigger_comment else None,
        "comment_author": trigger_comment.get('user', {}).get('login') if trigger_comment else None,
    }
    
    with open(args.output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if result['triggered']:
        print(f"✓ Found /apply-logs trigger in comment #{result['comment_id']}")
    else:
        print("No /apply-logs trigger found")
    
    return 0 if result['triggered'] else 1


if __name__ == "__main__":
    sys.exit(main())

