#!/usr/bin/env python3
"""Post success comment after applying logs"""

import os
import sys
import argparse
import requests


def post_comment(github_token: str, repository: str, pr_number: int, comment_id: str = None):
    """Post a comment on the PR."""
    owner, repo = repository.split("/")
    
    comment_body = "✅ **Logging improvements applied!**\n\n"
    comment_body += "Please review the changes in the latest commit.\n\n"
    comment_body += "_Applied by AI automation 🤖_"
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    response = requests.post(url, headers=headers, json={"body": comment_body})
    response.raise_for_status()
    print("✓ Comment posted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str)
    args = parser.parse_args()
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    post_comment(github_token, args.repository, int(args.pr_number), args.comment_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

