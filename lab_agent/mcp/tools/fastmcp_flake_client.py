"""
FastMCP client for 2D flake classification server.

This module provides a direct FastMCP client connection to the 2D flake classification
server, replacing the complex HTTP proxy implementation with a simple, direct interface.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastmcp.client import Client


class FastMCPFlakeClient:
    """Direct FastMCP client for 2D flake classification server"""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        """
        Initialize FastMCP client for 2D flake server
        
        Args:
            server_url: Base URL of the FastMCP server endpoint
        """
        self.logger = logging.getLogger("fastmcp.flake_client")
        self.server_url = server_url
        self.client: Optional[Client] = None
        self._connection_lock = asyncio.Lock()
        self.available_tools: List[Dict[str, Any]] = []
        
    async def connect(self) -> bool:
        """Connect to the FastMCP server"""
        async with self._connection_lock:
            if self.client is not None:
                return True
                
            try:
                self.client = Client(self.server_url)
                await self.client.__aenter__()
                
                # Discover available tools
                self.available_tools = await self.client.list_tools()
                
                self.logger.info(f"Connected to FastMCP server at {self.server_url}")
                self.logger.info(f"Discovered {len(self.available_tools)} tools")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect to FastMCP server: {e}")
                self.client = None
                return False
    
    async def disconnect(self):
        """Disconnect from the FastMCP server"""
        async with self._connection_lock:
            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.warning(f"Error during disconnect: {e}")
                finally:
                    self.client = None
                    self.available_tools = []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the remote FastMCP server
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result from the server
        """
        # Ensure connection
        if not self.client:
            connected = await self.connect()
            if not connected:
                return {
                    "success": False,
                    "error": f"Failed to connect to FastMCP server at {self.server_url}"
                }
        
        try:
            # Call tool directly through FastMCP client
            result = await self.client.call_tool(tool_name, arguments)
            
            self.logger.info(f"FastMCP tool '{tool_name}' called successfully")
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"FastMCP tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server"""
        # Ensure connection and tool discovery
        if not self.client:
            connected = await self.connect()
            if not connected:
                return []
        
        # Convert Tool objects to dictionaries
        tools_list = []
        for tool in self.available_tools:
            if hasattr(tool, 'name'):
                # FastMCP Tool object
                tool_dict = {
                    "name": tool.name,
                    "description": getattr(tool, 'description', ''),
                    "inputSchema": getattr(tool, 'input_schema', {})
                }
                tools_list.append(tool_dict)
            elif isinstance(tool, dict):
                # Already a dictionary
                tools_list.append(tool)
        
        return tools_list
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions in sync mode (for compatibility)
        Note: This runs the async version in a new event loop or uses cached tools
        """
        try:
            # If we already have tools cached, return them directly
            if self.available_tools:
                # Convert Tool objects to dictionaries if needed
                tools_list = []
                for tool in self.available_tools:
                    if hasattr(tool, 'name'):
                        # FastMCP Tool object
                        tool_dict = {
                            "name": tool.name,
                            "description": getattr(tool, 'description', ''),
                            "inputSchema": getattr(tool, 'input_schema', {})
                        }
                        tools_list.append(tool_dict)
                    elif isinstance(tool, dict):
                        # Already a dictionary
                        tools_list.append(tool)
                return tools_list
            
            # Try to run async version
            try:
                loop = asyncio.get_running_loop()
                # We're in an existing event loop, use thread executor to run async code
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    # Create new event loop in thread
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
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool (compatibility method for MCP client interface)
        This is just a wrapper around call_tool for interface compatibility
        """
        return await self.call_tool(tool_name, arguments)
    
    def execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool synchronously (for use in existing event loops)
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an existing event loop, use thread executor to run async code
            import concurrent.futures
            
            def run_tool_in_thread():
                # Create new event loop in thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Create a new client instance for this thread
                    thread_client = FastMCPFlakeClient(self.server_url)
                    return new_loop.run_until_complete(thread_client.call_tool(tool_name, arguments))
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
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.client:
            # Note: This is not ideal for async cleanup, but provides fallback
            self.logger.info("FastMCP client destroyed, connection may remain open")