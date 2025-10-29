#!/usr/bin/env python3
"""AI Analyzer Module"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add libs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))
from cursor_client import CursorClient
from prompts import ALERT_ANALYSIS_PROMPT


class AlertRecommendation:
    """Alert recommendation data."""
    
    def __init__(self, should_create: bool, name: str = "", description: str = "",
                 severity: str = "", condition: str = "", threshold: str = ""):
        self.should_create = should_create
        self.name = name
        self.description = description
        self.severity = severity
        self.condition = condition
        self.threshold = threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_create": self.should_create,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "condition": self.condition,
            "threshold": self.threshold
        }


class AIAnalyzer:
    """Analyzes log lines using AI."""
    
    def __init__(self):
        self.cursor = CursorClient()
        # Install and verify Cursor CLI
        if not self.cursor.install_cursor_cli():
            raise RuntimeError("Failed to install Cursor CLI")
        if not self.cursor.verify_setup():
            raise RuntimeError("Cursor CLI setup verification failed")
    
    def analyze_log_line(self, log_line: Dict[str, Any]) -> AlertRecommendation:
        """Analyze a log line to determine if an alert should be created."""
        log_context = json.dumps(log_line, indent=2)
        prompt = ALERT_ANALYSIS_PROMPT.format(log_line=log_context)

        try:
            response = self.cursor.send_message(prompt)
            
            # Parse response
            if isinstance(response, dict):
                data = response
            elif isinstance(response, str):
                start = response.find('{')
                end = response.rfind('}') + 1
                data = json.loads(response[start:end])
            else:
                return AlertRecommendation(should_create=False)
            
            return AlertRecommendation(
                should_create=data.get('should_create', False),
                name=data.get('name', ''),
                description=data.get('description', ''),
                severity=data.get('severity', 'medium'),
                condition=data.get('condition', ''),
                threshold=data.get('threshold', '')
            )
        except Exception as e:
            print(f"Error: {e}")
            return AlertRecommendation(should_create=False)

