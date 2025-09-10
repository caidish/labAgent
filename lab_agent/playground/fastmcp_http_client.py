"""
Generic FastMCP HTTP client for connecting to any FastMCP server via HTTP transport.

This module provides a configuration-based client that creates fresh connections
for each operation, respecting FastMCP's async context manager design.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from fastmcp.client import Client


class FastMCPHTTPClient:
    """Generic FastMCP client for HTTP transport - configuration based, not connection based"""
    
    def __init__(self, server_url: str, server_id: str = None):
        """
        Initialize FastMCP HTTP client configuration
        
        Args:
            server_url: Full URL of the FastMCP server endpoint (e.g., http://localhost:8123/mcp)
            server_id: Optional identifier for the server (used for logging and routing)
        """
        self.logger = logging.getLogger(f"fastmcp.http_client.{server_id or 'unknown'}")
        self.server_url = server_url.rstrip('/')  # Remove trailing slash
        self.server_id = server_id or self._generate_server_id(server_url)
        
        # Store configuration only - no persistent connection
        self._config_validated = False
        self._last_known_tools = []
        
    def _generate_server_id(self, url: str) -> str:
        """Generate a server ID from URL"""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or 'localhost'
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            return f"{host}_{port}"
        except Exception:
            return "custom_server"
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the FastMCP server and discover tools
        
        Returns:
            Connection test result with status and tool count
        """
        try:
            self.logger.info(f"Testing connection to FastMCP server at {self.server_url}")
            
            # Create a fresh client for testing
            client = Client(self.server_url)
            
            async with client:
                # Test basic connectivity
                await client.ping()
                
                # Discover available tools
                tools = await client.list_tools()
                self._last_known_tools = tools
                self._config_validated = True
                
                self.logger.info(f"Successfully tested connection to {self.server_url}")
                self.logger.info(f"Discovered {len(tools)} tools")
                
                return {
                    "success": True,
                    "message": f"Connection test successful",
                    "tool_count": len(tools),
                    "server_id": self.server_id,
                    "server_url": self.server_url
                }
                
        except Exception as e:
            error_msg = f"Failed to connect to FastMCP server at {self.server_url}: {str(e)}"
            self.logger.error(error_msg)
            self._config_validated = False
            return {
                "success": False,
                "error": error_msg,
                "server_url": self.server_url
            }
    
    # No disconnect method needed - connections are ephemeral
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the remote FastMCP server using a fresh connection
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result from the server
        """
        try:
            self.logger.info(f"Calling tool '{tool_name}' with args: {json.dumps(arguments, indent=2)}")
            
            # Create a fresh client for this tool call
            client = Client(self.server_url)
            
            async with client:
                result = await client.call_tool(tool_name, arguments)
                
                self.logger.info(f"FastMCP tool '{tool_name}' completed successfully")
                return {
                    "success": True,
                    "result": result,
                    "tool_name": tool_name,
                    "server_id": self.server_id
                }
            
        except Exception as e:
            error_msg = f"FastMCP tool call failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name,
                "server_id": self.server_id
            }
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server using a fresh connection"""
        try:
            # Create a fresh client for tool listing
            client = Client(self.server_url)
            
            async with client:
                tools = await client.list_tools()
                self._last_known_tools = tools
                
                # Convert Tool objects to dictionaries for compatibility
                tools_list = []
                for tool in tools:
                    if hasattr(tool, 'name'):
                        # FastMCP Tool object - convert to dict
                        tool_dict = {
                            "name": tool.name,
                            "description": getattr(tool, 'description', ''),
                            "inputSchema": getattr(tool, 'input_schema', {})
                        }
                        tools_list.append(tool_dict)
                    elif isinstance(tool, dict):
                        # Already a dictionary
                        tools_list.append(tool)
                    else:
                        # Handle other formats
                        self.logger.warning(f"Unknown tool format: {type(tool)}")
                        
                return tools_list
                
        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}")
            return []
    
    def get_tools_sync(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions synchronously (for compatibility)
        Uses last known tools or fetches fresh ones in a thread
        """
        try:
            # If we have cached tools, return them
            if self._last_known_tools:
                # Convert Tool objects to dictionaries if needed
                tools_list = []
                for tool in self._last_known_tools:
                    if hasattr(tool, 'name'):
                        tool_dict = {
                            "name": tool.name,
                            "description": getattr(tool, 'description', ''),
                            "inputSchema": getattr(tool, 'input_schema', {})
                        }
                        tools_list.append(tool_dict)
                    elif isinstance(tool, dict):
                        tools_list.append(tool)
                return tools_list
            
            # Try to run async version in a safe way
            try:
                loop = asyncio.get_running_loop()
                # We're in an existing event loop, use thread executor
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.list_tools())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=10)  # 10 second timeout
                    return result
                    
            except RuntimeError:
                # No event loop, safe to create one
                return asyncio.run(self.list_tools())
                
        except Exception as e:
            self.logger.error(f"Error getting tool definitions: {e}")
            return []
    
    
    def call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool synchronously (for use in existing event loops)
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an existing event loop, use thread executor
            import concurrent.futures
            
            def run_tool_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.call_tool(tool_name, arguments))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_tool_in_thread)
                return future.result(timeout=30)  # 30 second timeout
                
        except RuntimeError:
            # No event loop, safe to run directly
            return asyncio.run(self.call_tool(tool_name, arguments))
        except Exception as e:
            self.logger.error(f"Sync tool execution failed: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name,
                "server_id": self.server_id
            }
    
    @property
    def is_configured(self) -> bool:
        """Check if the client configuration has been validated"""
        return self._config_validated
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get basic server information"""
        return {
            "server_id": self.server_id,
            "server_url": self.server_url,
            "configured": self.is_configured,
            "tool_count": len(self._last_known_tools) if self._last_known_tools else 0
        }
    
    # No cleanup needed - connections are ephemeral