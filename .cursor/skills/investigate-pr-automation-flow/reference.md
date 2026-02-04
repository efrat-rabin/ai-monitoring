# PR Automation Workflow Reference

Reference for `.github/workflows/pr-automation.yml`: job triggers, comment markers, and bot vs user rules.

## Workflow triggers

| Event | Job(s) that may run |
|-------|----------------------|
| `pull_request` (opened, reopened) | **analyze** (only if same repo, actor ≠ github-actions[bot]) |
| `pull_request` (synchronize) | **refresh-patches** |
| `pull_request_review_comment` (created) | **apply-logs** (if body contains `/apply-logs`), **generate-monitor** (`/generate-monitor`), **create-monitor** (`/create-monitor`), **generate-dashboard** (`/generate-dashboard`), **create-dashboard** (`/create-dashboard`) |

## Job flow (analyze → apply-logs → refresh)

1. **analyze** – Runs on PR opened/reopened. Runs `code_analyzer.py` then `post_comment.py`. Posts **review comments** (one per issue) with:
   - Visible: `🤖 <severity>`, description, recommendation, `Reply with \`/apply-logs\` to apply this change automatically.`
   - Hidden: `<!-- ISSUE_DATA: {...} -->`, `<!-- STATUS: analyzed -->`
   - Author: `github-actions[bot]` (app).

2. **apply-logs** – Runs when a **review comment** is created whose body contains `/apply-logs`. The comment must be a **reply** to a bot analysis comment. Workflow:
   - `comment_state.py check`: ensures parent comment has `<!-- STATUS: analyzed -->` (or no STATUS). If parent is already `applied`, job exits without applying.
   - Applies patches via `apply-suggested-logs/main.py`, commits and pushes.
   - Posts a **reply** to the user’s comment: "✅ Done! Logging improvements applied successfully".
   - Updates the **parent** comment: adds `<!-- STATUS: applied -->`, replaces "Reply with `/apply-logs`" with "✅ Applied".
   - Runs **refresh-patches** in-job for applied files (so synchronize is not required).

3. **refresh-patches** – Runs on `pull_request` synchronize (or in-job after apply-logs). Refreshes ISSUE_DATA patches in other bot comments for the same file (downstream lines).

## Comment markers (bot analysis)

| Marker | Meaning |
|--------|---------|
| `Reply with \`/apply-logs\` to apply this change automatically.` | Bot analysis comment; user can reply with `/apply-logs`. |
| `<!-- STATUS: analyzed -->` | Comment is in "analyzed" state; apply-logs is allowed. |
| `<!-- STATUS: applied -->` | Comment was applied; apply-logs will skip. |
| `✅ Applied` | Visible text after apply; replaces the "Reply with `/apply-logs`" line. |
| `<!-- ISSUE_DATA: {...} -->` | JSON metadata (file, line, patch, etc.) for the issue. |

## Identifying bot vs user comments

- **Bot (app):** `user.login` ends with `[bot]` (e.g. `github-actions[bot]`), or comment body contains `Reply with \`/apply-logs\`` or `<!-- STATUS: analyzed -->` or `<!-- STATUS: applied -->`.
- **User:** Human author; login does not end with `[bot]`.

## Expected comment order (analyze + apply-logs)

1. Bot posts one or more review comments (analysis, STATUS: analyzed).
2. User replies to one of them with exactly `/apply-logs` (or body containing it).
3. Bot posts a reply under that comment ("✅ Done! ...").
4. Bot updates the parent comment body (STATUS: applied, "✅ Applied").

## Common failure reasons

- **apply-logs did not run:** User replied to a non-bot comment, or to a comment that already had STATUS: applied; or body did not contain `/apply-logs`.
- **Wrong comment order in tests:** Review comments are ordered by thread/created_at; ensure test expects bot comments first, then user reply, then bot reply.
- **Refresh not applied:** refresh-patches runs on synchronize or after apply-logs in-job; if using GITHUB_TOKEN, push from apply-logs does not trigger a new workflow run, so refresh is only via the in-job step.
