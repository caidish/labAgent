"""
Base class for MCP tools in Lab Agent.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from mcp import Tool


class BaseTool(ABC):
    """Base class for all MCP tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"mcp.tools.{name}")
    
    @abstractmethod
    def get_tool_definition(self) -> Tool:
        """Return the MCP tool definition"""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments"""
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any], required_params: List[str]) -> bool:
        """Validate that required parameters are present"""
        for param in required_params:
            if param not in arguments:
                raise ValueError(f"Missing required parameter: {param}")
        return True
    
    def format_success_response(self, data: Any, message: str = "Success") -> Dict[str, Any]:
        """Format a successful response"""
        return {
            "success": True,
            "message": message,
            "data": data
        }
    
    def format_error_response(self, error: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Format an error response"""
        response = {
            "success": False,
            "error": error
        }
        if details:
            response["details"] = details
        return response
    
    def log_execution(self, arguments: Dict[str, Any], result: Dict[str, Any]):
        """Log tool execution"""
        self.logger.info(f"Tool {self.name} executed with args: {arguments}")
        if result.get("success"):
            self.logger.info(f"Tool {self.name} succeeded")
        else:
            self.logger.error(f"Tool {self.name} failed: {result.get('error')}")