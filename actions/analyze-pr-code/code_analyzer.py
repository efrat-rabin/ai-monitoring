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

# Import patch validation
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_patch import validate_patch_format, fix_patch_format
    PATCH_VALIDATION_AVAILABLE = True
except ImportError:
    PATCH_VALIDATION_AVAILABLE = False
    print("Warning: Patch validation module not available")


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
    
    def analyze_files(self, file_paths: List[str], prompt: str, test_mode: bool = False, use_mock: bool = False, demo_mode: bool = False, verbose: bool = True) -> List[Dict[str, Any]]:
        """Analyze multiple files in one request using cursor-agent."""
        print(f"Analyzing {len(file_paths)} files in batch...")
        
        # Demo mode: load demo-specific mock data
        if demo_mode:
            print("[DEMO MODE] Loading demo mock analysis results")
            return self._load_demo_results(file_paths)
        
        # Use mock mode: load predefined mock data
        if use_mock:
            print("[MOCK MODE] Loading mock analysis results from file")
            return self._load_mock_results()
        
        # Test mode: return generated mock data
        if test_mode:
            print("[TEST MODE] Using generated mock analysis results")
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
            result = self.cursor_client.send_message(prompt, context=context, verbose=verbose)
            
            # Validate and fix patches in the result
            if PATCH_VALIDATION_AVAILABLE:
                result = self._validate_and_fix_patches(result, verbose=verbose)
            
            # Parse result - handle various response formats
            if isinstance(result, list):
                if verbose:
                    print(f"[DEBUG] Got list result with {len(result)} items")
                return result
            elif isinstance(result, dict):
                if verbose:
                    print(f"[DEBUG] Got dict result with keys: {list(result.keys())}")
                
                # Try various dict keys that might contain results
                for key in ['results', 'analysis', 'files', 'data', 'items']:
                    if key in result and isinstance(result[key], list):
                        if verbose:
                            print(f"[DEBUG] Found results in key '{key}'")
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
                        if verbose:
                            print(f"[DEBUG] Formatted {len(formatted_results)} file results from dict")
                        return formatted_results
                
                # Single file analysis - wrap in list
                if verbose:
                    print(f"[DEBUG] Wrapping dict as single file analysis")
                return [{
                    'file': file_paths[0] if file_paths else 'unknown',
                    'analysis': result
                }]
            elif isinstance(result, str):
                if verbose:
                    print(f"[DEBUG] Got string result, length: {len(result)} chars")
                
                # Try to parse string as JSON
                result_stripped = result.strip()
                try:
                    parsed = json.loads(result_stripped)
                    if isinstance(parsed, list):
                        if verbose:
                            print(f"[DEBUG] Parsed string as list with {len(parsed)} items")
                        return parsed
                    elif isinstance(parsed, dict):
                        if verbose:
                            print(f"[DEBUG] Parsed string as dict")
                        return [{'file': file_paths[0] if file_paths else 'unknown', 'analysis': parsed}]
                except json.JSONDecodeError:
                    if verbose:
                        print(f"[DEBUG] String is not valid JSON, extracting JSON from text")
                    
                    # Extract JSON array from text (AI often adds explanatory text despite instructions)
                    import re
                    # Find JSON array starting with [ and ending with ]
                    json_match = re.search(r'\[\s*\{', result_stripped)
                    if json_match:
                        start_pos = json_match.start()
                        # Extract from first [ to end
                        json_str = result_stripped[start_pos:]
                        
                        # Try to parse the extracted JSON
                        try:
                            parsed = json.loads(json_str)
                            if isinstance(parsed, list):
                                if verbose:
                                    print(f"[DEBUG] Extracted and parsed JSON array with {len(parsed)} items")
                                return parsed
                        except json.JSONDecodeError:
                            # JSON might be truncated, try to find the closing ]
                            if verbose:
                                print(f"[DEBUG] Trying to find complete JSON array")
                            
                            # Count brackets to find matching ]
                            bracket_count = 0
                            end_pos = -1
                            for i, char in enumerate(json_str):
                                if char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        end_pos = i + 1
                                        break
                            
                            if end_pos > 0:
                                json_str = json_str[:end_pos]
                                try:
                                    parsed = json.loads(json_str)
                                    if isinstance(parsed, list):
                                        if verbose:
                                            print(f"[DEBUG] Extracted complete JSON array with {len(parsed)} items")
                                        return parsed
                                except json.JSONDecodeError as e:
                                    if verbose:
                                        print(f"[DEBUG] Failed to parse extracted JSON: {e}")
                    
                    # Last attempt: Look for largest valid JSON array
                    if verbose:
                        print(f"[DEBUG] Attempting aggressive JSON extraction...")
                    
                    # Try to find and extract the largest possible JSON array
                    for i in range(len(result_stripped)):
                        if result_stripped[i] == '[':
                            for j in range(len(result_stripped) - 1, i, -1):
                                if result_stripped[j] == ']':
                                    try:
                                        json_str = result_stripped[i:j+1]
                                        parsed = json.loads(json_str)
                                        if isinstance(parsed, list) and len(parsed) > 0:
                                            if verbose:
                                                print(f"[DEBUG] Aggressively extracted JSON array with {len(parsed)} items")
                                            return parsed
                                    except json.JSONDecodeError:
                                        continue
                    
                    # Final fallback: Try to extract JSON using a second AI call
                    print(f"⚠️  Could not parse JSON from AI response, attempting AI extraction...")
                    print(f"Response preview: {result_stripped[:500]}")
                    
                    extracted_result = self._extract_json_with_ai(result_stripped, verbose)
                    if extracted_result:
                        return extracted_result
                    
                    print(f"ERROR: Could not extract valid JSON even after retry")
                    print(f"Full response length: {len(result_stripped)} chars")
                    return []
            else:
                print(f"ERROR: Unexpected result format: {type(result)}")
                print(f"Result preview: {str(result)[:500]}")
                return []
                
        except Exception as e:
            print(f"ERROR: Failed to analyze files: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_json_with_ai(self, original_response: str, verbose: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Use AI to extract JSON from a malformed response.
        
        Args:
            original_response: The original AI response containing JSON mixed with other text
            verbose: Whether to print debug info
            
        Returns:
            Parsed JSON list or None if extraction fails
        """
        try:
            # Load extraction prompt
            extract_prompt_path = '.ai-monitoring/.github/prompts/extract-json.txt'
            if not os.path.exists(extract_prompt_path):
                if verbose:
                    print(f"[DEBUG] Extract prompt file not found: {extract_prompt_path}")
                return None
            
            with open(extract_prompt_path, 'r') as f:
                extract_prompt = f.read()
            
            # Replace placeholder with original response
            extract_prompt = extract_prompt.replace('{original_response}', original_response[:10000])  # Limit size
            
            if verbose:
                print(f"[DEBUG] Sending extraction request to AI")
                print(f"[DEBUG] Extraction prompt length: {len(extract_prompt)} chars")
            
            # Send extraction request
            result = self.cursor_client.send_message(extract_prompt, context="", verbose=verbose)
            
            if verbose:
                print(f"[DEBUG] Extraction result type: {type(result)}")
                print(f"[DEBUG] Extraction result preview: {str(result)[:200]}")
            
            # Try to parse the extracted result
            if isinstance(result, str):
                # Remove any markdown code blocks
                result = result.strip()
                if result.startswith('```'):
                    result = result.split('\n', 1)[1] if '\n' in result else result
                if result.endswith('```'):
                    result = result.rsplit('\n', 1)[0] if '\n' in result else result
                result = result.strip()
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        print(f"✓ Successfully extracted JSON array with {len(parsed)} items")
                        return parsed
                except json.JSONDecodeError:
                    if verbose:
                        print(f"[DEBUG] Extraction result is not valid JSON")
            
            return None
            
        except Exception as e:
            if verbose:
                print(f"[DEBUG] Error during JSON extraction: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _validate_and_fix_patches(self, result: Any, verbose: bool = False) -> Any:
        """Validate and fix patch format in analysis results."""
        if not PATCH_VALIDATION_AVAILABLE:
            return result
        
        def fix_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Fix patches in a list of issues."""
            fixed_issues = []
            for issue in issues:
                if 'patch' in issue and issue['patch']:
                    patch = issue['patch']
                    
                    # Always normalize newlines first (convert literal \n to actual newlines)
                    from validate_patch import normalize_patch_newlines
                    patch = normalize_patch_newlines(patch)
                    issue['patch'] = patch
                    
                    # Then validate and fix format
                    if not validate_patch_format(patch):
                        if verbose:
                            print(f"⚠️  Invalid patch format detected in {issue.get('method', 'unknown')}, attempting to fix...")
                        fixed_patch = fix_patch_format(patch)
                        if validate_patch_format(fixed_patch):
                            issue['patch'] = fixed_patch
                            if verbose:
                                print(f"✅ Patch fixed successfully")
                        else:
                            if verbose:
                                print(f"❌ Could not fix patch format")
                    elif verbose:
                        print(f"✅ Patch format valid for {issue.get('method', 'unknown')}")
                        
                fixed_issues.append(issue)
            return fixed_issues
        
        # Handle different result structures
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and 'analysis' in item:
                    analysis = item['analysis']
                    if isinstance(analysis, dict) and 'issues' in analysis:
                        analysis['issues'] = fix_issues(analysis['issues'])
        elif isinstance(result, dict):
            if 'analysis' in result and isinstance(result['analysis'], dict):
                if 'issues' in result['analysis']:
                    result['analysis']['issues'] = fix_issues(result['analysis']['issues'])
        
        return result
    
    def _load_demo_results(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Load demo-specific mock results based on file paths."""
        # Map file names to their demo mock data files
        demo_mocks = {
            "entity-processor.ts": "demo-mock-entity-processor.json",
            # Add more demo mock files here as needed
        }
        
        # Find matching demo mock file
        for file_path in file_paths:
            file_name = Path(file_path).name
            if file_name in demo_mocks:
                demo_file = Path(__file__).parent / demo_mocks[file_name]
                try:
                    with open(demo_file, 'r') as f:
                        results = json.load(f)
                    print(f"✓ Loaded {len(results)} demo analysis results from {demo_mocks[file_name]}")
                    return results
                except FileNotFoundError:
                    print(f"ERROR: Demo mock file not found at {demo_file}")
                    return []
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse demo mock file: {e}")
                    return []
        
        # No matching demo mock found
        print(f"⚠️  No demo mock data found for files: {file_paths}")
        print(f"   Available demo mocks: {list(demo_mocks.keys())}")
        return []
    
    def _load_mock_results(self) -> List[Dict[str, Any]]:
        """Load mock analysis results from file."""
        mock_file = Path(__file__).parent / "mock-analysis-results.json"
        
        try:
            with open(mock_file, 'r') as f:
                results = json.load(f)
            print(f"✓ Loaded {len(results)} mock analysis results")
            return results
        except FileNotFoundError:
            print(f"ERROR: Mock file not found at {mock_file}")
            return []
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse mock file: {e}")
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
                            "recommendation": "logger.info('sending_cursor_message', extra={'prompt_length': len(prompt), 'has_context': bool(context), 'correlation_id': correlation_id});\nstart_time = time.time();\n# ... existing code ...\nlogger.info('cursor_message_success', extra={'duration_ms': (time.time() - start_time) * 1000, 'response_size': len(str(result))});\n# On error:\nlogger.error('cursor_message_failed', extra={'error': str(e), 'stderr': result.stderr}, exc_info=True)",
                            "impact": "Without logs in send_message, production issues with Cursor API calls cannot be diagnosed. Cannot determine request rates, latency patterns, failure modes, or correlate errors with specific requests. Violates observability best practices for external API integrations."
                        },
                        {
                            "severity": "CRITICAL",
                            "category": "error-context",
                            "line": 75,
                            "method": "install_cursor_cli",
                            "description": "Generic exception handler catches all exceptions and returns False without logging. Installation failures are completely silent, making it impossible to debug why installation attempts fail in production.",
                            "recommendation": "except Exception as e:\n    logger.error('cursor_cli_install_failed', extra={'error': str(e), 'error_type': type(e).__name__}, exc_info=True)\n    return False",
                            "impact": "Installation failures in production environments cannot be diagnosed. Security issues, permission problems, network failures, or binary corruption go undetected. No audit trail for installation attempts."
                        },
                        {
                            "severity": "HIGH",
                            "category": "performance-metrics",
                            "line": 119,
                            "method": "send_message",
                            "description": "External API call to cursor-agent subprocess lacks performance timing. No duration metrics collected, no SLA/SLO monitoring possible, cannot identify slow requests or timeout patterns.",
                            "recommendation": "import time\nstart_time = time.time()\nresult = subprocess.run(...)\nduration_ms = (time.time() - start_time) * 1000\nlogger.info('cursor_agent_call_completed', extra={'duration_ms': duration_ms, 'returncode': result.returncode})\nif duration_ms > 5000:\n    logger.warning('cursor_agent_slow_request', extra={'duration_ms': duration_ms})",
                            "impact": "Cannot monitor API latency, detect performance degradation, or alert on slow requests. Cannot establish SLAs or track performance over time. Debugging slow requests is impossible without timing data."
                        },
                        {
                            "severity": "HIGH",
                            "category": "error-context",
                            "line": 132,
                            "method": "send_message",
                            "description": "Exception handlers raise errors without logging them first. Timeout, FileNotFoundError, and generic exceptions are raised but not logged, making error tracking and alerting impossible. Errors lack context like prompt length, correlation IDs, and request metadata.",
                            "recommendation": "except subprocess.TimeoutExpired as e:\n    logger.error('cursor_agent_timeout', extra={'timeout_seconds': 300, 'prompt_length': len(prompt)}, exc_info=True)\n    raise\nexcept FileNotFoundError as e:\n    logger.error('cursor_agent_not_found', extra={'search_paths': search_paths}, exc_info=True)\n    raise\nexcept Exception as e:\n    logger.error('cursor_agent_error', extra={'error': str(e), 'error_type': type(e).__name__, 'prompt_length': len(prompt)}, exc_info=True)\n    raise",
                            "impact": "Errors cannot be tracked, monitored, or alerted on. Error rates are unknown. Cannot correlate errors with specific requests or identify patterns. Troubleshooting production incidents requires code changes instead of log analysis."
                        },
                        {
                            "severity": "MEDIUM",
                            "category": "error-context",
                            "line": 164,
                            "method": "_parse_output",
                            "description": "Silent exception catch at line 164 when JSON parsing fails - exception is caught but not logged. Additionally, JSONDecodeError at line 171 is caught but not logged, making it impossible to debug parsing failures or track malformed response patterns.",
                            "recommendation": "except json.JSONDecodeError as e:\n    logger.warning('cursor_response_parse_failed', extra={'raw_output_preview': raw_output[:200], 'error': str(e)}, exc_info=True)\n    return raw_output\n# At line 164:\nexcept Exception as e:\n    logger.warning('json_extraction_failed', extra={'error': str(e), 'result_field': str(result_field)[:200]}, exc_info=True)\n    pass",
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
                       default='.ai-monitoring/.github/prompts/analyze-logs.txt',
                       help='Path to prompt file')
    parser.add_argument('--output-file', type=str,
                       default='analysis-results.json',
                       help='Output file for analysis results')
    parser.add_argument('--test-mode', action='store_true',
                       help='Use generated mock data instead of calling Cursor API')
    parser.add_argument('--use-mock', action='store_true',
                       help='Use predefined mock data from mock-analysis-results.json')
    parser.add_argument('--demo', action='store_true',
                       help='Use demo mode with file-specific mock data')
    parser.add_argument('--use-cursor', action='store_true', default=True,
                       help='Use Cursor AI for analysis (default: True)')
    
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
    
    # Determine which mode to use
    # Priority: --demo > --use-mock > --test-mode > --use-cursor (default)
    use_cursor = not args.demo and not args.use_mock and not args.test_mode
    
    # Skip Cursor CLI setup in demo, test mode, or mock mode
    if use_cursor:
        # Install and verify Cursor CLI
        if not cursor.install_cursor_cli():
            print("ERROR: Failed to install Cursor CLI")
            return 1
        
        if not cursor.verify_setup():
            print("ERROR: Cursor CLI setup verification failed")
            return 1
    else:
        if args.demo:
            print("[DEMO MODE] Using demo-specific mock data")
        elif args.use_mock:
            print("[MOCK MODE] Using predefined mock data from file")
        elif args.test_mode:
            print("[TEST MODE] Using generated mock data")
        else:
            print("[SKIP MODE] Cursor CLI setup skipped")
    
    # Get changed files
    pr_analyzer = GitHubPRAnalyzer(github_token, repository, pr_number)
    changed_files = pr_analyzer.get_changed_files()
    
    if not changed_files:
        print("No relevant files changed in this PR")
        # Write empty results
        with open(args.output_file, 'w') as f:
            json.dump([], f, indent=2)
        
        # Set output for GitHub Actions
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write("has_issues=false\n")
                f.write("total_issues=0\n")
        
        print("\n✓ No files to analyze - skipping")
        return 0
    
    # Analyze all files in one request
    print(f"\n=== Analyzing {len(changed_files)} files ===\n")
    results = cursor.analyze_files(changed_files, prompt, test_mode=args.test_mode, use_mock=args.use_mock, demo_mode=args.demo, verbose=verbose)
    
    # Write results to file
    print(f"\n=== Analysis Complete ===")
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {args.output_file}")
    print(f"Total files analyzed: {len(results)}")
    
    # Check if any issues were found
    total_issues = 0
    for result in results:
        if 'analysis' in result and 'issues' in result['analysis']:
            total_issues += len(result['analysis']['issues'])
    
    print(f"Total issues found: {total_issues}")
    
    # Set output for GitHub Actions
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"has_issues={'true' if total_issues > 0 else 'false'}\n")
            f.write(f"total_issues={total_issues}\n")
    
    # Print results to logs if verbose is enabled
    if verbose:
        print(f"\n=== Analysis Results JSON ===")
        print(json.dumps(results, indent=2))
        print(f"=== End Analysis Results ===\n")
    
    # Exit with message if no issues found
    if total_issues == 0:
        print("\n✓ No issues found - analysis complete!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

