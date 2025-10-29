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
    
    def analyze_files(self, file_paths: List[str], prompt: str, test_mode: bool = False) -> List[Dict[str, Any]]:
        """Analyze multiple files in one request using cursor-agent."""
        print(f"Analyzing {len(file_paths)} files in batch...")
        
        # Test mode: return mock data
        if test_mode:
            print("[TEST MODE] Using mock analysis results")
            return self._generate_mock_results(file_paths)
        
        if not self.cursor_client:
            self.cursor_client = CursorClient(api_key=self.cursor_api_key)
        
        # Build context with all files
        context = "Analyze the following files:\n\n"
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"Skipping {file_path} - file not found")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    file_content = f.read()
                context += f"=== FILE: {file_path} ===\n{file_content}\n\n"
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        try:
            result = self.cursor_client.send_message(prompt, context=context)
            
            # Parse result
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and 'results' in result:
                return result['results']
            else:
                print(f"Unexpected result format: {type(result)}")
                return []
                
        except Exception as e:
            print(f"ERROR: Failed to analyze files: {e}")
            return []
    
    def _generate_mock_results(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Generate mock analysis results for testing."""
        results = []
        for file_path in file_paths:
            results.append({
                "file": file_path,
                "analysis": {
                    "issues": [
                        {
                            "severity": "CRITICAL",
                            "category": "missing-logs",
                            "line": 95,
                            "method": "send_message",
                            "description": "The core method that performs external API calls to cursor-agent lacks any logging. No entry logs with request details, no success logs, no timing metrics, and errors are raised without being logged first. This makes it impossible to troubleshoot API call failures, track request volume, or monitor performance.",
                            "recommendation": "Add structured logging: log entry with prompt length/truncated prompt, log success with response metadata, log duration/timing, and log errors before raising. Example: logger.info('sending_cursor_message', extra={'prompt_length': len(prompt), 'has_context': bool(context), 'correlation_id': correlation_id}); start_time = time.time(); ...; logger.info('cursor_message_success', extra={'duration_ms': (time.time() - start_time) * 1000, 'response_size': len(str(result))}); logger.error('cursor_message_failed', extra={'error': str(e), 'stderr': result.stderr}, exc_info=True)",
                            "impact": "Without logs in send_message, production issues with Cursor API calls cannot be diagnosed. Cannot determine request rates, latency patterns, failure modes, or correlate errors with specific requests. Violates observability best practices for external API integrations."
                        },
                        {
                            "severity": "CRITICAL",
                            "category": "error-context",
                            "line": 75,
                            "method": "install_cursor_cli",
                            "description": "Generic exception handler catches all exceptions and returns False without logging. Installation failures are completely silent, making it impossible to debug why installation attempts fail in production.",
                            "recommendation": "Log exceptions with full context before returning False. Example: except Exception as e: logger.error('cursor_cli_install_failed', extra={'error': str(e), 'error_type': type(e).__name__}, exc_info=True); return False",
                            "impact": "Installation failures in production environments cannot be diagnosed. Security issues, permission problems, network failures, or binary corruption go undetected. No audit trail for installation attempts."
                        },
                        {
                            "severity": "HIGH",
                            "category": "performance-metrics",
                            "line": 119,
                            "method": "send_message",
                            "description": "External API call to cursor-agent subprocess lacks performance timing. No duration metrics collected, no SLA/SLO monitoring possible, cannot identify slow requests or timeout patterns.",
                            "recommendation": "Add timing instrumentation around subprocess call. Example: import time; start_time = time.time(); result = subprocess.run(...); duration_ms = (time.time() - start_time) * 1000; logger.info('cursor_agent_call_completed', extra={'duration_ms': duration_ms, 'returncode': result.returncode}); also log warning if duration exceeds threshold (e.g., >5s)",
                            "impact": "Cannot monitor API latency, detect performance degradation, or alert on slow requests. Cannot establish SLAs or track performance over time. Debugging slow requests is impossible without timing data."
                        },
                        {
                            "severity": "HIGH",
                            "category": "error-context",
                            "line": 132,
                            "method": "send_message",
                            "description": "Exception handlers raise errors without logging them first. Timeout, FileNotFoundError, and generic exceptions are raised but not logged, making error tracking and alerting impossible. Errors lack context like prompt length, correlation IDs, and request metadata.",
                            "recommendation": "Log all exceptions with full context before raising. Example: except subprocess.TimeoutExpired as e: logger.error('cursor_agent_timeout', extra={'timeout_seconds': 300, 'prompt_length': len(prompt)}, exc_info=True); raise; except FileNotFoundError as e: logger.error('cursor_agent_not_found', extra={'search_paths': search_paths}, exc_info=True); raise; except Exception as e: logger.error('cursor_agent_error', extra={'error': str(e), 'error_type': type(e).__name__, 'prompt_length': len(prompt)}, exc_info=True); raise",
                            "impact": "Errors cannot be tracked, monitored, or alerted on. Error rates are unknown. Cannot correlate errors with specific requests or identify patterns. Troubleshooting production incidents requires code changes instead of log analysis."
                        },
                        {
                            "severity": "MEDIUM",
                            "category": "error-context",
                            "line": 164,
                            "method": "_parse_output",
                            "description": "Silent exception catch at line 164 when JSON parsing fails - exception is caught but not logged. Additionally, JSONDecodeError at line 171 is caught but not logged, making it impossible to debug parsing failures or track malformed response patterns.",
                            "recommendation": "Log parsing failures with context. Example: except json.JSONDecodeError as e: logger.warning('cursor_response_parse_failed', extra={'raw_output_preview': raw_output[:200], 'error': str(e)}, exc_info=True); return raw_output. Also log at line 164: except Exception as e: logger.warning('json_extraction_failed', extra={'error': str(e), 'result_field': str(result_field)[:200]}, exc_info=True); pass",
                            "impact": "Parsing failures go undetected, making it impossible to identify when Cursor API response format changes or becomes malformed. Cannot track parse error rates or alert on parsing issues."
                        }
                    ],
                    "summary": "[MOCK] File has 2 logging issues that should be addressed"
                }
            })
        return results


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
            # Use git diff to get changed files (only files in the diff)
            result = subprocess.run(
                ['git', 'diff', '--name-only', '--diff-filter=ACMR', 'origin/main...HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            
            all_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # Filter by file patterns and verify files exist
            filtered_files = []
            for file in all_files:
                # Check if file exists (not deleted)
                if not os.path.exists(file):
                    print(f"Skipping {file} - file deleted")
                    continue
                
                file_path = Path(file)
                for pattern in file_patterns:
                    # Simple pattern matching
                    pattern_ext = pattern.split('.')[-1]
                    if file.endswith(f'.{pattern_ext}'):
                        filtered_files.append(file)
                        break
            
            print(f"Found {len(filtered_files)} changed files in PR diff")
            if filtered_files:
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
    parser.add_argument('--test-mode', action='store_true',
                       help='Use mock data instead of calling Cursor API')
    
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
    
    # Skip Cursor CLI setup in test mode
    if not args.test_mode:
        # Install and verify Cursor CLI
        if not cursor.install_cursor_cli():
            print("ERROR: Failed to install Cursor CLI")
            return 1
        
        if not cursor.verify_setup():
            print("ERROR: Cursor CLI setup verification failed")
            return 1
    else:
        print("[TEST MODE] Skipping Cursor CLI setup")
    
    # Get changed files
    pr_analyzer = GitHubPRAnalyzer(github_token, repository, pr_number)
    changed_files = pr_analyzer.get_changed_files()
    
    if not changed_files:
        print("No relevant files changed in this PR")
        # Write empty results
        with open(args.output_file, 'w') as f:
            json.dump([], f, indent=2)
        return 0
    
    # Analyze all files in one request
    print(f"\n=== Analyzing {len(changed_files)} files ===\n")
    results = cursor.analyze_files(changed_files, prompt, test_mode=args.test_mode)
    
    # Write results to file
    print(f"\n=== Analysis Complete ===")
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {args.output_file}")
    print(f"Total files analyzed: {len(results)}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

