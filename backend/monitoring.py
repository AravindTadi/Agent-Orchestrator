"""
Monitoring module for CloudWatch and Datadog integrations.
Handles sending logs and metrics to external services.
"""

import boto3
import time
import requests
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self):
        self.cw_client = None
        self.dd_api_key = None
        self.dd_site = "datadoghq.com"
        self.cw_group_name = "/agenthub/logs"
        self.cw_stream_name = f"stream-{int(time.time())}"
        self.cw_sequence_token = None
        self._enabled = False

    def configure_aws(self, access_key: str, secret_key: str, region: str, log_group: str = None):
        """Configure AWS CloudWatch credentials."""
        try:
            self.cw_client = boto3.client(
                'logs',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            if log_group:
                self.cw_group_name = log_group
                
            # Ensure log group exists
            try:
                self.cw_client.create_log_group(logGroupName=self.cw_group_name)
            except self.cw_client.exceptions.ResourceAlreadyExistsException:
                pass

            # Create log stream
            try:
                self.cw_client.create_log_stream(
                    logGroupName=self.cw_group_name,
                    logStreamName=self.cw_stream_name
                )
            except self.cw_client.exceptions.ResourceAlreadyExistsException:
                pass
                
            self._enabled = True
            logger.info("✅ CloudWatch logging configured")
        except Exception as e:
            logger.error(f"❌ Failed to configure CloudWatch: {e}")

    def configure_datadog(self, api_key: str, site: str = "datadoghq.com"):
        """Configure Datadog credentials."""
        self.dd_api_key = api_key
        self.dd_site = site
        self._enabled = True
        logger.info("✅ Datadog logging configured")

    def test_aws_connection(self, access_key: str, secret_key: str, region: str) -> tuple:
        """Test AWS CloudWatch connection. Returns (success, message)."""
        try:
            client = boto3.client(
                'logs',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            # Try to describe log groups - this validates credentials
            client.describe_log_groups(limit=1)
            return True, "AWS CloudWatch connection successful"
        except client.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'InvalidClientTokenId':
                return False, "Invalid Access Key ID"
            elif error_code == 'SignatureDoesNotMatch':
                return False, "Invalid Secret Access Key"
            elif error_code == 'AccessDenied':
                return False, "Access denied - check IAM permissions"
            else:
                return False, f"AWS Error: {error_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def test_datadog_connection(self, api_key: str, site: str = "datadoghq.com") -> tuple:
        """Test Datadog connection. Returns (success, message)."""
        try:
            # Validate API key using Datadog's validate endpoint
            url = f"https://api.{site}/api/v1/validate"
            headers = {
                "DD-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "Datadog connection successful"
            elif response.status_code == 403:
                return False, "Invalid API Key"
            else:
                return False, f"Datadog error: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Connection timeout - check network"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to {site}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def log_event(self, level: str, message: str, user_email: str = None, metadata: Dict[str, Any] = None):
        """Send log event to configured services."""
        if not self._enabled:
            return

        timestamp = int(time.time() * 1000)
        
        # Prepare payload
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "user": user_email or "system",
            "metadata": metadata or {}
        }
        
        json_log = json.dumps(log_entry)

        # 1. Send to CloudWatch
        if self.cw_client:
            try:
                event = {
                    'timestamp': timestamp,
                    'message': json_log
                }
                
                kwargs = {
                    'logGroupName': self.cw_group_name,
                    'logStreamName': self.cw_stream_name,
                    'logEvents': [event]
                }
                
                if self.cw_sequence_token:
                    kwargs['sequenceToken'] = self.cw_sequence_token
                    
                response = self.cw_client.put_log_events(**kwargs)
                self.cw_sequence_token = response.get('nextSequenceToken')
            except Exception as e:
                logger.warning(f"Failed to send to CloudWatch: {e}")

        # 2. Send to Datadog
        if self.dd_api_key:
            try:
                url = f"https://http-intake.logs.{self.dd_site}/api/v2/logs"
                headers = {
                    "DD-API-KEY": self.dd_api_key,
                    "Content-Type": "application/json"
                }
                
                dd_payload = {
                    "ddsource": "agenthub",
                    "service": "backend",
                    "message": message,
                    "status": level.lower(),
                    "user": {"email": user_email} if user_email else None,
                    "metadata": metadata
                }
                
                requests.post(url, headers=headers, json=dd_payload, timeout=2)
            except Exception as e:
                logger.warning(f"Failed to send to Datadog: {e}")

# Global instance
monitor = MonitoringService()
