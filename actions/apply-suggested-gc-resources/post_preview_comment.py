#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
import argparse
import json
import yaml
import requests
import base64
from generate_monitor_image import generate_monitor_image_sync


def post_preview_comment(github_token: str, repository: str, pr_number: int, 
                        comment_id: str, mock_monitor_path: str, verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-alerts comment."""
    owner, repo = repository.split("/")
    
    # Load mock monitor data
    with open(mock_monitor_path, 'r') as f:
        monitor = yaml.safe_load(f)
    
    if verbose:
        print(f"[DEBUG] Generating monitor preview image...")
    
    # Generate monitor preview image
    image_path = generate_monitor_image_sync(monitor, 'monitor-preview.png')
    
    if verbose:
        print(f"[DEBUG] Image generated: {image_path}")
    
    # Read image and encode as base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    print(f"[INFO] Image size: {len(image_data)} bytes, base64 length: {len(image_base64)} chars")
    
    if verbose:
        print(f"[DEBUG] Creating GitHub Gist with image...")
    
    # Create a GitHub Gist with the image
    gist_url = "https://api.github.com/gists"
    gist_headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    title = monitor.get('title', 'Monitor')
    gist_payload = {
        "description": f"GroundCover Monitor Preview - {title}",
        "public": True,
        "files": {
            "monitor-preview.png": {
                "content": image_base64
            }
        }
    }
    
    if verbose:
        print(f"[DEBUG] Gist payload structure: public={gist_payload['public']}, files={list(gist_payload['files'].keys())}")
    
    print(f"[INFO] Creating GitHub Gist...")
    
    # Create the gist
    gist_response = requests.post(gist_url, headers=gist_headers, json=gist_payload)
    
    print(f"[INFO] Gist API response status: {gist_response.status_code}")
    
    if verbose:
        print(f"[DEBUG] Gist response headers: {dict(gist_response.headers)}")
    
    if gist_response.status_code != 201:
        # Fallback to markdown if gist creation fails
        print(f"[ERROR] Gist creation failed with status {gist_response.status_code}")
        print(f"[ERROR] Response body: {gist_response.text}")
        
        if verbose:
            print(f"[DEBUG] Falling back to markdown format")
        
        # Use simple markdown format as fallback
        title = monitor.get('title', 'Monitor')
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
    else:
        # Gist created successfully - get the raw URL
        print(f"[INFO] Gist created successfully!")
        
        gist_data = gist_response.json()
        
        if verbose:
            print(f"[DEBUG] Gist response keys: {list(gist_data.keys())}")
            print(f"[DEBUG] Gist files: {list(gist_data.get('files', {}).keys())}")
        
        print(f"[INFO] Gist ID: {gist_data.get('id')}")
        print(f"[INFO] Gist URL: {gist_data.get('html_url')}")
        
        image_url = gist_data['files']['monitor-preview.png']['raw_url']
        
        print(f"[INFO] Image raw URL: {image_url}")
        
        if verbose:
            print(f"[DEBUG] Full file data: {gist_data['files']['monitor-preview.png'].keys()}")
        
        # Create comment with gist image
        comment_body = f"""## 🔍 GroundCover Monitor Preview

![Monitor Preview]({image_url})

---

**Reply with `/create-monitor` to create it.**

_Preview by AI automation 🤖_"""
        
        print(f"[INFO] Comment will contain image from Gist")
    
    # Clean up image file
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

