# Apply Suggested Logs - Workflow Guide

This guide explains how the `actions/apply-suggested-logs/` scripts integrate with the main workflow (`.github/workflows/pr-automation.yml`) and how to use them.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Workflow                            │
│                       (pr-automation.yml)                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ├─── On PR Open/Update
                                 │
                    ┌────────────▼────────────┐
                    │  Analyze PR Code        │
                    │  (pr-automation job)    │
                    └────────────┬────────────┘
                                 │
                                 ├─── Generates analysis results
                                 │
                    ┌────────────▼────────────┐
                    │  Post Comment on PR     │
                    │  with /apply-logs hint  │
                    └─────────────────────────┘
                                 │
                                 │
                    ┌────────────▼────────────┐
                    │  User reviews and       │
                    │  replies: /apply-logs   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Check Apply Trigger    │
                    │  (on comment created)   │
                    └────────────┬────────────┘
                                 │
                                 ├─── Trigger detected
                                 │
                    ┌────────────▼────────────┐
                    │  Apply Suggested Logs   │
                    │  (pr-automation job)    │
                    └────────────┬────────────┘
                                 │
                                 ├─── Applies changes
                                 │
                    ┌────────────▼────────────┐
                    │  Commit & Push Changes  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Post Success Comment   │
                    └─────────────────────────┘
```

## Workflow Steps

### Step 1: Analysis Phase

When a PR is opened or updated:

1. **Trigger**: `pull_request` event (opened, synchronize)
2. **Action**: `pr-automation.yml` runs its `analyze` job
3. **Output**: 
   - Analysis results saved as artifact
   - Comment posted on PR with findings
   - Comment includes `/apply-logs` instruction

**Example Comment:**

```markdown
## 🤖 AI Code Analysis Results

### 📄 File: `actions/analyze-pr-code/code_analyzer.py`

**Found 16 issue(s):**

<details>
<summary><strong>CRITICAL</strong> - structured-logging: install_cursor_cli</summary>

**Description:** Uses print() statements instead of structured logging...

**Recommendation:** Replace all print() statements with structured logging...

</details>

---

### 🤖 Auto-Apply Available

Want to automatically apply these logging improvements? Reply to this comment with:

```
/apply-logs
```

The AI will automatically apply all suggested improvements and commit them to this PR.
```

### Step 2: Trigger Detection Phase

When a user replies to the analysis comment:

1. **Trigger**: `pull_request_review_comment` event (created)
2. **Check**: Comment body contains `/apply-logs`
3. **Validation**: 
   - Comment is on a pull request
   - Comment contains the exact trigger phrase
4. **Output**: Sets `should_apply` flag to true

### Step 3: Apply Changes

The `apply-logs` job inside `pr-automation.yml` runs:

1. **Checkout PR Branch**: Checks out the PR's head branch
2. **Install Dependencies**: Sets up Python and installs requirements
3. **Run Apply Script**: 
   - Loads the parent analysis comment body (the one containing hidden `ISSUE_DATA` JSON)
   - Applies the unified diff patch embedded in that metadata
4. **Commit Changes**: 
   - Stages all modified files
   - Creates commit with descriptive message
   - Pushes to PR branch
5. **Post Comment**: Adds success comment to PR

## Usage Examples

### Example 1: Basic Usage

1. Open a PR with code changes
2. Wait for analysis to complete
3. Review the analysis comment
4. Reply with `/apply-logs`
5. Wait for changes to be applied
6. Review the commit and merge

### Example 2: Manual Trigger

If you want to test the apply logic outside GitHub Actions, run `main.py` locally with a saved parent comment body (see Example 3).

### Example 3: Testing Locally

```bash
# Set environment variables
export GITHUB_TOKEN=your_token

# Run the apply script
cd actions/apply-suggested-logs
python main.py \
  --pr-number 123 \
  --repository owner/repo \
  --comment-body-file parent-comment.txt
```

## Configuration

### Required Secrets

Add these secrets to your repository:

1. **BOT_GITHUB_TOKEN**: GitHub token with write access
   - Permissions needed: `contents: write`, `pull-requests: write`
   - Can be a personal access token or GitHub App token

2. **CURSOR_API_KEY**: Cursor AI API key
   - Get from: https://cursor.com/settings
   - Used for AI-powered code modifications

### Workflow Permissions

Ensure your workflow has these permissions:

```yaml
permissions:
  contents: write        # To commit changes
  pull-requests: write   # To post comments
  actions: read          # To download artifacts
```

## File Structure

```
actions/apply-suggested-logs/
├── main.py                    # Main script that applies changes
├── check_apply_trigger.py     # Checks for /apply-logs in comments
├── post_apply_comment.py      # Posts success comment
├── test_apply.sh              # Test script
├── README.md                  # Documentation
└── WORKFLOW_GUIDE.md          # This file

.github/workflows/
├── pr-automation.yml          # Orchestrates analysis + /apply-logs apply
```

## Input/Output Formats

### Analysis Results Format

```json
[
  {
    "file": "path/to/file.py",
    "analysis": {
      "issues": [
        {
          "severity": "CRITICAL|HIGH|MEDIUM|LOW",
          "category": "structured-logging|error-context|missing-logs|...",
          "line": 29,
          "method": "function_name",
          "description": "What's wrong",
          "recommendation": "How to fix it",
          "impact": "Why it matters"
        }
      ]
    }
  }
]
```

### Trigger Check Output

```json
{
  "triggered": true,
  "comment_id": 123456,
  "comment_author": "username",
  "comment_body": "/apply-logs",
  "comment_created_at": "2025-10-29T12:00:00Z"
}
```

## Error Handling

### Common Errors and Solutions

#### 1. No Analysis Results Found

**Error**: `No analysis results found`

**Solution**: 
- Ensure analyze-pr-code workflow completed successfully
- Check that analysis-results artifact was uploaded
- Verify artifact retention hasn't expired (default 30 days)

#### 2. Cursor CLI Installation Failed

**Error**: `Failed to install Cursor CLI`

**Solution**:
- Check network connectivity
- Verify Cursor API key is valid
- Try running workflow again (transient failure)

#### 3. No Changes Applied

**Error**: `No changes suggested by AI`

**Solution**:
- Review the analysis results format
- Ensure issues array is not empty
- Check AI response in logs
- May need to adjust prompt

#### 4. Permission Denied

**Error**: `Permission denied` when pushing

**Solution**:
- Verify BOT_GITHUB_TOKEN has write access
- Check branch protection rules
- Ensure token hasn't expired

## Best Practices

### 1. Review Before Merging

Always review AI-generated changes:
- Check that functionality is preserved
- Verify logging statements are appropriate
- Ensure imports are correct
- Test the code

### 2. Incremental Application

For large PRs:
- Consider applying changes to a few files at a time
- Review each batch before applying more
- This helps catch issues early

### 3. Custom Prompts

You can customize the AI prompt in `main.py`:
- Adjust the `_build_apply_prompt` method
- Add specific instructions for your codebase
- Include style guidelines

### 4. Monitoring

Monitor workflow runs:
- Check GitHub Actions logs
- Review commit messages
- Track success/failure rates

## Troubleshooting

### Debug Mode

Enable debug logging:

```bash
export ACTIONS_STEP_DEBUG=true
export ACTIONS_RUNNER_DEBUG=true
```

### Local Testing

Test the script locally:

```bash
# Create a test analysis file
cat > test-analysis.json << 'EOF'
[
  {
    "file": "test.py",
    "analysis": {
      "issues": [
        {
          "severity": "MEDIUM",
          "category": "structured-logging",
          "line": 10,
          "method": "test_function",
          "description": "Uses print()",
          "recommendation": "Use logger.info()",
          "impact": "Logs not structured"
        }
      ]
    }
  }
]
EOF

# Run the script
python main.py \
  --pr-number 123 \
  --repository owner/repo \
  --analysis-results "$(cat test-analysis.json)"
```

### Workflow Logs

Check workflow logs for:
- AI responses
- File modifications
- Commit details
- Error messages

## Advanced Usage

### Custom Triggers

Modify `check_apply_trigger.py` to support:
- Different trigger keywords
- Role-based access control
- Selective file application

### Integration with Other Tools

The workflow can be extended to:
- Run linters after applying changes
- Run tests automatically
- Create review requests
- Send notifications

## Security Considerations

1. **Token Security**
   - Store tokens as secrets
   - Use minimal required permissions
   - Rotate tokens regularly

2. **Code Review**
   - Always review AI-generated code
   - Don't auto-merge without review
   - Test changes before merging

3. **Access Control**
   - Limit who can trigger apply
   - Use CODEOWNERS for sensitive files
   - Enable branch protection

## FAQ

**Q: Can I apply changes to specific files only?**

A: Currently, the workflow applies changes to all files in the analysis. You can modify the script to filter by file path.

**Q: What if the AI generates invalid code?**

A: The changes are committed to the PR branch, so you can review and fix them before merging. Consider adding syntax validation.

**Q: Can I use this with other languages?**

A: Yes, but you may need to adjust the prompts and code extraction logic in `main.py`.

**Q: How do I rollback if something goes wrong?**

A: Use `git revert` on the commit created by the workflow, or force-push the previous state.

**Q: Can I customize the commit message?**

A: Yes, modify the commit message in the workflow YAML file.

## Support

For issues or questions:
1. Check the workflow logs
2. Review this documentation
3. Check the README.md
4. Open an issue in the repository

