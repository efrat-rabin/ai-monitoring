#!/bin/bash
# Test examples for the groundcover alert creation script

echo "=========================================="
echo "Groundcover Alert Creation - Test Examples"
echo "=========================================="
echo ""

# Check if environment variables are set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
fi

if [ -z "$GROUNDCOVER_API_KEY" ]; then
    echo "⚠️  Warning: GROUNDCOVER_API_KEY not set"
fi

echo ""
echo "Running tests in DRY RUN mode (no alerts will be created)"
echo ""

# Test 1: Error log that should create an alert
echo "Test 1: Database Connection Error"
echo "-----------------------------------"
python main.py --log-line '{"level":"error","message":"Database connection failed after 3 retries","service":"user-service","timestamp":"2025-10-29T10:30:00Z","error":"Connection timeout"}' --dry-run
echo ""

# Test 2: High memory warning
echo "Test 2: High Memory Usage Warning"
echo "-----------------------------------"
python main.py --log-line '{"level":"warning","message":"Memory usage above 85%","service":"payment-service","memory_usage":"87%","timestamp":"2025-10-29T10:31:00Z"}' --dry-run
echo ""

# Test 3: Info log that likely won't create an alert
echo "Test 3: Informational Log"
echo "-----------------------------------"
python main.py --log-line '{"level":"info","message":"User logged in successfully","user_id":"12345","timestamp":"2025-10-29T10:32:00Z"}' --dry-run
echo ""

# Test 4: Critical error
echo "Test 4: Critical Service Crash"
echo "-----------------------------------"
python main.py --log-line '{"level":"critical","message":"Service crashed unexpectedly","service":"order-service","exit_code":1,"timestamp":"2025-10-29T10:33:00Z"}' --dry-run
echo ""

# Test 5: API rate limit warning
echo "Test 5: API Rate Limit Warning"
echo "-----------------------------------"
python main.py --log-line '{"level":"warning","message":"API rate limit approaching","service":"api-gateway","current_rate":"950/1000","timestamp":"2025-10-29T10:34:00Z"}' --dry-run
echo ""

echo "=========================================="
echo "Tests completed!"
echo "=========================================="
echo ""
echo "To run without --dry-run and actually create alerts:"
echo "  python main.py --log-line '<your-json-log>'"

