# Using AI Monitoring from External Repositories

This guide explains how to use the AI Monitoring workflows from your own repositories.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Setup Instructions](#setup-instructions)
- [Workflow Examples](#workflow-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The AI Monitoring repository provides reusable GitHub Actions workflows that can be called from any repository in your organization (or publicly, if this repo is public). This allows you to:

- Analyze PRs with AI-powered code review
- Automatically apply logging improvements
- Create observability alerts from log patterns

All without duplicating the automation logic in each repository.

## How It Works

### Architecture

When you call a workflow from an external repository, the workflow performs a dual-checkout:

1. **Checkout your repository** (the calling repo) - This is the code that will be analyzed or modified
2. **Checkout workflow repository** (this repo) - This provides the Python scripts and automation logic

The workflow scripts are then executed against your repository's code, and any changes are committed back to your repository.

```
┌─────────────────────────┐
│ Your Repository         │
│ (External Repo)         │
│                         │
│ .github/workflows/      │
│   └── ai-analysis.yml   │  ← Calls reusable workflow
└─────────┬───────────────┘
          │ uses:
          │
          ▼
┌─────────────────────────┐
│ AI-Monitoring Repo      │
│                         │
│ .github/workflows/      │
│   ├── analyze-pr-code.yml      ← Reusable workflow
│   ├── apply-suggested-logs.yml │
│   └── apply-suggested-gc-resources.yml
│                         │
│ actions/                │
│   ├── analyze-pr-code/  │
│   ├── apply-suggested-logs/    ← Python scripts
│   └── apply-suggested-gc-resources/
│                         │
│ libs/                   │
│   └── cursor_client.py  │
└─────────────────────────┘
```

### Dual Checkout Process

Each workflow performs these steps:

1. Checkout your repository to the workspace root
2. Checkout workflow repository to `.ai-monitoring/` subdirectory
3. Add `.ai-monitoring/libs` to Python path
4. Execute scripts from `.ai-monitoring/actions/` against your code
5. Commit changes to your repository (if applicable)

## Setup Instructions

### Step 1: Configure Secrets

In your external repository, go to **Settings → Secrets and variables → Actions** and add:

**Required Secrets:**
- `CURSOR_API_KEY` - Your Cursor API key for AI analysis
  - Get it from: https://cursor.sh/settings

**Optional Secrets:**
- `ANTHROPIC_API_KEY` - For groundcover resources workflow
- `GROUNDCOVER_API_KEY` - For creating alerts
- `BOT_GITHUB_TOKEN` - GitHub PAT if you need cross-org access or specific permissions

### Step 2: Ensure Repository Access

**For Same Organization:**
- No additional setup needed if both repos are in the same GitHub org

**For Different Organizations or Private Repos:**
- Create a Personal Access Token (PAT) with `repo` scope
- Add it as `BOT_GITHUB_TOKEN` secret in your repository
- The PAT must have access to both your repo and the workflow repo

### Step 3: Create Workflow in Your Repository

Create `.github/workflows/ai-pr-automation.yml` in your repository:

**Option A: Complete Automation (Recommended)**

```yaml
name: AI PR Automation

on:
  pull_request:
    types: [opened, synchronize]
  pull_request_review_comment:
    types: [created]

jobs:
  pr-automation:
    uses: your-org/ai-monitoring/.github/workflows/pr-automation.yml@main
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

This single workflow provides:
- Automatic PR analysis when opened/updated
- Interactive fix application via `/apply-logs` comments
- Automatic commit and push of fixes

**Option B: Analysis Only**

```yaml
name: AI Code Analysis

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  analyze:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
      post_comment: true
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

**Important:** Replace `your-org/ai-monitoring` with the actual organization and repository name.

### Step 4: Create Prompt File (Optional)

If you want custom analysis prompts, create `.github/prompts/analyze-logs.txt` in your repository:

```
Analyze this code for logging best practices.

Focus on:
1. Missing error handling logs
2. Lack of structured logging
3. Missing performance metrics

Return JSON format with issues found.
```

## Workflow Examples

### Example 1: Complete PR Automation (Recommended - One Workflow to Rule Them All)

The simplest way to get started is to use the complete `pr-automation.yml` workflow that handles everything:

```yaml
name: AI PR Automation

on:
  pull_request:
    types: [opened, synchronize]
  pull_request_review_comment:
    types: [created]

jobs:
  pr-automation:
    uses: your-org/ai-monitoring/.github/workflows/pr-automation.yml@main
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

**What this does:**
1. ✅ Automatically analyzes PRs when opened or updated
2. ✅ Posts analysis results as PR comments
3. ✅ Allows developers to apply fixes by commenting `/apply-logs`
4. ✅ Automatically commits and pushes the changes
5. ✅ Posts confirmation when fixes are applied

**That's it!** This single workflow gives you the complete AI-powered PR automation experience.

### Example 2: Full PR Automation (Manual Composition)

If you prefer more control, you can compose the workflows yourself:

```yaml
name: PR Automation

on:
  pull_request:
    types: [opened, synchronize]
  pull_request_review_comment:
    types: [created]

jobs:
  # Analyze when PR is opened/updated
  analyze:
    if: github.event_name == 'pull_request'
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
      post_comment: true
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
  
  # Apply fixes when developer comments /apply-logs
  apply-logs:
    if: |
      github.event_name == 'pull_request_review_comment' &&
      contains(github.event.comment.body, '/apply-logs')
    uses: your-org/ai-monitoring/.github/workflows/apply-suggested-logs.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
      comment_body: ${{ github.event.comment.body }}
      comment_id: ${{ github.event.comment.id }}
    secrets:
      git_token: ${{ secrets.GITHUB_TOKEN }}
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

### Example 3: Manual Analysis Only

Only run analysis when manually triggered:

```yaml
name: Manual Code Analysis

on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: 'PR Number to analyze'
        required: true
        type: string

jobs:
  analyze:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ inputs.pr_number }}
      repository: ${{ github.repository }}
      post_comment: true
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

### Example 4: Create Groundcover Alerts from Logs

Automatically create alerts when error logs are detected:

```yaml
name: Create Observability Alerts

on:
  push:
    branches: [main]

jobs:
  scan-logs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Extract error logs
        id: extract
        run: |
          # Your logic to extract log patterns
          echo 'log_line={"level":"error","message":"Database timeout","service":"api"}' >> $GITHUB_OUTPUT
      
      - name: Create alert
        uses: your-org/ai-monitoring/.github/workflows/apply-suggested-gc-resources.yml@main
        with:
          log_line: ${{ steps.extract.outputs.log_line }}
        secrets:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          groundcover_api_key: ${{ secrets.GROUNDCOVER_API_KEY }}
```

### Example 5: Test Mode for Development

Use test mode to avoid consuming API credits during development:

```yaml
name: Test AI Analysis

on:
  pull_request:
    branches: [develop]

jobs:
  analyze:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
      test_mode: true  # Uses mock data instead of real AI
      post_comment: true
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

## Troubleshooting

### Issue: "Repository not found" error

**Cause:** The workflow cannot access the workflow repository.

**Solutions:**
1. Ensure the workflow repo is public, or
2. Create a PAT with `repo` scope and add as `BOT_GITHUB_TOKEN` secret
3. Verify the repository name is correct in the `uses:` line

### Issue: "Resource not accessible by integration"

**Cause:** Insufficient permissions for the GitHub token.

**Solutions:**
1. Add `BOT_GITHUB_TOKEN` secret with appropriate permissions
2. Check workflow permissions in Settings → Actions → General → Workflow permissions
3. Ensure the workflow has necessary permissions defined:
   ```yaml
   permissions:
     contents: write      # For pushing changes
     pull-requests: write # For posting comments
   ```

### Issue: Scripts fail with "Module not found"

**Cause:** Python path not correctly configured.

**Solution:** This should be automatic, but verify the workflow includes:
```yaml
export PYTHONPATH="${PYTHONPATH}:${GITHUB_WORKSPACE}/.ai-monitoring/libs"
```

Note: The directory is named `.ai-monitoring` for compatibility, even though it refers to the workflow repository.

### Issue: Changes not committed to PR

**Cause:** Branch protection rules or missing write permissions.

**Solutions:**
1. Ensure `contents: write` permission is granted
2. Check branch protection rules allow GitHub Actions to push
3. Verify the token has write access to the repository

### Issue: Analysis returns no results

**Possible Causes:**
1. No files match the analysis patterns (check file extensions)
2. PR has no changed files
3. Test mode is enabled
4. Cursor API key is invalid or expired

**Solutions:**
1. Check workflow logs for file filtering messages
2. Verify Cursor API key is valid
3. Disable test mode if enabled
4. Check that files are in supported formats (.py, .js, .ts, .tsx, .go, etc.)

## Advanced Usage

### Using Specific Versions

Instead of `@main`, you can pin to specific versions:

```yaml
uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@v1.0.0
```

Or use branches:

```yaml
uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@develop
```

### Custom Prompt Files

The analyze workflow looks for `.github/prompts/analyze-logs.txt` in your repository. Create this file to customize what the AI looks for:

```
Analyze this code for security vulnerabilities.

Look for:
- SQL injection risks
- XSS vulnerabilities
- Hardcoded credentials
- Missing input validation

Return JSON with:
{
  "issues": [{
    "severity": "HIGH|MEDIUM|LOW",
    "line": <line_number>,
    "description": "<description>",
    "recommendation": "<how_to_fix>"
  }]
}
```

### Conditional Execution

Only run analysis on specific paths:

```yaml
name: Analyze Backend Only

on:
  pull_request:
    paths:
      - 'backend/**'
      - 'api/**'

jobs:
  analyze:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

### Running Multiple Analyses

Run different types of analysis in parallel:

```yaml
jobs:
  analyze-logging:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
  
  analyze-security:
    uses: your-org/ai-monitoring/.github/workflows/analyze-pr-code.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      repository: ${{ github.repository }}
      # Use different prompt file for security analysis
    secrets:
      cursor_api_key: ${{ secrets.CURSOR_API_KEY }}
```

## Support

For issues or questions:

1. Check the [main README](README.md) for general documentation
2. Review workflow logs in your repository's Actions tab
3. Examine the ai-monitoring repository's workflow definitions
4. Open an issue in the ai-monitoring repository

## Contributing

To improve the workflows:

1. Fork this repository
2. Make your changes
3. Test with your external repository using your fork
4. Submit a pull request to the main repository

