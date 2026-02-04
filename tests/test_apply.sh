#!/bin/bash
# Test script for apply-suggested-logs action.
# DEPRECATED: main.py uses --comment-body-file (ISSUE_DATA in comment body), not --analysis-results.
# Run from repo root: bash tests/test_apply.sh

set -e

cd "$(git rev-parse --show-toplevel)"

echo "=== Testing Apply Suggested Logs Action ==="
echo ""

# Check if required environment variables are set
if [ -z "$CURSOR_API_KEY" ]; then
    echo "ERROR: CURSOR_API_KEY environment variable is not set"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable is not set"
    exit 1
fi

# Sample analysis results (minimal example)
SAMPLE_ANALYSIS='[
  {
    "file": "actions/apply-suggested-logs/main.py",
    "analysis": {
      "issues": [
        {
          "severity": "MEDIUM",
          "category": "structured-logging",
          "line": 30,
          "method": "install_cursor_cli",
          "description": "Uses print() statements instead of structured logging",
          "recommendation": "Replace print() with logger.info() for better log management",
          "impact": "Logs cannot be easily parsed or filtered in production"
        }
      ]
    }
  }
]'

echo "Sample Analysis Results:"
echo "$SAMPLE_ANALYSIS" | python3 -m json.tool
echo ""

# Test 1: Check if script can parse analysis results
echo "Test 1: Parsing analysis results..."
python3 actions/apply-suggested-logs/main.py \
    --pr-number "123" \
    --repository "test/repo" \
    --analysis-results "$SAMPLE_ANALYSIS" \
    --comment-id "456" || true

echo ""
echo "=== Test Complete ==="
echo ""
echo "Note: This is a dry-run test. main.py expects --comment-body-file with ISSUE_DATA. To fully test:"
echo "1. Set CURSOR_API_KEY and GITHUB_TOKEN"
echo "2. Use a real PR number and repository"
echo "3. Provide a parent comment body file (with <!-- ISSUE_DATA: {...} -->)"
