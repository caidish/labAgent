"""
Tool Manager for Lab Agent - handles activation/deactivation of MCP tools.
"""

import json
import os
from typing import Dict, List, Any
from datetime import datetime


class ToolManager:
    """Manages activation state of MCP tools"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config', 
                'tool_activation_state.json'
            )
        self.config_path = config_path
        self.activation_state = self._load_activation_state()
    
    def _load_activation_state(self) -> Dict[str, Any]:
        """Load tool activation state from config file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default state if file doesn't exist
            default_state = {
                "last_updated": datetime.now().isoformat(),
                "tools": {
                    "arxiv_daily": {
                        "active": True,
                        "name": "ArXiv Daily",
                        "description": "Automated paper recommendations with AI scoring",
                        "category": "research"
                    },
                    "flake_2d": {
                        "active": False,  # Disabled by default
                        "name": "2D Flake Classification", 
                        "description": "AI-powered quality assessment via external MCP server",
                        "category": "analysis",
                        "server_url": "",
                        "connection_status": "disconnected"
                    }
                }
            }
            self._save_activation_state(default_state)
            return default_state
    
    def _save_activation_state(self, state: Dict[str, Any] = None):
        """Save tool activation state to config file"""
        if state is None:
            state = self.activation_state
        
        state["last_updated"] = datetime.now().isoformat()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save tool activation state: {e}")
    
    def get_tool_status(self, tool_id: str) -> Dict[str, Any]:
        """Get status of a specific tool"""
        return self.activation_state.get("tools", {}).get(tool_id, {})
    
    def is_tool_active(self, tool_id: str) -> bool:
        """Check if a tool is currently active"""
        return self.get_tool_status(tool_id).get("active", False)
    
    def activate_tool(self, tool_id: str) -> bool:
        """Activate a tool"""
        if tool_id in self.activation_state.get("tools", {}):
            self.activation_state["tools"][tool_id]["active"] = True
            self._save_activation_state()
            return True
        return False
    
    def deactivate_tool(self, tool_id: str) -> bool:
        """Deactivate a tool"""
        if tool_id in self.activation_state.get("tools", {}):
            self.activation_state["tools"][tool_id]["active"] = False
            self._save_activation_state()
            return True
        return False
    
    def get_active_tools(self) -> Dict[str, Any]:
        """Get all currently active tools"""
        return {
            tool_id: tool_info 
            for tool_id, tool_info in self.activation_state.get("tools", {}).items()
            if tool_info.get("active", False)
        }
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Get all tools with their status"""
        return self.activation_state.get("tools", {})
    
    def update_tool_config(self, tool_id: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a tool"""
        if tool_id in self.activation_state.get("tools", {}):
            self.activation_state["tools"][tool_id].update(config)
            self._save_activation_state()
            return True
        return False
    
    def set_flake_2d_server(self, server_url: str, connection_status: str = "configured") -> bool:
        """Set the 2D flake server URL and connection status"""
        return self.update_tool_config("flake_2d", {
            "server_url": server_url,
            "connection_status": connection_status
        })
    
    def get_activation_summary(self) -> Dict[str, Any]:
        """Get summary of tool activation status"""
        tools = self.activation_state.get("tools", {})
        active_count = sum(1 for tool in tools.values() if tool.get("active", False))
        
        return {
            "total_tools": len(tools),
            "active_tools": active_count,
            "inactive_tools": len(tools) - active_count,
            "last_updated": self.activation_state.get("last_updated"),
            "tools_by_category": self._group_by_category()
        }
    
    def _group_by_category(self) -> Dict[str, List[str]]:
        """Group tools by category"""
        categories = {}
        for tool_id, tool_info in self.activation_state.get("tools", {}).items():
            category = tool_info.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_id)
        return categories