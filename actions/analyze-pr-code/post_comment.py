#!/usr/bin/env python3
"""
Post PR Review Comments Script
Posts review comments on specific code lines.
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, List, Any


def format_review_comment(issue: Dict[str, Any]) -> str:
    """Format a single issue as a review comment."""
    severity = issue.get("severity", "MEDIUM")
    category = issue.get("category", "general")
    method = issue.get("method", "N/A") 
    
    comment = f"**🤖 {severity}** - {category}\n\n"
    
    if "description" in issue:
        comment += f"{issue['description']}\n\n"
    
    if "recommendation" in issue:
        comment += f"**Recommendation:**\n```python\n{issue['recommendation']}\n```\n\n"
    
    if "impact" in issue:
        comment += f"**Impact:** {issue['impact']}\n\n"
    
    comment += "---\n"
    comment += "Reply with `/apply-logs` to apply this change automatically."
    
    return comment


def format_summary_comment(results: List[Dict[str, Any]]) -> str:
    """Format a summary comment with all issues found."""
    total_issues = sum(len(r.get("analysis", {}).get("issues", [])) for r in results)
    
    comment = "## 🤖 AI Code Analysis Complete\n\n"
    comment += f"Found **{total_issues} logging improvement(s)** across **{len(results)} file(s)**.\n\n"
    
    if total_issues > 0:
        comment += "Each issue has been posted as a separate comment below. "
        comment += "Review each suggestion and reply with `/apply-logs` to apply it.\n\n"
        
        comment += "### Summary by File\n\n"
        for result in results:
            file_path = result.get("file", "unknown")
            analysis = result.get("analysis", {})
            issues = analysis.get("issues", [])
            
            if issues:
                comment += f"- `{file_path}`: {len(issues)} issue(s)\n"
    else:
        comment += "✅ No logging issues found. Great job!\n\n"
    
    comment += "\n*Analysis powered by Cursor AI*\n"
    return comment


def post_issue_comment(
    github_token: str,
    repository: str,
    pr_number: int,
    comment_body: str
) -> bool:
    """Post a general comment on a GitHub PR."""
    owner, repo = repository.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    try:
        response = requests.post(url, headers=headers, json={"body": comment_body})
        response.raise_for_status()
        print(f"✅ Posted comment")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


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
    # test
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
    
    # Post summary comment first
    print("Posting summary comment...")
    summary = format_summary_comment(results)
    if not post_issue_comment(github_token, args.repository, pr_number, summary):
        print("Failed to post summary comment")
        return 1
    
    # Post review comments on specific lines
    total_comments = 0
    for result in results:
        file_path = result.get("file")
        analysis = result.get("analysis", {})
        issues = analysis.get("issues", [])
        
        for issue in issues:
            line = issue.get("line")
            if not line or line == "N/A":
                print(f"Skipping {file_path} - no line number")
                continue
            
            method = issue.get("method", "N/A")
            print(f"Posting review comment on {file_path}:{line} ({method})")
            
            comment = format_review_comment(issue)
            
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
    
    print(f"\n✅ Posted {total_comments} review comment(s) + 1 summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())

