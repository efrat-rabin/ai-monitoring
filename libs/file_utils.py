"""Shared file utilities: hashing, etc."""

from __future__ import annotations

import hashlib


def sha256_hex(path: str) -> str:
    """Compute SHA256 hash of file at path; return hex digest. Returns empty string on error."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        # Caller may log; keep signature simple
        raise OSError(f"Cannot compute hash for {path}: {e}") from e


def sha256_hex_or_empty(path: str) -> str:
    """Compute SHA256 hash of file; return hex digest or empty string on error (no raise)."""
    try:
        return sha256_hex(path)
    except Exception:
        return ""
