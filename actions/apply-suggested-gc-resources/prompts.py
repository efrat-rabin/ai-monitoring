#!/usr/bin/env python3
"""AI Prompts Configuration"""

ALERT_ANALYSIS_PROMPT = """Analyze this log line and determine if it needs an alert.

Log: {log_line}

Respond with JSON only:
{{
  "should_create": true/false,
  "name": "Alert name",
  "description": "Alert description",
  "severity": "critical/high/medium/low",
  "condition": "Trigger condition",
  "threshold": "Threshold value"
}}

Only create alerts for errors, warnings, or critical conditions. Skip informational logs."""

