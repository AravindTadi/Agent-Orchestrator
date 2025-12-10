"""
Connection Templates
====================
OOTB (Out Of The Box) connection templates for common services.
Users select a template and fill in their credentials.
"""

from typing import Dict, List, Any

# OOTB Connection Templates
CONNECTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    
    # ServiceNow
    "servicenow": {
        "id": "servicenow",
        "name": "ServiceNow",
        "description": "Connect to your ServiceNow instance for ITSM operations",
        "icon": "🔧",
        "category": "itsm",
        "auth_type": "basic",
        "documentation_url": "https://docs.servicenow.com/",
        "fields": [
            {
                "key": "instance_url",
                "label": "Instance URL",
                "type": "url",
                "required": True,
                "placeholder": "https://yourcompany.service-now.com",
                "help_text": "Your ServiceNow instance URL"
            },
            {
                "key": "username",
                "label": "Username",
                "type": "text",
                "required": True,
                "placeholder": "admin",
                "help_text": "ServiceNow username with API access"
            },
            {
                "key": "password",
                "label": "Password",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "ServiceNow password"
            }
        ]
    },
    
    # Jira
    "jira": {
        "id": "jira",
        "name": "Jira",
        "description": "Connect to Atlassian Jira for issue tracking",
        "icon": "📋",
        "category": "productivity",
        "auth_type": "api_key",
        "documentation_url": "https://developer.atlassian.com/cloud/jira/platform/rest/",
        "fields": [
            {
                "key": "base_url",
                "label": "Jira URL",
                "type": "url",
                "required": True,
                "placeholder": "https://yourcompany.atlassian.net",
                "help_text": "Your Jira Cloud or Server URL"
            },
            {
                "key": "email",
                "label": "Email",
                "type": "email",
                "required": True,
                "placeholder": "you@company.com",
                "help_text": "Atlassian account email"
            },
            {
                "key": "api_token",
                "label": "API Token",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "Generate at id.atlassian.com/manage-profile/security/api-tokens"
            }
        ]
    },
    
    # Slack
    "slack": {
        "id": "slack",
        "name": "Slack",
        "description": "Connect to Slack for messaging and notifications",
        "icon": "💬",
        "category": "communication",
        "auth_type": "oauth",
        "documentation_url": "https://api.slack.com/",
        "fields": [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "required": True,
                "placeholder": "xoxb-...",
                "help_text": "Slack Bot User OAuth Token (starts with xoxb-)"
            }
        ]
    },
    
    # AWS
    "aws": {
        "id": "aws",
        "name": "Amazon Web Services",
        "description": "Connect to AWS for cloud services (S3, Lambda, etc.)",
        "icon": "☁️",
        "category": "cloud",
        "auth_type": "aws_credentials",
        "documentation_url": "https://docs.aws.amazon.com/",
        "fields": [
            {
                "key": "access_key_id",
                "label": "Access Key ID",
                "type": "text",
                "required": True,
                "placeholder": "AKIA...",
                "help_text": "AWS Access Key ID"
            },
            {
                "key": "secret_access_key",
                "label": "Secret Access Key",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "AWS Secret Access Key"
            },
            {
                "key": "region",
                "label": "Region",
                "type": "text",
                "required": True,
                "default": "us-east-1",
                "placeholder": "us-east-1",
                "help_text": "AWS Region (e.g., us-east-1, eu-west-1)"
            }
        ]
    },
    
    # OpenAI
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "description": "Connect to OpenAI API for GPT models",
        "icon": "🤖",
        "category": "ai",
        "auth_type": "api_key",
        "documentation_url": "https://platform.openai.com/docs/",
        "fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
                "placeholder": "sk-...",
                "help_text": "OpenAI API Key (starts with sk-)"
            },
            {
                "key": "organization_id",
                "label": "Organization ID",
                "type": "text",
                "required": False,
                "placeholder": "org-...",
                "help_text": "Optional: OpenAI Organization ID"
            }
        ]
    },
    
    # Salesforce
    "salesforce": {
        "id": "salesforce",
        "name": "Salesforce",
        "description": "Connect to Salesforce CRM",
        "icon": "☁️",
        "category": "crm",
        "auth_type": "oauth",
        "documentation_url": "https://developer.salesforce.com/",
        "fields": [
            {
                "key": "instance_url",
                "label": "Instance URL",
                "type": "url",
                "required": True,
                "placeholder": "https://yourcompany.salesforce.com",
                "help_text": "Your Salesforce instance URL"
            },
            {
                "key": "client_id",
                "label": "Client ID",
                "type": "text",
                "required": True,
                "placeholder": "",
                "help_text": "Connected App Consumer Key"
            },
            {
                "key": "client_secret",
                "label": "Client Secret",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "Connected App Consumer Secret"
            },
            {
                "key": "username",
                "label": "Username",
                "type": "text",
                "required": True,
                "placeholder": "user@company.com",
                "help_text": "Salesforce username"
            },
            {
                "key": "password",
                "label": "Password + Security Token",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "Password concatenated with security token"
            }
        ]
    },
    
    # Generic API Key
    "api_key": {
        "id": "api_key",
        "name": "API Key",
        "description": "Generic API Key connection for any service",
        "icon": "🔑",
        "category": "general",
        "auth_type": "api_key",
        "documentation_url": "",
        "fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
                "placeholder": "",
                "help_text": "API Key for the service"
            },
            {
                "key": "base_url",
                "label": "Base URL",
                "type": "url",
                "required": False,
                "placeholder": "https://api.example.com",
                "help_text": "Optional: Base URL for API calls"
            }
        ]
    }
}


class ConnectionTemplates:
    """Manager for connection templates."""
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all available connection templates."""
        return list(CONNECTION_TEMPLATES.values())
    
    @staticmethod
    def get(template_id: str) -> Dict[str, Any]:
        """Get a specific connection template by ID."""
        return CONNECTION_TEMPLATES.get(template_id)
    
    @staticmethod
    def get_by_category(category: str) -> List[Dict[str, Any]]:
        """Get all templates in a category."""
        return [t for t in CONNECTION_TEMPLATES.values() if t.get("category") == category]
    
    @staticmethod
    def get_categories() -> List[str]:
        """Get all unique categories."""
        return list(set(t.get("category", "general") for t in CONNECTION_TEMPLATES.values()))
