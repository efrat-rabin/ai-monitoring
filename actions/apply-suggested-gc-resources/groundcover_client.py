#!/usr/bin/env python3
"""Groundcover API Client"""

import os
import requests
from typing import Dict, Any


class GroundcoverClient:
    """Client for groundcover API."""

    def __init__(self):
        self.api_key = os.getenv('GROUNDCOVER_API_KEY')
        self.base_url = os.getenv('GROUNDCOVER_API_URL', 'https://app.groundcover.com').rstrip('/')

    def create_monitor_from_yaml(self, yaml_str: str) -> Dict[str, Any]:
        """
        Create a monitor in GroundCover by POSTing arbitrary monitor YAML.
        Uses Content-Type: text/plain and X-Backend-Id as required by the API.
        """
        tenant_uuid = os.getenv('GROUNDCOVER_TENANT_UUID', '58b6c61c-6289-4323-bbcb-e295ca71f745')
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'text/event-stream',
            'Content-Type': 'text/plain',
            'X-Backend-Id': 'groundcover',
            'X-Tenant-UUID': tenant_uuid,
        }
        response = requests.post(
            f'{self.base_url}/api/monitors',
            headers=headers,
            data=yaml_str,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

