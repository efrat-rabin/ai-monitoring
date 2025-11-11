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
    
    # Build HTML comment (GroundCover style - exact match)
    comment_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif; border: 1px solid #d0d7de; border-radius: 6px; padding: 20px; background: #ffffff; color: #1f2328;">
  
  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
    <h2 style="margin: 0; font-size: 20px; font-weight: 600; color: #1f2328;">{title}</h2>
    <span style="background: #d1242f; color: #ffffff; padding: 2px 10px; border-radius: 3px; font-size: 13px; font-weight: 500;">Alerting</span>
  </div>
  
  <div style="display: flex; gap: 24px; margin-bottom: 24px; font-size: 14px; color: #656d76;">
    <div><span style="font-weight: 400;">Monitor type:</span> <span style="color: #1f2328; font-weight: 400;">{monitor_type}</span></div>
    <div><span style="font-weight: 400;">Severity:</span> <span style="color: #1f2328; font-weight: 600;">{severity}</span></div>
  </div>
  
  <div style="margin-bottom: 24px;">
    <div style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #1f2328;">Description</div>
    <div style="font-size: 14px; color: #656d76; line-height: 1.5;">{description}</div>
  </div>
  
  <div style="margin-bottom: 24px;">
    <div style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #1f2328;">Query</div>
    <pre style="background: #f6f8fa; padding: 14px; border-radius: 6px; border: 1px solid #d0d7de; overflow-x: auto; font-size: 12px; font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; margin: 0; color: #1f2328; line-height: 1.6;"><code>{query_expr}</code></pre>
  </div>
  
  <div style="background: #f6f8fa; padding: 16px; border-radius: 6px; border: 1px solid #d0d7de; font-size: 14px; color: #1f2328;">
    <div style="margin-bottom: 6px;"><span style="font-weight: 600;">Threshold:</span> {operator_symbol} {threshold_value}</div>
    <div style="margin-bottom: 6px;"><span style="font-weight: 600;">Evaluation Interval:</span> {eval_interval}</div>
    <div><span style="font-weight: 600;">Pending For:</span> {pending_for}</div>
  </div>
  
  <hr style="margin: 20px 0; border: none; border-top: 1px solid #d0d7de;">
  
  <div style="text-align: center; color: #656d76; font-size: 14px;">
    Reply with <code style="background: #f6f8fa; padding: 3px 6px; border-radius: 3px; font-size: 12px; color: #1f2328; border: 1px solid #d0d7de;">/create-monitor</code> to create it.
  </div>
  
</div>

<p style="margin-top: 12px; font-size: 12px; color: #656d76; font-style: italic; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">Preview by AI automation 🤖</p>"""
    
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

