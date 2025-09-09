"""
Tool Adapter - Convert MCP tools to OpenAI Responses API format
"""

import logging
from typing import Dict, Any, List, Optional, Union


class ToolAdapter:
    """Adapter to convert MCP tools to OpenAI Responses API format"""
    
    def __init__(self):
        self.logger = logging.getLogger("playground.tool_adapter")
    
    def mcp_to_openai_tool(self, mcp_tool: Dict[str, Any], server_id: str = None) -> Dict[str, Any]:
        """Convert an MCP tool definition to OpenAI Responses API format"""
        try:
            # Handle both dictionary and object-based MCP tool definitions
            if isinstance(mcp_tool, dict):
                name = mcp_tool.get("name", "unknown_tool")
                description = mcp_tool.get("description", "")
                parameters = mcp_tool.get("inputSchema", {})
            else:
                # Object-based tool definition (like ArxivDailyTools)
                name = getattr(mcp_tool, 'name', 'unknown_tool')
                description = getattr(mcp_tool, 'description', '')
                parameters = getattr(mcp_tool, 'inputSchema', {})
            
            # Convert to OpenAI format
            openai_tool = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": self._convert_parameters(parameters)
                },
                # Add routing information for execution
                "_route": {
                    "kind": "mcp",
                    "server_id": server_id,
                    "tool_name": name
                }
            }
            
            return openai_tool
            
        except Exception as e:
            self.logger.error(f"Failed to convert MCP tool: {e}")
            return self._create_error_tool(str(e))
    
    def _convert_parameters(self, mcp_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MCP parameter schema to OpenAI format"""
        if not mcp_parameters:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        # If it's already in JSON Schema format, use as-is
        if isinstance(mcp_parameters, dict) and "type" in mcp_parameters:
            return mcp_parameters
        
        # Otherwise, try to convert
        try:
            return {
                "type": "object",
                "properties": mcp_parameters.get("properties", {}),
                "required": mcp_parameters.get("required", []),
                "description": mcp_parameters.get("description", "")
            }
        except Exception as e:
            self.logger.warning(f"Parameter conversion failed, using default: {e}")
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
    
    def _create_error_tool(self, error_msg: str) -> Dict[str, Any]:
        """Create an error tool when conversion fails"""
        return {
            "type": "function",
            "function": {
                "name": "tool_conversion_error",
                "description": f"Tool conversion failed: {error_msg}",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "_route": {
                "kind": "error",
                "server_id": None,
                "tool_name": "tool_conversion_error"
            }
        }
    
    def batch_convert_tools(
        self, 
        mcp_tools: List[Dict[str, Any]], 
        server_id: str = None
    ) -> List[Dict[str, Any]]:
        """Convert a batch of MCP tools to OpenAI format"""
        converted_tools = []
        
        for tool in mcp_tools:
            converted = self.mcp_to_openai_tool(tool, server_id)
            converted_tools.append(converted)
        
        self.logger.info(f"Converted {len(converted_tools)} tools from server '{server_id}'")
        return converted_tools
    
    def extract_tool_routing(self, openai_tool: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract routing information from an OpenAI tool"""
        return openai_tool.get("_route")
    
    def is_mcp_tool(self, openai_tool: Dict[str, Any]) -> bool:
        """Check if a tool is from an MCP server"""
        route = self.extract_tool_routing(openai_tool)
        return route and route.get("kind") == "mcp"
    
    def get_tool_server_id(self, openai_tool: Dict[str, Any]) -> Optional[str]:
        """Get the server ID for an MCP tool"""
        route = self.extract_tool_routing(openai_tool)
        return route.get("server_id") if route else None
    
    def get_original_tool_name(self, openai_tool: Dict[str, Any]) -> Optional[str]:
        """Get the original MCP tool name"""
        route = self.extract_tool_routing(openai_tool)
        return route.get("tool_name") if route else None
    
    def create_builtin_tool(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any],
        handler: str = None
    ) -> Dict[str, Any]:
        """Create a built-in tool definition"""
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            },
            "_route": {
                "kind": "builtin",
                "handler": handler,
                "tool_name": name
            }
        }
    
    def format_tool_result(
        self, 
        result: Any, 
        tool_call_id: str = None
    ) -> Dict[str, Any]:
        """Format tool execution result for OpenAI tool_outputs"""
        try:
            # If result is already a dict with expected structure
            if isinstance(result, dict):
                if "success" in result:
                    # MCP result format
                    output = {
                        "success": result.get("success", False),
                        "result": result.get("result", result.get("data", "")),
                    }
                    if result.get("error"):
                        output["error"] = result["error"]
                else:
                    # Direct result
                    output = result
            else:
                # Simple result
                output = {"result": str(result)}
            
            # Format for OpenAI tool_outputs
            tool_output = {
                "output": output
            }
            
            if tool_call_id:
                tool_output["tool_call_id"] = tool_call_id
            
            return tool_output
            
        except Exception as e:
            self.logger.error(f"Failed to format tool result: {e}")
            return {
                "tool_call_id": tool_call_id,
                "output": {
                    "success": False,
                    "error": f"Result formatting failed: {e}"
                }
            }
    
    def validate_tool_definition(self, tool: Dict[str, Any]) -> bool:
        """Validate that a tool definition is properly formatted"""
        try:
            # Check required fields
            if not isinstance(tool, dict):
                return False
            
            if tool.get("type") != "function":
                return False
            
            function = tool.get("function", {})
            if not function.get("name"):
                return False
            
            parameters = function.get("parameters", {})
            if not isinstance(parameters, dict):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_tool_signature(self, tool: Dict[str, Any]) -> str:
        """Get a human-readable signature for a tool"""
        try:
            function = tool.get("function", {})
            name = function.get("name", "unknown")
            description = function.get("description", "No description")
            
            parameters = function.get("parameters", {})
            props = parameters.get("properties", {})
            required = parameters.get("required", [])
            
            # Build parameter list
            param_strs = []
            for param_name, param_info in props.items():
                param_type = param_info.get("type", "any")
                is_required = param_name in required
                param_str = f"{param_name}: {param_type}"
                if is_required:
                    param_str = f"*{param_str}"
                param_strs.append(param_str)
            
            params_str = ", ".join(param_strs)
            return f"{name}({params_str}) - {description}"
            
        except Exception as e:
            return f"tool_signature_error: {e}"