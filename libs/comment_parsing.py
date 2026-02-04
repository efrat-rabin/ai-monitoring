"""Shared comment parsing: ISSUE_DATA and related."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

ISSUE_DATA_RE = re.compile(r"<!--\s*ISSUE_DATA:\s*(.+?)\s*-->", re.DOTALL)


def extract_issue_data(comment_body: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Extract ISSUE_DATA JSON from comment body (<!-- ISSUE_DATA: {...} -->).
    Returns None when not found or on parse error.
    """
    if not comment_body:
        return None
    m = ISSUE_DATA_RE.search(comment_body)
    if not m:
        if verbose:
            print("[DEBUG] No ISSUE_DATA found in comment")
        return None
    raw = m.group(1)
    try:
        data = json.loads(raw)
        if verbose:
            print(f"[DEBUG] Extracted issue data with keys: {list(data.keys())}")
        return data
    except json.JSONDecodeError as e:
        try:
            data = json.loads(raw.strip())
            if verbose:
                print(f"[DEBUG] Extracted issue data with keys: {list(data.keys())}")
            return data
        except Exception:
            pass
        if verbose:
            print(f"[ERROR] Failed to parse issue JSON: {e}")
        return None
