# Apply Suggested Logs - Quick Start

## Overview

This workflow automatically applies AI-suggested logging improvements to your code when triggered by a `/apply-logs` comment.

## How It Works

1. **Analysis runs** on PR → Posts comment with logging issues
2. **User reviews** and replies with `/apply-logs` 
3. **Workflow applies** all suggested improvements automatically
4. **Changes committed** to the PR branch

## Setup

### Required Secrets

Add to your repository settings:

- `BOT_GITHUB_TOKEN` - GitHub token with write access
- `CURSOR_API_KEY` - Cursor AI API key

### Workflow Integration

The workflow is designed to be called by a main orchestrator workflow when `/apply-logs` is detected in comments.

## Usage

1. Open a PR with code changes
2. Wait for analysis to complete
3. Review the analysis comment
4. Reply with: `/apply-logs`
5. Wait for changes to be applied
6. Review and merge

## Files

- `main.py` - Applies logging improvements using AI
- `check_apply_trigger.py` - Checks for `/apply-logs` in comments
- `post_apply_comment.py` - Posts success comment
- `.github/prompts/apply-logs.txt` - AI prompt template

## Example Analysis Input

```json
[
  {
    "file": "path/to/file.py",
    "analysis": {
      "issues": [
        {
          "severity": "CRITICAL",
          "category": "structured-logging",
          "line": 29,
          "method": "function_name",
          "description": "Uses print() instead of logging",
          "recommendation": "Use logger.info() with structured data"
        }
      ]
    }
  }
]
```

## Testing Locally

```bash
export CURSOR_API_KEY=your_key
export GITHUB_TOKEN=your_token

python main.py \
  --pr-number 123 \
  --repository owner/repo \
  --analysis-results '$(cat analysis.json)'
```

## Notes

- Always review AI-generated changes before merging
- Changes are committed to the PR branch (not main)
- The workflow preserves code functionality, only adds logging

