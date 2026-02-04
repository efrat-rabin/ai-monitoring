#!/usr/bin/env python3
"""Post success response after /create-dashboard command"""

import os
import sys
from pathlib import Path

import argparse
import requests

# Ensure libs is on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
import github_api  # noqa: E402
from actions_env import add_common_pr_args, is_verbose, require_github_token  # noqa: E402


def post_create_dashboard_response(github_token: str, repository: str, pr_number: int,
                                   comment_id: str, verbose: bool = False):
    """Post a success message as reply to /create-dashboard comment."""
    # Hardcoded GroundCover dashboard URL
    dashboard_url = "https://app.groundcover.com/grafana/d/entity-writer-kafka-consumer-env/e697dfa"

    print("[INFO] Posting dashboard creation success message")

    comment_body = f"""✅ **Dashboard created in GroundCover observability system**

[View Dashboard in GroundCover]({dashboard_url})

_Created by AI automation 🤖_"""

    if verbose:
        print(f"[DEBUG] Posting to PR #{pr_number}")
        print(f"[DEBUG] Reply to comment: {comment_id}")

    comment_id_out = github_api.post_pr_review_comment_and_return_id(
        github_token,
        repository,
        pr_number,
        comment_body,
        in_reply_to=int(comment_id),
        verbose=verbose,
    )
    print("✓ Dashboard creation response posted")
    return comment_id_out


def main():
    parser = argparse.ArgumentParser()
    add_common_pr_args(parser)
    args = parser.parse_args()

    verbose = is_verbose()
    if verbose:
        print("[DEBUG] Running post_create_dashboard_response.py")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")

    github_token = require_github_token()
    if not github_token:
        return 1
    
    try:
        post_create_dashboard_response(
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

