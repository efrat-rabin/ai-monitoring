# AI Monitoring - GitHub Actions

This repository contains GitHub Actions workflows for AI-powered code monitoring and optimization.

## Structure

```
.
├── .github/
│   └── workflows/          # GitHub Actions workflow definitions
│       ├── analyze-pr-code.yml
│       ├── apply-suggested-logs.yml
│       └── apply-suggested-gc-resources.yml
├── actions/                # Action implementation scripts
│   ├── analyze-pr-code/
│   │   └── main.py
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

Analyzes pull request code to provide insights and recommendations.

**Trigger:** `workflow_dispatch` (can be called from external workflows)

**Inputs:**
- `pr_number` - Pull request number (optional)
- `repository` - Repository in format `owner/repo` (optional)
- `git_token` - GitHub token for API access (required)

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

Each workflow calls a corresponding Python script in the `actions/` directory. The scripts currently contain placeholder implementations with TODO markers where the actual logic should be added.

To implement the logic:

1. Navigate to the appropriate `main.py` file in `actions/<action-name>/`
2. Add your implementation in the `main()` function
3. Add any required dependencies to `requirements.txt`
4. Test locally before committing

## Environment Variables

The workflows provide the following environment variables to the Python scripts:

- `GITHUB_TOKEN` - GitHub token for API access
- `PR_NUMBER` - Pull request number (if provided)
- `REPOSITORY` - Repository name in format `owner/repo` (if provided)

## License

[Add your license here]

