"""
MCP Client for Lab Agent - provides interface to MCP tools from the chatbox
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from .tools.arxiv_daily_tools import ArxivDailyTools


class MCPClient:
    """MCP client for accessing Lab Agent tools from GPT-5-mini chatbox"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp.client")
        self.tool_groups = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize available tool groups"""
        try:
            # Initialize ArXiv Daily tools
            self.tool_groups["arxiv_daily"] = ArxivDailyTools()
            self.logger.info("MCP client initialized with ArXiv Daily tools")
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP tools: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name"""
        self.logger.info(f"🔧 MCP CLIENT: Calling tool '{tool_name}' with args: {arguments}")
        
        # Find which tool group contains this tool
        for group_name, tool_group in self.tool_groups.items():
            try:
                # Get tool definitions from the group
                tool_defs = tool_group.get_tool_definitions()
                tool_names = [tool.name for tool in tool_defs]
                
                if tool_name in tool_names:
                    self.logger.info(f"🎯 MCP CLIENT: Found tool '{tool_name}' in group '{group_name}', executing...")
                    # Execute the tool in the appropriate group
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
                    tools.append({
                        "name": tool_def.name,
                        "description": tool_def.description,
                        "group": group_name,
                        "inputSchema": tool_def.inputSchema
                    })
            except Exception as e:
                self.logger.error(f"Error getting tools from group {group_name}: {e}")
        
        return tools
    
    def get_tools_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        """Get tools for a specific group"""
        if group_name not in self.tool_groups:
            return []
        
        tools = []
        tool_group = self.tool_groups[group_name]
        
        try:
            tool_defs = tool_group.get_tool_definitions()
            for tool_def in tool_defs:
                tools.append({
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "inputSchema": tool_def.inputSchema
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