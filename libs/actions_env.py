"""GitHub Actions env helpers: verbose, GITHUB_TOKEN, common CLI args."""

from __future__ import annotations

import argparse
import os
from typing import Optional


def is_verbose() -> bool:
    """True when ACTIONS_STEP_DEBUG is 'true' or '1'."""
    return os.getenv("ACTIONS_STEP_DEBUG", "false").lower() in ("true", "1")


def require_github_token() -> Optional[str]:
    """Return GITHUB_TOKEN or None (prints error and returns None so caller can return 1)."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set")
        return None
    return token


def add_common_pr_args(parser: argparse.ArgumentParser) -> None:
    """Add --pr-number, --repository, --comment-id to parser."""
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--comment-id", type=str, required=True)
