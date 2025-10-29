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
    """Check if any comment contains /apply-logs trigger and extract the parent comment."""
    for comment in comments:
        body = comment.get('body', '').strip().lower()
        
        if '/apply-logs' in body:
            # Find the parent comment (the one being replied to)
            # Look for the comment that contains the issue details
            parent_id = comment.get('in_reply_to_id')
            
            if parent_id:
                # Find the parent comment
                for parent_comment in comments:
                    if parent_comment.get('id') == parent_id:
                        return {
                            'trigger_comment': comment,
                            'parent_comment': parent_comment
                        }
            
            # If no parent, the comment itself might contain the issue
            if '## 🤖 Logging Suggestion' in comment.get('body', ''):
                return {
                    'trigger_comment': comment,
                    'parent_comment': comment
                }
    
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
    trigger_data = check_for_trigger(comments, analysis_comment_id)
    
    if trigger_data:
        trigger_comment = trigger_data['trigger_comment']
        parent_comment = trigger_data['parent_comment']
        
        result = {
            "triggered": True,
            "comment_id": trigger_comment.get('id'),
            "comment_author": trigger_comment.get('user', {}).get('login'),
            "parent_comment_id": parent_comment.get('id'),
            "parent_comment_body": parent_comment.get('body', '')
        }
    else:
        result = {
            "triggered": False,
            "comment_id": None,
            "comment_author": None,
            "parent_comment_id": None,
            "parent_comment_body": None
        }
    
    with open(args.output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if result['triggered']:
        print(f"✓ Found /apply-logs trigger in comment #{result['comment_id']}")
        print(f"  Parent comment: #{result['parent_comment_id']}")
    else:
        print("No /apply-logs trigger found")
    
    return 0 if result['triggered'] else 1


if __name__ == "__main__":
    sys.exit(main())

