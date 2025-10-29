# Apply Suggested Logs Action

This action automatically applies AI-suggested logging improvements to your codebase.

## Overview

The Apply Suggested Logs action takes analysis results from the code analysis workflow and uses AI to automatically apply the recommended logging improvements to your code files.

## How It Works

1. **Triggered by Comment**: The workflow is triggered when someone replies to an analysis comment with `/apply-logs`
2. **Receives Analysis Results**: Gets the JSON analysis results containing all logging issues and recommendations
3. **AI-Powered Application**: Uses Cursor AI to intelligently apply the logging improvements while preserving code functionality
4. **Automatic Commit**: Commits and pushes the changes to the PR branch
5. **Success Comment**: Posts a comment on the PR confirming the changes were applied

## Workflow Inputs

### Required Inputs

- `pr_number`: Pull request number
- `repository`: Repository in format `owner/repo`
- `analysis_results`: JSON string containing the analysis results
- `git_token`: GitHub token with write permissions
- `cursor_api_key`: Cursor API key for AI-powered code modifications

### Optional Inputs

- `comment_id`: ID of the comment that triggered the apply action (for tracking)

## Analysis Results Format

The action expects analysis results in the following JSON format:

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
          "description": "Description of the issue",
          "recommendation": "Specific code recommendation",
          "impact": "Impact of not fixing this issue"
        }
      ]
    }
  }
]
```

## Usage

### Manual Trigger

You can manually trigger the workflow from GitHub Actions:

1. Go to Actions → Apply Suggested Logs
2. Click "Run workflow"
3. Fill in the required inputs
4. Click "Run workflow"

### Automatic Trigger (via Main Workflow)

The workflow is designed to be triggered automatically by a main orchestrator workflow when:

1. Code analysis has been completed
2. A user replies to the analysis comment with `/apply-logs`
3. The main workflow calls this workflow with the analysis results

## Scripts

### main.py

The main script that applies logging improvements:

- Parses analysis results JSON
- Initializes Cursor AI client
- For each file with issues:
  - Reads the current file content
  - Builds a prompt with all logging improvements
  - Uses AI to generate improved code
  - Writes the improved code back to the file
- Reports summary of changes

### check_apply_trigger.py

Helper script to check for `/apply-logs` trigger in comments:

- Fetches PR comments
- Searches for `/apply-logs` keyword
- Outputs trigger information to JSON file
- Used by orchestrator workflows to determine if apply should run

### post_apply_comment.py

Posts a success comment after changes are applied:

- Creates a formatted comment explaining what was changed
- Posts to the PR
- Includes next steps for the developer

## Example Workflow Call

```yaml
jobs:
  apply-logs:
    uses: ./.github/workflows/apply-suggested-logs.yml
    with:
      pr_number: "123"
      repository: "owner/repo"
      analysis_results: ${{ needs.analyze.outputs.results }}
      comment_id: "456"
    secrets:
      git_token: ${{ secrets.BOT_GITHUB_TOKEN }}
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

## AI Prompt Strategy

The action uses a carefully crafted prompt that:

1. **Preserves Functionality**: Instructs AI to only modify logging, not business logic
2. **Maintains Formatting**: Keeps original code structure and indentation
3. **Adds Imports**: Automatically adds necessary imports (logging, time, uuid, etc.)
4. **Complete Output**: Requests full file content, not snippets
5. **No Markdown**: Instructs AI to return pure code without markdown formatting

## Error Handling

The action handles various error scenarios:

- **File Not Found**: Skips files that don't exist
- **Analysis Errors**: Skips files with analysis errors
- **No Issues**: Skips files with no logging issues
- **AI Extraction Failure**: Reports when code cannot be extracted from AI response
- **No Changes**: Detects when AI suggests no changes

## Output

The action produces:

1. **Modified Files**: Updated code files with improved logging
2. **Git Commit**: Automatic commit with descriptive message
3. **PR Comment**: Success comment with summary of changes
4. **Console Output**: Detailed logs of the application process

## Requirements

- Python 3.11+
- Cursor CLI (automatically installed)
- GitHub token with repository write access
- Cursor API key

## Security Considerations

- Uses GitHub token with minimal required permissions
- Cursor API key should be stored as a secret
- All changes are committed to the PR branch (not main)
- Changes can be reviewed before merging

## Limitations

- Only applies logging improvements (not other code changes)
- Requires valid Cursor API key
- May need manual adjustment for complex code structures
- AI-generated code should always be reviewed before merging

## Troubleshooting

### No Changes Applied

- Check that analysis results contain valid issues
- Verify Cursor API key is valid
- Review console output for AI extraction errors

### Invalid Code Generated

- AI may occasionally generate invalid code
- Always review changes before merging
- File an issue if patterns emerge

### Permission Errors

- Ensure GitHub token has write access to repository
- Check that PR branch is not protected

## Future Enhancements

- [ ] Support for selective application (apply only specific issues)
- [ ] Dry-run mode to preview changes
- [ ] Validation of generated code (syntax checking)
- [ ] Support for multiple programming languages
- [ ] Rollback mechanism for failed applications

