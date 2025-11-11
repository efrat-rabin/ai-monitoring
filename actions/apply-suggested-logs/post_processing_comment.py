#!/usr/bin/env python3
"""Post immediate acknowledgement comment when /apply-logs is triggered"""

import os
import sys
import argparse
import json
import requests


def post_processing_comment(github_token: str, repository: str, pr_number: int, comment_id: str, verbose: bool = False):
    """Post a processing acknowledgement comment as reply to the trigger comment."""
    owner, repo = repository.split("/")
    
    # Post as a reply to the /apply-logs comment
    comment_body = "✅ **SRE bot is processing your request**\n\n"
    comment_body += "This may take up to one minute. Please wait...\n\n"
    comment_body += "_Processing by SRE AI Bot 🤖_"
    
    # Use PR review comments API to reply to the specific comment
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
        print(f"[DEBUG] API Request: POST {url}")
        print(f"[DEBUG] Headers: Authorization=Bearer *****, Accept={headers['Accept']}")
        print(f"[DEBUG] Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if verbose:
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response size: {len(response.content)} bytes")
    
    response.raise_for_status()
    
    if verbose:
        response_data = response.json()
        print(f"[DEBUG] Processing comment posted successfully")
        print(f"[DEBUG] Comment ID: {response_data.get('id')}")
        print(f"[DEBUG] Comment URL: {response_data.get('html_url')}")
    
    print("✓ Processing comment posted")
    return response.json().get('id')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True, 
                       help="The comment ID to reply to")
    args = parser.parse_args()
    
    # Use GitHub Actions' native debug mode
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running post_processing_comment.py with verbose mode")
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
        processing_comment_id = post_processing_comment(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id, 
            verbose=verbose
        )
        
        # Output for GitHub Actions
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"processing_comment_id={processing_comment_id}\n")
        
        if verbose:
            print(f"[DEBUG] Successfully completed post_processing_comment.py")
            print(f"[DEBUG] Processing comment ID: {processing_comment_id}")
        
        return 0
    except Exception as e:
        print(f"ERROR: Failed to post processing comment: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

