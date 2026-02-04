#!/usr/bin/env python3
"""Post dashboard preview comment"""

import os
import sys
from pathlib import Path

import argparse
import requests

# Ensure libs and same dir are on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import github_api  # noqa: E402
from actions_env import add_common_pr_args, is_verbose, require_github_token  # noqa: E402
from github_comment_utils import extract_issue_data_from_comment, get_root_comment  # noqa: E402


def post_dashboard_preview(github_token: str, repository: str, pr_number: int,
                           comment_id: str, verbose: bool = False):
    """Post a dashboard preview comment as reply to /generate-dashboard comment."""
    print("[INFO] Preparing dashboard preview")

    # Default dashboard image URL
    image_url = "https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main/assets/default.png"

    # Walk up thread to find root comment
    root_comment = get_root_comment(github_token, repository, int(comment_id), verbose)

    if root_comment:
        root_body = root_comment.get("body", "")
        root_id = root_comment.get("id")

        print(f"[INFO] Root comment ID: {root_id}")
        print(f"[INFO] Root comment body preview: {root_body[:200]}...")

        # Extract issue data from root comment
        issue_data = extract_issue_data_from_comment(root_body, verbose)

        if issue_data:
            print("[INFO] ✓ Extracted issue data")
            print(f"[INFO] Issue severity: {issue_data.get('severity', 'N/A')}")
            print(f"[INFO] Issue line: {issue_data.get('line', 'N/A')}")
            print(f"[INFO] Issue monitor_image: {issue_data.get('monitor_image', 'N/A')}")
            print(f"[INFO] Issue dashboard_image: {issue_data.get('dashboard_image', 'N/A')}")

            # Get dashboard image from issue data
            dashboard_image = issue_data.get("dashboard_image", "")

            if dashboard_image:
                image_url = f"https://raw.githubusercontent.com/efrat-rabin/ai-monitoring/main{dashboard_image}"
                print(f"[INFO] ✓ Using issue-specific dashboard image: {dashboard_image}")
            else:
                print("[INFO] No dashboard_image in issue data, using default")
        else:
            print("[WARN] No issue data found in root comment, using default image")
    else:
        print("[WARN] Could not find root comment, using default image")

    print(f"[INFO] Final dashboard preview image: {image_url}")

    # Create comment with image
    comment_body = f"""## 📊 GroundCover Dashboard Preview

![Dashboard Preview]({image_url})

---

**Reply with `/create-dashboard` to create it.**

_Preview by AI automation 🤖_"""

    print(f"[INFO] Posting comment to PR #{pr_number}")
    print(f"[INFO] Comment will be reply to comment ID: {comment_id}")
    if verbose:
        print(f"[DEBUG] Comment body length: {len(comment_body)} chars")

    comment_id_out = github_api.post_pr_review_comment_and_return_id(
        github_token,
        repository,
        pr_number,
        comment_body,
        in_reply_to=int(comment_id),
        verbose=verbose,
    )
    print("✓ Dashboard preview comment posted")
    return comment_id_out


def main():
    parser = argparse.ArgumentParser()
    add_common_pr_args(parser)
    args = parser.parse_args()

    verbose = is_verbose()
    if verbose:
        print("[DEBUG] Running post_dashboard_preview.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")

    github_token = require_github_token()
    if not github_token:
        return 1
    if verbose:
        print("[DEBUG] GITHUB_TOKEN present: True")
    
    try:
        post_dashboard_preview(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id,
            verbose=verbose
        )
        return 0
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP Error posting dashboard preview: {e}")
        print(f"ERROR: Status code: {e.response.status_code if e.response else 'N/A'}")
        if e.response:
            print(f"ERROR: Response body: {e.response.text}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"ERROR: Failed to post dashboard preview: {e}")
        print(f"ERROR: Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
