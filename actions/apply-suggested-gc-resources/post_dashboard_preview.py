#!/usr/bin/env python3
"""Post dashboard preview comment"""

import os
import sys
import argparse
import json
import re
import requests


def get_root_comment(github_token: str, repository: str, comment_id: int, verbose: bool = False) -> dict:
    """Walk up the thread to find the first (root) comment."""
    owner, repo = repository.split("/")
    current_id = comment_id
    visited = set()  # Prevent infinite loops
    
    print(f"[INFO] Walking up thread to find root comment, starting from comment #{current_id}")
    
    while current_id and current_id not in visited:
        visited.add(current_id)
        
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{current_id}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            comment = response.json()
            
            in_reply_to = comment.get('in_reply_to_id')
            
            if verbose:
                print(f"[DEBUG] Comment #{current_id}, in_reply_to_id={in_reply_to}")
            
            # If this comment has no parent, it's the root
            if not in_reply_to:
                print(f"[INFO] ✓ Found root comment: #{current_id}")
                return comment
            
            # Otherwise, move up to parent
            print(f"[INFO] Moving up: #{current_id} -> #{in_reply_to}")
            current_id = in_reply_to
            
        except Exception as e:
            print(f"[ERROR] Failed to get comment #{current_id}: {e}")
            return None
    
    print(f"[WARN] Could not find root comment (loop or error)")
    return None


def extract_issue_data_from_comment(comment_body: str, verbose: bool = False) -> dict:
    """Extract issue data from hidden JSON in comment."""
    json_match = re.search(r'<!-- ISSUE_DATA: (.+?) -->', comment_body, re.DOTALL)
    
    if not json_match:
        if verbose:
            print(f"[DEBUG] No ISSUE_DATA found in comment")
        return {}
    
    try:
        raw_json = json_match.group(1)
        issue_data = json.loads(raw_json)
        
        if verbose:
            print(f"[DEBUG] Extracted issue data with keys: {list(issue_data.keys())}")
        
        return issue_data
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse issue JSON: {e}")
        return {}


def post_dashboard_preview(github_token: str, repository: str, pr_number: int, 
                          comment_id: str, verbose: bool = False):
    """Post a dashboard preview comment as reply to /generate-dashboard comment."""
    owner, repo = repository.split("/")
    
    print(f"[INFO] Preparing dashboard preview")
    
    # Default dashboard image URL
    image_url = "https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main/assets/default.png"
    
    # Walk up thread to find root comment
    root_comment = get_root_comment(github_token, repository, int(comment_id), verbose)
    
    if root_comment:
        root_body = root_comment.get('body', '')
        root_id = root_comment.get('id')
        
        print(f"[INFO] Root comment ID: {root_id}")
        print(f"[INFO] Root comment body preview: {root_body[:200]}...")
        
        # Extract issue data from root comment
        issue_data = extract_issue_data_from_comment(root_body, verbose)
        
        if issue_data:
            print(f"[INFO] ✓ Extracted issue data")
            print(f"[INFO] Issue severity: {issue_data.get('severity', 'N/A')}")
            print(f"[INFO] Issue line: {issue_data.get('line', 'N/A')}")
            print(f"[INFO] Issue monitor_image: {issue_data.get('monitor_image', 'N/A')}")
            print(f"[INFO] Issue dashboard_image: {issue_data.get('dashboard_image', 'N/A')}")
            
            # Get dashboard image from issue data
            dashboard_image = issue_data.get('dashboard_image', '')
            
            if dashboard_image:
                image_url = f"https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main{dashboard_image}"
                print(f"[INFO] ✓ Using issue-specific dashboard image: {dashboard_image}")
            else:
                print(f"[INFO] No dashboard_image in issue data, using default")
        else:
            print(f"[WARN] No issue data found in root comment, using default image")
    else:
        print(f"[WARN] Could not find root comment, using default image")
    
    print(f"[INFO] Final dashboard preview image: {image_url}")
    
    # Create comment with image
    comment_body = f"""## 📊 GroundCover Dashboard Preview

![Dashboard Preview]({image_url})

---

**Reply with `/create-dashboard` to create it.**

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
        print(f"[DEBUG] Comment body length: {len(comment_body)} chars")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"[INFO] Comment API response status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"[ERROR] Comment posting failed!")
        print(f"[ERROR] Response: {response.text}")
    
    response.raise_for_status()
    
    if verbose:
        response_data = response.json()
        print(f"[DEBUG] Dashboard preview comment posted successfully")
        print(f"[DEBUG] Comment ID: {response_data.get('id')}")
        print(f"[DEBUG] Comment URL: {response_data.get('html_url')}")
    
    print("✓ Dashboard preview comment posted")
    return response.json().get('id')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_dashboard_preview.py with verbose mode")
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
        post_dashboard_preview(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id,
            verbose=verbose
        )
        return 0
    except Exception as e:
        print(f"ERROR: Failed to post dashboard preview: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
