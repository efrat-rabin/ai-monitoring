"""Shared GitHub comment helpers for GC resources: get_root_comment, extract_issue_data_from_comment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure libs is on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
import github_api  # noqa: E402
from comment_parsing import extract_issue_data as _extract_issue_data  # noqa: E402


def get_root_comment(
    github_token: str, repository: str, comment_id: int, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    """Walk up the thread to find the first (root) comment."""
    current_id = comment_id
    visited = set()  # Prevent infinite loops

    print(f"[INFO] Walking up thread to find root comment, starting from comment #{current_id}")

    while current_id and current_id not in visited:
        visited.add(current_id)

        try:
            comment = github_api.get_pr_comment(github_token, repository, current_id)
            in_reply_to = comment.get("in_reply_to_id")

            if verbose:
                print(f"[DEBUG] Comment #{current_id}, in_reply_to_id={in_reply_to}")

            # If this comment has no parent, it's the root
            if not in_reply_to:
                print(f"[INFO] ✓ Found root comment: #{current_id}")
                return comment

            # Otherwise, move up to parent
            print(f"[INFO] Moving up: #{current_id} -> #{in_reply_to}")
            current_id = in_reply_to

        except Exception as e:
            print(f"[ERROR] Failed to get comment #{current_id}: {e}")
            return None

    print("[WARN] Could not find root comment (loop or error)")
    return None


def extract_issue_data_from_comment(comment_body: str, verbose: bool = False) -> Dict[str, Any]:
    """Extract issue data from hidden JSON in comment. Returns {} when not found."""
    result = _extract_issue_data(comment_body, verbose=verbose)
    return result if result is not None else {}
