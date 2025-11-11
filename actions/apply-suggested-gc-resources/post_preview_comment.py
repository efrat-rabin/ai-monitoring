#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
import argparse
import json
import yaml
import requests
import shutil
import time
from generate_monitor_image import generate_monitor_image_sync


def post_preview_comment(github_token: str, repository: str, pr_number: int, 
                        comment_id: str, mock_monitor_path: str, workflow_repo_path: str = None,
                        verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-alerts comment."""
    owner, repo = repository.split("/")
    
    # Load mock monitor data
    with open(mock_monitor_path, 'r') as f:
        monitor = yaml.safe_load(f)
    
    title = monitor.get('title', 'Monitor')
    
    print(f"[INFO] Generating monitor preview image...")
    
    # Generate monitor preview image with timestamp to make it unique
    timestamp = int(time.time())
    temp_image_name = f'monitor-preview-{timestamp}.png'
    image_path = generate_monitor_image_sync(monitor, temp_image_name)
    
    print(f"[INFO] Image generated: {image_path}")
    
    # Get file size
    image_size = os.path.getsize(image_path)
    print(f"[INFO] Image size: {image_size} bytes")
    
    # Move image to workflow repo if path provided
    if workflow_repo_path:
        # Create preview-images directory if it doesn't exist
        preview_dir = os.path.join(workflow_repo_path, 'preview-images')
        os.makedirs(preview_dir, exist_ok=True)
        
        # Move image to the preview directory
        dest_path = os.path.join(preview_dir, temp_image_name)
        shutil.move(image_path, dest_path)
        
        print(f"[INFO] Image moved to: {dest_path}")
        
        # Construct GitHub raw URL using the customer's repository
        # Format: https://raw.githubusercontent.com/{owner}/{repo}/HEAD/preview-images/{filename}
        # Using HEAD so it works regardless of default branch name (main/master)
        image_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/preview-images/{temp_image_name}"
        
        print(f"[INFO] Image will be accessible at: {image_url}")
        print(f"[INFO] Image will be committed to: {owner}/{repo}")
        
        # Create comment with image
        comment_body = f"""## 🔍 GroundCover Monitor Preview

![Monitor Preview]({image_url})

---

**Reply with `/create-monitor` to create it.**

_Preview by AI automation 🤖_"""
        
        print(f"[INFO] Comment will contain image from GitHub repo")
        
    else:
        # Fallback to markdown if no workflow repo path provided
        print(f"[WARNING] No workflow repo path provided, using markdown fallback")
        
        description = monitor['display']['description']
        severity = monitor.get('severity', 'Unknown')
        monitor_type = monitor.get('measurementType', 'state').title()
        queries = monitor['model'].get('queries', [])
        query_expr = queries[0]['expression'] if queries else 'N/A'
        thresholds = monitor['model'].get('thresholds', [])
        threshold_value = thresholds[0]['values'][0] if thresholds else 0
        threshold_op = thresholds[0].get('operator', 'gt') if thresholds else 'gt'
        operator_symbol = {'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<=', 'eq': '=='}.get(threshold_op, '>')
        eval_interval = monitor['evaluationInterval']['interval']
        pending_for = monitor['evaluationInterval']['pendingFor']
        
        comment_body = f"""## 🔍 GroundCover Monitor Preview

### {title}
**🚨 Alerting** • Monitor type: {monitor_type} • Severity: **{severity}**

**Description**  
{description}

**Query**
```promql
{query_expr}
```

**Evaluation Settings**
• Threshold: `{operator_symbol} {threshold_value}`  
• Evaluation Interval: `{eval_interval}`  
• Pending For: `{pending_for}`

---

**Reply with `/create-monitor` to create it.**

_Preview by AI automation 🤖_"""
        
        # Clean up temp image since we're not using it
        if os.path.exists(image_path):
            os.remove(image_path)
    
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
    print(f"[INFO] Comment body length: {len(comment_body)} chars")
    
    if verbose:
        print(f"[DEBUG] Monitor: {title}")
        print(f"[DEBUG] Comment body preview: {comment_body[:200]}...")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"[INFO] Comment API response status: {response.status_code}")
    
    if verbose:
        print(f"[DEBUG] Response size: {len(response.content)} bytes")
    
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
    parser.add_argument("--workflow-repo-path", type=str, default=None,
                       help="Path to the workflow repo for committing image")
    args = parser.parse_args()
    
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_preview_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Mock Monitor Path: {args.mock_monitor}")
        print(f"[DEBUG] Workflow Repo Path: {args.workflow_repo_path}")
    
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
            args.workflow_repo_path,
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

