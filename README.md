# AI Monitoring - GitHub Actions

This repository contains GitHub Actions workflows for AI-powered code monitoring and optimization.

## Structure

```
.
├── .github/
│   └── workflows/          # GitHub Actions workflow definitions
│       ├── pr-automation.yml
├── actions/                # Action implementation scripts
│   ├── analyze-pr-code/
│   │   ├── code_analyzer.py    # Full Cursor AI integration
│   │   └── post_comment.py     # Post PR comments
│   ├── apply-suggested-logs/
│   │   └── main.py
│   └── apply-suggested-gc-resources/
│       ├── main.py
│       ├── ai_analyzer.py
│       ├── groundcover_client.py
│       └── prompts.py
├── libs/                   # Shared libraries
│   ├── cursor_client.py   # Common Cursor CLI client
│   └── README.md
├── requirements.txt        # Python dependencies
└── README.md
```

## Workflows

### 1. Complete PR Automation (Recommended)

**File:** `.github/workflows/pr-automation.yml`

Automatically analyzes PRs and lets developers apply fixes by replying with `/apply-logs`.

**Trigger:** `pull_request` + `pull_request_review_comment` (can also be called from external workflows)

**Required Secrets:**
- `CURSOR_API_KEY` - Cursor API key for AI analysis (passed as `cursor_api_key`)

## Usage

### Using from External Repositories

`pr-automation.yml` is designed to be called from external repositories as a **reusable workflow**. This allows you to add AI-powered PR automation to any of your repositories without duplicating the automation logic.

**📘 For detailed setup instructions, examples, and troubleshooting, see [EXTERNAL_REPO_USAGE.md](EXTERNAL_REPO_USAGE.md)**

#### Quick Start

In your external repository, create a workflow file (e.g., `.github/workflows/ai-analysis.yml`):

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

#### Available Workflows

**1. Complete PR Automation (Recommended)** - `.github/workflows/pr-automation.yml`

One-stop solution that automatically analyzes PRs and allows developers to apply fixes with `/apply-logs` comment.

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

This workflow combines analysis and automatic fix application in one package.

#### Required Secrets in Your External Repository

To use these workflows from your repository, you need to configure the following secrets:

1. **CURSOR_API_KEY** - For AI-powered code analysis (required)
2. **BOT_GITHUB_TOKEN** (Optional) - GitHub PAT with repo access. If not provided, falls back to `GITHUB_TOKEN`

**Note:** The ai-monitoring repository must be accessible to your external repository. For private repos, ensure the calling repository has access or use a BOT_GITHUB_TOKEN with appropriate permissions.

#### Manual Trigger (Alternative)

`pr-automation.yml` is intended to run on PR events; for local development/testing, run the scripts directly (see “Development” below).

## Development

### Prerequisites

- Python 3.11+
- pip

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run a script locally:
   ```bash
   python actions/analyze-pr-code/code_analyzer.py --pr-number 123 --repository owner/repo
   ```

### Adding Dependencies

Add Python packages to `requirements.txt` as needed for your implementation.

## Implementation

### Analyze PR Code (Fully Implemented)

The `analyze-pr-code` action is fully implemented with:

**Classes:**
- `CursorAnalyzer` - Handles Cursor CLI installation and file analysis
- `GitHubPRAnalyzer` - Gets changed files from PR using git diff

**Features:**
- Auto-installs Cursor CLI if not present
- Analyzes changed files (`.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.go`)
- Uses customizable prompt files
- Parses Cursor AI JSON responses (including markdown-wrapped JSON)
- Uploads results as artifacts
- Posts formatted comment on PR with findings

**Local Testing:**
```bash
# Set environment variables
export GITHUB_TOKEN="your-token"
export CURSOR_API_KEY="your-cursor-api-key"

# Run the script
cd your-repo-with-changes
python /path/to/actions/analyze-pr-code/code_analyzer.py \
  --pr-number 123 \
  --repository owner/repo \
  --prompt-file .github/prompts/analyze-logs.txt
```

### Other Actions (Placeholder)

The `apply-suggested-logs` and `apply-suggested-gc-resources` actions contain placeholder implementations. To implement:

1. Navigate to the appropriate `main.py` file in `actions/<action-name>/`
2. Add your implementation following the pattern in `analyze-pr-code/code_analyzer.py`
3. Add any required dependencies to `requirements.txt`
4. Test locally before committing

## Prompts

Create custom analysis prompts in `.github/prompts/` directory. The prompt should:
- Describe what to analyze
- Specify the output format (preferably JSON)
- Be clear and actionable

Example prompt structure:
```
Analyze this code for [specific concern].

Provide:
1. [Aspect 1]
2. [Aspect 2]

Return JSON format:
{
  "issues": ["list of issues"],
  "summary": "overall summary"
}
```

## Environment Variables

The workflows and scripts use the following environment variables:

### General
- `GITHUB_TOKEN` - GitHub token for API access
- `PR_NUMBER` - Pull request number (if provided)
- `REPOSITORY` - Repository name in format `owner/repo` (if provided)

### Groundcover Alert Creation
- `ANTHROPIC_API_KEY` - API key for Claude AI analysis
- `GROUNDCOVER_API_KEY` - API key for groundcover (get via `groundcover auth get-datasources-api-key`)
- `GROUNDCOVER_API_URL` - (Optional) Base URL for groundcover API (defaults to `https://api.groundcover.com`)

## License

[Add your license here]

