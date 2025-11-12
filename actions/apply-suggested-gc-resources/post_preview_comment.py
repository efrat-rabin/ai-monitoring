#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
import argparse
import yaml
import requests


def post_preview_comment(github_token: str, repository: str, pr_number: int, 
                        comment_id: str, mock_monitor_path: str, verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-alerts comment."""
    owner, repo = repository.split("/")
    
    # Load mock monitor data
    with open(mock_monitor_path, 'r') as f:
        monitor = yaml.safe_load(f)
    
    title = monitor.get('title', 'Monitor')
    
    print(f"[INFO] Preparing monitor preview for: {title}")
    
    # Use static image from assets folder
    image_url = "https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main/assets/monitor_view.png"
    
    print(f"[INFO] Using static preview image from assets")
    
    # Create comment with static image
    comment_body = f"""## 🔍 GroundCover Monitor Preview

![Monitor Preview]({image_url})

---

**Reply with `/create-monitor` to create it.**

_Preview by AI automation 🤖_"""
    
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
    
    print(f"[INFO] Posting comment to PR #{pr_number}")
    print(f"[INFO] Comment will be reply to comment ID: {comment_id}")
    
    if verbose:
        print(f"[DEBUG] Monitor: {title}")
        print(f"[DEBUG] Comment body length: {len(comment_body)} chars")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"[INFO] Comment API response status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"[ERROR] Comment posting failed!")
        print(f"[ERROR] Response: {response.text}")
    
    response.raise_for_status()
    
    if verbose:
        response_data = response.json()
        print(f"[DEBUG] Preview comment posted successfully")
        print(f"[DEBUG] Comment ID: {response_data.get('id')}")
        print(f"[DEBUG] Comment URL: {response_data.get('html_url')}")
    
    print("✓ Monitor preview comment posted")
    return response.json().get('id')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
    parser.add_argument("--mock-monitor", type=str, 
                       default="actions/apply-suggested-gc-resources/mock-monitor.yaml")
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_preview_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Mock Monitor Path: {args.mock_monitor}")
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    if verbose:
        print(f"[DEBUG] GITHUB_TOKEN present: True")
    
    try:
        preview_comment_id = post_preview_comment(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id,
            args.mock_monitor,
            verbose=verbose
        )
        
        # Output for GitHub Actions
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"preview_comment_id={preview_comment_id}\n")
        
        if verbose:
            print(f"[DEBUG] Successfully completed post_preview_comment.py")
            print(f"[DEBUG] Preview comment ID: {preview_comment_id}")
        
        return 0
    except Exception as e:
        print(f"ERROR: Failed to post preview comment: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
