#!/usr/bin/env python3
"""
Apply Suggested Logs Action
"""

import os
import sys
import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add libs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))
from cursor_client import CursorClient


class LogApplier:
    """Applies logging improvements to files using AI."""
    
    def __init__(self, cursor_api_key: str, prompt_file: str = '.github/prompts/apply-logs.txt', verbose: bool = False):
        self.cursor_client = CursorClient(api_key=cursor_api_key)
        self.cursor_client.install_cursor_cli()
        self.verbose = verbose
        
        # Load prompt template
        with open(prompt_file, 'r') as f:
            self.prompt_template = f.read()
        
        if self.verbose:
            print(f"[DEBUG] LogApplier initialized")
            print(f"[DEBUG] Prompt template length: {len(self.prompt_template)} chars")
    
    def apply_logging_improvements(self, file_path: str, issues: List[Dict[str, Any]]) -> bool:
        """Apply logging improvements to a file."""
        print(f"Applying improvements to: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        # Read current file content
        with open(file_path, 'r') as f:
            original_content = f.read()
        
        if self.verbose:
            print(f"[DEBUG] Original file size: {len(original_content)} chars")
            print(f"[DEBUG] Number of issues to apply: {len(issues)}")
        
        # Build prompt with issues
        issues_text = ""
        for idx, issue in enumerate(issues, 1):
            issues_text += f"\n{idx}. **{issue.get('severity', 'MEDIUM')}** - {issue.get('category', 'logging')}\n"
            issues_text += f"   Line: {issue.get('line', 'N/A')}\n"
            issues_text += f"   Method: {issue.get('method', 'N/A')}\n"
            issues_text += f"   Description: {issue.get('description', 'N/A')}\n"
            issues_text += f"   Recommendation: {issue.get('recommendation', 'N/A')}\n"
            
            if self.verbose:
                print(f"[DEBUG] Issue {idx}: {issue.get('severity')} at line {issue.get('line')} in {issue.get('method')}")
        
        prompt = self.prompt_template.replace('{issues}', issues_text)
        context = f"File: {file_path}\n\nCurrent content:\n{original_content}"
        
        if self.verbose:
            print(f"[DEBUG] Prompt length: {len(prompt)} chars")
            print(f"[DEBUG] Context length: {len(context)} chars")
            print(f"[DEBUG] Calling Cursor AI...")
        
        # Get improved code from AI
        result = self.cursor_client.send_message(prompt, context=context, verbose=self.verbose)
        
        if self.verbose:
            print(f"[DEBUG] AI result type: {type(result)}")
            print(f"[DEBUG] AI result preview: {str(result)[:300]}...")
        
        improved_code = self._extract_code(result)
        
        if self.verbose:
            if improved_code:
                print(f"[DEBUG] Extracted code length: {len(improved_code)} chars")
                print(f"[DEBUG] Code comparison:")
                print(f"  Original: {len(original_content)} chars")
                print(f"  Improved: {len(improved_code)} chars")
                print(f"  Same content: {improved_code == original_content}")
            else:
                print(f"[DEBUG] No code extracted from AI response")
        
        if not improved_code or improved_code == original_content:
            print(f"No changes for {file_path}")
            return False
        
        print(f"✓ Applied changes to {file_path}")
        return True
    
    def _extract_code(self, result: Any) -> Optional[str]:
        """Extract code from AI result."""
        if self.verbose:
            print(f"[DEBUG] _extract_code called with type: {type(result)}")
        
        if isinstance(result, str):
            code = result
            
            if self.verbose:
                print(f"[DEBUG] Processing string result, length: {len(code)} chars")
            
            # Remove markdown code blocks
            python_block = re.search(r'```python\s*\n(.*?)\n```', code, re.DOTALL)
            if python_block:
                if self.verbose:
                    print(f"[DEBUG] Found Python markdown block")
                code = python_block.group(1)
            else:
                generic_block = re.search(r'```\s*\n(.*?)\n```', code, re.DOTALL)
                if generic_block:
                    if self.verbose:
                        print(f"[DEBUG] Found generic markdown block")
                    code = generic_block.group(1)
                elif self.verbose:
                    print(f"[DEBUG] No markdown blocks found, using raw string")
            
            code = code.strip()
            if 'import ' in code or 'def ' in code or 'class ' in code:
                if self.verbose:
                    print(f"[DEBUG] Code validated (contains Python keywords)")
                return code
            elif self.verbose:
                print(f"[DEBUG] Code rejected (no Python keywords found)")
        
        elif isinstance(result, dict):
            if self.verbose:
                print(f"[DEBUG] Processing dict result with keys: {list(result.keys())}")
            
            if 'code' in result:
                if self.verbose:
                    print(f"[DEBUG] Found 'code' key in dict")
                return result['code']
            elif 'result' in result:
                if self.verbose:
                    print(f"[DEBUG] Found 'result' key, recursing...")
                return self._extract_code(result['result'])
            elif 'improved_code' in result:
                if self.verbose:
                    print(f"[DEBUG] Found 'improved_code' key in dict")
                return result['improved_code']
            elif self.verbose:
                print(f"[DEBUG] No recognized keys found in dict")
        
        if self.verbose:
            print(f"[DEBUG] No code could be extracted")
        
        return None

   
def parse_issue_from_comment(comment_body: str) -> Optional[Dict[str, Any]]:
    """Parse issue details from a comment body."""
    import re
    
    # Try to extract from hidden JSON metadata
    json_match = re.search(r'<!-- ISSUE_DATA: (.+?) -->', comment_body, re.DOTALL)
    
    if not json_match:
        print("⚠️  No JSON metadata found in comment - cannot determine file path")
        return None
    
    try:
        metadata = json.loads(json_match.group(1))
        return {
            'file': metadata['file'],
            'severity': metadata.get('severity', 'MEDIUM'),
            'category': metadata.get('category', 'logging'),
            'method': metadata.get('method', 'N/A'),
            'line': metadata.get('line', 0),
            'description': metadata.get('description', ''),
            'recommendation': metadata.get('recommendation', ''),
            'impact': metadata.get('impact', '')
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Failed to parse JSON metadata: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Apply suggested logs from review comment')
    parser.add_argument('--pr-number', type=str, required=True)
    parser.add_argument('--repository', type=str, required=True)
    parser.add_argument('--comment-body', type=str,
                       help='Review comment body with hidden JSON metadata')
    parser.add_argument('--comment-body-file', type=str,
                       help='File containing review comment body')
    parser.add_argument('--comment-id', type=str)
    parser.add_argument('--prompt-file', type=str, 
                       default='.github/prompts/apply-logs.txt')
    
    args = parser.parse_args()
    
    # Use GitHub Actions' native debug mode
    verbose = os.getenv('ACTIONS_STEP_DEBUG', 'false').lower() in ('true', '1')
    
    if verbose:
        print(f"[DEBUG] Running apply-suggested-logs/main.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Prompt file: {args.prompt_file}")
    
    # Get comment body from file or argument
    if args.comment_body_file:
        if verbose:
            print(f"[DEBUG] Reading comment body from file: {args.comment_body_file}")
        with open(args.comment_body_file, 'r') as f:
            comment_body = f.read()
        if verbose:
            print(f"[DEBUG] Comment body length: {len(comment_body)} chars")
    elif args.comment_body:
        comment_body = args.comment_body
        if verbose:
            print(f"[DEBUG] Using comment body from argument: {len(comment_body)} chars")
    else:
        print("ERROR: Either --comment-body or --comment-body-file is required")
        return 1
    
    cursor_api_key = os.getenv('CURSOR_API_KEY')
    if not cursor_api_key:
        print("ERROR: CURSOR_API_KEY not set")
        return 1
    
    if verbose:
        print(f"[DEBUG] CURSOR_API_KEY present: True")
    
    # Initialize applier
    applier = LogApplier(cursor_api_key, args.prompt_file, verbose=verbose)
    
    # Parse issue from comment body
    print("Parsing issue from comment...")
    issue = parse_issue_from_comment(comment_body)
    
    if not issue:
        print("ERROR: Could not parse issue from comment")
        print("Make sure the comment includes hidden JSON metadata: <!-- ISSUE_DATA: {...} -->")
        return 1
    
    if verbose:
        print(f"[DEBUG] Parsed issue: {json.dumps(issue, indent=2)}")
    
    file_path = issue.pop('file')
    print(f"Applying single issue to {file_path}")
    
    if applier.apply_logging_improvements(file_path, [issue]):
        print(f"\n✓ Applied change to {file_path}")
        if verbose:
            print(f"[DEBUG] Successfully completed apply-suggested-logs/main.py")
        return 0
    else:
        print(f"\n✗ Failed to apply change")
        return 1


if __name__ == '__main__':
    sys.exit(main())

