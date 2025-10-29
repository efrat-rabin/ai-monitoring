#!/usr/bin/env python3
"""
Post PR Comment Script
Posts individual comments for each suggested change.
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, List, Any


def format_issue_comment(file_path: str, issue: Dict[str, Any], commit_sha: str = "") -> str:
    """Format a single issue as a markdown comment."""
    severity = issue.get("severity", "MEDIUM")
    category = issue.get("category", "general")
    method = issue.get("method", "N/A")
    line = issue.get("line", "N/A")
    
    comment = f"## 🤖 Logging Suggestion: {severity}\n\n"
    comment += f"**File:** `{file_path}`\n"
    comment += f"**Method:** `{method}`\n"
    comment += f"**Line:** {line}\n"
    
    if commit_sha and line != "N/A":
        comment += f"**Location:** [`{file_path}:{line}`](../blob/{commit_sha}/{file_path}#L{line})\n"
    
    comment += f"**Category:** {category}\n\n"
    
    if "description" in issue:
        comment += f"### Description\n{issue['description']}\n\n"
    
    if "recommendation" in issue:
        comment += f"### Recommendation\n```python\n{issue['recommendation']}\n```\n\n"
    
    if "impact" in issue:
        comment += f"### Impact\n{issue['impact']}\n\n"
    
    comment += "---\n\n"
    comment += "### 🤖 Auto-Apply\n\n"
    comment += "To apply this change, reply to this comment with:\n\n"
    comment += "```\n/apply-logs\n```\n\n"
    comment += "*Powered by Cursor AI*\n"
    
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


def post_comment(
    github_token: str,
    repository: str,
    pr_number: int,
    comment_body: str
) -> bool:
    """Post a comment on a GitHub PR."""
    
    # Parse repository (owner/repo)
    try:
        owner, repo = repository.split("/")
    except ValueError:
        print(f"ERROR: Invalid repository format: {repository}")
        print("Expected format: owner/repo")
        return False
    
    # GitHub API endpoint
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "body": comment_body
    }
    
    print(f"Posting comment to PR #{pr_number} in {repository}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        print(f"✅ Successfully posted comment")
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to post comment: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Post analysis results as PR comments")
    parser.add_argument("--pr-number", type=str, required=True, help="Pull request number")
    parser.add_argument("--repository", type=str, required=True, help="Repository (owner/repo)")
    parser.add_argument("--results-file", type=str, default="analysis-results.json", help="Results file")
    parser.add_argument("--commit-sha", type=str, help="Commit SHA for linking to files")
    
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
    if not post_comment(github_token, args.repository, pr_number, summary):
        print("Failed to post summary comment")
        return 1
    
    # Post individual comments for each issue
    total_issues = 0
    for result in results:
        file_path = result.get("file", "unknown")
        analysis = result.get("analysis", {})
        issues = analysis.get("issues", [])
        
        for issue in issues:
            print(f"Posting comment for {file_path} - {issue.get('method', 'N/A')}")
            comment = format_issue_comment(file_path, issue, args.commit_sha)
            
            if post_comment(github_token, args.repository, pr_number, comment):
                total_issues += 1
            else:
                print(f"Failed to post comment for {file_path}")
    
    print(f"\n✅ Posted {total_issues} issue comment(s) + 1 summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())

