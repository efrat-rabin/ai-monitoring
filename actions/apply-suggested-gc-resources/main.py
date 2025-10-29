#!/usr/bin/env python3
"""
Create Groundcover Alerts from Log Lines
"""

import os
import sys
import argparse
import json

from ai_analyzer import AIAnalyzer
from groundcover_client import GroundcoverClient


def main():
    """Main entry point for creating groundcover alerts from log lines."""
    parser = argparse.ArgumentParser(description='Create alerts in groundcover from log lines')
    parser.add_argument('--log-line', type=str, required=True, help='Log line in stringified JSON format')
    parser.add_argument('--dry-run', action='store_true', help='Analyze log but do not create alert')
    parser.add_argument('--test-mode', action='store_true', help='Skip AI analysis and use mock recommendation for testing')
    args = parser.parse_args()
    
    try:
        # Parse log line
        log_data = json.loads(args.log_line)
        
        # Analyze with AI or use mock data for testing
        if args.test_mode:
            print("[TEST MODE] Using mock AI recommendation")
            from ai_analyzer import AlertRecommendation
            recommendation = AlertRecommendation(
                should_create=True,
                name="Test Alert - Database Connection Issue",
                description="This is a test alert for database connection failures",
                severity="high",
                condition="error rate > threshold",
                threshold="1 error per minute"
            )
        else:
            analyzer = AIAnalyzer()
            recommendation = analyzer.analyze_log_line(log_data)
        
        if not recommendation.should_create:
            print("No alert needed for this log line")
            print(json.dumps(recommendation.to_dict(), indent=2))
            return 0
        
        print(f"Alert: {recommendation.name} ({recommendation.severity})")
        
        # Build the groundcover request
        gc_client = GroundcoverClient()
        gc_request = gc_client.build_alert_config(
            name=recommendation.name,
            description=recommendation.description,
            severity=recommendation.severity,
            condition=recommendation.condition,
            threshold=recommendation.threshold,
            log_context=log_data
        )
        
        if args.dry_run:
            print("\n[DRY RUN] Groundcover API Request:")
            print(f"URL: {gc_client.base_url}/api/monitors")
            print(f"Method: POST")
            print(f"Headers: {json.dumps(gc_client.headers, indent=2)}")
            print(f"\nRequest Body:")
            print(json.dumps(gc_request, indent=2))
            return 0
        
        # Create alert in groundcover
        result = gc_client.create_alert(
            name=recommendation.name,
            description=recommendation.description,
            severity=recommendation.severity,
            condition=recommendation.condition,
            threshold=recommendation.threshold,
            log_context=log_data
        )
        
        print(f"Alert created: {result.get('id', 'N/A')}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

