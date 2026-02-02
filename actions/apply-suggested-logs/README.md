# Apply Suggested Logs (scripts)

These scripts power the `/apply-logs` experience in `.github/workflows/pr-automation.yml`.

There is **no standalone** `apply-suggested-logs.yml` workflow in this repository anymore; applying fixes is handled by the `apply-logs` job inside `pr-automation.yml`.

## How it works

1. **Trigger**: A developer replies with `/apply-logs` on a PR review comment.
2. **Trigger validation**: `check_apply_trigger.py` determines whether the reply should trigger an apply run and (when needed) loads the parent analysis comment.
3. **Apply**: `main.py` reads the parent comment body and extracts hidden JSON metadata of the form `<!-- ISSUE_DATA: {...} -->`, including a unified diff patch.
4. **Commit + notify**: The calling workflow commits/pushes changes and uses `post_apply_comment.py` to post a confirmation comment.

## Script inputs

### `main.py`

- `--pr-number` (required)
- `--repository` (required, `owner/repo`)
- `--comment-body` or `--comment-body-file` (required)
- `--comment-id` (optional)

## Local testing

To test locally, copy an analysis comment body (the one containing `<!-- ISSUE_DATA: ... -->`) into a file and run:

```bash
cd actions/apply-suggested-logs
python main.py \
  --pr-number 123 \
  --repository owner/repo \
  --comment-body-file parent-comment.txt
```

## Scripts

### main.py

The main script that applies a patch embedded in an analysis comment:

- Parses `<!-- ISSUE_DATA: ... -->` metadata from the comment body
- Validates/fixes patch formatting (when validation utilities are available)
- Applies the unified diff patch to the target file
- Emits a commit message via workflow outputs (when running in GitHub Actions)

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
- GitHub token with repository write access

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
- [ ] Rollback mechanism for failed applications

