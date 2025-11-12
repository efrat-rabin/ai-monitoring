#!/usr/bin/env python3
"""Post success response after /create-monitor command"""

import os
import sys
import argparse
import requests


def post_create_response(github_token: str, repository: str, pr_number: int, 
                         comment_id: str, verbose: bool = False):
    """Post a success message as reply to /create-monitor comment."""
    owner, repo = repository.split("/")
    
    # Hardcoded GroundCover monitor URL
    monitor_url = "https://app.groundcover.com/monitors?src_env=master&src_cluster=xm-platform-mt-master-eu&backendId=groundcover&tenantUUID=58b6c61c-6289-4323-bbcb-e295ca71f745&duration=Last+hour&selectedEntities=[{%22id%22:%22339aacda-dc57-4998-a92e-da99aba7b9c1%22,%22type%22:%22monitor%22}]"
    
    print(f"[INFO] Posting monitor creation success message")
    
    comment_body = f"""✅ **Monitor created in GroundCover observability system**

[View Monitor in GroundCover]({monitor_url})

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
    
    print("✓ Monitor creation response posted")
    
    return response.json().get('id')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_create_monitor_response.py")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    try:
        post_create_response(
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

