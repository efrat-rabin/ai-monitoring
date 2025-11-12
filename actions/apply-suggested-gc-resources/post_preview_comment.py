#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
import argparse
import json
import yaml
import requests


def find_matching_issue(comment_body: str, analysis_data: list, verbose: bool = False) -> dict:
    """Find issue in analysis results that matches the parent comment."""
    if verbose:
        print(f"[DEBUG] Searching for matching issue in {len(analysis_data)} file(s)")
    
    for file_data in analysis_data:
        file_path = file_data.get('file', '')
        issues = file_data.get('analysis', {}).get('issues', [])
        
        if verbose:
            print(f"[DEBUG] Checking file: {file_path} with {len(issues)} issues")
        
        for issue in issues:
            # Match based on file path, line number, description
            if file_path in comment_body:
                line = issue.get('line')
                description = issue.get('description', '')
                
                # Check if line number or description snippet is in comment
                if (line and str(line) in comment_body) or (description[:50] in comment_body):
                    if verbose:
                        print(f"[DEBUG] Found matching issue at {file_path}:{line}")
                    return issue
    
    if verbose:
        print(f"[DEBUG] No matching issue found")
    return None


def post_preview_comment(github_token: str, repository: str, pr_number: int, 
                        comment_id: str, mock_monitor_path: str,
                        parent_comment_id: str = None,
                        analysis_results_path: str = None,
                        verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-alerts comment."""
    owner, repo = repository.split("/")
    
    # Load mock monitor data
    with open(mock_monitor_path, 'r') as f:
        monitor = yaml.safe_load(f)
    
    title = monitor.get('title', 'Monitor')
    
    print(f"[INFO] Preparing monitor preview for: {title}")
    
    # Default image URL
    image_url = "https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main/assets/monitor_view.png"
    
    # Try to get issue-specific image from parent comment
    if parent_comment_id and analysis_results_path and os.path.exists(analysis_results_path):
        print(f"[INFO] Attempting to get issue-specific image")
        
        # Get parent comment
        parent_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{parent_comment_id}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }
        
        try:
            parent_response = requests.get(parent_url, headers=headers)
            if parent_response.status_code == 200:
                parent_comment = parent_response.json()
                parent_body = parent_comment.get('body', '')
                
                if verbose:
                    print(f"[DEBUG] Parent comment body preview: {parent_body[:200]}...")
                
                # Load analysis results
                with open(analysis_results_path, 'r') as f:
                    analysis_data = json.load(f)
                
                # Match parent comment to issue in analysis results
                matched_issue = find_matching_issue(parent_body, analysis_data, verbose)
                
                if matched_issue and 'monitor_image' in matched_issue:
                    monitor_image = matched_issue['monitor_image']
                    image_url = f"https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main{monitor_image}"
                    print(f"[INFO] Using issue-specific monitor image: {monitor_image}")
                else:
                    print(f"[INFO] No issue-specific image found, using default")
            else:
                print(f"[WARN] Failed to get parent comment: {parent_response.status_code}")
        except Exception as e:
            print(f"[WARN] Error getting issue-specific image: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
    else:
        if verbose:
            print(f"[DEBUG] Using default image (parent_comment_id={parent_comment_id}, analysis_results_exists={os.path.exists(analysis_results_path) if analysis_results_path else False})")
    
    print(f"[INFO] Using monitor preview image: {image_url}")
    
    # Create comment with image
    comment_body = f"""## 🔍 GroundCover Monitor Preview

![Monitor Preview]({image_url})

---

**Reply with `/create-monitor` to create it.**

_Preview by SRE AI Bot 🤖_"""
    
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
    parser.add_argument("--parent-comment-id", type=str, default=None,
                       help="Parent comment ID containing issue data")
    parser.add_argument("--mock-monitor", type=str, 
                       default="actions/apply-suggested-gc-resources/mock-monitor.yaml")
    parser.add_argument("--analysis-results", type=str, default=None,
                       help="Path to analysis results JSON file")
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_preview_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Parent Comment ID: {args.parent_comment_id}")
        print(f"[DEBUG] Mock Monitor Path: {args.mock_monitor}")
        print(f"[DEBUG] Analysis Results Path: {args.analysis_results}")
    
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
            args.parent_comment_id,
            args.analysis_results,
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
