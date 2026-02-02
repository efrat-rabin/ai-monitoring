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

    def _truncate_for_cli(self, text: str, max_chars: int, label: str, verbose: bool = False) -> str:
        """Truncate very large prompt/context blocks to avoid OS argv limits.

        This does not change the analysis prompt itself; it only limits the size of
        contextual payload sent to the CLI.
        """
        if max_chars <= 0 or len(text) <= max_chars:
            return text

        suffix = f"\n\n...[TRUNCATED {label}: {len(text)} chars total]...\n"
        keep = max(0, max_chars - len(suffix))
        truncated = text[:keep] + suffix
        if verbose:
            print(f"[DEBUG] Truncated {label}: {len(text)} -> {len(truncated)} chars (limit {max_chars})")
        return truncated

    def _send_batched(self, prompt: str, base_context: str, file_chunks: List[Dict[str, Any]], verbose: bool = True) -> List[Dict[str, Any]]:
        """Send analysis requests in batches to avoid 'Argument list too long'."""
        if not self.cursor_client:
            self.cursor_client = CursorClient(api_key=self.cursor_api_key)

        # Keep well below typical Linux ARG_MAX (~2MB) since the CLI payload is passed as argv.
        max_chars = int(os.getenv("CURSOR_AGENT_MAX_PROMPT_CHARS", "250000"))

        all_results: List[Dict[str, Any]] = []
        batch_context = base_context
        batch_files: List[str] = []

        def flush():
            nonlocal batch_context, batch_files, all_results
            if not batch_files:
                return

            result = self.cursor_client.send_message(prompt, context=batch_context, verbose=verbose)
            if PATCH_VALIDATION_AVAILABLE:
                result = self._validate_and_fix_patches(result, verbose=verbose)
            all_results.extend(self._parse_analysis_result(result, batch_files, verbose))

            batch_context = base_context
            batch_files = []

        for item in file_chunks:
            file_path = item["file"]
            chunk = item["chunk"]

            # If a single chunk is too big, truncate it so the subprocess argv stays safe.
            max_chunk_chars = max(1000, max_chars - len(base_context) - 1000)
            chunk = self._truncate_for_cli(chunk, max_chunk_chars, label=f"context for {file_path}", verbose=verbose)

            if (len(batch_context) + len(chunk)) > max_chars and batch_files:
                flush()

            batch_context += chunk
            batch_files.append(file_path)

        flush()
        return all_results
        
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
    
    def analyze_diffs(self, diff_data: List[Dict[str, Any]], prompt: str, context_lines: int = 5, verbose: bool = True) -> List[Dict[str, Any]]:
        """Analyze PR diffs with surrounding context using cursor-agent.
        
        Args:
            diff_data: List of dicts from GitHubPRAnalyzer.get_changed_files_with_diff()
                       Each dict has: file, patch, line_ranges, added_lines, status
            prompt: The analysis prompt to use
            context_lines: Number of context lines to include around changes
            verbose: Whether to print debug output
            
        Returns:
            List of analysis results per file
        """
        print(f"Analyzing {len(diff_data)} file diffs...")
        
        if not self.cursor_client:
            self.cursor_client = CursorClient(api_key=self.cursor_api_key)
        
        try:
            base_context = (
                "Analyze the following PR DIFFS (not full files).\n"
                "Focus ONLY on lines that were added/modified (lines starting with + in the diff).\n\n"
            )

            # Keep well below typical Linux ARG_MAX (~2MB) since the CLI payload is passed as argv.
            max_chars = int(os.getenv("CURSOR_AGENT_MAX_PROMPT_CHARS", "250000"))

            all_results: List[Dict[str, Any]] = []

            for file_info in diff_data:
                file_path = file_info["file"]
                patch = file_info.get("patch", "")
                line_ranges = file_info.get("line_ranges", [])
                added_lines = file_info.get("added_lines", [])

                chunk = f"=== FILE: {file_path} ===\n"
                chunk += f"Status: {file_info.get('status', 'unknown')}\n"
                if added_lines:
                    chunk += f"Added/modified line numbers: {added_lines}\n"

                if patch:
                    chunk += f"\n--- DIFF ---\n{patch}\n--- END DIFF ---\n"

                if line_ranges:
                    code_context = self._get_context_around_diff(file_path, line_ranges, context_lines)
                    chunk += f"\n--- CODE CONTEXT (with line numbers) ---\n{code_context}\n--- END CONTEXT ---\n"

                chunk += "\n"

                # Ensure even a single file's payload can't exceed argv limits.
                max_chunk_chars = max(1000, max_chars - len(base_context) - 1000)
                chunk = self._truncate_for_cli(chunk, max_chunk_chars, label=f"context for {file_path}", verbose=verbose)

                try:
                    result = self.cursor_client.send_message(prompt, context=base_context + chunk, verbose=verbose)
                    if PATCH_VALIDATION_AVAILABLE:
                        result = self._validate_and_fix_patches(result, verbose=verbose)

                    # Parse this file's response only. This avoids any cross-file ambiguity.
                    parsed = self._parse_analysis_result(result, [file_path], verbose)
                    all_results.extend(parsed)
                except Exception as e:
                    print(f"ERROR: Failed to analyze {file_path}: {e}")
                    all_results.append({
                        "file": file_path,
                        "analysis": {
                            "issues": [],
                            "summary": f"Error analyzing file: {e}"
                        }
                    })

            return all_results
                
        except Exception as e:
            print(f"ERROR: Failed to analyze diffs: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_analysis_result(self, result: Any, file_paths: List[str], verbose: bool = True) -> List[Dict[str, Any]]:
        """Parse the AI analysis result into a standardized format.
        
        Args:
            result: The raw result from cursor-agent
            file_paths: List of file paths being analyzed (for fallback)
            verbose: Whether to print debug output
            
        Returns:
            List of analysis results per file
        """
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
    
    # =====================================================================
    # MOCK MODES - COMMENTED OUT (can be re-enabled if needed)
    # =====================================================================
    # def analyze_files(self, file_paths: List[str], prompt: str, test_mode: bool = False, use_mock: bool = False, demo_mode: bool = False, verbose: bool = True) -> List[Dict[str, Any]]:
    #     """Analyze multiple files in one request using cursor-agent."""
    #     print(f"Analyzing {len(file_paths)} files in batch...")
    #     
    #     # Demo mode: load demo-specific mock data
    #     if demo_mode:
    #         print("[DEMO MODE] Loading demo mock analysis results")
    #         return self._load_demo_results(file_paths)
    #     
    #     # Use mock mode: load predefined mock data
    #     if use_mock:
    #         print("[MOCK MODE] Loading mock analysis results from file")
    #         return self._load_mock_results()
    #     
    #     # Test mode: return generated mock data
    #     if test_mode:
    #         print("[TEST MODE] Using generated mock analysis results")
    #         return self._generate_mock_results(file_paths)
    #     
    #     ... rest of old implementation ...
    # =====================================================================
    
    def analyze_files(self, file_paths: List[str], prompt: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """Analyze multiple files in one request using cursor-agent.
        
        Note: Mock modes have been disabled. Use analyze_diffs() for diff-based analysis.
        """
        print(f"Analyzing {len(file_paths)} files in batch...")
        
        if not self.cursor_client:
            self.cursor_client = CursorClient(api_key=self.cursor_api_key)
        
        try:
            base_context = "Analyze the following files:\n\n"

            file_chunks: List[Dict[str, Any]] = []
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    print(f"Skipping {file_path} - file not found")
                    continue

                try:
                    with open(file_path, "r") as f:
                        file_content = f.read()
                    chunk = f"=== FILE: {file_path} ===\n{file_content}\n\n"
                    file_chunks.append({"file": file_path, "chunk": chunk})
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

            return self._send_batched(prompt, base_context, file_chunks, verbose=verbose)
                
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
    
    def _get_context_around_diff(self, file_path: str, line_ranges: List[Dict[str, int]], 
                                    context_lines: int = 5) -> str:
        """Extract code context around changed line ranges from a file.
        
        Args:
            file_path: Path to the source file
            line_ranges: List of dicts with 'start' and 'end' line numbers
            context_lines: Number of lines to include before/after each range
            
        Returns:
            String with the relevant code sections and line numbers
        """
        if not os.path.exists(file_path):
            return f"[File not found: {file_path}]"
        
        try:
            with open(file_path, 'r') as f:
                all_lines = f.readlines()
        except Exception as e:
            return f"[Error reading file: {e}]"
        
        if not line_ranges:
            return "[No line ranges to extract]"
        
        # Merge overlapping ranges with context
        expanded_ranges = []
        for r in line_ranges:
            start = max(1, r['start'] - context_lines)
            end = min(len(all_lines), r['end'] + context_lines)
            expanded_ranges.append({'start': start, 'end': end})
        
        # Sort and merge overlapping ranges
        expanded_ranges.sort(key=lambda x: x['start'])
        merged_ranges = []
        for r in expanded_ranges:
            if merged_ranges and r['start'] <= merged_ranges[-1]['end'] + 1:
                # Merge with previous range
                merged_ranges[-1]['end'] = max(merged_ranges[-1]['end'], r['end'])
            else:
                merged_ranges.append(r.copy())
        
        # Extract the code sections
        sections = []
        for r in merged_ranges:
            section_lines = []
            for line_num in range(r['start'], r['end'] + 1):
                if line_num <= len(all_lines):
                    line_content = all_lines[line_num - 1].rstrip('\n')
                    section_lines.append(f"{line_num:4d} | {line_content}")
            
            if section_lines:
                sections.append(f"Lines {r['start']}-{r['end']}:\n" + '\n'.join(section_lines))
        
        return '\n\n'.join(sections)
    
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
    
    # =====================================================================
    # MOCK METHODS - COMMENTED OUT (can be re-enabled if needed)
    # =====================================================================
    # def _load_demo_results(self, file_paths: List[str]) -> List[Dict[str, Any]]:
    #     """Load demo-specific mock results based on file paths."""
    #     # Map file names to their demo mock data files
    #     demo_mocks = {
    #         "entity-processor.ts": "demo-mock-entity-processor.json",
    #         # Add more demo mock files here as needed
    #     }
    #     
    #     # Find matching demo mock file
    #     for file_path in file_paths:
    #         file_name = Path(file_path).name
    #         if file_name in demo_mocks:
    #             demo_file = Path(__file__).parent / demo_mocks[file_name]
    #             try:
    #                 with open(demo_file, 'r') as f:
    #                     results = json.load(f)
    #                 print(f"✓ Loaded {len(results)} demo analysis results from {demo_mocks[file_name]}")
    #                 return results
    #             except FileNotFoundError:
    #                 print(f"ERROR: Demo mock file not found at {demo_file}")
    #                 return []
    #             except json.JSONDecodeError as e:
    #                 print(f"ERROR: Failed to parse demo mock file: {e}")
    #                 return []
    #     
    #     # No matching demo mock found
    #     print(f"⚠️  No demo mock data found for files: {file_paths}")
    #     print(f"   Available demo mocks: {list(demo_mocks.keys())}")
    #     return []
    # 
    # def _load_mock_results(self) -> List[Dict[str, Any]]:
    #     """Load mock analysis results from file."""
    #     mock_file = Path(__file__).parent / "mock-analysis-results.json"
    #     
    #     try:
    #         with open(mock_file, 'r') as f:
    #             results = json.load(f)
    #         print(f"✓ Loaded {len(results)} mock analysis results")
    #         return results
    #     except FileNotFoundError:
    #         print(f"ERROR: Mock file not found at {mock_file}")
    #         return []
    #     except json.JSONDecodeError as e:
    #         print(f"ERROR: Failed to parse mock file: {e}")
    #         return []
    # 
    # def _generate_mock_results(self, file_paths: List[str]) -> List[Dict[str, Any]]:
    #     """Generate mock analysis results for testing."""
    #     results = []
    #     for file_path in file_paths:
    #         results.append({
    #             "file": file_path,
    #             "analysis": {
    #                 "issues": [
    #                     {
    #                         "severity": "CRITICAL",
    #                         "category": "missing-logs",
    #                         "line": 95,
    #                         "method": "send_message",
    #                         "description": "...",
    #                         "recommendation": "...",
    #                         "impact": "..."
    #                     }
    #                 ],
    #                 "summary": "[MOCK] File has logging issues that should be addressed"
    #             }
    #         })
    #     return results
    # =====================================================================


class GitHubPRAnalyzer:
    """Handles GitHub PR operations and file retrieval."""
    
    def __init__(self, github_token: str, repository: str, pr_number: str):
        self.github_token = github_token
        self.repository = repository
        self.pr_number = pr_number
    
    def _parse_diff_line_ranges(self, patch: str) -> List[Dict[str, int]]:
        """Parse diff hunk headers to extract changed line ranges.
        
        Args:
            patch: The unified diff patch string from GitHub API
            
        Returns:
            List of dicts with 'start' and 'end' line numbers for each hunk
        """
        import re
        ranges = []
        # Match hunk headers like @@ -10,5 +10,7 @@
        hunk_pattern = re.compile(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
        
        for match in hunk_pattern.finditer(patch):
            start_line = int(match.group(1))
            line_count = int(match.group(2)) if match.group(2) else 1
            ranges.append({
                'start': start_line,
                'end': start_line + line_count - 1
            })
        
        return ranges
    
    def _get_added_line_numbers(self, patch: str) -> List[int]:
        """Extract line numbers of added/modified lines (lines starting with +).
        
        Args:
            patch: The unified diff patch string
            
        Returns:
            List of line numbers that were added/modified
        """
        added_lines = []
        current_line = 0
        
        for line in patch.split('\n'):
            if line.startswith('@@'):
                # Parse hunk header to get starting line number
                import re
                match = re.search(r'\+(\d+)', line)
                if match:
                    current_line = int(match.group(1))
            elif line.startswith('+') and not line.startswith('+++'):
                # This is an added line
                added_lines.append(current_line)
                current_line += 1
            elif line.startswith('-') and not line.startswith('---'):
                # Removed line - don't increment current_line
                pass
            elif not line.startswith('\\'):  # Ignore "\ No newline at end of file"
                # Context line
                current_line += 1
        
        return added_lines
    
    def get_changed_files_with_diff(self, file_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get changed files with their diff patches from the PR.
        
        Returns:
            List of dicts containing:
            - file: file path
            - patch: the unified diff patch
            - line_ranges: list of {start, end} dicts for changed hunks
            - added_lines: list of line numbers that were added/modified
            - status: file status (added, modified, etc.)
        """
        print(f"Getting changed files with diffs for PR #{self.pr_number}...")
        
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
            
            # Extract file info with patches
            changed_files = []
            for file_info in pr_files:
                status = file_info.get('status', '')
                filename = file_info.get('filename', '')
                patch = file_info.get('patch', '')
                
                # Include: added, modified, renamed, copied
                # Exclude: removed, deleted
                if status in ['added', 'modified', 'renamed', 'copied'] and filename:
                    # Only analyze a strict whitelist of source files.
                    # Requested: js, ts, python (treat .jsx/.tsx as js/ts variants).
                    allowed_exts = {'.js', '.jsx', '.ts', '.tsx', '.py'}
                    ext = Path(filename).suffix.lower()
                    if ext not in allowed_exts:
                        print(f"  - {filename} ({status}) - unsupported file type ({ext or 'no extension'}), skipping")
                        continue

                    # Check if file exists locally
                    if not os.path.exists(filename):
                        print(f"  - {filename} ({status}) - file not found locally, skipping")
                        continue
                    
                    # Parse line ranges and added lines from the patch
                    line_ranges = self._parse_diff_line_ranges(patch) if patch else []
                    added_lines = self._get_added_line_numbers(patch) if patch else []
                    
                    file_data = {
                        'file': filename,
                        'patch': patch,
                        'line_ranges': line_ranges,
                        'added_lines': added_lines,
                        'status': status
                    }
                    changed_files.append(file_data)
                    
                    print(f"  - {filename} ({status})")
                    if line_ranges:
                        ranges_str = ', '.join([f"{r['start']}-{r['end']}" for r in line_ranges])
                        print(f"    Changed line ranges: {ranges_str}")
                    if added_lines:
                        print(f"    Added/modified lines: {len(added_lines)} lines")
            
            print(f"Found {len(changed_files)} files to analyze")
            
            return changed_files
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to get changed files from GitHub API: {e}")
            return []
        except Exception as e:
            print(f"ERROR: Unexpected error getting changed files: {e}")
            return []
    
    # Keep old method for backward compatibility (commented out for reference)
    # def get_changed_files(self, file_patterns: Optional[List[str]] = None) -> List[str]:
    #     """Get list of changed files in the PR using GitHub API."""
    #     ... (old implementation)


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
    parser.add_argument('--context-lines', type=int, default=1,
                       help='Number of context lines to include around changes (default: 1)')
    
    # =====================================================================
    # MOCK MODES - COMMENTED OUT (can be re-enabled if needed)
    # =====================================================================
    # parser.add_argument('--test-mode', action='store_true',
    #                    help='Use generated mock data instead of calling Cursor API')
    # parser.add_argument('--use-mock', action='store_true',
    #                    help='Use predefined mock data from mock-analysis-results.json')
    # parser.add_argument('--demo', action='store_true',
    #                    help='Use demo mode with file-specific mock data')
    # parser.add_argument('--use-cursor', action='store_true', default=True,
    #                    help='Use Cursor AI for analysis (default: True)')
    # =====================================================================
    
    args = parser.parse_args()
    
    # Get environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    cursor_api_key = os.getenv('CURSOR_API_KEY')
    pr_number = args.pr_number or os.getenv('PR_NUMBER')
    repository = args.repository or os.getenv('REPOSITORY')
    verbose = os.getenv('VERBOSE', 'true').lower() in ('true', '1', 'yes')
    
    print("=== Analyze PR Code Action (Diff-based) ===")
    print(f"PR Number: {pr_number}")
    print(f"Repository: {repository}")
    print(f"GitHub Token present: {bool(github_token)}")
    print(f"Cursor API Key present: {bool(cursor_api_key)}")
    print(f"Prompt file: {args.prompt_file}")
    print(f"Output file: {args.output_file}")
    print(f"Context lines: {args.context_lines}")
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
    
    # Install and verify Cursor CLI (always required now - no mock modes)
    if not cursor.install_cursor_cli():
        print("ERROR: Failed to install Cursor CLI")
        return 1
    
    if not cursor.verify_setup():
        print("ERROR: Cursor CLI setup verification failed")
        return 1
    
    # Get changed files WITH DIFFS (new diff-based approach)
    pr_analyzer = GitHubPRAnalyzer(github_token, repository, pr_number)
    diff_data = pr_analyzer.get_changed_files_with_diff()
    
    if not diff_data:
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
    
    # Analyze diffs (new diff-based approach)
    print(f"\n=== Analyzing {len(diff_data)} file diffs ===\n")
    results = cursor.analyze_diffs(diff_data, prompt, context_lines=args.context_lines, verbose=verbose)
    
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

