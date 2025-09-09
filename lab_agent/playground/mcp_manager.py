"""
MCP Manager - Manages connections to multiple MCP servers and tool discovery
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional, Union
from ..mcp.client import get_mcp_client, reset_mcp_client
from ..utils.tool_manager import ToolManager
from .tool_adapter import ToolAdapter


class MCPManager:
    """Manages connections to MCP servers and aggregates their tools"""
    
    def __init__(self):
        self.logger = logging.getLogger("playground.mcp_manager")
        self.tool_adapter = ToolAdapter()
        self.tool_manager = ToolManager()
        self.connections = {}
        self.server_configs = {}
        self._load_server_configs()
        
        # Get existing MCP client for compatibility
        self.mcp_client = get_mcp_client()
    
    def _load_server_configs(self):
        """Load MCP server configurations"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'playground_models.json'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.server_configs = config.get("mcp_servers", {})
                self.logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")
        except FileNotFoundError:
            self.logger.warning(f"MCP server config not found at {config_path}")
            self.server_configs = self._default_server_configs()
    
    def _default_server_configs(self) -> Dict[str, Any]:
        """Default MCP server configurations"""
        return {
            "local_fastmcp": {
                "id": "local_fastmcp",
                "name": "Local FastMCP Server",
                "description": "Local development MCP server",
                "transport": "http",
                "url": "http://localhost:8123/mcp",
                "enabled": True,
                "category": "development"
            }
        }
    
    def get_available_servers(self) -> Dict[str, Any]:
        """Get all configured MCP servers"""
        return self.server_configs.copy()
    
    def get_enabled_servers(self) -> Dict[str, Any]:
        """Get only enabled MCP servers"""
        return {
            server_id: config for server_id, config in self.server_configs.items()
            if config.get("enabled", True)
        }
    
    def connect_to_server(self, server_id: str) -> bool:
        """Connect to a specific MCP server"""
        if server_id not in self.server_configs:
            self.logger.error(f"Unknown server ID: {server_id}")
            return False
        
        server_config = self.server_configs[server_id]
        
        try:
            transport = server_config.get("transport")
            
            if transport == "internal":
                # Internal servers use the existing MCP client
                if server_id in ["arxiv_daily", "flake_2d"]:
                    self.connections[server_id] = "internal"
                    self.logger.info(f"Connected to internal MCP server: {server_id}")
                    return True
                else:
                    self.logger.warning(f"Unknown internal server: {server_id}")
                    return False
                    
            elif transport == "http":
                # HTTP servers
                if server_id in ["arxiv_daily", "flake_2d"]:
                    # These can also work as HTTP if configured that way
                    self.connections[server_id] = "http"
                    self.logger.info(f"Connected to HTTP MCP server: {server_id}")
                    return True
                else:
                    # For new HTTP servers like localhost:8123, we would implement
                    # HTTP MCP client here. For now, mark as planned.
                    self.logger.info(f"HTTP MCP connection to {server_id} planned but not implemented yet")
                    self.connections[server_id] = "planned"
                    return True
            else:
                self.logger.warning(f"Unsupported transport for {server_id}: {transport}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to {server_id}: {e}")
            return False
    
    def disconnect_from_server(self, server_id: str):
        """Disconnect from a specific MCP server"""
        if server_id in self.connections:
            # Perform cleanup if needed
            del self.connections[server_id]
            self.logger.info(f"Disconnected from MCP server: {server_id}")
    
    def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Get tools from a specific MCP server"""
        if server_id not in self.connections:
            if not self.connect_to_server(server_id):
                return []
        
        try:
            if server_id in ["arxiv_daily", "flake_2d"]:
                # Use existing MCP client for internal servers
                tools = self.mcp_client.get_tools_by_group(server_id)
                return [self.tool_adapter.mcp_to_openai_tool(tool, server_id) for tool in tools]
            
            elif server_id == "local_fastmcp":
                # For local FastMCP server, return placeholder tools for now
                return self._get_local_fastmcp_tools()
            
            else:
                self.logger.warning(f"Tool retrieval not implemented for {server_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get tools from {server_id}: {e}")
            return []
    
    def _get_local_fastmcp_tools(self) -> List[Dict[str, Any]]:
        """Get tools from local FastMCP server (placeholder implementation)"""
        # This would be replaced with actual HTTP MCP client calls
        placeholder_tools = [
            {
                "type": "function",
                "function": {
                    "name": "local_test_tool",
                    "description": "Test tool from local FastMCP server",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Test message"
                            }
                        },
                        "required": ["message"]
                    }
                },
                "_route": {
                    "kind": "mcp",
                    "server_id": "local_fastmcp",
                    "tool_name": "local_test_tool"
                }
            }
        ]
        
        self.logger.info("Returning placeholder tools for local_fastmcp")
        return placeholder_tools
    
    def get_all_tools(self, selected_servers: List[str] = None) -> List[Dict[str, Any]]:
        """Get tools from all selected servers"""
        if selected_servers is None:
            selected_servers = list(self.get_enabled_servers().keys())
        
        all_tools = []
        
        for server_id in selected_servers:
            if server_id in self.server_configs:
                server_tools = self.get_server_tools(server_id)
                all_tools.extend(server_tools)
                self.logger.info(f"Added {len(server_tools)} tools from {server_id}")
        
        self.logger.info(f"Total tools aggregated: {len(all_tools)}")
        return all_tools
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call on the appropriate MCP server"""
        route = self.tool_adapter.extract_tool_routing(tool_def)
        
        if not route or route.get("kind") != "mcp":
            return {
                "success": False,
                "error": f"Invalid tool routing for {tool_name}",
                "tool_name": tool_name
            }
        
        server_id = route.get("server_id")
        original_tool_name = route.get("tool_name", tool_name)
        
        self.logger.info(f"Executing tool {original_tool_name} on server {server_id}")
        
        try:
            if server_id in ["arxiv_daily", "flake_2d"]:
                # Use existing MCP client
                result = asyncio.run(self.mcp_client.call_tool(original_tool_name, arguments))
                return result
            
            elif server_id == "local_fastmcp":
                # Placeholder execution for local FastMCP server
                return self._execute_local_fastmcp_tool(original_tool_name, arguments)
            
            else:
                return {
                    "success": False,
                    "error": f"Tool execution not implemented for server {server_id}",
                    "tool_name": tool_name
                }
                
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def _execute_local_fastmcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on local FastMCP server (placeholder)"""
        self.logger.info(f"Placeholder execution for {tool_name} with args: {arguments}")
        
        if tool_name == "local_test_tool":
            message = arguments.get("message", "No message provided")
            return {
                "success": True,
                "result": f"Local FastMCP response: {message}",
                "tool_name": tool_name
            }
        else:
            return {
                "success": False,
                "error": f"Unknown local FastMCP tool: {tool_name}",
                "tool_name": tool_name
            }
    
    def check_server_health(self, server_id: str) -> Dict[str, Any]:
        """Check health status of an MCP server"""
        if server_id not in self.server_configs:
            return {
                "status": "unknown",
                "error": f"Unknown server: {server_id}"
            }
        
        if server_id not in self.connections:
            if not self.connect_to_server(server_id):
                return {
                    "status": "disconnected",
                    "error": f"Cannot connect to {server_id}"
                }
        
        try:
            if server_id in ["arxiv_daily", "flake_2d"]:
                # Check using existing MCP client
                tools = self.mcp_client.get_tools_by_group(server_id)
                return {
                    "status": "healthy",
                    "tool_count": len(tools),
                    "connection": self.connections.get(server_id)
                }
            
            elif server_id == "local_fastmcp":
                return {
                    "status": "planned",
                    "message": "Local FastMCP health check not implemented yet",
                    "connection": self.connections.get(server_id)
                }
            
            else:
                return {
                    "status": "unknown",
                    "message": f"Health check not implemented for {server_id}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def refresh_connections(self):
        """Refresh all MCP server connections"""
        self.logger.info("Refreshing MCP connections")
        
        # Reset existing MCP client to pick up any changes
        reset_mcp_client()
        self.mcp_client = get_mcp_client()
        
        # Clear and rebuild connections
        self.connections.clear()
        
        for server_id in self.get_enabled_servers():
            self.connect_to_server(server_id)
        
        self.logger.info(f"Refreshed connections to {len(self.connections)} servers")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all server connections"""
        status = {}
        
        for server_id, config in self.server_configs.items():
            health = self.check_server_health(server_id)
            status[server_id] = {
                "name": config.get("name", server_id),
                "enabled": config.get("enabled", True),
                "connected": server_id in self.connections,
                "health": health
            }
        
        return status