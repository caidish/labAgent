"""
Playground Client - Non-streaming client based on proven llm_chatbox patterns
"""

import json
import logging
import os
import asyncio
from typing import List, Dict, Optional, Any
from openai import OpenAI
from ..utils import Config
from .model_capabilities import get_model_caps, ModelCapabilities


class PlaygroundClient:
    """Non-streaming playground client based on llm_chatbox proven patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger("playground.client")
        self.config = Config()
        
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        
        self.client = OpenAI(api_key=self.config.openai_api_key)
        
        # Initialize conversation
        self.conversation_history = []
        self.current_tools = []
        self.tool_executor = None
    
    def start_conversation(self, system_prompt: Optional[str] = None):
        """Initialize a new conversation"""
        if system_prompt:
            self.conversation_history = [{"role": "system", "content": system_prompt}]
        else:
            self.conversation_history = []
        self.logger.info("New playground conversation started")
    
    def set_tools(self, tools: List[Dict[str, Any]], tool_executor_func):
        """Set available tools and executor function"""
        self.current_tools = tools
        self.tool_executor = tool_executor_func
        self.logger.info(f"Set {len(tools)} tools for playground conversation")
    
    async def chat(self, user_message: str, model: str, config: Dict[str, Any] = None, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Send a message and get response with tool calling support
        Returns immediate results with proper message persistence
        """
        try:
            # Add user message to history immediately
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            self.logger.info(f"User message added to conversation: {user_message[:100]}...")
            
            # Get model capabilities to format request correctly  
            model_caps = get_model_caps(model)
            if not model_caps:
                return {
                    "success": False,
                    "error": f"Unknown model: {model}",
                    "conversation": self.conversation_history.copy()
                }
            
            # Prepare API parameters based on model capabilities
            api_params = self._prepare_api_params(model, config or {}, model_caps)
            
            # Add tools if available (Chat Completions format for GPT-4.1 compatibility)
            if self.current_tools and self.tool_executor:
                api_params["tools"] = self._format_tools_for_chat_completions(self.current_tools)
                self.logger.info(f"Added {len(self.current_tools)} tools to API request")
            
            # Make initial API call
            self.logger.info(f"Making API call to {model}")
            result = self._make_api_call(model, self.conversation_history, api_params)
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result["error"],
                    "conversation": self.conversation_history.copy()
                }
            
            # Handle tool calling with iterative approach (like llm_chatbox)
            final_content, tool_call_results = await self._handle_tool_calling_loop(
                result, model, api_params, max_iterations
            )
            
            # Return complete result
            return {
                "success": True,
                "response": final_content,
                "tool_results": tool_call_results,
                "conversation": self.conversation_history.copy(),
                "model_used": model,
                "total_messages": len(self.conversation_history)
            }
            
        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation": self.conversation_history.copy()
            }
    
    def _prepare_api_params(self, model: str, config: Dict[str, Any], model_caps: ModelCapabilities) -> Dict[str, Any]:
        """Prepare API parameters based on model and config"""
        params = {
            "model": model,
            "temperature": config.get("temperature", model_caps.defaults.temperature),
            "top_p": config.get("top_p", model_caps.defaults.top_p),
            "stream": False,  # Non-streaming for reliability
        }
        
        # Add model-specific parameters
        if model_caps.defaults.max_tokens:
            params["max_tokens"] = config.get("max_tokens", model_caps.defaults.max_tokens)
        
        # Add reasoning parameters for reasoning models
        if model_caps.supports.reasoning_effort and "reasoning_effort" in config:
            params["reasoning_effort"] = config["reasoning_effort"]
        
        # Add verbosity for GPT-5
        if model_caps.supports.verbosity and "verbosity" in config:
            params["verbosity"] = config["verbosity"]
        
        return params
    
    def _format_tools_for_chat_completions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for Chat Completions API (GPT-4.1 compatible)"""
        formatted_tools = []
        
        for tool in tools:
            # Handle different tool formats and convert to Chat Completions format
            if "function" in tool:
                # Already in correct format
                formatted_tools.append(tool)
            else:
                # Convert from other formats
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "unknown"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", tool.get("parameters", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }))
                    }
                })
        
        return formatted_tools
    
    def _make_api_call(self, model: str, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Make OpenAI API call"""
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                **params
            )
            
            # Extract response data
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = getattr(message, 'tool_calls', None)
            
            return {
                "success": True,
                "content": content,
                "tool_calls": tool_calls,
                "response": response
            }
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_tool_calling_loop(self, initial_result: Dict[str, Any], model: str, api_params: Dict[str, Any], max_iterations: int = 10) -> tuple[str, List[Dict[str, Any]]]:
        """Handle iterative tool calling like llm_chatbox"""
        current_result = initial_result
        api_call_count = 1
        tool_call_results = []
        
        while api_call_count <= max_iterations:
            tool_calls = current_result.get('tool_calls')
            content = current_result.get('content', '')
            
            if not tool_calls:
                # No more tool calls - add final assistant message and return
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content
                })
                self.logger.info(f"Conversation completed after {api_call_count} API calls")
                return content, tool_call_results
            
            # Add assistant message with tool calls to conversation
            assistant_message = {
                "role": "assistant",
                "content": content
            }
            
            # Format tool calls for conversation history
            if tool_calls:
                formatted_tool_calls = []
                for tool_call in tool_calls:
                    formatted_tool_calls.append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
                assistant_message["tool_calls"] = formatted_tool_calls
            
            self.conversation_history.append(assistant_message)
            self.logger.info(f"Added assistant message with {len(tool_calls)} tool calls")
            
            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                
                self.logger.info(f"Executing tool: {tool_name}")
                
                # Execute tool using the provided executor
                if self.tool_executor:
                    try:
                        # Find tool definition
                        tool_def = None
                        for tool in self.current_tools:
                            if tool.get("function", {}).get("name") == tool_name:
                                tool_def = tool
                                break
                        
                        if tool_def:
                            tool_result = self.tool_executor(tool_name, arguments, tool_def)
                        else:
                            tool_result = {"success": False, "error": f"Tool {tool_name} not found"}
                        
                        # Store result for UI display
                        tool_call_results.append({
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                            "success": tool_result.get("success", True)
                        })
                        
                        # Format result for GPT
                        if tool_result.get("success", True):
                            result_content = self._format_tool_result_for_gpt(tool_result)
                        else:
                            result_content = f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"
                        
                    except Exception as e:
                        self.logger.error(f"Tool execution failed: {e}")
                        result_content = f"Tool execution error: {str(e)}"
                        tool_call_results.append({
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": {"success": False, "error": str(e)},
                            "success": False
                        })
                else:
                    result_content = "No tool executor available"
                
                # Add tool result to conversation
                self.conversation_history.append({
                    "role": "tool",
                    "content": result_content,
                    "tool_call_id": tool_call.id
                })
            
            # Add continuation prompt
            self.conversation_history.append({
                "role": "user", 
                "content": "Continue with the analysis based on the tool results above."
            })
            
            # Make next API call
            api_call_count += 1
            self.logger.info(f"Making API call #{api_call_count}")
            
            current_result = self._make_api_call(model, self.conversation_history, api_params)
            
            if not current_result["success"]:
                # API call failed - return what we have
                error_msg = f"API call #{api_call_count} failed: {current_result['error']}"
                self.logger.error(error_msg)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"Tool execution completed, but processing error occurred: {current_result['error']}"
                })
                return f"Tool execution completed with error: {current_result['error']}", tool_call_results
        
        # Max iterations reached
        self.logger.warning(f"Max iterations ({max_iterations}) reached")
        final_msg = f"Completed analysis after {max_iterations} iterations, but more tools were requested."
        self.conversation_history.append({
            "role": "assistant",
            "content": final_msg
        })
        return final_msg, tool_call_results
    
    def _format_tool_result_for_gpt(self, tool_result: Dict[str, Any]) -> str:
        """Format tool result for GPT analysis with complete data"""
        if not tool_result.get('success', True):
            return f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"
        
        # Handle standard MCP result format
        data = tool_result.get('data', tool_result.get('result', {}))
        message = tool_result.get('message', 'Tool executed successfully')
        
        content_parts = [f"Tool Result: {message}"]
        
        if isinstance(data, dict):
            # Add complete data for GPT analysis - no truncation
            for key, value in data.items():
                content_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        else:
            # Include complete data for proper analysis
            content_parts.append(f"Data: {str(data)}")
        
        return '\n'.join(content_parts)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history"""
        return self.conversation_history.copy()
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.logger.info("Playground conversation cleared")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        message_count = len([msg for msg in self.conversation_history if msg["role"] != "system"])
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len([msg for msg in self.conversation_history if msg["role"] == "user"]),
            "assistant_messages": len([msg for msg in self.conversation_history if msg["role"] == "assistant"]),
            "tool_messages": len([msg for msg in self.conversation_history if msg["role"] == "tool"]),
            "conversation_active": message_count > 0
        }