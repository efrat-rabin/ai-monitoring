#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
import argparse
import json
import yaml
import requests


def post_preview_comment(github_token: str, repository: str, pr_number: int, 
                        comment_id: str, mock_monitor_path: str, verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-alerts comment."""
    owner, repo = repository.split("/")
    
    # Load mock monitor data
    with open(mock_monitor_path, 'r') as f:
        monitor = yaml.safe_load(f)
    
    # Extract monitor details
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
    
    # Build HTML comment (GroundCover style)
    comment_body = f"""<div style="border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; background: #ffffff;">
  
  <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
    <h3 style="margin: 0; font-size: 18px; font-weight: 600;">{title}</h3>
    <span style="background: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">Alerting</span>
  </div>
  
  <div style="display: flex; gap: 16px; margin-bottom: 12px; font-size: 14px; color: #586069;">
    <span><strong>Monitor type:</strong> {monitor_type}</span>
    <span><strong>Severity:</strong> {severity}</span>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #24292e;">Description</h4>
    <p style="margin: 0; color: #586069; font-size: 14px;">{description}</p>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #24292e;">Query</h4>
    <pre style="background: #f6f8fa; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; margin: 0;"><code>{query_expr}</code></pre>
  </div>
  
  <div style="background: #f6f8fa; padding: 12px; border-radius: 4px; font-size: 13px;">
    <div style="margin-bottom: 4px;"><strong>Threshold:</strong> {operator_symbol} {threshold_value}</div>
    <div style="margin-bottom: 4px;"><strong>Evaluation Interval:</strong> {eval_interval}</div>
    <div><strong>Pending For:</strong> {pending_for}</div>
  </div>
  
  <hr style="margin: 16px 0; border: none; border-top: 1px solid #e1e4e8;">
  
  <div style="text-align: center; color: #586069; font-size: 14px;">
    Reply with <code>/create-monitor</code> to create it.
  </div>
  
</div>

<p style="margin-top: 8px; font-size: 12px; color: #6a737d; font-style: italic;">Preview by AI automation 🤖</p>"""
    
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
        print(f"[DEBUG] Posting preview comment")
        print(f"[DEBUG] Monitor: {title}")
        print(f"[DEBUG] Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if verbose:
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response size: {len(response.content)} bytes")
    
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

