#!/bin/bash
# Test script for code analyzer with mock data
# Run from repo root: bash tests/test_analyzer.sh [mock|test|cursor]

set -e

cd "$(git rev-parse --show-toplevel)"

# Set minimal required env vars
export GITHUB_TOKEN="${GITHUB_TOKEN:-fake-token-for-testing}"
export CURSOR_API_KEY="${CURSOR_API_KEY:-fake-key-for-testing}"
export PR_NUMBER="${PR_NUMBER:-123}"
export REPOSITORY="${REPOSITORY:-owner/repo}"

# Check command line argument for mode
MODE="${1:-mock}"

if [ "$MODE" = "mock" ]; then
    echo "=== Testing Code Analyzer with Predefined Mock Data ==="
    echo ""
    echo "Running analyzer with --use-mock flag..."
    python actions/analyze-pr-code/code_analyzer.py --use-mock
elif [ "$MODE" = "test" ]; then
    echo "=== Testing Code Analyzer with Generated Mock Data ==="
    echo ""
    echo "Running analyzer with --test-mode flag..."
    python actions/analyze-pr-code/code_analyzer.py --test-mode
elif [ "$MODE" = "cursor" ]; then
    echo "=== Testing Code Analyzer with Cursor AI ==="
    echo ""
    echo "Running analyzer with real Cursor AI..."
    python actions/analyze-pr-code/code_analyzer.py --use-cursor
else
    echo "ERROR: Unknown mode '$MODE'"
    echo "Usage: $0 [mock|test|cursor]"
    echo "  mock   - Use predefined mock data (default)"
    echo "  test   - Generate mock data per file"
    echo "  cursor - Use real Cursor AI"
    exit 1
fi

echo ""
echo "=== Test Complete ==="
echo ""

if [ -f analysis-results.json ]; then
    echo "Results written to analysis-results.json:"
    echo ""
    echo "Summary:"
    python3 -c "
import json
with open('analysis-results.json') as f:
    data = json.load(f)
    print(f'  Files analyzed: {len(data)}')
    total_issues = sum(len(r.get('analysis', {}).get('issues', [])) for r in data)
    print(f'  Total issues: {total_issues}')
    for result in data:
        file = result.get('file', 'unknown')
        issues = result.get('analysis', {}).get('issues', [])
        print(f'  - {file}: {len(issues)} issue(s)')
"
    echo ""
    echo "Full JSON output:"
    cat analysis-results.json | python3 -m json.tool
else
    echo "ERROR: No results file generated"
    exit 1
fi
