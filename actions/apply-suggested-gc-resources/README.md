# Groundcover Resources (Monitors & Dashboards)

Scripts used by `.github/workflows/pr-automation.yml` to generate and create Groundcover monitors and dashboards from PR review comments.

## How the workflow uses this directory

| Comment command       | Script invoked                         |
|-----------------------|----------------------------------------|
| `/generate-monitor`   | `generate_monitor_yaml.py`             |
| `/create-monitor`     | `post_create_monitor_response.py`      |
| `/generate-dashboard` | `post_dashboard_preview.py`            |
| `/create-dashboard`   | `post_create_dashboard_response.py`    |

Users reply with these commands on PR review comment threads. The workflow runs the corresponding script (see [pr-automation.yml](../../.github/workflows/pr-automation.yml)).

## Module structure

- `generate_monitor_yaml.py` – Uses Cursor AI to generate monitor YAML from issue context and posts a preview comment.
- `post_create_monitor_response.py` – Reads YAML from the parent comment and creates the monitor in Groundcover (or posts manual instructions if no API key).
- `post_dashboard_preview.py` – Posts a dashboard preview comment (image + metadata).
- `post_create_dashboard_response.py` – Posts instructions or confirmation for dashboard creation.
- `post_preview_comment.py` – Helpers used by `generate_monitor_yaml.py`: `extract_issue_data_from_comment`, `get_root_comment`.
- `prompts.py` – `MONITOR_YAML_GENERATION_PROMPT` for Cursor.
- `groundcover_client.py` – Groundcover API client (used when `GROUNDCOVER_API_KEY` is set).

## Environment variables

- `CURSOR_API_KEY` – Used by `generate_monitor_yaml.py`.
- `GITHUB_TOKEN` – Used by all scripts for GitHub API.
- `GROUNDCOVER_API_KEY` – (Optional) Enables creating monitors via API in `post_create_monitor_response.py`.

## Test scripts (dev-only)

- [tests/test_examples.sh](../../tests/test_examples.sh) – Previously ran the removed standalone log-line flow; **no longer runnable** (see plan: unused code removed).
- [tests/test_gc_only.sh](../../tests/test_gc_only.sh) – Same; **no longer runnable**.

For workflow testing, use the PR automation workflow or see [tests/TEST_PLAN_PR_WORKFLOW.md](../../tests/TEST_PLAN_PR_WORKFLOW.md).
