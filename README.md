# AI Monitoring - GitHub Actions

This repository contains GitHub Actions workflows for AI-powered code monitoring and optimization.

## Structure

```
.
├── .github/
│   ├── workflows/          # GitHub Actions workflow definitions
│   │   ├── analyze-pr-code.yml
│   │   ├── apply-suggested-logs.yml
│   │   └── apply-suggested-gc-resources.yml
│   └── prompts/            # AI prompts for code analysis
│       └── analyze-logs.txt
├── actions/                # Action implementation scripts
│   ├── analyze-pr-code/
│   │   └── main.py        # Full Cursor AI integration
│   ├── apply-suggested-logs/
│   │   └── main.py
│   └── apply-suggested-gc-resources/
│       └── main.py
├── requirements.txt        # Python dependencies
└── README.md
```

## Workflows

### 1. Analyze PR Code

**File:** `.github/workflows/analyze-pr-code.yml`

Analyzes pull request code using Cursor AI to provide insights and recommendations. The workflow:
- Installs Cursor CLI
- Gets changed files from the PR
- Analyzes each file using a custom prompt
- Uploads results as an artifact
- Posts a comment on the PR with findings

**Trigger:** `workflow_dispatch` (can be called from external workflows)

**Inputs:**
- `pr_number` - Pull request number (optional)
- `repository` - Repository in format `owner/repo` (optional)
- `git_token` - GitHub token for API access (required)
- `cursor_api_key` - Cursor API key for AI analysis (required)
- `prompt_file` - Path to prompt file (default: `.github/prompts/analyze-logs.txt`)

### 2. Apply Suggested Logs

**File:** `.github/workflows/apply-suggested-logs.yml`

Applies AI-suggested logging statements to the codebase.

**Trigger:** `workflow_dispatch` (can be called from external workflows)

**Inputs:**
- `pr_number` - Pull request number (optional)
- `repository` - Repository in format `owner/repo` (optional)
- `git_token` - GitHub token for API access (required)

### 3. Apply Suggested GC Resources

**File:** `.github/workflows/apply-suggested-gc-resources.yml`

Applies suggested garbage collection resource optimizations.

**Trigger:** `workflow_dispatch` (can be called from external workflows)

**Inputs:**
- `pr_number` - Pull request number (optional)
- `repository` - Repository in format `owner/repo` (optional)
- `git_token` - GitHub token for API access (required)

## Usage

### Calling workflows from external repositories

You can trigger these workflows from other repositories using the `workflow_dispatch` event:

```yaml
- name: Trigger workflow
  uses: peter-evans/repository-dispatch@v2
  with:
    token: ${{ secrets.PAT_TOKEN }}
    repository: your-org/ai-monitoring
    event-type: workflow_dispatch
    workflow: analyze-pr-code.yml
    inputs: |
      pr_number: "123"
      repository: "your-org/your-repo"
```

Or using the GitHub CLI:

```bash
gh workflow run analyze-pr-code.yml \
  --repo your-org/ai-monitoring \
  -f pr_number=123 \
  -f repository=your-org/your-repo \
  -f git_token=$GITHUB_TOKEN
```

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
   python actions/analyze-pr-code/main.py --pr-number 123 --repository owner/repo
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
python /path/to/actions/analyze-pr-code/main.py \
  --pr-number 123 \
  --repository owner/repo \
  --prompt-file .github/prompts/analyze-logs.txt
```

### Other Actions (Placeholder)

The `apply-suggested-logs` and `apply-suggested-gc-resources` actions contain placeholder implementations. To implement:

1. Navigate to the appropriate `main.py` file in `actions/<action-name>/`
2. Add your implementation following the pattern in `analyze-pr-code/main.py`
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

The workflows provide the following environment variables to the Python scripts:

- `GITHUB_TOKEN` - GitHub token for API access
- `PR_NUMBER` - Pull request number (if provided)
- `REPOSITORY` - Repository name in format `owner/repo` (if provided)

## License

[Add your license here]

