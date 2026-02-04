#!/bin/bash
# Test groundcover alert creation without calling AI agent
# DEPRECATED: This script called main.py (log-line flow), which was removed.
# The workflow uses generate_monitor_yaml.py, post_create_* etc. instead.
# See actions/apply-suggested-gc-resources/README.md and .github/workflows/pr-automation.yml.
# Run from repo root: bash tests/test_gc_only.sh

set -e

cd "$(git rev-parse --show-toplevel)"

echo "=========================================="
echo "Groundcover Alert Creation - Test Mode"
echo "=========================================="
echo ""

# Check if environment variables are set
if [ -z "$GROUNDCOVER_API_KEY" ]; then
    echo "⚠️  Warning: GROUNDCOVER_API_KEY not set"
    exit 1
fi

echo "Testing groundcover alert creation with mock AI data..."
echo ""

# Test 1: Dry run to see the request
echo "Test 1: Dry Run - Show Request"
echo "-----------------------------------"
python3 actions/apply-suggested-gc-resources/main.py \
  --log-line '{"level":"error","message":"Database connection failed","service":"user-service"}' \
  --test-mode \
  --dry-run || true
echo ""

# Test 2: Actually create the alert (if you want to test)
# Uncomment the following to create a real alert
# echo "Test 2: Create Alert in Groundcover"
# echo "-----------------------------------"
# python3 actions/apply-suggested-gc-resources/main.py \
#   --log-line '{"level":"error","message":"Database connection failed","service":"user-service"}' \
#   --test-mode
# echo ""

echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""
echo "DEPRECATED: main.py (log-line flow) was removed. This script is reference-only."
echo "Usage (if main.py were present):"
echo "  --test-mode          : Skip AI and use mock data"
echo "  --dry-run            : Show request without sending"
echo "  --test-mode --dry-run: Show request with mock data (no AI, no API call)"
