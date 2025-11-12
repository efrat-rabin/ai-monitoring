#!/usr/bin/env python3
"""Post dashboard preview comment"""

import os
import sys
import argparse
import json
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


def post_dashboard_preview(github_token: str, repository: str, pr_number: int, 
                          comment_id: str,
                          parent_comment_id: str = None,
                          analysis_results_path: str = None,
                          verbose: bool = False):
    """Post a dashboard preview comment as reply to /generate-dashboard comment."""
    owner, repo = repository.split("/")
    
    print(f"[INFO] Preparing dashboard preview")
    
    # Default dashboard image URL
    image_url = "https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main/assets/monitor_dashboard.png"
    
    # Try to get issue-specific image from parent comment
    if parent_comment_id and analysis_results_path and os.path.exists(analysis_results_path):
        print(f"[INFO] Attempting to get issue-specific dashboard image")
        print(f"[INFO] Parent comment ID: {parent_comment_id}")
        print(f"[INFO] Analysis results path: {analysis_results_path}")
        
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
                
                print(f"[INFO] Parent comment body preview: {parent_body[:200]}...")
                
                # Load analysis results
                with open(analysis_results_path, 'r') as f:
                    analysis_data = json.load(f)
                
                print(f"[INFO] Loaded analysis data with {len(analysis_data)} file(s)")
                for idx, file_data in enumerate(analysis_data):
                    file_path = file_data.get('file', 'unknown')
                    issues_count = len(file_data.get('analysis', {}).get('issues', []))
                    print(f"[INFO] File {idx+1}: {file_path} with {issues_count} issue(s)")
                    
                    # Log image fields for each issue
                    for issue_idx, issue in enumerate(file_data.get('analysis', {}).get('issues', [])):
                        monitor_img = issue.get('monitor_image', 'N/A')
                        dashboard_img = issue.get('dashboard_image', 'N/A')
                        severity = issue.get('severity', 'N/A')
                        line = issue.get('line', 'N/A')
                        print(f"[INFO]   Issue {issue_idx+1} (line {line}, {severity}): monitor_image={monitor_img}, dashboard_image={dashboard_img}")
                
                # Match parent comment to issue in analysis results
                matched_issue = find_matching_issue(parent_body, analysis_data, verbose)
                
                if matched_issue:
                    print(f"[INFO] ✓ Matched issue found!")
                    print(f"[INFO] Matched issue line: {matched_issue.get('line', 'N/A')}")
                    print(f"[INFO] Matched issue severity: {matched_issue.get('severity', 'N/A')}")
                    print(f"[INFO] Matched issue monitor_image: {matched_issue.get('monitor_image', 'N/A')}")
                    print(f"[INFO] Matched issue dashboard_image: {matched_issue.get('dashboard_image', 'N/A')}")
                    
                    if 'dashboard_image' in matched_issue:
                        dashboard_image = matched_issue['dashboard_image']
                        image_url = f"https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main{dashboard_image}"
                        print(f"[INFO] ✓ Using issue-specific dashboard image: {dashboard_image}")
                    else:
                        print(f"[WARN] Matched issue has no dashboard_image field, using default")
                else:
                    print(f"[WARN] No matching issue found, using default image")
            else:
                print(f"[WARN] Failed to get parent comment: {parent_response.status_code}")
        except Exception as e:
            print(f"[ERROR] Error getting issue-specific image: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[INFO] Using default image - parent_comment_id={parent_comment_id}, analysis_results_path={analysis_results_path}, exists={os.path.exists(analysis_results_path) if analysis_results_path else False}")
    
    print(f"[INFO] Using dashboard preview image: {image_url}")
    
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
    parser.add_argument("--parent-comment-id", type=str, default=None,
                       help="Parent comment ID containing issue data")
    parser.add_argument("--analysis-results", type=str, default=None,
                       help="Path to analysis results JSON file")
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_dashboard_preview.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Parent Comment ID: {args.parent_comment_id}")
        print(f"[DEBUG] Analysis Results Path: {args.analysis_results}")
    
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
            args.parent_comment_id,
            args.analysis_results,
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
