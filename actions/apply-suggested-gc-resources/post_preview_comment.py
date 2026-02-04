#!/usr/bin/env python3
"""Post monitor preview comment asking for user confirmation"""

import os
import sys
from pathlib import Path

import argparse
import yaml
import requests

# Ensure libs and same dir are on path (workflow runs from repo root)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "libs"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import github_api  # noqa: E402
from actions_env import add_common_pr_args, is_verbose, require_github_token  # noqa: E402
from github_comment_utils import extract_issue_data_from_comment, get_root_comment  # noqa: E402


def post_preview_comment(github_token: str, repository: str, pr_number: int,
                        comment_id: str, monitor_path: str,
                        verbose: bool = False):
    """Post a monitor preview comment as reply to the /generate-monitor comment."""
    # Load monitor YAML from file
    with open(monitor_path, "r") as f:
        monitor = yaml.safe_load(f)

    title = monitor.get("title", "Monitor")
    print(f"[INFO] Preparing monitor preview for: {title}")

    # Serialize monitor for the code block (readable YAML)
    yaml_str = yaml.dump(monitor, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Build comment: header + collapsible YAML block + footer
    comment_body = """## GroundCover monitor preview

<details>
<summary>View full YAML</summary>

```yaml
""" + yaml_str + """
```

</details>

---

**Reply with `/create-monitor` to create it in GroundCover.**

_Preview by AI automation 🤖_"""

    print(f"[INFO] Posting comment to PR #{pr_number}")
    print(f"[INFO] Comment will be reply to comment ID: {comment_id}")
    if verbose:
        print(f"[DEBUG] Monitor: {title}")
        print(f"[DEBUG] Comment body length: {len(comment_body)} chars")

    comment_id_out = github_api.post_pr_review_comment_and_return_id(
        github_token,
        repository,
        pr_number,
        comment_body,
        in_reply_to=int(comment_id),
        verbose=verbose,
    )
    print("✓ Monitor preview comment posted")
    return comment_id_out


def main():
    parser = argparse.ArgumentParser()
    add_common_pr_args(parser)
    parser.add_argument("--monitor", type=str,
                        default="actions/apply-suggested-gc-resources/mock-monitor.yaml",
                        help="Path to monitor YAML file")
    args = parser.parse_args()

    verbose = is_verbose()
    if verbose:
        print("[DEBUG] Running post_preview_comment.py with verbose mode")
        print(f"[DEBUG] PR Number: {args.pr_number}")
        print(f"[DEBUG] Repository: {args.repository}")
        print(f"[DEBUG] Comment ID: {args.comment_id}")
        print(f"[DEBUG] Monitor path: {args.monitor}")

    github_token = require_github_token()
    if not github_token:
        return 1
    if verbose:
        print("[DEBUG] GITHUB_TOKEN present: True")
    
    try:
        preview_comment_id = post_preview_comment(
            github_token, 
            args.repository, 
            int(args.pr_number), 
            args.comment_id,
            args.monitor,
            verbose=verbose
        )
        
        # Output for GitHub Actions
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"preview_comment_id={preview_comment_id}\n")
        
        if verbose:
            print(f"[DEBUG] Successfully completed post_preview_comment.py")
            print(f"[DEBUG] Preview comment ID: {preview_comment_id}")
        
        return 0
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP Error posting preview comment: {e}")
        print(f"ERROR: Status code: {e.response.status_code if e.response else 'N/A'}")
        if e.response:
            print(f"ERROR: Response body: {e.response.text}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"ERROR: Failed to post preview comment: {e}")
        print(f"ERROR: Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
