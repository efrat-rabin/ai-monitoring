# Analyze PR Code - Usage Guide

## Overview
This action analyzes PR code for logging improvements using either Cursor AI or mock data for testing.

## Modes of Operation

### 1. **Cursor AI Mode (Default)** ✅
Uses real Cursor AI to analyze the code.

```bash
python code_analyzer.py --pr-number 123 --repository owner/repo
```

Or explicitly:
```bash
python code_analyzer.py --pr-number 123 --repository owner/repo --use-cursor
```

### 2. **Mock Data Mode** 📋
Uses predefined analysis results from `mock-analysis-results.json`.

```bash
python code_analyzer.py --pr-number 123 --repository owner/repo --use-mock
```

This is useful for:
- Testing the comment posting functionality without using Cursor API credits
- Demonstrating the workflow with known results
- Development and debugging

### 3. **Test Mode** 🧪
Generates generic mock data based on the files in the PR.

```bash
python code_analyzer.py --pr-number 123 --repository owner/repo --test-mode
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--pr-number` | Pull request number | From `PR_NUMBER` env var |
| `--repository` | Repository (owner/repo format) | From `REPOSITORY` env var |
| `--prompt-file` | Path to analysis prompt | `.ai-monitoring/.github/prompts/analyze-logs.txt` |
| `--output-file` | Output file for results | `analysis-results.json` |
| `--use-cursor` | Use Cursor AI (default) | `True` |
| `--use-mock` | Use predefined mock data | `False` |
| `--test-mode` | Use generated mock data | `False` |

## Environment Variables

- `GITHUB_TOKEN` - GitHub API token (required)
- `CURSOR_API_KEY` - Cursor API key (required for Cursor mode)
- `PR_NUMBER` - Pull request number (alternative to --pr-number)
- `REPOSITORY` - Repository name (alternative to --repository)
- `VERBOSE` - Enable verbose output (`true`/`false`)

## Mock Data File

The mock data is stored in `mock-analysis-results.json` and contains sample analysis results for:
- `apps/api/src/middleware/error-handler.ts`
- `apps/api/src/services/cursor.service.ts`
- `apps/api/src/services/github.service.ts`

To update the mock data, edit this file with your desired analysis results.

## Examples

### Quick test with mock data:
```bash
export GITHUB_TOKEN=ghp_...
python code_analyzer.py --pr-number 123 --repository owner/repo --use-mock
```

### Full analysis with Cursor AI:
```bash
export GITHUB_TOKEN=ghp_...
export CURSOR_API_KEY=sk-...
python code_analyzer.py --pr-number 123 --repository owner/repo
```

### Test mode (generates mock per file):
```bash
export GITHUB_TOKEN=ghp_...
python code_analyzer.py --pr-number 123 --repository owner/repo --test-mode
```

