# Quick Start Guide

Get started with groundcover alert creation from log lines in 5 minutes.

## Step 1: Install Dependencies

```bash
cd /Users/ayala.gottfried/Documents/dev/ai-monitoring
pip install -r requirements.txt
```

## Step 2: Set Environment Variables

```bash
# Required: Anthropic API key for AI analysis
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Required: Groundcover API key
export GROUNDCOVER_API_KEY="your-groundcover-api-key"

# Optional: Custom groundcover API URL
export GROUNDCOVER_API_URL="https://api.groundcover.com"
```

### Getting Your API Keys

**Anthropic API Key:**
1. Sign up at https://console.anthropic.com/
2. Navigate to API Keys section
3. Create a new API key

**Groundcover API Key:**
```bash
groundcover auth get-datasources-api-key
```

## Step 3: Test with Dry Run

Test the script without creating actual alerts:

```bash
cd actions/apply-suggested-gc-resources

# Test with an error log
python main.py --log-line '{"level":"error","message":"Database connection failed","service":"api"}' --dry-run
```

## Step 4: Create Your First Alert

Remove the `--dry-run` flag to create an actual alert:

```bash
python main.py --log-line '{"level":"error","message":"Database connection failed","service":"api"}'
```

## Step 5: Run Test Suite

Run the included test examples:

```bash
./test_examples.sh
```

## Common Use Cases

### Error Monitoring
```bash
python main.py --log-line '{
  "level": "error",
  "message": "Payment processing failed",
  "service": "payment-service",
  "error_code": "PAYMENT_TIMEOUT"
}'
```

### Performance Issues
```bash
python main.py --log-line '{
  "level": "warning",
  "message": "Response time exceeds threshold",
  "service": "api-gateway",
  "response_time_ms": 5000,
  "threshold_ms": 1000
}'
```

### Resource Alerts
```bash
python main.py --log-line '{
  "level": "critical",
  "message": "Memory usage critical",
  "service": "worker-service",
  "memory_usage_percent": 95
}'
```

## What Happens Next?

1. **AI Analysis**: Claude analyzes your log line
2. **Decision**: AI determines if an alert is appropriate
3. **Alert Creation**: If appropriate, an alert is created in groundcover
4. **Confirmation**: You receive the alert ID and details

## Troubleshooting

### "Missing required environment variables"
Make sure both API keys are set:
```bash
echo $ANTHROPIC_API_KEY
echo $GROUNDCOVER_API_KEY
```

### "Invalid JSON in log line"
Ensure your JSON is properly formatted and escaped:
```bash
# Use single quotes around the JSON
python main.py --log-line '{"key":"value"}'
```

### Test Connection
```python
# Test groundcover connection
python -c "from groundcover_client import GroundcoverClient; gc = GroundcoverClient(); print('Connected!' if gc.test_connection() else 'Failed')"
```

## Next Steps

- Read the [full documentation](README.md)
- Integrate with your CI/CD pipeline
- Set up automated log monitoring
- Configure alert notification channels in groundcover

## Support

For issues or questions:
1. Check the [README](README.md) for detailed documentation
2. Review the test examples in `test_examples.sh`
3. Verify your API keys and permissions

