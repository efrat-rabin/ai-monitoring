#!/usr/bin/env python3
"""
Analyze PR Code Action
This script analyzes pull request code and provides insights using Cursor AI.
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add libs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))
from cursor_client import CursorClient


class CursorAnalyzer:
    """Handles file analysis using Cursor CLI."""
    
    def __init__(self, cursor_api_key: Optional[str] = None):
        self.cursor_api_key = cursor_api_key or os.getenv('CURSOR_API_KEY')
        self.cursor_client = None
        
    def install_cursor_cli(self) -> bool:
        """Install Cursor CLI if not already installed."""
        print("=== Installing Cursor CLI ===")
        
        try:
            self.cursor_client = CursorClient(api_key=self.cursor_api_key)
            if self.cursor_client.install_cursor_cli():
                print(f"✓ cursor-agent installed")
                return True
            else:
                print("ERROR: cursor-agent not found after installation")
                return False
        except Exception as e:
            print(f"ERROR: Failed to install Cursor CLI: {e}")
            return False
    
    def verify_setup(self) -> bool:
        """Verify cursor-agent is available and API key is set."""
        if not self.cursor_client:
            try:
                self.cursor_client = CursorClient(api_key=self.cursor_api_key)
            except ValueError as e:
                print(f"ERROR: {e}")
                return False
        
        if self.cursor_client.verify_setup():
            print(f"✓ cursor-agent available")
            print("✓ CURSOR_API_KEY is set")
            return True
        else:
            print("ERROR: Cursor CLI setup verification failed")
            return False
    
    def analyze_file(self, file_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze a single file using cursor-agent."""
        print(f"\n{'='*50}")
        print(f"Analyzing file: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"ERROR: File does not exist: {file_path}")
            return {"error": "File not found"}
        
        file_size = sum(1 for _ in open(file_path))
        print(f"File size: {file_size} lines")
        print(f"{'='*50}")
        
        try:
            # Read file content as context
            with open(file_path, 'r') as f:
                file_content = f.read()
            
            # Use CursorClient to send message
            if not self.cursor_client:
                self.cursor_client = CursorClient(api_key=self.cursor_api_key)
            
            context = f"File: {file_path}\n\n{file_content}"
            
            print("Running cursor-agent command...")
            result = self.cursor_client.send_message(prompt, context=context)
            
            print("Parsed analysis JSON:")
            print(json.dumps(result, indent=2))
            print(f"{'='*50}")
            
            return result if isinstance(result, dict) else {"result": result}
            
        except Exception as e:
            print(f"ERROR: Failed to analyze file: {e}")
            return {"error": str(e)}


class GitHubPRAnalyzer:
    """Handles GitHub PR operations and file retrieval."""
    
    def __init__(self, github_token: str, repository: str, pr_number: str):
        self.github_token = github_token
        self.repository = repository
        self.pr_number = pr_number
    
    def get_changed_files(self, file_patterns: Optional[List[str]] = None) -> List[str]:
        """Get list of changed files in the PR."""
        if file_patterns is None:
            file_patterns = ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx', 
                           '**/*.py', '**/*.go']
        
        print(f"Getting changed files for PR #{self.pr_number}...")
        
        try:
            # Use git diff to get changed files
            # Assumes we're in a checked-out repository
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'main...HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            
            all_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # Filter by file patterns
            filtered_files = []
            for file in all_files:
                file_path = Path(file)
                for pattern in file_patterns:
                    # Simple pattern matching (could be enhanced with glob)
                    pattern_ext = pattern.split('.')[-1]
                    if file.endswith(f'.{pattern_ext}'):
                        filtered_files.append(file)
                        break
            
            print(f"Found {len(filtered_files)} changed files")
            print(f"Files: {', '.join(filtered_files)}")
            
            return filtered_files
            
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to get changed files: {e}")
            return []


def main():
    """Main entry point for the analyze PR code action."""
    parser = argparse.ArgumentParser(description='Analyze PR code with Cursor AI')
    parser.add_argument('--pr-number', type=str, help='Pull request number')
    parser.add_argument('--repository', type=str, help='Repository (owner/repo)')
    parser.add_argument('--prompt-file', type=str, 
                       default='.github/prompts/analyze-logs.txt',
                       help='Path to prompt file')
    parser.add_argument('--output-file', type=str,
                       default='analysis-results.json',
                       help='Output file for analysis results')
    
    args = parser.parse_args()
    
    # Get environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    cursor_api_key = os.getenv('CURSOR_API_KEY')
    pr_number = args.pr_number or os.getenv('PR_NUMBER')
    repository = args.repository or os.getenv('REPOSITORY')
    
    print("=== Analyze PR Code Action ===")
    print(f"PR Number: {pr_number}")
    print(f"Repository: {repository}")
    print(f"GitHub Token present: {bool(github_token)}")
    print(f"Cursor API Key present: {bool(cursor_api_key)}")
    print(f"Prompt file: {args.prompt_file}")
    print(f"Output file: {args.output_file}")
    print("="*50)
    
    # Validate inputs
    if not all([github_token, pr_number, repository]):
        print("ERROR: Missing required inputs (github_token, pr_number, repository)")
        return 1
    
    # Check if prompt file exists
    if not os.path.exists(args.prompt_file):
        print(f"ERROR: Prompt file not found at {args.prompt_file}")
        print("Please create a prompt file with analysis instructions")
        return 1
    
    # Read prompt
    with open(args.prompt_file, 'r') as f:
        prompt = f.read()
    
    print(f"✓ Prompt file loaded ({len(prompt)} characters)")
    
    # Initialize Cursor analyzer
    cursor = CursorAnalyzer(cursor_api_key)
    
    # Install and verify Cursor CLI
    if not cursor.install_cursor_cli():
        print("ERROR: Failed to install Cursor CLI")
        return 1
    
    if not cursor.verify_setup():
        print("ERROR: Cursor CLI setup verification failed")
        return 1
    
    # Get changed files
    pr_analyzer = GitHubPRAnalyzer(github_token, repository, pr_number)
    changed_files = pr_analyzer.get_changed_files()
    
    if not changed_files:
        print("No relevant files changed in this PR")
        # Write empty results
        with open(args.output_file, 'w') as f:
            json.dump([], f, indent=2)
        return 0
    
    # Analyze each file
    print(f"\n=== Starting Analysis of {len(changed_files)} files ===\n")
    results = []
    
    for file_path in changed_files:
        analysis = cursor.analyze_file(file_path, prompt)
        results.append({
            "file": file_path,
            "analysis": analysis
        })
    
    # Write results to file
    print(f"\n=== Analysis Complete ===")
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {args.output_file}")
    print(f"Total files analyzed: {len(results)}")
    
    # Pretty print final output
    print("\nFinal Analysis Results:")
    print(json.dumps(results, indent=2))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

