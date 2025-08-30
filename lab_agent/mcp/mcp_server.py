"""
MCP Server for Lab Agent ArXiv Daily tools.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
from mcp import Tool

from .tools.arxiv_daily_tools import ArxivDailyTools
from .tools.flake_2d_client import Flake2DClient
from ..utils.tool_manager import ToolManager


class MCPServer:
    """MCP Server for Lab Agent"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.server = Server(self.config["server"]["name"])
        self.tools: Dict[str, Any] = {}
        self.logger = self._setup_logging()
        self.tool_manager = ToolManager()  # Add tool manager
        
        # Initialize tools
        self._initialize_tools()
        self._register_handlers()
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load MCP server configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "mcp_config.json")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {config_path}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration if config file is missing"""
        return {
            "server": {
                "name": "labagent-mcp-server",
                "version": "1.0.0",
                "description": "MCP server for Lab Agent",
                "transport": "stdio",
                "logging": {"level": "INFO"}
            },
            "tools": []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for MCP server"""
        logger = logging.getLogger("mcp.server")
        
        # Set log level
        log_level = self.config.get("server", {}).get("logging", {}).get("level", "INFO")
        logger.setLevel(getattr(logging, log_level))
        
        # Create handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                self.config.get("server", {}).get("logging", {}).get(
                    "format", 
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_tools(self):
        """Initialize only activated tools"""
        try:
            # Initialize ArXiv Daily tools if active
            if self.tool_manager.is_tool_active("arxiv_daily"):
                arxiv_tools = ArxivDailyTools()
                self.tools["arxiv_daily"] = arxiv_tools
                self.logger.info("Initialized ArXiv Daily tools")
            
            # Initialize 2D Flake client tools if active
            if self.tool_manager.is_tool_active("flake_2d"):
                flake_2d_client = Flake2DClient()
                self.tools["flake_2d_client"] = flake_2d_client
                self.logger.info("Initialized 2D Flake client tools")
            
            active_tools = self.tool_manager.get_active_tools()
            self.logger.info(f"Initialized {len(self.tools)} active tool groups: {list(active_tools.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to initialize tools: {e}")
            raise
    
    def _register_handlers(self):
        """Register MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            tools = []
            
            # Get tools from ArXiv Daily tools
            if "arxiv_daily" in self.tools:
                arxiv_daily_tools = self.tools["arxiv_daily"].get_tool_definitions()
                tools.extend(arxiv_daily_tools)
            
            # Get tools from 2D Flake client
            if "flake_2d_client" in self.tools:
                flake_2d_tools = self.tools["flake_2d_client"].get_tool_definitions()
                tools.extend(flake_2d_tools)
            
            self.logger.info(f"Listed {len(tools)} available tools")
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool execution"""
            self.logger.info(f"Tool call requested: {name} with args: {arguments}")
            
            try:
                result = None
                
                # Route ArXiv Daily tool calls
                arxiv_tools = ["read_daily_report", "generate_daily_report", "list_available_reports", "search_papers_by_author"]
                if name in arxiv_tools:
                    if "arxiv_daily" not in self.tools:
                        raise ValueError("ArXiv Daily tools not available")
                    result = await self.tools["arxiv_daily"].execute_tool(name, arguments)
                
                # Route 2D Flake client tool calls
                elif name in ["connect_2d_flake_server", "get_2d_flake_models", "upload_2d_flake_image", 
                              "classify_2d_flake", "get_2d_flake_history", "get_2d_flake_server_status"]:
                    if "flake_2d_client" not in self.tools:
                        raise ValueError("2D Flake client tools not available")
                    result = await self.tools["flake_2d_client"].execute_tool(name, arguments)
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                if result is None:
                    raise ValueError(f"No result returned for tool: {name}")
                
                # Format response as TextContent
                response_text = json.dumps(result, indent=2)
                return [TextContent(type="text", text=response_text)]
                
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                self.logger.error(error_msg)
                error_response = {
                    "success": False,
                    "error": error_msg
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def run(self):
        """Run the MCP server"""
        self.logger.info(f"Starting MCP server: {self.config['server']['name']}")
        
        # Initialize server options
        options = InitializationOptions(
            server_name=self.config["server"]["name"],
            server_version=self.config["server"]["version"]
        )
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                self.logger.info("MCP server running with stdio transport")
                await self.server.run(
                    read_stream, 
                    write_stream, 
                    options
                )
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
    
    def refresh_tools(self):
        """Refresh tools based on current activation state"""
        self.logger.info("Refreshing tool activation state")
        self.tool_manager = ToolManager()  # Reload activation state
        
        # Clear existing tools
        old_tools = list(self.tools.keys())
        self.tools.clear()
        
        # Reinitialize tools
        self._initialize_tools()
        
        new_tools = list(self.tools.keys())
        self.logger.info(f"Tool refresh: {old_tools} -> {new_tools}")
    
    def get_tool_manager(self) -> ToolManager:
        """Get the tool manager instance"""
        return self.tool_manager
    
    def shutdown(self):
        """Shutdown the MCP server"""
        self.logger.info("Shutting down MCP server")
        # Cleanup resources if needed


async def main():
    """Main entry point for MCP server"""
    server = MCPServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        print("Server interrupted by user")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())