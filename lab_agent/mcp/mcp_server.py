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


class MCPServer:
    """MCP Server for Lab Agent"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.server = Server(self.config["server"]["name"])
        self.tools: Dict[str, ArxivDailyTools] = {}
        self.logger = self._setup_logging()
        
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
        """Initialize all enabled tools"""
        try:
            # Initialize ArXiv Daily tools
            arxiv_tools = ArxivDailyTools()
            self.tools["arxiv_daily"] = arxiv_tools
            
            self.logger.info(f"Initialized {len(self.tools)} tool groups")
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
            
            self.logger.info(f"Listed {len(tools)} available tools")
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool execution"""
            self.logger.info(f"Tool call requested: {name} with args: {arguments}")
            
            try:
                # Route tool calls to appropriate handler
                if name in ["read_daily_report", "generate_daily_report", "list_available_reports"]:
                    if "arxiv_daily" not in self.tools:
                        raise ValueError("ArXiv Daily tools not available")
                    
                    result = await self.tools["arxiv_daily"].execute_tool(name, arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
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