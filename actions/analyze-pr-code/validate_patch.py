#!/usr/bin/env python3
"""
Patch Validation and Correction Utilities
Ensures patches follow proper git diff format
"""

import re
from typing import Optional


def normalize_patch_newlines(patch: str) -> str:
    """
    Convert literal \\n strings to actual newlines in patches.
    
    Args:
        patch: Patch string that may contain literal \\n
    
    Returns:
        Patch with actual newlines
    """
    if not patch:
        return patch
    
    # Check if patch contains literal \n (escaped newlines)
    if '\\n' in patch and '\n' not in patch:
        # Replace literal \n with actual newlines
        patch = patch.replace('\\n', '\n')
    
    return patch


def validate_patch_format(patch: str) -> bool:
    """
    Validate that a patch follows proper git diff format.
    
    Returns:
        True if patch is valid, False otherwise
    """
    if not patch or not patch.strip():
        return False
    
    # Normalize newlines first
    patch = normalize_patch_newlines(patch)
    
    # Check for hunk header
    if not re.search(r'@@.*@@', patch):
        return False
    
    lines = patch.split('\n')
    has_changes = False
    
    for line in lines:
        # Skip empty lines and hunk headers
        if not line or line.startswith('@@'):
            continue
        
        # Check if line has proper prefix
        if line.startswith('+') or line.startswith('-'):
            has_changes = True
        elif line.startswith(' '):
            # Context line is OK
            pass
        else:
            # Line without proper prefix (except for context at start of patch)
            # This might be OK if it's just context without space prefix
            pass
    
    return has_changes


def fix_hunk_header_counts(patch: str) -> str:
    """
    Fix incorrect line counts in hunk headers.
    
    Args:
        patch: The patch string with potentially incorrect hunk headers
    
    Returns:
        Patch with corrected hunk headers
    """
    if not patch or not patch.strip():
        return patch
    
    lines = patch.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a hunk header
        if line.startswith('@@'):
            # Parse the header
            hunk_match = re.match(r'@@\s+-(\d+),?(\d+)?\s+\+(\d+),?(\d+)?\s+@@', line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                new_start = int(hunk_match.group(3))
                
                # Count the actual lines in this hunk
                old_count = 0
                new_count = 0
                j = i + 1
                
                while j < len(lines):
                    next_line = lines[j]
                    # Stop at next hunk or end
                    if next_line.startswith('@@'):
                        break
                    if not next_line.strip():
                        j += 1
                        continue
                    
                    if next_line.startswith('-'):
                        old_count += 1
                    elif next_line.startswith('+'):
                        new_count += 1
                    elif next_line.startswith(' '):
                        # Context line counts in both
                        old_count += 1
                        new_count += 1
                    
                    j += 1
                
                # Reconstruct hunk header with correct counts
                fixed_header = f'@@ -{old_start},{old_count} +{new_start},{new_count} @@'
                fixed_lines.append(fixed_header)
            else:
                # Couldn't parse, keep original
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        
        i += 1
    
    return '\n'.join(fixed_lines)


def fix_patch_format(patch: str, file_content_before: Optional[str] = None) -> str:
    """
    Attempt to fix a malformed patch to follow git diff format.
    
    Args:
        patch: The patch string to fix
        file_content_before: Original file content (optional, for better correction)
    
    Returns:
        Fixed patch string
    """
    if not patch or not patch.strip():
        return patch
    
    # First, normalize newlines (convert literal \n to actual newlines)
    patch = normalize_patch_newlines(patch)
    
    lines = patch.split('\n')
    fixed_lines = []
    in_hunk = False
    
    for line in lines:
        # Preserve hunk headers
        if line.startswith('@@'):
            fixed_lines.append(line)
            in_hunk = True
            continue
        
        if not in_hunk:
            # Before first hunk, preserve as-is
            fixed_lines.append(line)
            continue
        
        # Empty lines
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        # Already has proper prefix
        if line.startswith(('+', '-', ' ')):
            fixed_lines.append(line)
            continue
        
        # No prefix - assume it's a context line
        # (In git diff, context lines start with space)
        fixed_lines.append(' ' + line)
    
    result = '\n'.join(fixed_lines)
    
    # Fix hunk header line counts
    result = fix_hunk_header_counts(result)
    
    return result


def format_patch_for_display(patch: str) -> str:
    """
    Format patch for display in code blocks (ensure proper escaping).
    
    Args:
        patch: The patch string
    
    Returns:
        Formatted patch suitable for markdown code blocks
    """
    if not patch:
        return ""
    
    # Ensure patch doesn't break out of code blocks
    patch = patch.replace('```', '\\`\\`\\`')
    
    return patch


def extract_changed_lines(patch: str) -> tuple[list[str], list[str]]:
    """
    Extract added and removed lines from a patch.
    
    Returns:
        Tuple of (added_lines, removed_lines)
    """
    added = []
    removed = []
    
    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added.append(line[1:].strip())
        elif line.startswith('-') and not line.startswith('---'):
            removed.append(line[1:].strip())
    
    return added, removed


def ensure_patch_has_context(patch: str, context_lines: int = 3) -> str:
    """
    Ensure patch has proper context lines around changes.
    
    Args:
        patch: The patch string
        context_lines: Number of context lines to ensure (default 3)
    
    Returns:
        Patch with proper context
    """
    # This is a simplified version - full implementation would need
    # access to the original file content
    return patch


if __name__ == '__main__':
    # Test cases
    test_patches = [
        # Good patch
        """@@ -5,7 +5,7 @@
 const logger = new Logger("ErrorHandler");
 
-  logger.error("Unhandled error:", err);
+  logger.error('Unhandled error:', { error: err.message, stack: err.stack });
 
   res.status(500).json({
""",
        # Bad patch (missing + and - prefixes)
        """@@ -5,7 +5,7 @@
const logger = new Logger("ErrorHandler");

  logger.error("Unhandled error:", err);
  logger.error('Unhandled error:', { error: err.message, stack: err.stack });

  res.status(500).json({
""",
    ]
    
    print("Testing patch validation:")
    for i, patch in enumerate(test_patches, 1):
        is_valid = validate_patch_format(patch)
        print(f"\nPatch {i}: {'✅ VALID' if is_valid else '❌ INVALID'}")
        if not is_valid:
            fixed = fix_patch_format(patch)
            print(f"Fixed patch:\n{fixed}")

