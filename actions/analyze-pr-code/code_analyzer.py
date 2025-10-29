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
import requests
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
            
            # Parse result - handle various response formats
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                # Try various dict keys that might contain results
                for key in ['results', 'analysis', 'files', 'data', 'items']:
                    if key in result and isinstance(result[key], list):
                        return result[key]
                
                # If dict has file path keys, convert to list format
                if any(isinstance(v, dict) for v in result.values()):
                    formatted_results = []
                    for file_path, analysis in result.items():
                        if isinstance(analysis, dict):
                            formatted_results.append({
                                'file': file_path,
                                'analysis': analysis
                            })
                    if formatted_results:
                        return formatted_results
                
                # Single file analysis - wrap in list
                print(f"Got dict result, wrapping as single file analysis")
                return [{
                    'file': file_paths[0] if file_paths else 'unknown',
                    'analysis': result
                }]
            elif isinstance(result, str):
                # Try to parse string as JSON
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        return parsed
                    elif isinstance(parsed, dict):
                        return [{'file': file_paths[0] if file_paths else 'unknown', 'analysis': parsed}]
                except json.JSONDecodeError:
                    pass
                
                # Return raw text as analysis
                print(f"Got text result, wrapping as analysis")
                return [{
                    'file': file_paths[0] if file_paths else 'unknown',
                    'analysis': {'response': result}
                }]
            else:
                print(f"ERROR: Unexpected result format: {type(result)}")
                print(f"Result preview: {str(result)[:500]}")
                return []
                
        except Exception as e:
            print(f"ERROR: Failed to analyze files: {e}")
            import traceback
            traceback.print_exc()
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
        """Get list of changed files in the PR using GitHub API."""
        print(f"Getting changed files for PR #{self.pr_number}...")
        
        try:
            # Use GitHub API to get PR files
            api_url = f"https://api.github.com/repos/{self.repository}/pulls/{self.pr_number}/files"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            pr_files = response.json()
            print(f"Found {len(pr_files)} total files in PR")
            
            # Extract filenames (only added or modified, not deleted)
            changed_files = []
            for file_info in pr_files:
                status = file_info.get('status', '')
                filename = file_info.get('filename', '')
                
                # Include: added, modified, renamed, copied
                # Exclude: removed, deleted
                if status in ['added', 'modified', 'renamed', 'copied'] and filename:
                    # Check if file exists locally
                    if not os.path.exists(filename):
                        print(f"  - {filename} ({status}) - file not found locally, skipping")
                        continue
                    
                    changed_files.append(filename)
                    print(f"  - {filename} ({status})")
            
            print(f"Found {len(changed_files)} files to analyze")
            if changed_files:
                print(f"Files to analyze: {', '.join(changed_files)}")
            
            return changed_files
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to get changed files from GitHub API: {e}")
            return []
        except Exception as e:
            print(f"ERROR: Unexpected error getting changed files: {e}")
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
    verbose = os.getenv('VERBOSE', 'true').lower() in ('true', '1', 'yes')
    
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
    
    # Print results to logs if verbose is enabled
    if verbose:
        print(f"\n=== Analysis Results JSON ===")
        print(json.dumps(results, indent=2))
        print(f"=== End Analysis Results ===\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

