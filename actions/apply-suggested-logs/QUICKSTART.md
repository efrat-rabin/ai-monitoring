# Apply Suggested Logs - Quick Start (scripts)

## Overview

These scripts apply logging improvements when triggered by a `/apply-logs` comment via `.github/workflows/pr-automation.yml`.

## How It Works

1. **Analysis runs** on PR → Posts comment with logging issues
2. **User reviews** and replies with `/apply-logs` 
3. **`pr-automation.yml` applies** the suggested improvements automatically
4. **Changes committed** to the PR branch

## Setup

### Required Secrets

Add to your repository settings:

- `BOT_GITHUB_TOKEN` - GitHub token with write access
- `CURSOR_API_KEY` - Used by analysis (this apply step is patch-based)

### Workflow Integration

The recommended integration is to use `.github/workflows/pr-automation.yml`, which handles both analysis and `/apply-logs` apply runs.

## Usage

1. Open a PR with code changes
2. Wait for analysis to complete
3. Review the analysis comment
4. Reply with: `/apply-logs`
5. Wait for changes to be applied
6. Review and merge

## Files

- `main.py` - Applies a patch embedded in the analysis comment
- `check_apply_trigger.py` - Checks for `/apply-logs` in comments
- `post_apply_comment.py` - Posts success comment
- (Analysis prompts live in `.github/prompts/`; the apply step uses the patch from the analysis comment.)

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
export GITHUB_TOKEN=your_token

python main.py \
  --pr-number 123 \
  --repository owner/repo \
  --comment-body-file parent-comment.txt
```

## Notes

- Always review AI-generated changes before merging
- Changes are committed to the PR branch (not main)
- The workflow preserves code functionality, only adds logging

