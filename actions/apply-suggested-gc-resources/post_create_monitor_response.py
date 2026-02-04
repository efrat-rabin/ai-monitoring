#!/usr/bin/env python3
"""Create monitor in GroundCover from YAML in parent comment, or post no-permission message."""

import os
import re
import sys
import argparse
import requests


GROUNDCOVER_MONITORS_URL = "https://app.groundcover.com/monitors"


def _get_comment(github_token: str, repository: str, comment_id: int) -> dict:
    """Fetch a PR review comment by ID."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _extract_yaml_from_comment_body(body: str) -> str:
    """Extract YAML from a comment body (```yaml ... ``` block)."""
    match = re.search(r"```yaml\s*\n(.*?)\n```", body, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)\n```", body, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _post_comment(
    github_token: str, repository: str, pr_number: int, comment_id: int, body: str
) -> int:
    """Post a PR review comment as reply to comment_id. Returns the new comment ID."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    payload = {"body": body, "in_reply_to": comment_id}
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def run_create_monitor(
    github_token: str,
    repository: str,
    pr_number: int,
    comment_id: int,
    verbose: bool = False,
) -> int:
    """
    Get YAML from parent comment, try to create monitor in GroundCover, post success or no-permission message.
    Returns 0 on success (comment posted), 1 on error.
    """
    comment_id_int = int(comment_id)
    owner, repo = repository.split("/")

    # Get the /create-monitor comment and its parent (the preview comment with YAML)
    try:
        current = _get_comment(github_token, repository, comment_id_int)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get comment: {e}")
        _post_comment(
            github_token,
            repository,
            pr_number,
            comment_id_int,
            "Could not load the comment thread. Please try again.",
        )
        return 1

    in_reply_to_id = current.get("in_reply_to_id")
    if not in_reply_to_id:
        _post_comment(
            github_token,
            repository,
            pr_number,
            comment_id_int,
            "No monitor preview found in this thread. Reply to a comment that contains a monitor YAML preview, then try `/create-monitor` again.",
        )
        return 0

    try:
        parent = _get_comment(github_token, repository, in_reply_to_id)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get parent comment: {e}")
        _post_comment(
            github_token,
            repository,
            pr_number,
            comment_id_int,
            "Could not load the preview comment. Please try again.",
        )
        return 1

    parent_body = parent.get("body", "")
    yaml_str = _extract_yaml_from_comment_body(parent_body)
    if not yaml_str.strip():
        _post_comment(
            github_token,
            repository,
            pr_number,
            comment_id_int,
            "No monitor YAML found in the thread. Reply to a monitor preview comment that contains YAML, then try `/create-monitor` again.",
        )
        return 0

    no_permission_body = f"""There is no permission to add this monitor automatically. Please do it manually: copy the YAML from the comment above and import it via the [GroundCover website]({GROUNDCOVER_MONITORS_URL}).

If you have API access, set `GROUNDCOVER_API_KEY` in this repo's secrets to enable automatic creation.

_Created by AI automation 🤖_"""

    api_key = os.getenv("GROUNDCOVER_API_KEY")
    if not api_key:
        print("[INFO] GROUNDCOVER_API_KEY not set; posting no-permission message")
        _post_comment(github_token, repository, pr_number, comment_id_int, no_permission_body)
        return 0

    try:
        sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))
        from groundcover_client import GroundcoverClient

        client = GroundcoverClient()
        result = client.create_monitor_from_yaml(yaml_str)
        if verbose:
            print(f"[DEBUG] GroundCover API response: {result}")

        monitor_url = GROUNDCOVER_MONITORS_URL
        if isinstance(result, dict):
            monitor_id = result.get("id") or result.get("monitorId")
            if monitor_id:
                monitor_url = f"{GROUNDCOVER_MONITORS_URL}?selectedEntities=[{{\"id\":\"{monitor_id}\",\"type\":\"monitor\"}}]"

        success_body = f"""Monitor created in GroundCover.

[View monitors in GroundCover]({monitor_url})

_Created by AI automation 🤖_"""
        _post_comment(github_token, repository, pr_number, comment_id_int, success_body)
        print("✓ Monitor created and success comment posted")
        return 0
    except Exception as e:
        print(f"[WARN] Monitor creation failed: {e}")
        _post_comment(github_token, repository, pr_number, comment_id_int, no_permission_body)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Create monitor in GroundCover or post manual instructions")
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
    args = parser.parse_args()

    verbose = os.getenv("ACTIONS_STEP_DEBUG", "false").lower() in ("true", "1")
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1

    return run_create_monitor(
        github_token,
        args.repository,
        int(args.pr_number),
        args.comment_id,
        verbose=verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
