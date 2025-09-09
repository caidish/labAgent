"""
MCP Client for Lab Agent - provides interface to MCP tools from the chatbox
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from .tools.arxiv_daily_tools import ArxivDailyTools
from .tools.fastmcp_flake_client import FastMCPFlakeClient
from ..utils.tool_manager import ToolManager


class MCPClient:
    """MCP client for accessing Lab Agent tools from GPT-5-mini chatbox"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp.client")
        self.tool_groups = {}
        self.tool_manager = ToolManager()
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize available tool groups based on activation state"""
        try:
            initialized_count = 0
            
            # Initialize ArXiv Daily tools if active
            if self.tool_manager.is_tool_active("arxiv_daily"):
                self.tool_groups["arxiv_daily"] = ArxivDailyTools()
                initialized_count += 1
                self.logger.info("MCP client: Initialized ArXiv Daily tools")
            
            # Initialize 2D Flake client tools if active
            if self.tool_manager.is_tool_active("flake_2d"):
                flake_client = FastMCPFlakeClient()
                # Pre-connect to ensure tools are available
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # Already in event loop, skip pre-connection
                    except RuntimeError:
                        # No event loop running, safe to connect
                        asyncio.run(flake_client.connect())
                except Exception as e:
                    self.logger.warning(f"Could not pre-connect to FastMCP server: {e}")
                
                self.tool_groups["flake_2d"] = flake_client
                initialized_count += 1
                self.logger.info("MCP client: Initialized FastMCP 2D Flake client")
            
            self.logger.info(f"MCP client initialized with {initialized_count} active tool groups")
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP tools: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name"""
        self.logger.info(f"🔧 MCP CLIENT: Calling tool '{tool_name}' with args: {arguments}")
        
        # Find which tool group contains this tool
        for group_name, tool_group in self.tool_groups.items():
            try:
                # Get tool definitions from the group
                tool_defs = tool_group.get_tool_definitions()
                
                # Handle both object-based and dict-based tool definitions
                tool_names = []
                for tool_def in tool_defs:
                    if isinstance(tool_def, dict):
                        tool_names.append(tool_def.get("name", "unknown"))
                    else:
                        tool_names.append(getattr(tool_def, 'name', 'unknown'))
                
                if tool_name in tool_names:
                    self.logger.info(f"🎯 MCP CLIENT: Found tool '{tool_name}' in group '{group_name}', executing...")
                    
                    # Check if this is a FastMCP client and use sync execution
                    if hasattr(tool_group, 'execute_tool_sync'):
                        # FastMCP client - use sync execution to avoid event loop conflicts
                        result = tool_group.execute_tool_sync(tool_name, arguments)
                    else:
                        # Regular MCP tool - use async execution
                        result = await tool_group.execute_tool(tool_name, arguments)
                    
                    self.logger.info(f"✅ MCP CLIENT: Tool '{tool_name}' executed successfully with result: {result.get('success', False)}")
                    return result
            except Exception as e:
                self.logger.error(f"❌ MCP CLIENT: Error calling tool {tool_name} in group {group_name}: {e}")
                continue
        
        # Tool not found
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found",
            "available_tools": self.get_available_tools()
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        tools = []
        
        for group_name, tool_group in self.tool_groups.items():
            try:
                tool_defs = tool_group.get_tool_definitions()
                for tool_def in tool_defs:
                    # Handle both object-based (ArxivDailyTools) and dict-based (FastMCP) tool definitions
                    if isinstance(tool_def, dict):
                        # Dictionary format (FastMCP)
                        tools.append({
                            "name": tool_def.get("name", "unknown"),
                            "description": tool_def.get("description", ""),
                            "group": group_name,
                            "inputSchema": tool_def.get("inputSchema", {})
                        })
                    else:
                        # Object format (ArxivDailyTools)
                        tools.append({
                            "name": getattr(tool_def, 'name', 'unknown'),
                            "description": getattr(tool_def, 'description', ''),
                            "group": group_name,
                            "inputSchema": getattr(tool_def, 'inputSchema', {})
                        })
            except Exception as e:
                self.logger.error(f"Error getting tools from group {group_name}: {e}")
        
        return tools
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools (async version for compatibility)"""
        return self.get_available_tools()
    
    def refresh_tools(self):
        """Refresh tool groups based on current activation state"""
        self.logger.info("🔄 MCP CLIENT: Refreshing tool groups")
        
        # Clear existing tools
        old_groups = list(self.tool_groups.keys())
        self.tool_groups.clear()
        
        # Reload tool manager and reinitialize
        self.tool_manager = ToolManager()
        self._initialize_tools()
        
        new_groups = list(self.tool_groups.keys())
        self.logger.info(f"🔄 MCP CLIENT: Tool groups refreshed: {old_groups} → {new_groups}")
    
    def get_tools_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        """Get tools for a specific group"""
        if group_name not in self.tool_groups:
            return []
        
        tools = []
        tool_group = self.tool_groups[group_name]
        
        try:
            tool_defs = tool_group.get_tool_definitions()
            for tool_def in tool_defs:
                # Handle both dict and object formats
                if isinstance(tool_def, dict):
                    # Tool is already a dictionary
                    tools.append({
                        "name": tool_def.get("name", "unknown_tool"),
                        "description": tool_def.get("description", ""),
                        "inputSchema": tool_def.get("inputSchema", {})
                    })
                else:
                    # Tool is an object with attributes
                    tools.append({
                        "name": getattr(tool_def, 'name', 'unknown_tool'),
                        "description": getattr(tool_def, 'description', ''),
                        "inputSchema": getattr(tool_def, 'inputSchema', {})
                    })
        except Exception as e:
            self.logger.error(f"Error getting tools from group {group_name}: {e}")
        
        return tools
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available"""
        available_tools = self.get_available_tools()
        return any(tool["name"] == tool_name for tool in available_tools)


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


def reset_mcp_client():
    """Reset the global MCP client instance"""
    global _mcp_client
    _mcp_client = None