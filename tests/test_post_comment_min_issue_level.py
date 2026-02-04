#!/usr/bin/env python3
"""
Unit tests for post_comment.py minimum issue level filtering.

Tests severity_rank and the filter rule: only issues with severity rank <= min_issue_level rank
are shown (e.g. min_issue_level=high => show CRITICAL and HIGH only).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add actions/analyze-pr-code and libs to path so we can import post_comment
REPO_ROOT = Path(__file__).resolve().parent.parent
LIBS = REPO_ROOT / "libs"
ACTION_DIR = REPO_ROOT / "actions" / "analyze-pr-code"
sys.path.insert(0, str(LIBS))
sys.path.insert(0, str(ACTION_DIR))

from post_comment import SEVERITY_RANK, severity_rank  # noqa: E402


def test_severity_rank_values() -> None:
    """severity_rank returns correct numeric rank (lower = more severe)."""
    assert severity_rank("CRITICAL") == 0
    assert severity_rank("critical") == 0
    assert severity_rank("HIGH") == 1
    assert severity_rank("high") == 1
    assert severity_rank("MEDIUM") == 2
    assert severity_rank("medium") == 2
    assert severity_rank("LOW") == 3
    assert severity_rank("low") == 3


def test_severity_rank_unknown_defaults_to_medium() -> None:
    """Unknown severity defaults to MEDIUM rank."""
    assert severity_rank("UNKNOWN") == SEVERITY_RANK["MEDIUM"]
    assert severity_rank("") == SEVERITY_RANK["MEDIUM"]
    assert severity_rank("  ") == SEVERITY_RANK["MEDIUM"]


def test_filter_min_issue_level_high() -> None:
    """With min_issue_level=high, only CRITICAL and HIGH issues are shown."""
    min_level_rank = SEVERITY_RANK["HIGH"]  # 1
    issues = [
        {"severity": "CRITICAL", "line": 1},
        {"severity": "HIGH", "line": 2},
        {"severity": "MEDIUM", "line": 3},
        {"severity": "LOW", "line": 4},
    ]
    shown = [i for i in issues if severity_rank(i.get("severity", "MEDIUM")) <= min_level_rank]
    assert len(shown) == 2
    assert [i["severity"] for i in shown] == ["CRITICAL", "HIGH"]


def test_filter_min_issue_level_low_shows_all() -> None:
    """With min_issue_level=low, all severities are shown."""
    min_level_rank = SEVERITY_RANK["LOW"]  # 3
    issues = [
        {"severity": "CRITICAL"},
        {"severity": "HIGH"},
        {"severity": "MEDIUM"},
        {"severity": "LOW"},
    ]
    shown = [i for i in issues if severity_rank(i.get("severity", "MEDIUM")) <= min_level_rank]
    assert len(shown) == 4


def test_filter_min_issue_level_critical_only() -> None:
    """With min_issue_level=critical, only CRITICAL is shown."""
    min_level_rank = SEVERITY_RANK["CRITICAL"]  # 0
    issues = [
        {"severity": "CRITICAL", "line": 1},
        {"severity": "HIGH", "line": 2},
        {"severity": "MEDIUM", "line": 3},
    ]
    shown = [i for i in issues if severity_rank(i.get("severity", "MEDIUM")) <= min_level_rank]
    assert len(shown) == 1
    assert shown[0]["severity"] == "CRITICAL"


if __name__ == "__main__":
    test_severity_rank_values()
    test_severity_rank_unknown_defaults_to_medium()
    test_filter_min_issue_level_high()
    test_filter_min_issue_level_low_shows_all()
    test_filter_min_issue_level_critical_only()
    print("All tests passed.")
