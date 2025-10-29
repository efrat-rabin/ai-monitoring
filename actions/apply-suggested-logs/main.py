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
    
    def __init__(self, cursor_api_key: str, prompt_file: str = '.github/prompts/apply-logs.txt'):
        self.cursor_client = CursorClient(api_key=cursor_api_key)
        self.cursor_client.install_cursor_cli()
        
        # Load prompt template
        with open(prompt_file, 'r') as f:
            self.prompt_template = f.read()
    
    def apply_logging_improvements(self, file_path: str, issues: List[Dict[str, Any]]) -> bool:
        """Apply logging improvements to a file."""
        print(f"Applying improvements to: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        # Read current file content
        with open(file_path, 'r') as f:
            original_content = f.read()
        
        # Build prompt with issues
        issues_text = ""
        for idx, issue in enumerate(issues, 1):
            issues_text += f"\n{idx}. **{issue.get('severity', 'MEDIUM')}** - {issue.get('category', 'logging')}\n"
            issues_text += f"   Line: {issue.get('line', 'N/A')}\n"
            issues_text += f"   Method: {issue.get('method', 'N/A')}\n"
            issues_text += f"   Description: {issue.get('description', 'N/A')}\n"
            issues_text += f"   Recommendation: {issue.get('recommendation', 'N/A')}\n"
        
        prompt = self.prompt_template.replace('{issues}', issues_text)
        context = f"File: {file_path}\n\nCurrent content:\n{original_content}"
        
        # Get improved code from AI
        result = self.cursor_client.send_message(prompt, context=context)
        improved_code = self._extract_code(result)
        
        if not improved_code or improved_code == original_content:
            print(f"No changes for {file_path}")
            return False
        
        # Write improved code
        with open(file_path, 'w') as f:
            f.write(improved_code)
        
        print(f"✓ Applied changes to {file_path}")
        return True
    
    def _extract_code(self, result: Any) -> Optional[str]:
        """Extract code from AI result."""
        if isinstance(result, str):
            code = result
            
            # Remove markdown code blocks
            python_block = re.search(r'```python\s*\n(.*?)\n```', code, re.DOTALL)
            if python_block:
                code = python_block.group(1)
            else:
                generic_block = re.search(r'```\s*\n(.*?)\n```', code, re.DOTALL)
                if generic_block:
                    code = generic_block.group(1)
            
            code = code.strip()
            if 'import ' in code or 'def ' in code or 'class ' in code:
                return code
        
        elif isinstance(result, dict):
            if 'code' in result:
                return result['code']
            elif 'result' in result:
                return self._extract_code(result['result'])
            elif 'improved_code' in result:
                return result['improved_code']
        
        return None


def parse_issue_from_comment(comment_body: str) -> Optional[Dict[str, Any]]:
    """Parse issue details from a comment body."""
    import re
    
    # Extract file path
    file_match = re.search(r'\*\*File:\*\* `([^`]+)`', comment_body)
    if not file_match:
        return None
    
    file_path = file_match.group(1)
    
    # Extract other fields
    method_match = re.search(r'\*\*Method:\*\* `([^`]+)`', comment_body)
    line_match = re.search(r'\*\*Line:\*\* (\d+)', comment_body)
    severity_match = re.search(r'## 🤖 Logging Suggestion: (\w+)', comment_body)
    category_match = re.search(r'\*\*Category:\*\* ([^\n]+)', comment_body)
    
    # Extract description, recommendation, impact
    desc_match = re.search(r'### Description\n([^#]+)', comment_body, re.DOTALL)
    rec_match = re.search(r'### Recommendation\n```[^\n]*\n(.*?)\n```', comment_body, re.DOTALL)
    impact_match = re.search(r'### Impact\n([^#]+)', comment_body, re.DOTALL)
    
    issue = {
        'file': file_path,
        'severity': severity_match.group(1) if severity_match else 'MEDIUM',
        'category': category_match.group(1) if category_match else 'logging',
        'method': method_match.group(1) if method_match else 'N/A',
        'line': int(line_match.group(1)) if line_match else 0,
        'description': desc_match.group(1).strip() if desc_match else '',
        'recommendation': rec_match.group(1).strip() if rec_match else '',
        'impact': impact_match.group(1).strip() if impact_match else ''
    }
    
    return issue


def main():
    parser = argparse.ArgumentParser(description='Apply suggested logs')
    parser.add_argument('--pr-number', type=str, required=True)
    parser.add_argument('--repository', type=str, required=True)
    parser.add_argument('--analysis-results', type=str)
    parser.add_argument('--comment-body', type=str, help='Comment body with issue to apply')
    parser.add_argument('--comment-id', type=str)
    parser.add_argument('--prompt-file', type=str, 
                       default='.github/prompts/apply-logs.txt')
    
    args = parser.parse_args()
    
    cursor_api_key = os.getenv('CURSOR_API_KEY')
    if not cursor_api_key:
        print("ERROR: CURSOR_API_KEY not set")
        return 1
    
    # Initialize applier
    applier = LogApplier(cursor_api_key, args.prompt_file)
    
    # Parse issue from comment body if provided
    if args.comment_body:
        print("Parsing issue from comment...")
        issue = parse_issue_from_comment(args.comment_body)
        
        if not issue:
            print("ERROR: Could not parse issue from comment")
            return 1
        
        file_path = issue.pop('file')
        print(f"Applying single issue to {file_path}")
        
        if applier.apply_logging_improvements(file_path, [issue]):
            print(f"\n✓ Applied change to {file_path}")
            return 0
        else:
            print(f"\n✗ Failed to apply change")
            return 1
    
    # Fallback: apply all from analysis results
    elif args.analysis_results:
        analysis_results = json.loads(args.analysis_results)
        
        files_modified = 0
        for file_result in analysis_results:
            file_path = file_result.get('file')
            analysis = file_result.get('analysis', {})
            issues = analysis.get('issues', [])
            
            if file_path and issues and 'error' not in analysis:
                if applier.apply_logging_improvements(file_path, issues):
                    files_modified += 1
        
        print(f"\nModified {files_modified} file(s)")
        return 0
    
    else:
        print("ERROR: Either --comment-body or --analysis-results required")
        return 1


if __name__ == '__main__':
    sys.exit(main())

