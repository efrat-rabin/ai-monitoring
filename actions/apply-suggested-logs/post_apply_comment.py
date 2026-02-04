#!/usr/bin/env python3
"""Post success comment after applying logs"""

import os
import sys
from pathlib import Path

import argparse
import requests

# Ensure libs is on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
import github_api  # noqa: E402
from actions_env import is_verbose, require_github_token  # noqa: E402


def post_comment(github_token: str, repository: str, pr_number: int, comment_id: str = None, verbose: bool = False):
    """Post a comment on the PR as a reply to the processing comment."""
    comment_body = "✅ **Done! Logging improvements applied successfully**\n\n"
    comment_body += "The changes have been committed to this PR. Please review the latest commit.\n\n"
    comment_body += "---\n\n"
    comment_body += "### 🚀 Next Level: Generate GroundCover Resources\n\n"
    comment_body += "**Monitors** track conditions and alert when thresholds are breached.  \n"
    comment_body += "**Dashboards** visualize metrics and trends over time.\n\n"
    comment_body += "Reply to this comment with:\n"
    comment_body += "```\n"
    comment_body += "/generate-monitor    # Create monitoring alerts\n"
    comment_body += "/generate-dashboard # Create visualization dashboard\n"
    comment_body += "```\n\n"
    comment_body += "_Applied by SRE AI Bot 🤖_"

    in_reply_to = int(comment_id) if comment_id else None
    print(f"[INFO] Posting comment to PR #{pr_number}")
    if verbose:
        print("[DEBUG] Headers: Authorization=Bearer *****, Accept=application/vnd.github+json")

    github_api.post_pr_review_comment_and_return_id(
        github_token,
        repository,
        pr_number,
        comment_body,
        in_reply_to=in_reply_to,
        verbose=verbose,
    )
    print("✓ Comment posted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str)
    args = parser.parse_args()

    verbose = is_verbose()
    if verbose:
        print("[DEBUG] Running post_apply_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")

    github_token = require_github_token()
    if not github_token:
        return 1
    if verbose:
        print("[DEBUG] GITHUB_TOKEN present: True")
    
    try:
        post_comment(github_token, args.repository, int(args.pr_number), args.comment_id, verbose=verbose)
        if verbose:
            print(f"[DEBUG] Successfully completed post_apply_comment.py")
        return 0
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP Error posting comment: {e}")
        print(f"ERROR: Status code: {e.response.status_code if e.response else 'N/A'}")
        if e.response:
            print(f"ERROR: Response body: {e.response.text}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"ERROR: Failed to post comment: {e}")
        print(f"ERROR: Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

