"""Shared bot comment state: analyzed, applied, gc-integrated.

Can be run as a script:
  check: validate parent comment state for /apply-logs (writes apply-trigger.json, sets GITHUB_OUTPUT)
  set:  set a comment's state (PATCH body with STATUS marker)
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Optional

import requests

# Marker in comment body: <!-- STATUS: <state> -->
STATUS_RE = re.compile(r"<!--\s*STATUS:\s*(\w+)\s*-->")

COMMENT_STATES = ("analyzed", "applied", "gc-integrated")
STATE_ANALYZED = "analyzed"
STATE_APPLIED = "applied"
STATE_GC_INTEGRATED = "gc-integrated"

# Visible line in analysis comment (used by analyze-pr-code/post_comment.py and here)
APPLY_LOGS_LINE = "Reply with `/apply-logs` to apply this change automatically."
APPLIED_LINE = "✅ Applied"


def status_marker(state: str) -> str:
    """Return the hidden HTML marker for a state, e.g. '<!-- STATUS: analyzed -->'."""
    if state not in COMMENT_STATES:
        raise ValueError(f"Invalid state {state!r}; must be one of {COMMENT_STATES}")
    return f"<!-- STATUS: {state} -->"


def get_comment_state(body: str) -> Optional[str]:
    """Parse comment body for STATUS marker. Returns None when no marker (treated as analyzed)."""
    if not body:
        return None
    m = STATUS_RE.search(body)
    if not m:
        return None
    state = m.group(1).strip().lower()
    return state if state in COMMENT_STATES else None


def is_analyzed_state(body: str) -> bool:
    """True if comment is in analyzed state (or has no STATUS marker, for backward compat)."""
    s = get_comment_state(body)
    return s is None or s == STATE_ANALYZED


def set_comment_state_body(body: str, new_state: str) -> str:
    """
    Set or replace STATUS marker in body. Optionally update visible text by state.
    new_state must be in COMMENT_STATES.
    """
    if new_state not in COMMENT_STATES:
        raise ValueError(f"Invalid state {new_state!r}; must be one of {COMMENT_STATES}")
    new_body = body
    # Replace existing STATUS marker if present
    if STATUS_RE.search(new_body):
        new_body = STATUS_RE.sub(status_marker(new_state), new_body, count=1)
    else:
        new_body = new_body.rstrip() + "\n\n" + status_marker(new_state) + "\n"
    # State-specific visible text
    if new_state == STATE_APPLIED and APPLY_LOGS_LINE in new_body:
        new_body = new_body.replace(
            APPLY_LOGS_LINE + "\n\n",
            APPLIED_LINE + "\n\n",
            1,
        )
        if APPLY_LOGS_LINE in new_body:
            new_body = new_body.replace(APPLY_LOGS_LINE, APPLIED_LINE, 1)
    return new_body


# --- CLI (check / set) ---


def _set_github_output(key: str, value: str) -> None:
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")


def _get_comment(github_token: str, repository: str, comment_id: int) -> Any:
    owner, repo = repository.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _patch_comment(github_token: str, repository: str, comment_id: int, body: str) -> None:
    owner, repo = repository.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
    resp = requests.patch(url, headers=headers, json={"body": body})
    resp.raise_for_status()


def _cmd_check(args: argparse.Namespace) -> int:
    verbose = os.getenv("ACTIONS_STEP_DEBUG", "false").lower() in ("true", "1")
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        _set_github_output("should_apply", "false")
        return 1
    try:
        parent = _get_comment(github_token, args.repository, int(args.in_reply_to_id))
        trigger = _get_comment(github_token, args.repository, int(args.comment_id))
    except Exception as e:
        logger.error('github_api_comments_fetch_failed', {'repository': args.repository, 'parent_comment_id': args.in_reply_to_id, 'trigger_comment_id': args.comment_id, 'error': str(e), 'error_type': type(e).__name__})
        if verbose:
            import traceback
            traceback.print_exc()
        _set_github_output("should_apply", "false")
        return 1
    state = get_comment_state(parent.get("body", ""))
    if state in (STATE_APPLIED, STATE_GC_INTEGRATED):
        print(f"Parent comment state is {state!r}; only analyzed comments can be applied. Skipping.")
        _set_github_output("should_apply", "false")
        return 0
    result = {
        "triggered": True,
        "comment_id": trigger.get("id"),
        "comment_author": trigger.get("user", {}).get("login"),
        "parent_comment_id": parent.get("id"),
        "parent_comment_body": parent.get("body", ""),
    }
    with open(args.output_file, "w") as f:
        json.dump(result, f, indent=2)
    _set_github_output("should_apply", "true")
    _set_github_output("comment_id", str(result["comment_id"]))
    _set_github_output("parent_comment_id", str(result["parent_comment_id"]))
    print(f"✓ Got parent comment #{result['parent_comment_id']} (state={state or STATE_ANALYZED})")
    print(f"  Triggered by comment #{result['comment_id']} from {result['comment_author']}")
    return 0


def _cmd_set(args: argparse.Namespace) -> int:
    verbose = os.getenv("ACTIONS_STEP_DEBUG", "false").lower() in ("true", "1")
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    comment_id = int(args.parent_comment_id.strip())
    try:
        comment = _get_comment(github_token, args.repository, comment_id)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Failed to get comment: {e}")
        if e.response is not None:
            print(f"ERROR: Response: {e.response.text[:500]}")
        return 1
    body = comment.get("body") or ""
    current = get_comment_state(body)
    if current == args.state:
        if verbose:
            print(f"[DEBUG] Comment already in state {args.state!r}; skipping PATCH")
        print(f"✓ Comment already in state {args.state!r}")
        return 0
    new_body = set_comment_state_body(body, args.state)
    try:
        _patch_comment(github_token, args.repository, comment_id, new_body)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Failed to update comment: {e}")
        if e.response is not None:
            print(f"ERROR: Response: {e.response.text[:500]}")
        return 1
    print(f"✓ Set comment #{comment_id} state to {args.state!r}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bot comment state: check (for apply trigger) or set.")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    check_p = subparsers.add_parser("check", help="Check parent comment state; only allow apply when analyzed")
    check_p.add_argument("--pr-number", type=str, required=True)
    check_p.add_argument("--repository", type=str, required=True)
    check_p.add_argument("--comment-id", type=str, required=True, help="Comment that triggered the workflow")
    check_p.add_argument("--in-reply-to-id", type=str, required=True, help="Parent comment ID")
    check_p.add_argument("--output-file", type=str, default="apply-trigger.json")
    check_p.set_defaults(func=_cmd_check)

    set_p = subparsers.add_parser("set", help=f"Set a comment's state ({', '.join(COMMENT_STATES)})")
    set_p.add_argument("--repository", type=str, required=True)
    set_p.add_argument("--parent-comment-id", type=str, required=True)
    set_p.add_argument("--state", type=str, required=True, choices=COMMENT_STATES)
    set_p.set_defaults(func=_cmd_set)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
# test_pr_workflow line 1
# test_pr_workflow line 2
# test_pr_workflow line 3
