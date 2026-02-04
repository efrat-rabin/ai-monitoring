# Implementation Summary

## Overview

This directory contains scripts used by `.github/workflows/pr-automation.yml` to generate and create Groundcover monitors and dashboards from PR review comments. Entry points are comment commands: `/generate-monitor`, `/create-monitor`, `/generate-dashboard`, `/create-dashboard`.

## Current components (in use by workflow)

| Script | Purpose |
|--------|---------|
| `generate_monitor_yaml.py` | Generates monitor YAML via Cursor AI from issue context; posts preview comment. |
| `post_create_monitor_response.py` | Creates monitor in Groundcover from YAML in parent comment (or posts manual instructions). |
| `post_dashboard_preview.py` | Posts dashboard preview comment. |
| `post_create_dashboard_response.py` | Posts dashboard creation response. |
| `post_preview_comment.py` | Helpers: `extract_issue_data_from_comment`, `get_root_comment` (used by `generate_monitor_yaml.py`). |
| `prompts.py` | `MONITOR_YAML_GENERATION_PROMPT` for Cursor. |
| `groundcover_client.py` | Groundcover API client (used when `GROUNDCOVER_API_KEY` is set). |

## Removed (unused from workflow)

The following were removed as part of the unused-code cleanup (not invoked by `pr-automation.yml`):

- `main.py` – Standalone log-line → alert flow (orchestrator).
- `ai_analyzer.py` – AI analysis for that flow.
- `generate_monitor_image.py` – Preview image generation (never used by workflow).

Test scripts [tests/test_examples.sh](../../tests/test_examples.sh) and [tests/test_gc_only.sh](../../tests/test_gc_only.sh) targeted the removed `main.py` and are kept for reference but are no longer runnable; see [README.md](README.md).

## Environment variables

- `CURSOR_API_KEY` – Used by `generate_monitor_yaml.py`.
- `GITHUB_TOKEN` – Used by all scripts for GitHub API.
- `GROUNDCOVER_API_KEY` – (Optional) Enables creating monitors via API in `post_create_monitor_response.py`.

## Getting started

See [QUICKSTART.md](QUICKSTART.md) and [README.md](README.md).
