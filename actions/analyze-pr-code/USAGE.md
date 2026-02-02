# Analyze PR Code - Usage Guide

## Overview
This action analyzes PR code diffs for logging improvements using Cursor AI. It focuses analysis on the actual changes made in the PR (not the entire files).

## How It Works

1. **Fetches PR diff** - Gets the actual changes (patch) from GitHub API
2. **Extracts context** - Reads surrounding lines from the changed files
3. **Analyzes with AI** - Sends diff + context to Cursor AI for analysis
4. **Filters results** - Only reports issues on lines that were actually changed

## Usage

### Basic Usage (Diff-based Analysis)

```bash
python code_analyzer.py --pr-number 123 --repository owner/repo
```

### With Custom Context Lines

```bash
python code_analyzer.py --pr-number 123 --repository owner/repo --context-lines 10
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--pr-number` | Pull request number | From `PR_NUMBER` env var |
| `--repository` | Repository (owner/repo format) | From `REPOSITORY` env var |
| `--prompt-file` | Path to analysis prompt | `.ai-monitoring/.github/prompts/analyze-logs.txt` |
| `--output-file` | Output file for results | `analysis-results.json` |
| `--context-lines` | Lines of context around changes | `5` |

## Environment Variables

- `GITHUB_TOKEN` - GitHub API token (required)
- `CURSOR_API_KEY` - Cursor API key (required)
- `PR_NUMBER` - Pull request number (alternative to --pr-number)
- `REPOSITORY` - Repository name (alternative to --repository)
- `VERBOSE` - Enable verbose output (`true`/`false`)

## Examples

### Analyze a PR:
```bash
export GITHUB_TOKEN=ghp_...
export CURSOR_API_KEY=sk-...
python code_analyzer.py --pr-number 123 --repository owner/repo
```

### With more context (10 lines):
```bash
export GITHUB_TOKEN=ghp_...
export CURSOR_API_KEY=sk-...
python code_analyzer.py --pr-number 123 --repository owner/repo --context-lines 10
```

---

## Mock Modes (Temporarily Disabled)

The following mock modes have been **temporarily disabled** but the code is preserved (commented out) for future re-enablement if needed:

- `--test-mode` - Generate mock data based on PR files
- `--use-mock` - Use predefined mock data from `mock-analysis-results.json`
- `--demo` - Use demo-specific mock data

The mock data files are still present in the repository:
- `mock-analysis-results.json`
- `demo-mock-entity-processor.json`

To re-enable mock modes, search for "MOCK MODES - COMMENTED OUT" in `code_analyzer.py` and uncomment the relevant sections.
