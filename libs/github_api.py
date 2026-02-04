"""Shared GitHub API helpers: repo split, headers, PR review comments."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import requests


def split_owner_repo(repository: str) -> Tuple[str, str]:
    """Split 'owner/repo' into (owner, repo). Uses split('/', 1) for safety."""
    if "/" not in repository:
        raise ValueError(f"Invalid repository (expected owner/repo): {repository!r}")
    owner, repo = repository.split("/", 1)
    return owner, repo


def github_headers(token: str) -> Dict[str, str]:
    """Standard headers for GitHub API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def get_pr_comment(token: str, repository: str, comment_id: int) -> Any:
    """Fetch a single PR review comment by ID."""
    owner, repo = split_owner_repo(repository)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    resp = requests.get(url, headers=github_headers(token))
    resp.raise_for_status()
    return resp.json()


def patch_pr_comment(token: str, repository: str, comment_id: int, body: str) -> None:
    """Update a PR review comment's body."""
    owner, repo = split_owner_repo(repository)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    resp = requests.patch(url, headers=github_headers(token), json={"body": body})
    resp.raise_for_status()


def post_pr_review_comment(
    token: str,
    repository: str,
    pr_number: int,
    body: str,
    in_reply_to: Optional[int] = None,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    """
    POST a new PR review comment. If payload is provided, use it; otherwise
    build from body and in_reply_to. Returns the response (caller may call
    .raise_for_status() and .json()).
    """
    owner, repo = split_owner_repo(repository)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    if payload is not None:
        data = payload
    else:
        data = {"body": body}
        if in_reply_to is not None:
            data["in_reply_to"] = in_reply_to
    return requests.post(url, headers=github_headers(token), json=data)


def post_pr_review_comment_and_return_id(
    token: str,
    repository: str,
    pr_number: int,
    body: str,
    in_reply_to: Optional[int] = None,
    *,
    verbose: bool = False,
) -> Optional[int]:
    """
    POST a PR review comment, log non-201 errors, raise on failure, return new comment id.
    """
    response = post_pr_review_comment(token, repository, pr_number, body, in_reply_to=in_reply_to)
    print(f"[INFO] Comment API response status: {response.status_code}")
    if response.status_code != 201:
        print("[ERROR] Comment posting failed!")
        print(f"[ERROR] Response status: {response.status_code}")
        print(f"[ERROR] Response body: {response.text}")
        try:
            error_data = response.json()
            print(f"[ERROR] Error details: {json.dumps(error_data, indent=2)}")
        except Exception:
            pass
    response.raise_for_status()
    data = response.json()
    if verbose:
        print("[DEBUG] Comment posted successfully")
        print(f"[DEBUG] Comment ID: {data.get('id')}")
        print(f"[DEBUG] Comment URL: {data.get('html_url')}")
    return data.get("id")


def pr_comments_url(repository: str, pr_number: int) -> str:
    """URL for listing/posting PR review comments."""
    owner, repo = split_owner_repo(repository)
    return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"


def pr_files_url(repository: str, pr_number: int) -> str:
    """URL for listing PR changed files."""
    owner, repo = split_owner_repo(repository)
    return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
