#!/usr/bin/env python3
"""Groundcover API Client"""

import os
import requests
from typing import Dict, Any


class GroundcoverClient:
    """Client for groundcover API."""
    
    def __init__(self):
        self.api_key = os.getenv('GROUNDCOVER_API_KEY')
        self.base_url = os.getenv('GROUNDCOVER_API_URL', 'https://api.groundcover.com').rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def build_alert_config(self, name: str, description: str, severity: str,
                           condition: str, threshold: str, log_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the alert configuration that will be sent to groundcover.
        Based on: https://docs.groundcover.com/use-groundcover/remote-access-and-apis/apis/monitors
        
        Follows the exact structure from POST /api/monitors endpoint.
        """
        return {
            'title': name,
            'annotations': {
                'condition': condition,
                'threshold': threshold,
                'original_message': log_context.get('message', ''),
                'severity': severity
            },
            'autoResolve': True,
            'display': {
                'description': description,
                'header': name
            },
            'evaluationInterval': {
                'interval': '5m',
                'pendingFor': '0s'
            },
            'executionErrorState': 'OK',
            'isPaused': True,
            'labels': {
                'source': 'ai-monitoring-script',
                'log_level': log_context.get('level', ''),
                'service': log_context.get('service', 'unknown')
            },
            'measurementType': 'state',
            'model': {
                'queries': [
                    {
                        'conditions': [
                            {
                                'key': 'message',
                                'type': 'string',
                                'filters': [
                                    {
                                        'op': 'contains',
                                        'value': log_context.get('message', '')
                                    }
                                ],
                                'isNullable': False,
                                'autoComplete': False
                            }
                        ],
                        'dataType': 'logs',
                        'name': 'A',
                        'queryType': 'logs',
                        'sqlPipeline': {
                            'filters': {
                                'key': 'message',
                                'type': 'string',
                                'processors': [
                                    {
                                        'op': 'contains',
                                        'args': [log_context.get('message', '')]
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
    
    def create_alert(self, name: str, description: str, severity: str,
                    condition: str, threshold: str, log_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an alert/monitor in groundcover.
        API endpoint: POST /api/monitors
        """
        config = self.build_alert_config(name, description, severity, condition, threshold, log_context)
        
        response = requests.post(
            f'{self.base_url}/api/monitors',
            headers=self.headers,
            json=config,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

