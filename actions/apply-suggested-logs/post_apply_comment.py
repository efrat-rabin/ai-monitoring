#!/usr/bin/env python3
"""Post success comment after applying logs"""

import os
import sys
import argparse
import json
import requests


def post_comment(github_token: str, repository: str, pr_number: int, comment_id: str = None, verbose: bool = False):
    """Post a comment on the PR as a reply to the processing comment."""
    owner, repo = repository.split("/")
    
    comment_body = "✅ **Done! Logging improvements applied successfully**\n\n"
    comment_body += "The changes have been committed to this PR. Please review the latest commit.\n\n"
    comment_body += "---\n\n"
    comment_body += "### 🚀 Next Level: Generate GroundCover Resources\n\n"
    comment_body += "**Monitors** track conditions and alert when thresholds are breached.  \n"
    comment_body += "**Dashboards** visualize metrics and trends over time.\n\n"
    comment_body += "Reply to this comment with:\n"
    comment_body += "```\n"
    comment_body += "/generate-alerts     # Create monitoring alerts\n"
    comment_body += "/generate-dashboard # Create visualization dashboard\n"
    comment_body += "```\n\n"
    comment_body += "_Applied by AI automation 🤖_"
    
    # Use PR review comments API to enable threaded replies
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    payload = {"body": comment_body}
    
    # Add in_reply_to field to make it a threaded reply
    if comment_id:
        payload["in_reply_to"] = int(comment_id)
    
    if verbose:
        print(f"[DEBUG] API Request: POST {url}")
        print(f"[DEBUG] Headers: Authorization=Bearer *****, Accept={headers['Accept']}")
        print(f"[DEBUG] Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if verbose:
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response size: {len(response.content)} bytes")
    
    response.raise_for_status()
    
    if verbose:
        response_data = response.json()
        print(f"[DEBUG] Comment posted successfully")
        print(f"[DEBUG] Comment ID: {response_data.get('id')}")
        print(f"[DEBUG] Comment URL: {response_data.get('html_url')}")
    
    print("✓ Comment posted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str)
    args = parser.parse_args()
    
    # Use GitHub Actions' native debug mode
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_apply_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    if verbose:
        print(f"[DEBUG] GITHUB_TOKEN present: True")
    
    try:
        post_comment(github_token, args.repository, int(args.pr_number), args.comment_id, verbose=verbose)
        if verbose:
            print(f"[DEBUG] Successfully completed post_apply_comment.py")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to post comment: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

