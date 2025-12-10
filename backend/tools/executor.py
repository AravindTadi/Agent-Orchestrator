"""
Tool Executor
=============
Executes tools with credential injection from user's saved connections.
"""

from typing import Dict, Any, Optional
import json
from .registry import tool_registry


class ToolExecutor:
    """
    Executes Python tools with runtime credential injection.
    """
    
    def __init__(self, db_module):
        """
        Args:
            db_module: Database module with connection management functions
        """
        self.db = db_module
    
    def execute(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> str:
        """
        Execute a tool with the given parameters.
        
        Args:
            tool_id: ID of the tool to execute
            parameters: Input parameters for the tool
            user_id: User ID to look up their connection
            connection_id: Specific connection ID to use (overrides user lookup)
        
        Returns:
            Tool execution result as string
        """
        # Get the tool function
        func = tool_registry.get_function(tool_id)
        if not func:
            return f"Error: Tool '{tool_id}' not found."
        
        # Get tool metadata
        tool_meta = tool_registry.get(tool_id)
        connection_type = tool_meta.get("connection_type")
        
        # Inject connection if required
        if connection_type:
            connection = self._get_connection(user_id, connection_id, connection_type)
            if connection:
                parameters["_connection"] = connection
            else:
                return f"Error: No {connection_type} connection found. Please configure your connection first."
        
        # Execute the tool
        try:
            result = func(**parameters)
            return result
        except TypeError as e:
            return f"Error: Invalid parameters - {str(e)}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    def _get_connection(
        self,
        user_id: Optional[str],
        connection_id: Optional[str],
        connection_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get decrypted connection credentials.
        
        Args:
            user_id: User ID to look up their connection
            connection_id: Specific connection ID
            connection_type: Type of connection needed
        
        Returns:
            Decrypted connection credentials dict or None
        """
        try:
            if connection_id:
                # Get specific connection
                connection = self.db.get_connection(connection_id)
            elif user_id:
                # Get user's connection for this type
                connection = self.db.get_user_connection_by_type(user_id, connection_type)
            else:
                # Get the first available connection of this type (for agents)
                connection = self.db.get_connection_by_type(connection_type)
            
            if connection:
                # Decrypt credentials
                credentials = self._decrypt_credentials(connection.get("credentials", "{}"))
                return credentials
            
            return None
            
        except Exception as e:
            print(f"Error fetching connection: {e}")
            return None
    
    def _decrypt_credentials(self, encrypted: str) -> Dict[str, Any]:
        """
        Decrypt stored credentials.
        For now, just parse JSON. In production, use proper encryption.
        
        TODO: Implement proper encryption with Fernet or similar
        """
        try:
            if isinstance(encrypted, dict):
                return encrypted
            return json.loads(encrypted)
        except (json.JSONDecodeError, TypeError):
            return {}


# Tool execution helper for use in chat endpoints
def execute_python_tool(
    tool_id: str,
    parameters: Dict[str, Any],
    db_module,
    user_id: Optional[str] = None,
    connection_id: Optional[str] = None
) -> str:
    """
    Convenience function to execute a Python tool.
    
    Args:
        tool_id: ID of the tool to execute
        parameters: Input parameters
        db_module: Database module
        user_id: Optional user ID for connection lookup
        connection_id: Optional specific connection ID
    
    Returns:
        Tool execution result
    """
    executor = ToolExecutor(db_module)
    return executor.execute(tool_id, parameters, user_id, connection_id)
