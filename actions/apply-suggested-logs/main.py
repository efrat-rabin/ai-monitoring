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
    
    # Get comment body from file or argument
    if args.comment_body_file:
        with open(args.comment_body_file, 'r') as f:
            comment_body = f.read()
    elif args.comment_body:
        comment_body = args.comment_body
    else:
        print("ERROR: Either --comment-body or --comment-body-file is required")
        return 1
    
    cursor_api_key = os.getenv('CURSOR_API_KEY')
    if not cursor_api_key:
        print("ERROR: CURSOR_API_KEY not set")
        return 1
    
    # Initialize applier
    applier = LogApplier(cursor_api_key, args.prompt_file)
    
    # Parse issue from comment body
    print("Parsing issue from comment...")
    issue = parse_issue_from_comment(comment_body)
    
    if not issue:
        print("ERROR: Could not parse issue from comment")
        print("Make sure the comment includes hidden JSON metadata: <!-- ISSUE_DATA: {...} -->")
        return 1
    
    file_path = issue.pop('file')
    print(f"Applying single issue to {file_path}")
    
    if applier.apply_logging_improvements(file_path, [issue]):
        print(f"\n✓ Applied change to {file_path}")
        return 0
    else:
        print(f"\n✗ Failed to apply change")
        return 1


if __name__ == '__main__':
    sys.exit(main())

