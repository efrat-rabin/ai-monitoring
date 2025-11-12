#!/usr/bin/env python3
"""Post success response after /create-dashboard command"""

import os
import sys
import argparse
import requests


def post_create_dashboard_response(github_token: str, repository: str, pr_number: int, 
                                   comment_id: str, verbose: bool = False):
    """Post a success message as reply to /create-dashboard comment."""
    owner, repo = repository.split("/")
    
    # Hardcoded GroundCover dashboard URL
    dashboard_url = "https://app.groundcover.com/grafana/d/entity-writer-kafka-consumer-env/e697dfa"
    
    print(f"[INFO] Posting dashboard creation success message")
    
    comment_body = f"""✅ **Dashboard created in GroundCover observability system**

[View Dashboard in GroundCover]({dashboard_url})

_Created by AI automation 🤖_"""
    
    # Use PR review comments API
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    payload = {
        "body": comment_body,
        "in_reply_to": int(comment_id)
    }
    
    if verbose:
        print(f"[DEBUG] Posting to PR #{pr_number}")
        print(f"[DEBUG] Reply to comment: {comment_id}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"[INFO] Response status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"[ERROR] Failed to post comment: {response.text}")
    
    response.raise_for_status()
    
    if verbose:
        response_data = response.json()
        print(f"[DEBUG] Comment ID: {response_data.get('id')}")
        print(f"[DEBUG] Comment URL: {response_data.get('html_url')}")
    
    print("✓ Dashboard creation response posted")
    
    return response.json().get('id')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_create_dashboard_response.py")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    try:
        post_create_dashboard_response(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id,
            verbose=verbose
        )
        return 0
    except Exception as e:
        print(f"ERROR: Failed to post response: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

