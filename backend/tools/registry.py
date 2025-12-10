"""
Tool Registry
==============
Discovers and manages all registered tools from the catalog.
"""

from typing import Dict, List, Any, Optional
import importlib
import pkgutil
from pathlib import Path


class ToolRegistry:
    """
    Central registry for all tools.
    Discovers tools from the catalog package and provides query methods.
    """
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._discovered = False
    
    def discover(self, package_name: str = "backend.tools.catalog"):
        """
        Discover all tools in the catalog package.
        This imports all modules which triggers the @tool decorators.
        """
        if self._discovered:
            return
        
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent
            
            # Import all modules in the catalog package
            for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
                full_module_name = f"{package_name}.{module_name}"
                try:
                    importlib.import_module(full_module_name)
                except Exception as e:
                    print(f"⚠️ Failed to load tool module {full_module_name}: {e}")
            
            # Get tools from the decorator registry
            from .decorators import get_all_tools
            self._tools = get_all_tools()
            self._discovered = True
            
            print(f"✅ Discovered {len(self._tools)} Python tools")
            
        except Exception as e:
            print(f"⚠️ Tool discovery failed: {e}")
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all registered tools as a list of metadata dicts."""
        self.discover()
        return [
            {
                "id": tool._tool_meta["id"],
                "name": tool._tool_meta["name"],
                "description": tool._tool_meta["description"],
                "category": tool._tool_meta["category"],
                "connection_type": tool._tool_meta["connection_type"],
                "icon": tool._tool_meta["icon"],
                "parameters": tool._tool_meta["parameters"],
                "source": tool._tool_meta["source"]
            }
            for tool in self._tools.values()
        ]
    
    def get(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by ID."""
        self.discover()
        tool = self._tools.get(tool_id)
        if tool:
            return tool._tool_meta
        return None
    
    def get_function(self, tool_id: str):
        """Get the callable function for a tool."""
        self.discover()
        tool = self._tools.get(tool_id)
        if tool:
            return tool._tool_meta["function"]
        return None
    
    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tools in a specific category."""
        return [t for t in self.get_all() if t.get("category") == category]
    
    def get_by_connection_type(self, connection_type: str) -> List[Dict[str, Any]]:
        """Get all tools that require a specific connection type."""
        return [t for t in self.get_all() if t.get("connection_type") == connection_type]
    
    def get_categories(self) -> List[str]:
        """Get all unique tool categories."""
        return list(set(t.get("category", "general") for t in self.get_all()))
    
    def to_openai_format(self, tool_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Convert tools to OpenAI function calling format.
        This is used when sending tools to the LLM.
        """
        tools = self.get_all()
        if tool_ids:
            tools = [t for t in tools if t["id"] in tool_ids]
        
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["id"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            for param in tool.get("parameters", []):
                openai_tool["function"]["parameters"]["properties"][param["name"]] = {
                    "type": param["type"],
                    "description": param.get("description", "")
                }
                if param.get("required"):
                    openai_tool["function"]["parameters"]["required"].append(param["name"])
            
            openai_tools.append(openai_tool)
        
        return openai_tools


# Global instance
tool_registry = ToolRegistry()
