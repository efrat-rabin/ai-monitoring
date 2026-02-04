---
name: investigate-pr-automation-flow
description: Gets PR list and investigates the flow of .github/workflows/pr-automation.yml for a PR: comment order (user vs bot/app), whether the flow succeeded or failed, and why. Use when debugging PR automation, investigating test failures, or verifying analyze/apply-logs/refresh comment sequences.
---

# Investigate PR Automation Flow

Use this skill to debug PR automation and test failures by listing PRs, fetching review comments in order, and mapping them to the `pr-automation.yml` workflow.

## Quick workflow

1. **Get PR list** – Use GitHub MCP `list_pull_requests` (owner, repo) or `search_pull_requests` if filtering by author/branch. Default: `owner`/`repo` from repo (e.g. `efrat-rabin`/`ai-monitoring`).
2. **Pick a PR** – Choose by number from the list (e.g. for a failing test).
3. **Get review comments in order** – Use GitHub MCP `pull_request_read` with `method: "get_review_comments"` for that PR. Paginate if needed (`perPage`, `after`/`page` as per tool schema).
4. **Classify each comment** – For each comment use:
   - **Bot/app**: `user.login` ends with `[bot]` (e.g. `github-actions[bot]`), or body contains `Reply with \`/apply-logs\`` or `<!-- STATUS: analyzed -->` / `<!-- STATUS: applied -->`.
   - **User**: human author (login does not end with `[bot]`).
5. **Map to workflow jobs** – Use [reference.md](reference.md) to map comment content and order to jobs (analyze → apply-logs → refresh, slash commands).
6. **Assess outcome** – Report: comment order (user vs bot), which job(s) ran, success/failure, and why (e.g. wrong order, missing STATUS, apply-logs not triggered).

## Comment order checklist

- **Expected (analyze + apply-logs)**:
  1. Bot posts one or more review comments (analysis with `<!-- STATUS: analyzed -->`, `Reply with \`/apply-logs\``).
  2. User replies to one of those comments with `/apply-logs`.
  3. Bot posts a reply (e.g. "✅ Done! Logging improvements applied successfully") and updates the parent comment to `<!-- STATUS: applied -->` and "✅ Applied".
- **Failure signals**: User comment before any bot analysis; `/apply-logs` on a non-bot or already-applied comment; missing STATUS marker; bot reply missing after `/apply-logs`.

## Output format

Produce a short report:

```markdown
## PR #<number> – Automation flow

**Comments (chronological):**
| # | Author (user/bot) | Snippet / Trigger | In-reply-to |
|---|-------------------|-------------------|-------------|
| 1 | bot (github-actions) | 🤖 HIGH - ... Reply with `/apply-logs` | — |
| 2 | user | /apply-logs | <parent_id> |
| 3 | bot | ✅ Done! Logging improvements applied | <comment_id> |

**Flow:** analyze → apply-logs (1st comment) → success reply + parent updated to applied.
**Result:** OK / FAIL – <reason>.
```

## GitHub MCP usage

- **List PRs:** `list_pull_requests` with `owner`, `repo`; optional `state`, `sort`, `direction`, `perPage`, `page`.
- **Review comments:** `pull_request_read` with `method: "get_review_comments"`, `owner`, `repo`, `pullNumber`; use pagination as in tool schema.
- **Workflow reference:** See [reference.md](reference.md) for job triggers, comment markers, and bot vs user rules.

## When to use

- After a test fails (e.g. `test_pr_workflow_apply_refresh.py`) to see real comment order and job behavior.
- To verify that analyze ran and posted comments, then apply-logs ran after a user `/apply-logs` reply.
- To explain why apply-logs did not run (e.g. reply to wrong comment, or parent not in "analyzed" state).
