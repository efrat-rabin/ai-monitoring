#!/usr/bin/env python3
"""
Post PR Review Comments Script
Posts review comments on specific code lines.
"""

import os
import sys
import json
import argparse
import hashlib
import requests
from typing import Dict, List, Any

from comment_state import APPLY_LOGS_LINE, STATE_ANALYZED, status_marker


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file for change detection."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Warning: Could not compute hash for {file_path}: {e}")
        return ""


def format_review_comment(issue: Dict[str, Any], file_path: str) -> str:
    """Format a single issue as a review comment."""
    severity = issue.get("severity", "MEDIUM")
    category = issue.get("category", "general")
    method = issue.get("method", "N/A")
    line = issue.get("line", "N/A")
    
    # Include metadata as hidden JSON for parsing
    recommendation = issue.get("recommendation", "")
    patch = issue.get("patch", "")
    
    # Debug: Check if doubled quotes already exist in source data
    if "''" in recommendation:
        print(f"⚠️  WARNING: Doubled quotes found in recommendation FROM CURSOR!")
        print(f"  Preview: {recommendation[:100]}")
    if "''" in patch:
        print(f"⚠️  WARNING: Doubled quotes found in patch FROM CURSOR!")
        print(f"  Preview: {patch[:100]}")
    
    metadata = {
        "file": file_path,
        "file_hash": compute_file_hash(file_path),
        "severity": severity,
        "category": category,
        "method": method,
        "line": line,
        "description": issue.get("description", ""),
        "recommendation": recommendation,
        "patch": patch,
        "impact": issue.get("impact", ""),
        "commit_message": issue.get("commit_message", ""),
        "monitor_image": issue.get("monitor_image", ""),
        "dashboard_image": issue.get("dashboard_image", "")
    }
    
    comment = f"**🤖 {severity}** - {category} in `{method}`\n\n"
    
    if "description" in issue:
        comment += f"{issue['description']}\n\n"
    
    if "recommendation" in issue:
        comment += f"**Recommendation:**\n```python\n{issue['recommendation']}\n```\n\n"
    
    if "impact" in issue:
        comment += f"**Impact:** {issue['impact']}\n\n"
    
    comment += "---\n"
    comment += APPLY_LOGS_LINE + "\n\n"

    # Serialize metadata as JSON
    # Use ensure_ascii=False to prevent unnecessary escaping of quotes
    # Use separators to avoid extra whitespace
    metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
    
    # Debug: Check for doubled quotes before posting
    if "''" in metadata_json:
        print(f"⚠️  WARNING: Found doubled single quotes in metadata JSON!")
        print(f"  Patch preview: {metadata.get('patch', '')[:200]}")
        print(f"  Recommendation preview: {metadata.get('recommendation', '')[:100]}")
    
    comment += f"<!-- ISSUE_DATA: {metadata_json} -->"
    comment += "\n\n" + status_marker(STATE_ANALYZED)
    return comment


def get_pr_changed_lines(
    github_token: str,
    repository: str,
    pr_number: int
) -> Dict[str, set]:
    """Get a map of file paths to their changed line numbers."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        files = response.json()
        
        changed_lines = {}
        for file_data in files:
            filename = file_data.get("filename")
            patch = file_data.get("patch", "")
            
            # Parse the patch to get changed line numbers
            lines = set()
            current_line = 0
            
            for line in patch.split('\n'):
                if line.startswith('@@'):
                    # Extract the starting line number from hunk header
                    # Format: @@ -1,4 +1,5 @@
                    parts = line.split('+')[1].split('@@')[0].strip()
                    current_line = int(parts.split(',')[0]) if ',' in parts else int(parts)
                elif not line.startswith('-'):
                    # This is either a context line or an addition
                    if current_line > 0:
                        lines.add(current_line)
                    current_line += 1
            
            if lines:
                changed_lines[filename] = lines
        
        return changed_lines
    except Exception as e:
        print(f"Warning: Could not fetch PR diff: {e}")
        return {}


def post_review_comment(
    github_token: str,
    repository: str,
    pr_number: int,
    commit_sha: str,
    file_path: str,
    line: int,   
    comment_body: str
) -> bool:
    """Post a review comment on a specific line."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    payload = {
        "body": comment_body,
        "commit_id": commit_sha,
        "path": file_path,
        "line": line,
        "side": "RIGHT"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Failed to post review comment on {file_path}:{line} - {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Post analysis results as PR review comments")
    parser.add_argument("--pr-number", type=str, required=True)
    parser.add_argument("--repository", type=str, required=True)
    parser.add_argument("--results-file", type=str, default="analysis-results.json")
    parser.add_argument("--commit-sha", type=str, required=True, help="Commit SHA to comment on")
    
    args = parser.parse_args()
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN not set")
        return 1
    
    # Read analysis results
    try:
        with open(args.results_file, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Results file not found: {args.results_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return 1
    
    pr_number = int(args.pr_number)
    
    # Get changed lines from PR diff
    print("Fetching PR diff...")
    changed_lines = get_pr_changed_lines(github_token, args.repository, pr_number)
    print(f"Found {len(changed_lines)} changed file(s)")
    
    # Post review comments on specific lines
    total_comments = 0
    skipped_not_in_diff = 0
    
    for result in results:
        file_path = result.get("file")
        analysis = result.get("analysis", {})
        issues = analysis.get("issues", [])
        
        # Get changed lines for this file
        file_changed_lines = changed_lines.get(file_path, set())
        
        for issue in issues:
            line = issue.get("line")
            if not line or line == "N/A":
                print(f"Skipping {file_path} - no line number")
                continue
            
            # Check if the line is in the PR diff
            if file_changed_lines and line not in file_changed_lines:
                print(f"Skipping {file_path}:{line} - line not in PR diff")
                skipped_not_in_diff += 1
                continue
            
            method = issue.get("method", "N/A")
            print(f"Posting review comment on {file_path}:{line} ({method})")
            
            comment = format_review_comment(issue, file_path)
            
            if post_review_comment(
                github_token,
                args.repository,
                pr_number,
                args.commit_sha,
                file_path,
                line,
                comment
            ):
                total_comments += 1
    
    if skipped_not_in_diff > 0:
        print(f"\n⚠️ Skipped {skipped_not_in_diff} issue(s) not in PR diff")

    print(f"✅ Posted {total_comments} review comment(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

