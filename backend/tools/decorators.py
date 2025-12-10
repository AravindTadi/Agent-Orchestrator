"""
Tool Decorator Framework
========================
Provides the @tool decorator for registering Python functions as callable tools.

Example:
    @tool(
        name="servicenow_create_incident",
        description="Create an incident in ServiceNow",
        connection_type="servicenow"
    )
    def create_incident(short_description: str, description: str, _connection: dict = None):
        # _connection is injected at runtime with user's saved credentials
        ...
"""

from functools import wraps
from typing import Callable, Optional, Any, get_type_hints
import inspect

# Global registry to store all decorated tools
_TOOL_REGISTRY = {}


def tool(
    name: str,
    description: str,
    category: str = "general",
    connection_type: Optional[str] = None,
    icon: str = "🔧"
):
    """
    Decorator to register a Python function as a tool.
    
    Args:
        name: Unique identifier for the tool (e.g., 'servicenow_create_incident')
        description: Human-readable description shown in the UI
        category: Tool category for grouping (e.g., 'itsm', 'productivity', 'cloud')
        connection_type: ID of required connection template (e.g., 'servicenow')
        icon: Emoji or icon URL for the tool
    
    Returns:
        Decorated function with attached metadata
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Extract parameter info from function signature and type hints
        sig = inspect.signature(func)
        type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        
        parameters = []
        for param_name, param in sig.parameters.items():
            # Skip internal parameters (start with _)
            if param_name.startswith('_'):
                continue
            
            param_info = {
                "name": param_name,
                "type": _python_type_to_json_type(type_hints.get(param_name, str)),
                "required": param.default == inspect.Parameter.empty,
                "default": None if param.default == inspect.Parameter.empty else param.default,
                "description": ""  # Can be extracted from docstring later
            }
            parameters.append(param_info)
        
        # Attach metadata to the function
        wrapper._tool_meta = {
            "id": name,
            "name": name.replace('_', ' ').title(),
            "description": description,
            "category": category,
            "connection_type": connection_type,
            "icon": icon,
            "parameters": parameters,
            "source": "python",
            "function": func  # Keep reference to original function
        }
        
        # Register in global registry
        _TOOL_REGISTRY[name] = wrapper
        
        return wrapper
    return decorator


def _python_type_to_json_type(python_type: Any) -> str:
    """Convert Python type hints to JSON Schema types."""
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    # Handle Optional types
    if hasattr(python_type, '__origin__'):
        if python_type.__origin__ is type(None):
            return "null"
        # For Optional[X], return the type of X
        args = getattr(python_type, '__args__', ())
        for arg in args:
            if arg is not type(None):
                return type_mapping.get(arg, "string")
    
    return type_mapping.get(python_type, "string")


def get_all_tools() -> dict:
    """Get all registered tools."""
    return _TOOL_REGISTRY.copy()


def get_tool(name: str) -> Optional[Callable]:
    """Get a specific tool by name."""
    return _TOOL_REGISTRY.get(name)
