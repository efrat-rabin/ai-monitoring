# Tests

Test scripts and the PR workflow test plan. **Run all scripts from the repository root.**

## Scripts

| Script | Purpose |
|--------|---------|
| [test_pr_workflow_apply_refresh.py](test_pr_workflow_apply_refresh.py) | End-to-end test for PR automation: analyze, apply-logs, refresh-patches. Creates a PR (optional), asserts 3 comments, applies 1st then 2nd, verifies commits and ISSUE_DATA updates. |
| [test_analyzer.sh](test_analyzer.sh) | Test the code analyzer with mock data (`mock`), generated mock (`test`), or real Cursor AI (`cursor`). |
| [test_apply.sh](test_apply.sh) | Test apply-suggested-logs (deprecated: main.py uses `--comment-body-file`, not `--analysis-results`). |
| [test_examples.sh](test_examples.sh) | Groundcover alert examples (deprecated: log-line flow removed). |
| [test_gc_only.sh](test_gc_only.sh) | Groundcover test mode without AI (deprecated: log-line flow removed). |

## Usage

From the repo root:

```bash
# PR workflow test (full: create branch, open PR, run assertions)
export GITHUB_TOKEN=...
python tests/test_pr_workflow_apply_refresh.py

# Assertions only (PR already open)
python tests/test_pr_workflow_apply_refresh.py --pr-number 123

# Code analyzer (mock / test / cursor)
bash tests/test_analyzer.sh [mock|test|cursor]
```

## Test plan

See [TEST_PLAN_PR_WORKFLOW.md](TEST_PLAN_PR_WORKFLOW.md) for the full step-by-step PR workflow test plan (analyze → apply-logs → refresh-patches).
