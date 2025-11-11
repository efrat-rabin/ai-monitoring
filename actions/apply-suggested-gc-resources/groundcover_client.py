#!/usr/bin/env python3
"""Groundcover API Client"""

import os
import requests
import yaml
from typing import Dict, Any


class GroundcoverClient:
    """Client for groundcover API."""
    
    def __init__(self):
        self.api_key = os.getenv('GROUNDCOVER_API_KEY')
        self.base_url = os.getenv('GROUNDCOVER_API_URL', 'https://app.groundcover.com').rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'text/event-stream'
        }
    
    def build_alert_config(self, name: str, description: str, severity: str,
                           condition: str, threshold: str, log_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the alert configuration that will be sent to groundcover.
        Based on: https://docs.groundcover.com/use-groundcover/remote-access-and-apis/apis/monitors
        
        Follows the YAML structure required by groundcover API.
        """
        # Get log level from context, default to 'error'
        log_level = log_context.get('level', 'error').lower()
        
        # Get context labels
        workload = log_context.get('workload', log_context.get('service', 'unknown'))
        namespace = log_context.get('namespace', 'default')
        
        return {
            'title': name,
            'display': {
                'header': name,
                'description': description,
                'resourceHeaderLabels': [],
                'contextHeaderLabels': [
                    'workload',
                    'pod',
                    'namespace',
                    'env'
                ]
            },
            'severity': severity.upper() if severity.upper() in ['S1', 'S2', 'S3', 'S4'] else 'S2',
            'model': {
                'queries': [
                    {
                        'name': 'threshold_input_query',
                        'sqlPipeline': {
                            'selectors': [
                                {
                                    'key': 'workload',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'workload'
                                },
                                {
                                    'key': 'pod',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'pod'
                                },
                                {
                                    'key': 'namespace',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'namespace'
                                },
                                {
                                    'key': 'env',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'env'
                                },
                                {
                                    'key': '*',
                                    'origin': 'root',
                                    'type': 'string',
                                    'processors': [
                                        {
                                            'op': 'count'
                                        }
                                    ],
                                    'alias': 'logs_total'
                                }
                            ],
                            'filters': {
                                'conditions': [
                                    {
                                        'key': 'level',
                                        'type': 'string',
                                        'origin': 'root',
                                        'filters': [
                                            {
                                                'op': 'match',
                                                'value': log_level
                                            }
                                        ]
                                    }
                                ],
                                'operator': 'or'
                            },
                            'groupBy': [
                                {
                                    'key': 'workload',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'workload'
                                },
                                {
                                    'key': 'pod',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'pod'
                                },
                                {
                                    'key': 'namespace',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'namespace'
                                },
                                {
                                    'key': 'env',
                                    'origin': 'root',
                                    'type': 'string',
                                    'alias': 'env'
                                }
                            ],
                            'orderBy': [],
                            'limit': None
                        },
                        'instantRollup': '5 minutes',
                        'dataType': 'logs'
                    }
                ],
                'thresholds': [
                    {
                        'name': 'threshold_1',
                        'inputName': 'threshold_input_query',
                        'operator': 'gt',
                        'values': [100]
                    }
                ]
            },
            'labels': {
                'source': 'ai-monitoring-script',
                'log_level': log_level,
                'service': workload
            },
            'annotations': {
                'condition': condition,
                'threshold': threshold,
                'test': 'enabled'
            },
            'executionErrorState': 'OK',
            'noDataState': 'OK',
            'evaluationInterval': {
                'interval': '5m',
                'pendingFor': '0s'
            },
            'measurementType': 'event'
        }
    
    def create_alert(self, name: str, description: str, severity: str,
                    condition: str, threshold: str, log_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an alert/monitor in groundcover.
        API endpoint: POST /api/monitors
        Sends data as YAML string as required by groundcover API.
        """
        config = self.build_alert_config(name, description, severity, condition, threshold, log_context)
        
        # Convert config to YAML string
        yaml_data = yaml.dump(config, default_flow_style=False, sort_keys=False)
        
        response = requests.post(
            f'{self.base_url}/api/monitors',
            headers=self.headers,
            data=yaml_data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

