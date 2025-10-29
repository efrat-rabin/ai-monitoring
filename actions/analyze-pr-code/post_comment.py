#!/usr/bin/env python3
"""
Post PR Comment Script
Posts analysis results as a comment on a GitHub Pull Request.
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, List, Any


def format_comment(results: List[Dict[str, Any]], commit_sha: str = "") -> str:
    """Format analysis results as a markdown comment."""
    comment = "## 🤖 AI Code Analysis Results\n\n"
    
    if len(results) == 0:
        comment += "No files were analyzed in this PR.\n"
    else:
        for result in results:
            file_path = result.get("file", "unknown")
            analysis = result.get("analysis", {})
            
            comment += f"### 📄 File: `{file_path}`\n\n"
            
            if "error" in analysis:
                comment += f"❌ **Error:** {analysis['error']}\n\n"
            elif "issues" in analysis and len(analysis["issues"]) > 0:
                issues = analysis["issues"]
                comment += f"**Found {len(issues)} issue(s):**\n\n"
                
                for issue in issues:
                    severity = issue.get("severity", "MEDIUM")
                    category = issue.get("category", "general")
                    method = issue.get("method", "N/A")
                    
                    comment += "<details>\n"
                    comment += f"<summary><strong>{severity}</strong> - {category}: {method}</summary>\n\n"
                    comment += f"**File:** `{file_path}`\n\n"
                    
                    if "line" in issue:
                        line = issue["line"]
                        comment += f"**Line:** {line}\n\n"
                        if commit_sha:
                            comment += f"**Location:** [`{file_path}:{line}`](../blob/{commit_sha}/{file_path}#L{line})\n\n"
                    
                    if "description" in issue:
                        comment += f"**Description:** {issue['description']}\n\n"
                    
                    if "recommendation" in issue:
                        comment += f"**Recommendation:**\n```typescript\n{issue['recommendation']}\n```\n\n"
                    
                    if "impact" in issue:
                        comment += f"**Impact:** {issue['impact']}\n\n"
                    
                    comment += "</details>\n\n"
            
            if "summary" in analysis:
                comment += f"**Summary:** {analysis['summary']}\n\n"
            
            comment += "---\n\n"
    
    comment += "### 🤖 Auto-Apply Available\n\n"
    comment += "Want to automatically apply these logging improvements? Reply to this comment with:\n\n"
    comment += "```\n/apply-logs\n```\n\n"
    comment += "The AI will automatically apply all suggested improvements and commit them to this PR.\n\n"
    comment += "---\n\n"
    comment += "*Analysis powered by Cursor AI*\n"
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
    parser = argparse.ArgumentParser(description="Post analysis results as PR comment")
    parser.add_argument("--pr-number", type=str, required=True, help="Pull request number")
    parser.add_argument("--repository", type=str, required=True, help="Repository (owner/repo)")
    parser.add_argument("--results-file", type=str, default="analysis-results.json", help="Results file")
    parser.add_argument("--commit-sha", type=str, help="Commit SHA for linking to files")
    
    args = parser.parse_args()
    
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        return 1
    
    # Read analysis results
    try:
        with open(args.results_file, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Results file not found: {args.results_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in results file: {e}")
        return 1
    
    # Format comment
    comment_body = format_comment(results, args.commit_sha)
    
    # Post comment
    success = post_comment(
        github_token=github_token,
        repository=args.repository,
        pr_number=int(args.pr_number),
        comment_body=comment_body
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

