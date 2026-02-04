"""Extract fenced code blocks from text (e.g. YAML from comments or API responses)."""

from __future__ import annotations

import re
from typing import Optional


def extract_code_block(text: str, language: str = "yaml") -> str:
    """
    Extract first fenced code block from text. Tries ```language ... ``` then ``` ... ```.
    Returns empty string when no block found.
    """
    if not text or not text.strip():
        return ""
    text = text.strip()
    # Try ```language ... ``` first
    pattern_lang = rf"```{re.escape(language)}\s*\n(.*?)\n```"
    match = re.search(pattern_lang, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: generic ``` ... ```
    match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""
