#!/usr/bin/env python3
"""
Refresh downstream ISSUE_DATA patches after one /apply-logs is applied.

Behavior:
- Identify the applied parent analysis review comment (via comment body file or by ID).
- Extract its ISSUE_DATA to get (file, line).
- List all PR review comments, filter to those with ISSUE_DATA for the same file.
- Only refresh comments whose ISSUE_DATA.line is AFTER the applied line (line > applied_line).
- Recalculate a unified diff patch against current HEAD (Cursor CLI), validate via git apply --check,
  and PATCH-edit the existing review comment body to update only the hidden ISSUE_DATA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

# Add libs directory to path for CursorClient
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))
from cursor_client import CursorClient  # type: ignore

# Import patch validation utilities (best-effort)
sys.path.insert(0, str(Path(__file__).parent.parent / "analyze-pr-code"))
try:
    from validate_patch import normalize_patch_newlines, fix_patch_format, validate_patch_format  # type: ignore

    PATCH_VALIDATION_AVAILABLE = True
except Exception:
    PATCH_VALIDATION_AVAILABLE = False


ISSUE_DATA_RE = re.compile(r"<!--\s*ISSUE_DATA:\s*(.+?)\s*-->", re.DOTALL)


@dataclass(frozen=True)
class ReviewComment:
    id: int
    body: str
    path: Optional[str]
    user_login: Optional[str]

def is_bot_issue_comment(comment: ReviewComment) -> bool:
    """
    Best-effort guard: only edit bot-generated review comments.

    We require the hidden ISSUE_DATA block and at least one of:
    - the visible /apply-logs instruction line
    - the 🤖 marker used by our formatter
    - a bot author login (endswith "[bot]")
    """
    if "ISSUE_DATA" not in comment.body:
        return False
    if "Reply with `/apply-logs`" in comment.body:
        return True
    if comment.body.lstrip().startswith("**🤖"):
        return True
    if comment.user_login and comment.user_login.endswith("[bot]"):
        return True
    return False


def _verbose_enabled() -> bool:
    return os.getenv("ACTIONS_STEP_DEBUG", "false").lower() in ("true", "1")


def _log(msg: str) -> None:
    print(msg)


def _debug(msg: str) -> None:
    if _verbose_enabled():
        print(f"[DEBUG] {msg}")


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _split_owner_repo(repository: str) -> Tuple[str, str]:
    if "/" not in repository:
        raise ValueError(f"Invalid --repository (expected owner/repo): {repository}")
    owner, repo = repository.split("/", 1)
    return owner, repo


def _request_json(method: str, url: str, token: str, **kwargs) -> Any:
    headers = _github_headers(token)
    headers.update(kwargs.pop("headers", {}))
    resp = requests.request(method, url, headers=headers, **kwargs)
    if _verbose_enabled():
        _debug(f"{method} {url} -> {resp.status_code} ({len(resp.content)} bytes)")
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json()


def get_review_comment_by_id(token: str, repository: str, comment_id: int) -> ReviewComment:
    owner, repo = _split_owner_repo(repository)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    data = _request_json("GET", url, token)
    return ReviewComment(
        id=int(data.get("id")),
        body=data.get("body") or "",
        path=data.get("path"),
        user_login=(data.get("user") or {}).get("login"),
    )


def list_pr_review_comments(token: str, repository: str, pr_number: int) -> List[ReviewComment]:
    owner, repo = _split_owner_repo(repository)
    comments: List[ReviewComment] = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = _request_json("GET", url, token, params={"per_page": per_page, "page": page})
        if not isinstance(data, list):
            raise RuntimeError("Unexpected API response for PR comments (expected list)")
        if not data:
            break
        for item in data:
            comments.append(
                ReviewComment(
                    id=int(item.get("id")),
                    body=item.get("body") or "",
                    path=item.get("path"),
                    user_login=(item.get("user") or {}).get("login"),
                )
            )
        if len(data) < per_page:
            break
        page += 1

    return comments


def update_review_comment_body(token: str, repository: str, comment_id: int, new_body: str) -> None:
    owner, repo = _split_owner_repo(repository)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    _request_json("PATCH", url, token, json={"body": new_body})


def extract_issue_data(comment_body: str) -> Optional[Dict[str, Any]]:
    m = ISSUE_DATA_RE.search(comment_body)
    if not m:
        return None
    raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Sometimes JSON may contain leading/trailing whitespace/newlines; try stripping.
        try:
            return json.loads(raw.strip())
        except Exception:
            return None


def replace_issue_data(comment_body: str, new_metadata: Dict[str, Any]) -> str:
    # Keep serialization stable like post_comment.py
    metadata_json = json.dumps(new_metadata, ensure_ascii=False, separators=(",", ":"))
    replacement = f"<!-- ISSUE_DATA: {metadata_json} -->"
    if not ISSUE_DATA_RE.search(comment_body):
        raise ValueError("No ISSUE_DATA block found to replace")
    return ISSUE_DATA_RE.sub(replacement, comment_body, count=1)


def parse_int_line(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v or v.upper() == "N/A":
            return None
        try:
            return int(v)
        except ValueError:
            return None
    return None


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_context_slices(file_text: str, approx_line: Optional[int], max_chars: int) -> str:
    """
    Build a compact context to send to Cursor.
    Includes head/tail and an around-line window when line is known.
    """
    lines = file_text.splitlines()

    def join_slice(start: int, end: int) -> str:
        chunk = lines[start:end]
        return "\n".join(chunk) + ("\n" if chunk else "")

    head = join_slice(0, min(200, len(lines)))
    tail = join_slice(max(0, len(lines) - 200), len(lines))

    around = ""
    if approx_line and 1 <= approx_line <= len(lines):
        # Use a moderate window; if still too large we'll shrink later.
        start = max(0, approx_line - 1 - 120)
        end = min(len(lines), approx_line - 1 + 120)
        around = join_slice(start, end)

    context = (
        "FILE_CONTEXT_BEGIN\n"
        "=== FILE_HEAD ===\n"
        f"{head}"
        "=== FILE_AROUND_LINE ===\n"
        f"{around}"
        "=== FILE_TAIL ===\n"
        f"{tail}"
        "FILE_CONTEXT_END\n"
    )

    if len(context) <= max_chars:
        return context

    # Shrink around window first
    if approx_line and 1 <= approx_line <= len(lines):
        for win in (80, 60, 40, 20, 10):
            start = max(0, approx_line - 1 - win)
            end = min(len(lines), approx_line - 1 + win)
            around = join_slice(start, end)
            context = (
                "FILE_CONTEXT_BEGIN\n"
                "=== FILE_HEAD ===\n"
                f"{head}"
                "=== FILE_AROUND_LINE ===\n"
                f"{around}"
                "=== FILE_TAIL ===\n"
                f"{tail}"
                "FILE_CONTEXT_END\n"
            )
            if len(context) <= max_chars:
                return context

    # If still too big, truncate hard.
    suffix = f"\n\n...[TRUNCATED CONTEXT: {len(context)} chars total]...\n"
    keep = max(0, max_chars - len(suffix))
    return context[:keep] + suffix


def ensure_cursor_ready(cursor: CursorClient) -> None:
    if cursor.install_cursor_cli():
        _debug("cursor-agent installed/available")
    else:
        raise RuntimeError("Failed to install/find cursor-agent")
    if not cursor.verify_setup():
        raise RuntimeError("cursor-agent verification failed (check CURSOR_API_KEY)")


def extract_patch_from_cursor_result(result: Any) -> Optional[str]:
    """
    CursorClient may return dict, list, or string. We expect JSON: {"patch": "..."} or raw patch text.
    """
    if isinstance(result, dict):
        patch = result.get("patch")
        if isinstance(patch, str) and patch.strip():
            return patch
        # Some models may return nested {"result":{"patch":...}}
        inner = result.get("result")
        if isinstance(inner, dict):
            patch = inner.get("patch")
            if isinstance(patch, str) and patch.strip():
                return patch
        return None
    if isinstance(result, str):
        text = result.strip()
        # Try to extract JSON object if embedded
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("patch"), str):
                return parsed.get("patch")
        except Exception:
            pass
        # Fallback: return the raw text as patch
        return text if text else None
    return None


def normalize_and_fix_patch(patch: str) -> str:
    patch_out = patch
    if PATCH_VALIDATION_AVAILABLE:
        patch_out = normalize_patch_newlines(patch_out)
        patch_out = fix_patch_format(patch_out)
    return patch_out


def validate_patch_or_raise(patch: str) -> None:
    if not patch or not patch.strip():
        raise ValueError("Empty patch")
    if PATCH_VALIDATION_AVAILABLE:
        if not validate_patch_format(patch):
            raise ValueError("Patch failed validate_patch_format()")
    # Basic check: must include at least one hunk header
    if "@@" not in patch:
        raise ValueError("Patch missing @@ hunk header")


def git_apply_check(file_path: str, patch: str) -> Tuple[bool, str]:
    """
    Validate that patch applies cleanly to current working tree.
    Returns (ok, stderr_or_reason).
    """
    full_patch = patch
    if not patch.startswith("---"):
        full_patch = f"--- a/{file_path}\n+++ b/{file_path}\n{patch}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as tmp:
        # Important: git apply treats missing trailing newline as a corrupt patch.
        if not full_patch.endswith("\n"):
            full_patch += "\n"
        tmp.write(full_patch)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["git", "apply", "--check", "--ignore-whitespace", "--whitespace=fix", tmp_path],
            capture_output=True,
            text=True,
            cwd=".",
        )
        if result.returncode == 0:
            return True, ""
        return False, (result.stderr or result.stdout or "git apply --check failed")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def build_cursor_prompt(issue: Dict[str, Any], file_path: str) -> str:
    """
    Ask Cursor to produce a unified diff patch, returned as JSON: {"patch":"..."}.
    """
    description = (issue.get("description") or "").strip()
    recommendation = (issue.get("recommendation") or "").strip()
    old_patch = (issue.get("patch") or "").strip()
    category = (issue.get("category") or "").strip()
    severity = (issue.get("severity") or "").strip()
    method = (issue.get("method") or "").strip()

    return (
        "You are a code improvement assistant.\n"
        "Your task: produce a unified diff patch that applies to the CURRENT version of the file.\n"
        "Only add/modify logging statements; keep functionality unchanged.\n\n"
        f"Target file: {file_path}\n"
        f"Issue severity: {severity}\n"
        f"Issue category: {category}\n"
        f"Method/area: {method}\n\n"
        "Issue description:\n"
        f"{description}\n\n"
        "Original recommendation (may include code snippet):\n"
        f"{recommendation}\n\n"
        "Original patch (may be stale; use only as intent reference):\n"
        f"{old_patch}\n\n"
        "OUTPUT REQUIREMENTS:\n"
        '- Return ONLY valid JSON: {"patch": "<unified diff hunk(s)>"}\n'
        "- The patch MUST include @@ hunk header(s) and lines prefixed with ' ', '+', or '-'.\n"
        "- Do NOT include markdown code fences.\n"
        "- Do NOT include explanations.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh downstream /apply-logs patches for same file")
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument(
        "--applied-parent-comment-id",
        type=str,
        required=False,
        help="Applied parent analysis review comment id (optional if --applied-comment-body-file is provided)",
    )
    parser.add_argument(
        "--applied-comment-body-file",
        type=str,
        required=False,
        help="Path to file containing the applied parent analysis comment body (recommended: parent-comment.txt)",
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=int(os.getenv("REFRESH_MAX_COMMENTS", "50")),
        help="Maximum number of downstream comments to refresh for a file (default 50)",
    )
    args = parser.parse_args()

    verbose = _verbose_enabled()

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        _log("ERROR: GITHUB_TOKEN not set")
        return 1

    pr_number = int(args.pr_number)
    repository = args.repository

    applied_body: Optional[str] = None
    applied_comment_id: Optional[int] = None
    if args.applied_comment_body_file:
        applied_body = read_text_file(args.applied_comment_body_file)
        _debug(f"Loaded applied comment body from {args.applied_comment_body_file} ({len(applied_body)} chars)")

    if args.applied_parent_comment_id:
        try:
            applied_comment_id = int(str(args.applied_parent_comment_id).strip())
        except ValueError:
            _log(f"ERROR: Invalid --applied-parent-comment-id: {args.applied_parent_comment_id}")
            return 1

    if not applied_body and applied_comment_id is not None:
        rc = get_review_comment_by_id(github_token, repository, applied_comment_id)
        applied_body = rc.body
        _debug(f"Fetched applied parent comment #{applied_comment_id} (len {len(applied_body)} chars)")

    if not applied_body:
        _log("ERROR: Need applied comment body. Provide --applied-comment-body-file or --applied-parent-comment-id.")
        return 1

    applied_issue = extract_issue_data(applied_body)
    if not applied_issue:
        _log("ERROR: Could not parse ISSUE_DATA from applied parent comment body.")
        return 1

    applied_file = applied_issue.get("file")
    if not isinstance(applied_file, str) or not applied_file.strip():
        _log("ERROR: Applied ISSUE_DATA missing 'file'")
        return 1

    applied_line = parse_int_line(applied_issue.get("line"))
    if applied_line is None:
        _log("ERROR: Applied ISSUE_DATA missing numeric 'line' (cannot apply downstream ordering rule).")
        return 1

    _log(f"Refreshing patches for file: {applied_file} (downstream line > {applied_line})")

    # List all review comments
    all_comments = list_pr_review_comments(github_token, repository, pr_number)
    _debug(f"Total PR review comments: {len(all_comments)}")

    # Filter to same file and ISSUE_DATA-present
    candidates: List[Tuple[ReviewComment, Dict[str, Any], int]] = []
    for c in all_comments:
        # Safety: only touch bot-style comments (never edit human review comments).
        if not is_bot_issue_comment(c):
            continue
        meta = extract_issue_data(c.body)
        if not meta:
            continue
        file_path = meta.get("file")
        if file_path != applied_file:
            continue
        line_int = parse_int_line(meta.get("line"))
        if line_int is None:
            continue
        if applied_comment_id is not None and c.id == applied_comment_id:
            continue
        if line_int <= applied_line:
            continue
        candidates.append((c, meta, line_int))

    candidates.sort(key=lambda t: t[2])
    if not candidates:
        _log("No downstream ISSUE_DATA comments found to refresh.")
        return 0

    if len(candidates) > args.max_comments:
        _log(f"⚠️ Limiting refresh to first {args.max_comments} downstream comments (found {len(candidates)})")
        candidates = candidates[: args.max_comments]

    # Read current file content once
    if not os.path.exists(applied_file):
        _log(f"ERROR: Target file not found in workspace: {applied_file}")
        return 1
    file_text = read_text_file(applied_file)
    current_hash = sha256_file(applied_file)
    _debug(f"Current file hash: {current_hash}")

    cursor_api_key = os.getenv("CURSOR_API_KEY")
    if not cursor_api_key:
        _log("ERROR: CURSOR_API_KEY not set (required to recalculate patches)")
        return 1

    cursor = CursorClient(api_key=cursor_api_key)
    ensure_cursor_ready(cursor)

    # Avoid OS argv limits (cursor-agent prompt sent as argv)
    max_chars = int(os.getenv("CURSOR_AGENT_MAX_PROMPT_CHARS", "250000"))

    updated = 0
    skipped = 0
    failed = 0

    for (comment, meta, line_int) in candidates:
        _log(f"\n---\nRefreshing comment #{comment.id} at {applied_file}:{line_int}")

        # Build context + prompt
        context = (
            f"REPOSITORY_FILE_PATH: {applied_file}\n"
            f"APPROX_LINE: {line_int}\n"
            f"CURRENT_FILE_SHA256: {current_hash}\n\n"
        )
        context += extract_context_slices(file_text, approx_line=line_int, max_chars=max_chars - 4000)

        prompt = build_cursor_prompt(meta, applied_file)

        try:
            result = cursor.send_message(prompt, context=context, verbose=verbose)
            patch = extract_patch_from_cursor_result(result)
            if not patch:
                _log("❌ No patch returned from Cursor; skipping")
                failed += 1
                continue

            patch = normalize_and_fix_patch(patch)
            validate_patch_or_raise(patch)

            ok, reason = git_apply_check(applied_file, patch)
            if not ok:
                _log("❌ Recalculated patch does not apply cleanly; skipping")
                _log(f"Reason: {reason.strip()[:800]}")
                failed += 1
                continue

            # Update metadata
            new_meta = dict(meta)
            new_meta["patch"] = patch
            new_meta["file_hash"] = current_hash

            # Replace in body and PATCH-edit comment
            new_body = replace_issue_data(comment.body, new_meta)
            if new_body == comment.body:
                _log("No body change detected; skipping update")
                skipped += 1
                continue

            update_review_comment_body(github_token, repository, comment.id, new_body)
            _log("✓ Updated ISSUE_DATA patch in-place")
            updated += 1

        except Exception as e:
            _log(f"❌ Failed to refresh comment #{comment.id}: {type(e).__name__}: {e}")
            failed += 1
            continue

    _log("\n=== Refresh Summary ===")
    _log(f"Updated comments: {updated}")
    _log(f"Skipped comments: {skipped}")
    _log(f"Failed comments:  {failed}")

    return 0 if failed == 0 else 0  # Do not fail the workflow on partial refresh issues


if __name__ == "__main__":
    sys.exit(main())

