#!/usr/bin/env python3
"""
Create Groundcover Alerts from Log Lines
"""

import os
import sys
import argparse
import json
import yaml
from typing import Dict, Any

from ai_analyzer import AIAnalyzer
from groundcover_client import GroundcoverClient


def _build_alert_config(
    name: str,
    description: str,
    severity: str,
    condition: str,
    threshold: str,
    log_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a log-based monitor config for GroundCover (same structure as API expects)."""
    log_level = log_context.get('level', 'error').lower()
    workload = log_context.get('workload', log_context.get('service', 'unknown'))
    sev = severity.upper() if severity.upper() in ['S1', 'S2', 'S3', 'S4'] else 'S2'
    return {
        'title': name,
        'display': {
            'header': name,
            'description': description,
            'resourceHeaderLabels': [],
            'contextHeaderLabels': ['workload', 'pod', 'namespace', 'env'],
        },
        'severity': sev,
        'model': {
            'queries': [
                {
                    'name': 'threshold_input_query',
                    'sqlPipeline': {
                        'selectors': [
                            {'key': 'workload', 'origin': 'root', 'type': 'string', 'alias': 'workload'},
                            {'key': 'pod', 'origin': 'root', 'type': 'string', 'alias': 'pod'},
                            {'key': 'namespace', 'origin': 'root', 'type': 'string', 'alias': 'namespace'},
                            {'key': 'env', 'origin': 'root', 'type': 'string', 'alias': 'env'},
                            {
                                'key': '*',
                                'origin': 'root',
                                'type': 'string',
                                'processors': [{'op': 'count'}],
                                'alias': 'logs_total',
                            },
                        ],
                        'filters': {
                            'conditions': [
                                {
                                    'key': 'level',
                                    'type': 'string',
                                    'origin': 'root',
                                    'filters': [{'op': 'match', 'value': log_level}],
                                }
                            ],
                            'operator': 'or',
                        },
                        'groupBy': [
                            {'key': 'workload', 'origin': 'root', 'type': 'string', 'alias': 'workload'},
                            {'key': 'pod', 'origin': 'root', 'type': 'string', 'alias': 'pod'},
                            {'key': 'namespace', 'origin': 'root', 'type': 'string', 'alias': 'namespace'},
                            {'key': 'env', 'origin': 'root', 'type': 'string', 'alias': 'env'},
                        ],
                        'orderBy': [],
                        'limit': None,
                    },
                    'instantRollup': '5 minutes',
                    'dataType': 'logs',
                }
            ],
            'thresholds': [
                {'name': 'threshold_1', 'inputName': 'threshold_input_query', 'operator': 'gt', 'values': [100]}
            ],
        },
        'labels': {'source': 'ai-monitoring-script', 'log_level': log_level, 'service': workload},
        'annotations': {'condition': condition, 'threshold': threshold, 'test': 'enabled'},
        'executionErrorState': 'OK',
        'noDataState': 'OK',
        'evaluationInterval': {'interval': '5m', 'pendingFor': '0s'},
        'measurementType': 'event',
    }


def main():
    """Main entry point for creating groundcover alerts from log lines."""
    parser = argparse.ArgumentParser(description='Create alerts in groundcover from log lines')
    parser.add_argument('--log-line', type=str, required=True, help='Log line in stringified JSON format')
    parser.add_argument('--dry-run', action='store_true', help='Analyze log but do not create alert')
    parser.add_argument('--test-mode', action='store_true', help='Skip AI analysis and use mock recommendation for testing')
    args = parser.parse_args()

    try:
        log_data = json.loads(args.log_line)

        if args.test_mode:
            print("[TEST MODE] Using mock AI recommendation")
            from ai_analyzer import AlertRecommendation
            recommendation = AlertRecommendation(
                should_create=True,
                name="Test Alert - Database Connection Issue",
                description="This is a test alert for database connection failures",
                severity="high",
                condition="error rate > threshold",
                threshold="1 error per minute",
            )
        else:
            analyzer = AIAnalyzer()
            recommendation = analyzer.analyze_log_line(log_data)

        if not recommendation.should_create:
            print("No alert needed for this log line")
            print(json.dumps(recommendation.to_dict(), indent=2))
            return 0

        print(f"Alert: {recommendation.name} ({recommendation.severity})")

        config = _build_alert_config(
            name=recommendation.name,
            description=recommendation.description,
            severity=recommendation.severity,
            condition=recommendation.condition,
            threshold=recommendation.threshold,
            log_context=log_data,
        )
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)

        if args.dry_run:
            print("\n[DRY RUN] Groundcover API Request:")
            gc_client = GroundcoverClient()
            print(f"URL: {gc_client.base_url}/api/monitors")
            print("Method: POST")
            print("\nRequest Body (YAML):")
            print(yaml_str)
            return 0

        gc_client = GroundcoverClient()
        result = gc_client.create_monitor_from_yaml(yaml_str)
        print(f"Alert created: {result.get('id', 'N/A')}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
