#!/bin/bash
# Test script for code analyzer with mock data

set -e

echo "=== Testing Code Analyzer with Mock Data ==="
echo ""

# Set minimal required env vars
export GITHUB_TOKEN="${GITHUB_TOKEN:-fake-token-for-testing}"
export CURSOR_API_KEY="${CURSOR_API_KEY:-fake-key-for-testing}"
export PR_NUMBER="${PR_NUMBER:-123}"
export REPOSITORY="${REPOSITORY:-owner/repo}"

echo "Running analyzer in test mode..."
python actions/analyze-pr-code/code_analyzer.py --test-mode

echo ""
echo "=== Test Complete ==="
echo ""

if [ -f analysis-results.json ]; then
    echo "Results written to analysis-results.json:"
    cat analysis-results.json | python3 -m json.tool
else
    echo "ERROR: No results file generated"
    exit 1
fi

