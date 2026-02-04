# Quick Start Guide

Groundcover monitors and dashboards are driven by PR review comment commands in `.github/workflows/pr-automation.yml`.

## How to use (from a PR)

1. Open a PR that uses the PR automation workflow.
2. Reply to an analysis comment (or a comment that contains issue/monitor context) with one of:
   - **`/generate-monitor`** – Generates monitor YAML via Cursor and posts a preview.
   - **`/create-monitor`** – Creates the monitor in Groundcover (if `GROUNDCOVER_API_KEY` is set) or posts manual instructions.
   - **`/generate-dashboard`** – Posts a dashboard preview.
   - **`/create-dashboard`** – Posts dashboard creation response.

The workflow runs the corresponding script in this directory (see [README.md](README.md)).

## Environment variables (for the workflow)

- `CURSOR_API_KEY` – Required for `/generate-monitor`.
- `GITHUB_TOKEN` – Provided by GitHub Actions.
- `GROUNDCOVER_API_KEY` – Optional; enables creating monitors via API when replying with `/create-monitor`.

## Local / dev

- Install: `pip install -r requirements.txt` (from repo root or this directory).
- Test Groundcover connection:  
  `python -c "from groundcover_client import GroundcoverClient; gc = GroundcoverClient(); print('Connected!' if gc.test_connection() else 'Failed')"`

The standalone log-line flow (`main.py` / `ai_analyzer.py`) was removed. For full workflow testing, see [tests/TEST_PLAN_PR_WORKFLOW.md](../../tests/TEST_PLAN_PR_WORKFLOW.md).
