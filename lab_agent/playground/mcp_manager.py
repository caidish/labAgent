"""
MCP Manager - Manages connections to multiple MCP servers and tool discovery
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from ..mcp.client import get_mcp_client, reset_mcp_client
from ..utils.tool_manager import ToolManager
from .tool_adapter import ToolAdapter
from .fastmcp_http_client import FastMCPHTTPClient


class MCPManager:
    """Manages connections to MCP servers and aggregates their tools"""
    
    def __init__(self):
        self.logger = logging.getLogger("playground.mcp_manager")
        self.tool_adapter = ToolAdapter()
        self.tool_manager = ToolManager()
        self.connections = {}
        self.server_configs = {}
        self.custom_servers = {}  # Store custom servers added at runtime
        self.fastmcp_clients = {}  # Store FastMCP HTTP clients
        self._load_server_configs()
        self._load_custom_servers()  # Load saved custom servers
        
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
        """Get all configured MCP servers including custom ones"""
        all_servers = self.server_configs.copy()
        all_servers.update(self.custom_servers)
        return all_servers
    
    def get_enabled_servers(self) -> Dict[str, Any]:
        """Get only enabled MCP servers"""
        return {
            server_id: config for server_id, config in self.server_configs.items()
            if config.get("enabled", True)
        }
    
    def _get_custom_servers_config_path(self) -> str:
        """Get path to custom servers config file"""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'custom_mcp_servers.json'
        )
    
    def _load_custom_servers(self):
        """Load custom servers from config file"""
        config_path = self._get_custom_servers_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                saved_servers = config.get("servers", {})
                
                # Create FastMCP clients for saved servers
                for server_id, server_config in saved_servers.items():
                    self.custom_servers[server_id] = server_config
                    server_url = server_config.get("url")
                    if server_url:
                        self.fastmcp_clients[server_id] = FastMCPHTTPClient(server_url, server_id)
                
                self.logger.info(f"Loaded {len(saved_servers)} custom MCP servers from config")
                
        except FileNotFoundError:
            self.logger.info("No custom servers config file found, starting with empty custom servers")
        except Exception as e:
            self.logger.error(f"Error loading custom servers config: {e}")
    
    def _save_custom_servers(self):
        """Save custom servers to config file"""
        config_path = self._get_custom_servers_config_path()
        
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Prepare config data
            config_data = {
                "servers": self.custom_servers.copy(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # Write to file
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(self.custom_servers)} custom servers to config")
            
        except Exception as e:
            self.logger.error(f"Error saving custom servers config: {e}")
    
    async def add_custom_server(self, server_url: str, server_name: str = None) -> Dict[str, Any]:
        """
        Add a custom FastMCP server at runtime
        
        Args:
            server_url: Full URL of the FastMCP server (e.g., http://localhost:8123/mcp)
            server_name: Optional display name for the server
            
        Returns:
            Result dictionary with success status and server info
        """
        try:
            # Create a unique server ID from the URL
            from urllib.parse import urlparse
            parsed = urlparse(server_url)
            host = parsed.hostname or 'localhost'
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            server_id = f"custom_{host}_{port}"
            
            # Avoid duplicate servers
            if server_id in self.custom_servers:
                return {
                    "success": False,
                    "error": f"Server already exists: {server_url}",
                    "server_id": server_id
                }
            
            # Test connection first
            test_client = FastMCPHTTPClient(server_url, server_id)
            test_result = await test_client.test_connection()
            
            if not test_result["success"]:
                return {
                    "success": False,
                    "error": f"Cannot connect to server: {test_result.get('error', 'Unknown error')}",
                    "server_url": server_url
                }
            
            # Add to custom servers configuration
            display_name = server_name or f"Custom Server ({host}:{port})"
            self.custom_servers[server_id] = {
                "id": server_id,
                "name": display_name,
                "description": f"Custom FastMCP server at {server_url}",
                "transport": "http",
                "url": server_url,
                "enabled": True,
                "category": "custom",
                "custom": True,  # Mark as custom server
                "added_at": datetime.now().isoformat()
            }
            
            # Store the client configuration (not connection)
            self.fastmcp_clients[server_id] = test_client
            # No persistent connections in new architecture
            
            # Save to config file for persistence
            self._save_custom_servers()
            
            self.logger.info(f"Added custom server: {server_id} at {server_url}")
            return {
                "success": True,
                "server_id": server_id,
                "server_name": display_name,
                "server_url": server_url,
                "tool_count": test_result.get("tool_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add custom server {server_url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "server_url": server_url
            }
    
    def remove_custom_server(self, server_id: str) -> bool:
        """Remove a custom server"""
        if server_id in self.custom_servers:
            del self.custom_servers[server_id]
            if server_id in self.fastmcp_clients:
                del self.fastmcp_clients[server_id]
            if server_id in self.connections:
                del self.connections[server_id]
            self.logger.info(f"Removed custom server: {server_id}")
            return True
        return False
    
    def connect_to_server(self, server_id: str) -> bool:
        """Connect to a specific MCP server"""
        # Check both regular configs and custom servers
        all_servers = self.get_available_servers()
        if server_id not in all_servers:
            self.logger.error(f"Unknown server ID: {server_id}")
            return False
        
        server_config = all_servers[server_id]
        
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
                elif server_config.get("custom", False):
                    # Custom FastMCP HTTP server - configuration-based, no persistent connection
                    if server_id in self.fastmcp_clients:
                        # Server is configured and ready to use
                        self.logger.info(f"FastMCP server configured: {server_id}")
                        return True
                    else:
                        self.logger.error(f"Custom server {server_id} not found in clients")
                        return False
                else:
                    # For other predefined HTTP servers like localhost:8123
                    server_url = server_config.get("url")
                    if server_url:
                        if server_id not in self.fastmcp_clients:
                            self.fastmcp_clients[server_id] = FastMCPHTTPClient(server_url, server_id)
                        self.logger.info(f"FastMCP HTTP server configured: {server_id}")
                        return True
                    else:
                        self.logger.error(f"No URL configured for HTTP server: {server_id}")
                        return False
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
            
            elif server_id in self.fastmcp_clients:
                # FastMCP HTTP server
                return self._get_fastmcp_tools(server_id)
            
            else:
                self.logger.warning(f"Tool retrieval not implemented for {server_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get tools from {server_id}: {e}")
            return []
    
    def _get_fastmcp_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Get tools from a FastMCP server"""
        if server_id not in self.fastmcp_clients:
            self.logger.error(f"FastMCP client not found for server: {server_id}")
            return []
        
        try:
            client = self.fastmcp_clients[server_id]
            tools = client.get_tools_sync()
            
            # Convert to OpenAI function calling format with routing info
            formatted_tools = []
            for tool in tools:
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "unknown"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    },
                    "_route": {
                        "kind": "mcp",
                        "server_id": server_id,
                        "tool_name": tool.get("name", "unknown")
                    }
                }
                formatted_tools.append(formatted_tool)
            
            self.logger.info(f"Retrieved {len(formatted_tools)} tools from FastMCP server {server_id}")
            return formatted_tools
            
        except Exception as e:
            self.logger.error(f"Failed to get tools from FastMCP server {server_id}: {e}")
            return []
    
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
            
            elif server_id in self.fastmcp_clients:
                # Execute on FastMCP HTTP server
                return self._execute_fastmcp_tool(server_id, original_tool_name, arguments)
            
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
    
    def _execute_fastmcp_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on a FastMCP server"""
        if server_id not in self.fastmcp_clients:
            return {
                "success": False,
                "error": f"FastMCP client not found for server: {server_id}",
                "tool_name": tool_name
            }
        
        try:
            client = self.fastmcp_clients[server_id]
            result = client.call_tool_sync(tool_name, arguments)
            
            # Normalize the result format
            if result.get("success", True):
                return {
                    "success": True,
                    "result": result.get("result", result),
                    "data": result.get("result", result),
                    "tool_name": tool_name,
                    "server_id": server_id
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "tool_name": tool_name,
                    "server_id": server_id
                }
                
        except Exception as e:
            self.logger.error(f"FastMCP tool execution failed for {tool_name} on {server_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "server_id": server_id
            }
    
    def check_server_health(self, server_id: str) -> Dict[str, Any]:
        """Check health status of an MCP server"""
        all_servers = self.get_available_servers()
        if server_id not in all_servers:
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
            
            elif server_id in self.fastmcp_clients:
                # FastMCP server health check - test fresh connection
                client = self.fastmcp_clients[server_id]
                if client.is_configured:
                    return {
                        "status": "configured",
                        "tool_count": len(client._last_known_tools),
                        "server_info": client.get_server_info(),
                        "message": "Server configured and ready to use"
                    }
                else:
                    return {
                        "status": "unconfigured",
                        "message": "FastMCP server not yet validated",
                        "server_info": client.get_server_info()
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
        all_servers = self.get_available_servers()
        
        for server_id, config in all_servers.items():
            health = self.check_server_health(server_id)
            status[server_id] = {
                "name": config.get("name", server_id),
                "enabled": config.get("enabled", True),
                "configured": server_id in self.fastmcp_clients or server_id in ["arxiv_daily", "flake_2d"],
                "custom": config.get("custom", False),
                "url": config.get("url"),
                "health": health
            }
        
        return status