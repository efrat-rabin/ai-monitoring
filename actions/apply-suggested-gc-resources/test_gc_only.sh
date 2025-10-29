#!/bin/bash
# Test groundcover alert creation without calling AI agent
# This is useful for testing the groundcover API integration repeatedly

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
python3 main.py \
  --log-line '{"level":"error","message":"Database connection failed","service":"user-service"}' \
  --test-mode \
  --dry-run
echo ""

# Test 2: Actually create the alert (if you want to test)
# Uncomment the following to create a real alert
# echo "Test 2: Create Alert in Groundcover"
# echo "-----------------------------------"
# python3 main.py \
#   --log-line '{"level":"error","message":"Database connection failed","service":"user-service"}' \
#   --test-mode
# echo ""

echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""
echo "Usage:"
echo "  --test-mode          : Skip AI and use mock data"
echo "  --dry-run            : Show request without sending"
echo "  --test-mode --dry-run: Show request with mock data (no AI, no API call)"
echo ""
echo "To create a real alert, remove --dry-run flag"

