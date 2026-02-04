#!/usr/bin/env python3
"""Create monitor in GroundCover from YAML in parent comment, or post no-permission message."""

import os
import sys
from pathlib import Path

import argparse
import requests


def _log(msg: str, level: str = "INFO") -> None:
    """Print to stderr so it appears in CI logs; flush so output isn't buffered."""
    print(f"[{level}] {msg}", file=sys.stderr, flush=True)

# Ensure libs is on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
import github_api  # noqa: E402
from actions_env import add_common_pr_args, is_verbose, require_github_token  # noqa: E402
from code_block import extract_code_block  # noqa: E402

GROUNDCOVER_MONITORS_URL = "https://app.groundcover.com/monitors"


def _get_comment(github_token: str, repository: str, comment_id: int) -> dict:
    """Fetch a PR review comment by ID."""
    return github_api.get_pr_comment(github_token, repository, comment_id)


def _extract_yaml_from_comment_body(body: str) -> str:
    """Extract YAML from a comment body (```yaml ... ``` or ``` ... ``` block)."""
    return extract_code_block(body, "yaml")


def _post_comment(
    github_token: str, repository: str, pr_number: int, comment_id: int, body: str
) -> int:
    """Post a PR review comment as reply to comment_id. Returns the new comment ID."""
    resp = github_api.post_pr_review_comment(
        github_token, repository, pr_number, body, in_reply_to=comment_id
    )
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
        _log(f"Failed to get comment: {e}", "ERROR")
        _post_comment(
            github_token,
            repository,
            pr_number,
            comment_id_int,
            "Could not load the comment thread. Please try again.",
        )
        return 1

    in_reply_to_id = current.get("in_reply_to_id")
    _log(f"Comment {comment_id_int} in_reply_to_id={in_reply_to_id}")
    if not in_reply_to_id:
        _log("No parent comment (in_reply_to_id missing); posting no-preview message")
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
        _log(f"Failed to get parent comment: {e}", "ERROR")
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
    _log(f"Extracted YAML length: {len(yaml_str)} chars")
    if not yaml_str.strip():
        _log("No YAML in parent comment; posting no-YAML message")
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
        _log("GROUNDCOVER_API_KEY not set; posting no-permission message")
        _post_comment(github_token, repository, pr_number, comment_id_int, no_permission_body)
        return 0

    try:
        sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))
        from groundcover_client import GroundcoverClient

        client = GroundcoverClient()
        result = client.create_monitor_from_yaml(yaml_str)
        if verbose:
            _log(f"GroundCover API response: {result}", "DEBUG")

        monitor_url = GROUNDCOVER_MONITORS_URL
        if isinstance(result, dict):
            monitor_id = result.get("id") or result.get("monitorId")
            if monitor_id:
                monitor_url = f"{GROUNDCOVER_MONITORS_URL}?selectedEntities=[{{\"id\":\"{monitor_id}\",\"type\":\"monitor\"}}]"

        success_body = f"""Monitor created in GroundCover.

[View monitors in GroundCover]({monitor_url})

_Created by AI automation 🤖_"""
        _post_comment(github_token, repository, pr_number, comment_id_int, success_body)
        _log("Monitor created and success comment posted")
        return 0
    except Exception as e:
        _log(f"Monitor creation failed: {e}", "WARN")
        _post_comment(github_token, repository, pr_number, comment_id_int, no_permission_body)
        return 0


def main():
    _log("post_create_monitor_response.py started")
    parser = argparse.ArgumentParser(description="Create monitor in GroundCover or post manual instructions")
    add_common_pr_args(parser)
    args = parser.parse_args()
    _log(f"Args: pr_number={args.pr_number} repository={args.repository} comment_id={args.comment_id}")

    verbose = is_verbose()
    github_token = require_github_token()
    if not github_token:
        _log("GITHUB_TOKEN missing or invalid; exiting", "ERROR")
        return 1
    _log("GITHUB_TOKEN present; fetching comment and creating monitor")

    exit_code = run_create_monitor(
        github_token,
        args.repository,
        int(args.pr_number),
        args.comment_id,
        verbose=verbose,
    )
    _log(f"Exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log(f"Unhandled exception: {e}", "ERROR")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
