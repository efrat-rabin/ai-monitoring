#!/usr/bin/env python3
"""
Cursor CLI Client
Simple wrapper for sending messages to Cursor CLI.
""" 

import os
import subprocess
import json
import re
from pathlib import Path
from typing import Optional, Any
  

class CursorClient:
    """Client for sending messages to Cursor CLI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Cursor client.
        
        Args:
            api_key: Cursor API key (defaults to CURSOR_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('CURSOR_API_KEY')
        if not self.api_key:
            raise ValueError("CURSOR_API_KEY environment variable is required")
        self.home_dir = Path.home()
        self.cursor_agent_path = None
    
    def install_cursor_cli(self) -> bool:
        """
        Install Cursor CLI if not already installed.
        
        Returns:
            True if installation successful or already installed, False otherwise
        """
        try:
            # Check if cursor-agent already exists
            result = subprocess.run(['which', 'cursor-agent'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.cursor_agent_path = result.stdout.strip()
                return True
            
            # Install Cursor
            install_cmd = "curl https://cursor.com/install -fsS | bash"
            subprocess.run(install_cmd, shell=True, check=True)
            
            # Search for cursor-agent binary
            search_paths = [
                self.home_dir / ".cursor" / "bin",
                self.home_dir / ".local" / "bin",
                self.home_dir / "bin"
            ]
            
            for path in search_paths:
                cursor_bin = path / "cursor-agent"
                if cursor_bin.exists() and cursor_bin.is_file():
                    self.cursor_agent_path = str(cursor_bin)
                    os.environ['PATH'] = f"{path}:{os.environ['PATH']}"
                    return True
            
            # Deep search in ~/.cursor directory
            cursor_dir = self.home_dir / ".cursor"
            if cursor_dir.exists():
                for item in cursor_dir.rglob("cursor-agent"):
                    if item.is_file():
                        self.cursor_agent_path = str(item)
                        os.environ['PATH'] = f"{item.parent}:{os.environ['PATH']}"
                        return True
            
            return False
            
        except Exception:
            return False
    
    def verify_setup(self) -> bool:
        """
        Verify cursor-agent is available and API key is set.
        
        Returns:
            True if setup is valid, False otherwise
        """
        if not self.cursor_agent_path:
            result = subprocess.run(['which', 'cursor-agent'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.cursor_agent_path = result.stdout.strip()
            else:
                return False
        
        return bool(self.api_key)
    
    def send_message(self, prompt: str, context: Optional[str] = None) -> Any:
        """
        Send a message to Cursor CLI and get response.
        
        Args:
            prompt: The prompt/question to send
            context: Optional context to include with the prompt
            
        Returns:
            Parsed response from Cursor (dict, str, or original response)
            
        Raises:
            Exception: If Cursor CLI is not available or call fails
        """
        # Build full prompt
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        try:
            # Run cursor-agent
            cmd = ['cursor-agent', '-p', full_prompt, '--output-format', 'json']
            
            env = os.environ.copy()
            env['CURSOR_API_KEY'] = self.api_key
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"cursor-agent failed: {result.stderr}")
            
            return self._parse_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise Exception("Cursor CLI request timed out")
        except FileNotFoundError:
            raise Exception("cursor-agent not found. Please install Cursor CLI")
        except Exception as e:
            raise Exception(f"Cursor CLI error: {e}")
    
    def _parse_output(self, raw_output: str) -> Any:
        """Parse cursor-agent output."""
        try:
            data = json.loads(raw_output)
            
            # Extract result field if present
            if 'result' in data:
                result_field = data['result']
                
                # Extract JSON from markdown code blocks
                if isinstance(result_field, str) and '```json' in result_field:
                    match = re.search(r'```json\s*\n(.*?)\n```', result_field, re.DOTALL)
                    if match:
                        return json.loads(match.group(1).strip())
                
                # Return result if it's structured
                if isinstance(result_field, dict):
                    return result_field
                
                # Try to extract JSON from string
                if isinstance(result_field, str):
                    match = re.search(r'\{.*\}', result_field, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group(0))
                        except:
                            pass
                    # Return plain text if no JSON found
                    return result_field
            
            return data
            
        except json.JSONDecodeError:
            # Return raw output if not JSON
            return raw_output
