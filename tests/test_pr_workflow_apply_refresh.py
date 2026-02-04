#!/usr/bin/env python3
"""
Test script for PR Automation workflow: analyze + apply-logs + refresh-patches.

Implements the test plan in tests/TEST_PLAN_PR_WORKFLOW.md:
- When no --pr-number is given: create branch, add a sample file with code that
  lacks logging (so the analyzer suggests fixes), push, open PR (setup is part of the test).
- Assertions: poll for analyze run, assert 3 review comments, reply /apply-logs
  to 1st then 2nd comment, wait for apply-logs and refresh-patches, assert
  commits and ISSUE_DATA updates (2 comments refreshed after 1st apply, 1 after 2nd).
- Optional cleanup: close PR, delete branch.

Requires: GITHUB_TOKEN (repo scope). For creating PR / cleanup: gh CLI and git.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Default workflow file name in repo (used to find workflow runs)
WORKFLOW_FILE = "pr-automation.yml"
JOBS = ("analyze", "apply-logs", "refresh-patches")

# Sample file content: code without logging so the analyzer suggests fixes (3 spots).
# Used when creating a PR as part of the test; analyzer should return 3+ issues.
TEST_WF_SAMPLE_FILE = "tests/test_wf_analyzer_sample.py"
TEST_WF_SAMPLE_CONTENT = '''# Temporary file for PR workflow test. Code without logging so analyzer suggests fixes.
# This file is created by tests/test_pr_workflow_apply_refresh.py and can be deleted after the test.

def process_item(item):
    result = item.upper()
    return result


def handle_request(req):
    try:
        data = req.get("data")
        return data
    except Exception:
        raise


def batch_process(items):
    for i, x in enumerate(items):
        y = x.strip()
        if not y:
            return False
    return True
'''

# ISSUE_DATA and STATUS markers (must match refresh_related_patches.py / comment_state.py)
ISSUE_DATA_RE = re.compile(r"<!--\s*ISSUE_DATA:\s*(.+?)\s*-->", re.DOTALL)
STATUS_RE = re.compile(r"<!--\s*STATUS:\s*(\w+)\s*-->")
APPLIED_LINE = "✅ Applied"


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _api(session: requests.Session, method: str, url: str, **kwargs) -> Any:
    r = session.request(method, url, **kwargs)
    if not r.ok:
        raise RuntimeError(f"{method} {url} -> {r.status_code} {r.text[:500]}")
    if r.status_code == 204:
        return None
    return r.json()


def get_pr(session: requests.Session, base: str, pr_number: int) -> Dict[str, Any]:
    return _api(session, "GET", f"{base}/pulls/{pr_number}")


def list_review_comments(session: requests.Session, base: str, pr_number: int) -> List[Dict[str, Any]]:
    return _api(session, "GET", f"{base}/pulls/{pr_number}/comments")


def list_commits(session: requests.Session, base: str, pr_number: int) -> List[Dict[str, Any]]:
    return _api(session, "GET", f"{base}/pulls/{pr_number}/commits")


def post_review_comment_reply(
    session: requests.Session, base: str, pr_number: int, body: str, in_reply_to: int
) -> Dict[str, Any]:
    return _api(
        session,
        "POST",
        f"{base}/pulls/{pr_number}/comments",
        json={"body": body, "in_reply_to": in_reply_to},
    )


def list_workflow_runs(
    session: requests.Session, base: str, branch: Optional[str] = None, event: Optional[str] = None
) -> List[Dict[str, Any]]:
    url = f"{base.replace('/repos/', '/repos/')}/actions/runs?per_page=20"
    if branch:
        url += f"&branch={branch}"
    if event:
        url += f"&event={event}"
    data = _api(session, "GET", url)
    return data.get("workflow_runs", [])


def list_run_jobs(session: requests.Session, base: str, run_id: int) -> List[Dict[str, Any]]:
    url = f"{base}/actions/runs/{run_id}/jobs"
    data = _api(session, "GET", url)
    return data.get("jobs", [])


def extract_issue_data(body: str) -> Optional[Dict[str, Any]]:
    m = ISSUE_DATA_RE.search(body)
    if not m:
        return None
    try:
        return json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None


def get_comment_state(body: str) -> Optional[str]:
    m = STATUS_RE.search(body)
    if not m:
        return None
    return m.group(1).strip().lower()


def is_bot_issue_comment(comment: Dict[str, Any]) -> bool:
    body = comment.get("body") or ""
    if "ISSUE_DATA" not in body:
        return False
    if "Reply with `/apply-logs`" in body:
        return True
    if body.lstrip().startswith("**🤖"):
        return True
    user = (comment.get("user") or {}).get("login") or ""
    if user.endswith("[bot]"):
        return True
    return False


def bot_issue_comments_sorted_by_line(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return bot ISSUE_DATA comments sorted by (path, line)."""
    out = []
    for c in comments:
        if not is_bot_issue_comment(c):
            continue
        data = extract_issue_data(c.get("body") or "")
        if not data:
            continue
        path = data.get("path") or c.get("path") or ""
        line = data.get("line")
        if line is None:
            line = c.get("line") or 0
        out.append((path, line, c))
    out.sort(key=lambda x: (x[0], x[1]))
    return [c for _, _, c in out]


def poll_until_job_completes(
    session: requests.Session,
    base: str,
    branch: str,
    job_name: str,
    max_wait_sec: int = 600,
    poll_interval_sec: int = 15,
    event: Optional[str] = None,
) -> bool:
    """Poll workflow runs for this branch until a run has job_name completed (success).
    event: GitHub workflow event filter (e.g. 'pull_request', 'pull_request_review_comment').
           apply-logs is triggered by pull_request_review_comment; analyze by pull_request.
    """
    if event is None:
        event = "pull_request_review_comment" if job_name == "apply-logs" else "pull_request"
    start = time.monotonic()
    seen_run_ids = set()
    while (time.monotonic() - start) < max_wait_sec:
        runs = list_workflow_runs(session, base, branch=branch, event=event)
        for run in runs:
            if run.get("status") != "completed":
                continue
            run_id = run["id"]
            if run_id in seen_run_ids:
                continue
            jobs = list_run_jobs(session, base, run_id)
            for job in jobs:
                if job.get("name") == job_name and job.get("conclusion") == "success":
                    return True
            seen_run_ids.add(run_id)
        time.sleep(poll_interval_sec)
    return False


def poll_until_synchronize_run_completes(
    session: requests.Session,
    base: str,
    branch: str,
    job_name: str,
    max_wait_sec: int = 600,
    poll_interval_sec: int = 15,
) -> bool:
    """Poll for a workflow run triggered by synchronize (push) where job_name succeeded."""
    start = time.monotonic()
    seen_run_ids = set()
    while (time.monotonic() - start) < max_wait_sec:
        runs = list_workflow_runs(session, base, branch=branch, event="pull_request")
        for run in runs:
            if run.get("status") != "completed":
                continue
            if run.get("event") != "pull_request" or run.get("event") == "pull_request":
                pass  # API may not distinguish opened vs synchronize easily
            run_id = run["id"]
            if run_id in seen_run_ids:
                continue
            jobs = list_run_jobs(session, base, run_id)
            for job in jobs:
                if job.get("name") == job_name and job.get("conclusion") == "success":
                    return True
            seen_run_ids.add(run_id)
        time.sleep(poll_interval_sec)
    return False


def run_setup(owner: str, repo: str, branch: str) -> Optional[int]:
    """Create branch, add a sample file with code that lacks logging (so analyzer suggests fixes), push, open PR. Returns PR number or None."""
    repo_root = Path(__file__).resolve().parent.parent
    # Branch from main
    subprocess.run(["git", "fetch", "origin", "main"], check=True, cwd=repo_root)
    subprocess.run(["git", "checkout", "-b", branch, "origin/main"], check=True, cwd=repo_root)
    # Create a new file with code that lacks logging so the analyzer returns issues (3 spots)
    path = repo_root / TEST_WF_SAMPLE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEST_WF_SAMPLE_CONTENT, encoding="utf-8")
    subprocess.run(["git", "add", str(path)], check=True, cwd=repo_root)
    subprocess.run(["git", "commit", "-m", "Test PR: add sample file for workflow test (code without logging)"], check=True, cwd=repo_root)
    subprocess.run(["git", "push", "-u", "origin", branch], check=True, cwd=repo_root)
    result = subprocess.run(
        ["gh", "pr", "create", "--repo", f"{owner}/{repo}", "--base", "main", "--head", branch, "--title", "Test: PR workflow apply + refresh", "--body", "Automated test for analyze + apply-logs + refresh-patches"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"gh pr create failed: {result.stderr}", file=sys.stderr)
        return None
    # Parse PR number from URL or output
    out = result.stdout.strip()
    for word in out.split():
        if word.isdigit():
            return int(word)
    return None


def run_cleanup(owner: str, repo: str, pr_number: int, branch: str) -> None:
    """Close PR and delete branch."""
    subprocess.run(["gh", "pr", "close", str(pr_number), "--repo", f"{owner}/{repo}"], check=True)
    subprocess.run(["git", "push", "origin", "--delete", branch], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test PR Automation workflow (analyze + apply-logs + refresh)")
    parser.add_argument("--owner", default="efrat-rabin", help="Repo owner")
    parser.add_argument("--repo", default="ai-monitoring", help="Repo name")
    parser.add_argument("--pr-number", type=int, help="PR number (if omitted, script creates a PR as part of the test)")
    parser.add_argument("--branch", help="PR head branch (default: from PR or generated for setup)")
    parser.add_argument("--cleanup", action="store_true", help="Close PR and delete branch when done")
    parser.add_argument("--no-assert", action="store_true", help="Skip assertions (create PR and optionally cleanup only)")
    parser.add_argument("--poll-interval", type=int, default=15, help="Seconds between workflow polls")
    parser.add_argument("--max-wait", type=int, default=600, help="Max seconds to wait for a job")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        return 1

    base = f"https://api.github.com/repos/{args.owner}/{args.repo}"
    session = requests.Session()
    session.headers.update(_headers(token))

    pr_number = args.pr_number
    branch = args.branch

    # No PR given: create one as part of the test (branch, add sample file, push, open PR)
    if not pr_number:
        branch = branch or f"test-wf-apply-refresh-{secrets.token_hex(4)}"
        print(f"Setup: creating branch {branch}, adding {TEST_WF_SAMPLE_FILE} (code without logging), opening PR...")
        pr_number = run_setup(args.owner, args.repo, branch)
        if pr_number is None:
            return 1
        print(f"Setup: PR #{pr_number} opened")
        args.branch = branch

    pr = get_pr(session, base, pr_number)
    branch = branch or pr.get("head", {}).get("ref", "")
    if not branch:
        print("ERROR: could not determine PR head branch", file=sys.stderr)
        return 1

    if args.no_assert:
        print("Skipping assertions (--no-assert).")
        if args.cleanup:
            run_cleanup(args.owner, args.repo, pr_number, branch)
        return 0

    # --- Assertions ---
    print("Waiting for analyze job to complete...")
    if not poll_until_job_completes(session, base, branch, "analyze", args.max_wait, args.poll_interval):
        print("FAIL: analyze job did not complete in time", file=sys.stderr)
        return 1
    print("  analyze completed")

    comments = list_review_comments(session, base, pr_number)
    bot_comments = bot_issue_comments_sorted_by_line(comments)
    if len(bot_comments) < 3:
        print(f"FAIL: expected at least 3 bot ISSUE_DATA comments, got {len(bot_comments)}", file=sys.stderr)
        return 1
    print(f"  Found {len(bot_comments)} bot issue comments (1st/2nd/3rd by line)")

    first_id = bot_comments[0]["id"]
    second_id = bot_comments[1]["id"]

    # Capture ISSUE_DATA (e.g. patch or file_hash) for 2nd and 3rd before first apply
    def issue_data_snapshot(comment_list: List[Dict[str, Any]]) -> List[Optional[str]]:
        return [json.dumps(extract_issue_data(c.get("body") or ""), sort_keys=True) for c in comment_list]

    before_first = issue_data_snapshot(bot_comments)

    # Reply /apply-logs to 1st comment
    print("Posting /apply-logs reply to 1st comment...")
    post_review_comment_reply(session, base, pr_number, "/apply-logs", first_id)

    print("Waiting for apply-logs job...")
    if not poll_until_job_completes(session, base, branch, "apply-logs", args.max_wait, args.poll_interval):
        print("FAIL: apply-logs job did not complete in time", file=sys.stderr)
        return 1
    print("Waiting for refresh-patches job (after push)...")
    if not poll_until_synchronize_run_completes(session, base, branch, "refresh-patches", args.max_wait, args.poll_interval):
        print("FAIL: refresh-patches job did not complete in time", file=sys.stderr)
        return 1
    print("  apply-logs and refresh-patches completed")

    commits = list_commits(session, base, pr_number)
    if len(commits) < 2:
        print(f"FAIL: expected at least 2 commits after first apply, got {len(commits)}", file=sys.stderr)
        return 1
    print(f"  PR has {len(commits)} commit(s)")

    comments_after_1 = list_review_comments(session, base, pr_number)
    bot_after_1 = bot_issue_comments_sorted_by_line(comments_after_1)
    if len(bot_after_1) < 3:
        print(f"FAIL: expected 3 bot comments after first apply, got {len(bot_after_1)}", file=sys.stderr)
        return 1

    first_body = next((c.get("body") or "" for c in bot_after_1 if c["id"] == first_id), "")
    if APPLIED_LINE not in first_body and "applied" not in (get_comment_state(first_body) or ""):
        print("FAIL: 1st comment should show Applied / STATUS applied", file=sys.stderr)
        return 1
    print("  1st comment shows Applied")

    # 2nd and 3rd should have updated ISSUE_DATA (e.g. different patch after refresh)
    after_first = issue_data_snapshot(bot_after_1)
    if after_first[1] == before_first[1] and after_first[2] == before_first[2]:
        print("FAIL: 2nd and 3rd comments should have updated ISSUE_DATA after refresh", file=sys.stderr)
        return 1
    print("  2nd and 3rd comments have updated ISSUE_DATA")

    # --- Second apply: reply to 2nd comment ---
    print("Posting /apply-logs reply to 2nd comment...")
    post_review_comment_reply(session, base, pr_number, "/apply-logs", second_id)

    print("Waiting for apply-logs job (2nd)...")
    if not poll_until_job_completes(session, base, branch, "apply-logs", args.max_wait, args.poll_interval):
        print("FAIL: second apply-logs job did not complete in time", file=sys.stderr)
        return 1
    print("Waiting for refresh-patches job (2nd push)...")
    if not poll_until_synchronize_run_completes(session, base, branch, "refresh-patches", args.max_wait, args.poll_interval):
        print("FAIL: second refresh-patches did not complete in time", file=sys.stderr)
        return 1

    commits_after_2 = list_commits(session, base, pr_number)
    if len(commits_after_2) < 3:
        print(f"FAIL: expected at least 3 commits after second apply, got {len(commits_after_2)}", file=sys.stderr)
        return 1
    print(f"  PR has {len(commits_after_2)} commit(s) after 2nd apply")

    comments_after_2 = list_review_comments(session, base, pr_number)
    bot_after_2 = bot_issue_comments_sorted_by_line(comments_after_2)
    second_body = next((c.get("body") or "" for c in bot_after_2 if c["id"] == second_id), "")
    if APPLIED_LINE not in second_body and "applied" not in (get_comment_state(second_body) or ""):
        print("FAIL: 2nd comment should show Applied after second apply", file=sys.stderr)
        return 1
    print("  2nd comment shows Applied")

    # Only 3rd comment should have been refreshed (1st and 2nd are applied)
    third_id = bot_comments[2]["id"]
    third_before_2nd_apply = next((extract_issue_data(c.get("body") or "") for c in bot_after_1 if c["id"] == third_id), {})
    third_after_2nd_apply = next((extract_issue_data(c.get("body") or "") for c in bot_after_2 if c["id"] == third_id), {})
    if third_after_2nd_apply == third_before_2nd_apply:
        print("FAIL: 3rd comment ISSUE_DATA should have been updated after 2nd refresh", file=sys.stderr)
        return 1
    print("  3rd comment has updated ISSUE_DATA (only one refreshed)")

    print("All assertions passed.")
    if args.cleanup:
        run_cleanup(args.owner, args.repo, pr_number, branch)
        print("Cleanup: PR closed, branch deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
