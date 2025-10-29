# Groundcover Alert Creation from Log Lines

This script analyzes individual log lines using AI and automatically creates appropriate alerts in groundcover.

## Overview

The script:
1. Receives a single log line as stringified JSON via command-line argument
2. Uses AI (Claude) to analyze if the log line warrants an alert
3. If appropriate, creates an alert in groundcover via their API

## Prerequisites

### Environment Variables

The following environment variables must be set:

- `ANTHROPIC_API_KEY` - API key for Claude AI analysis
- `GROUNDCOVER_API_KEY` - API key for groundcover (get via `groundcover auth get-datasources-api-key`)
- `GROUNDCOVER_API_URL` (optional) - Base URL for groundcover API (defaults to `https://api.groundcover.com`)

### Dependencies

Install required Python packages:

```bash
pip install -r ../../requirements.txt
```

## Usage

### Basic Usage

```bash
python main.py --log-line '{"level":"error","message":"Database connection failed","service":"api","timestamp":"2025-10-29T10:30:00Z"}'
```

### Dry Run Mode

Analyze the log line without creating an alert:

```bash
python main.py --log-line '{"level":"error","message":"Database connection failed"}' --dry-run
```

### Example Log Line Formats

**Error Log:**
```json
{
  "level": "error",
  "message": "Failed to connect to database",
  "service": "user-service",
  "timestamp": "2025-10-29T10:30:00Z",
  "error": "Connection timeout after 30s"
}
```

**Warning Log:**
```json
{
  "level": "warning",
  "message": "High memory usage detected",
  "service": "payment-service",
  "memory_usage": "85%",
  "timestamp": "2025-10-29T10:30:00Z"
}
```

**Info Log (likely won't create alert):**
```json
{
  "level": "info",
  "message": "User logged in successfully",
  "user_id": "12345",
  "timestamp": "2025-10-29T10:30:00Z"
}
```

## How It Works

### 1. Log Line Parsing
The script parses the stringified JSON log line and validates its structure.

### 2. AI Analysis
Claude AI analyzes the log line to determine:
- Should an alert be created?
- What should the alert name be?
- What severity level is appropriate? (critical/high/medium/low)
- What condition should trigger the alert?
- What threshold should be used?

### 3. Alert Creation
If the AI determines an alert is appropriate, the script:
- Constructs a monitor configuration
- Sends it to groundcover API
- Returns the created alert ID

## Output

### Successful Alert Creation
```
============================================================
Groundcover Alert Creation from Log Lines
============================================================

[1/5] Validating environment...
✓ Environment variables present

[2/5] Parsing log line...
✓ Log line parsed successfully
   Log preview: {
  "level": "error",
  "message": "Database connection failed"
}...

[3/5] Analyzing log line with AI...
✓ Analysis complete
   Should create alert: True
   Alert name: Database Connection Failure Alert
   Severity: high
   Condition: error rate > threshold
   Threshold: 1 error per minute

[4/5] Creating alert in groundcover...
Successfully created alert: Database Connection Failure Alert
Alert ID: alert-12345
✓ Alert created successfully

[5/5] Summary
============================================================
Alert Name: Database Connection Failure Alert
Alert ID: alert-12345
Severity: high
Status: Created
============================================================
```

### No Alert Needed
```
[RESULT] AI determined this log line does not warrant an alert.
   Reason: Log appears to be informational or routine.
```

## Module Structure

- `main.py` - Main script orchestrating the workflow
- `ai_analyzer.py` - AI analysis module using Claude
- `groundcover_client.py` - Groundcover API client

## Error Handling

The script handles various error scenarios:
- Invalid JSON in log line
- Missing environment variables
- AI API failures
- Groundcover API failures

All errors are logged with descriptive messages.

## Integration with GitHub Actions

This script can be integrated into GitHub Actions workflows. See the parent directory's workflow files for examples.

## Troubleshooting

### "Missing required environment variables"
Ensure both `ANTHROPIC_API_KEY` and `GROUNDCOVER_API_KEY` are set:
```bash
export ANTHROPIC_API_KEY="your-key-here"
export GROUNDCOVER_API_KEY="your-key-here"
```

### "Invalid JSON in log line"
Ensure your log line is valid JSON and properly escaped:
```bash
# Good
python main.py --log-line '{"level":"error","message":"test"}'

# Bad (not escaped)
python main.py --log-line {"level":"error"}
```

### "HTTP error creating alert"
- Verify your groundcover API key is valid
- Check if the groundcover API URL is correct
- Ensure you have permissions to create alerts

## Future Enhancements

Potential improvements:
- Support for batch processing multiple log lines
- Custom alert templates
- Integration with different LLM providers
- Support for dashboard creation
- Alert deduplication logic

