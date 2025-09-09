"""
Tool Loop - Recursive tool calling until completion
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Iterator
from .responses_client import ResponsesClient
from .tool_adapter import ToolAdapter


class ToolLoop:
    """Handles recursive tool calling until model stops requesting tools"""
    
    def __init__(self, responses_client: ResponsesClient = None, tool_adapter: ToolAdapter = None):
        self.logger = logging.getLogger("playground.tool_loop")
        self.responses_client = responses_client or ResponsesClient()
        self.tool_adapter = tool_adapter or ToolAdapter()
        self.max_recursive_calls = 10
        self.tool_timeout = 30
    
    def execute_tool_loop(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        config: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Execute the complete tool calling loop"""
        
        if stream:
            return self._execute_streaming_loop(model, messages, tools, tool_executor, config)
        else:
            return self._execute_blocking_loop(model, messages, tools, tool_executor, config)
    
    def _execute_blocking_loop(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute tool loop in blocking mode"""
        self.logger.info(f"Starting tool loop for {model} with {len(tools)} tools available")
        
        loop_count = 0
        conversation_messages = messages.copy()
        tool_call_history = []
        
        while loop_count < self.max_recursive_calls:
            loop_count += 1
            self.logger.info(f"Tool loop iteration {loop_count}")
            
            # Make API call
            try:
                response = self.responses_client.create_response(
                    model=model,
                    messages=conversation_messages,
                    tools=tools,
                    config=config,
                    stream=False
                )
            except Exception as e:
                self.logger.error(f"API call failed in loop {loop_count}: {e}")
                return {
                    "success": False,
                    "error": f"API call failed: {e}",
                    "loop_count": loop_count,
                    "tool_calls": tool_call_history
                }
            
            # Extract tool calls
            tool_calls = self.responses_client.extract_tool_calls(response)
            text_content = self.responses_client.extract_text_content(response)
            
            # Add assistant response to conversation
            assistant_msg = {"role": "assistant", "content": text_content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            conversation_messages.append(assistant_msg)
            
            # If no tool calls, we're done
            if not tool_calls:
                self.logger.info(f"Tool loop completed after {loop_count} iterations")
                return {
                    "success": True,
                    "response": response,
                    "final_content": text_content,
                    "loop_count": loop_count,
                    "tool_calls": tool_call_history,
                    "conversation": conversation_messages
                }
            
            # Execute tool calls
            tool_outputs = []
            for tool_call in tool_calls:
                try:
                    result = self._execute_single_tool(tool_call, tool_executor, tools)
                    tool_output = self.tool_adapter.format_tool_result(result, tool_call["id"])
                    tool_outputs.append(tool_output)
                    
                    # Record in history
                    tool_call_history.append({
                        "call": tool_call,
                        "result": result,
                        "iteration": loop_count
                    })
                    
                    # Add tool result to conversation
                    conversation_messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call["id"]
                    })
                    
                except Exception as e:
                    error_result = {"success": False, "error": str(e)}
                    tool_output = self.tool_adapter.format_tool_result(error_result, tool_call["id"])
                    tool_outputs.append(tool_output)
                    
                    tool_call_history.append({
                        "call": tool_call,
                        "result": error_result,
                        "iteration": loop_count,
                        "error": str(e)
                    })
                    
                    conversation_messages.append({
                        "role": "tool",
                        "content": json.dumps(error_result),
                        "tool_call_id": tool_call["id"]
                    })
            
            # After all tool calls are executed, add user continuation prompt
            # This is critical for Chat Completions API - the model needs a user prompt to continue
            self.logger.info(f"Adding user continuation prompt after {len(tool_calls)} tool calls")
            conversation_messages.append({
                "role": "user", 
                "content": "Continue with the analysis based on the tool results above."
            })
        
        # Max iterations reached
        self.logger.warning(f"Tool loop reached max iterations ({self.max_recursive_calls})")
        return {
            "success": False,
            "error": f"Maximum recursion depth reached ({self.max_recursive_calls})",
            "loop_count": loop_count,
            "tool_calls": tool_call_history,
            "conversation": conversation_messages
        }
    
    def _execute_streaming_loop(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:
        """Execute tool loop in streaming mode"""
        self.logger.info(f"Starting streaming tool loop for {model}")
        
        loop_count = 0
        conversation_messages = messages.copy()
        tool_call_history = []
        
        while loop_count < self.max_recursive_calls:
            loop_count += 1
            yield {
                "type": "loop_iteration",
                "iteration": loop_count,
                "message": f"Starting iteration {loop_count}"
            }
            
            # Stream the response
            current_tool_calls = []
            current_content = ""
            
            try:
                for event in self.responses_client.stream_response(
                    model=model,
                    messages=conversation_messages,
                    tools=tools,
                    config=config
                ):
                    # Forward streaming events
                    yield event
                    
                    # Collect information for tool processing
                    if event.get("type") == "tool_calls":
                        current_tool_calls = event.get("tool_calls", [])
                    elif event.get("type") == "content_delta":
                        current_content += event.get("content", "")
                    elif event.get("type") == "final_response":
                        # Extract final information
                        response = event.get("response")
                        if response:
                            current_tool_calls = self.responses_client.extract_tool_calls(response)
                            current_content = self.responses_client.extract_text_content(response)
                
            except Exception as e:
                yield {
                    "type": "error",
                    "error": f"Streaming failed: {e}",
                    "iteration": loop_count
                }
                return
            
            # Add assistant response to conversation
            assistant_msg = {"role": "assistant", "content": current_content}
            if current_tool_calls:
                assistant_msg["tool_calls"] = current_tool_calls
            conversation_messages.append(assistant_msg)
            
            # If no tool calls, we're done
            if not current_tool_calls:
                yield {
                    "type": "loop_complete",
                    "final_content": current_content,
                    "loop_count": loop_count,
                    "tool_calls": tool_call_history,
                    "conversation": conversation_messages
                }
                return
            
            # Execute tool calls
            yield {
                "type": "tool_execution_start",
                "tool_count": len(current_tool_calls),
                "iteration": loop_count
            }
            
            for i, tool_call in enumerate(current_tool_calls):
                yield {
                    "type": "tool_executing",
                    "tool_name": tool_call["function"]["name"],
                    "tool_index": i + 1,
                    "total_tools": len(current_tool_calls)
                }
                
                try:
                    result = self._execute_single_tool(tool_call, tool_executor, tools)
                    
                    tool_call_history.append({
                        "call": tool_call,
                        "result": result,
                        "iteration": loop_count
                    })
                    
                    conversation_messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call["id"]
                    })
                    
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_call["function"]["name"],
                        "result": result,
                        "success": True
                    }
                    
                except Exception as e:
                    error_result = {"success": False, "error": str(e)}
                    
                    tool_call_history.append({
                        "call": tool_call,
                        "result": error_result,
                        "iteration": loop_count,
                        "error": str(e)
                    })
                    
                    conversation_messages.append({
                        "role": "tool",
                        "content": json.dumps(error_result),
                        "tool_call_id": tool_call["id"]
                    })
                    
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_call["function"]["name"],
                        "result": error_result,
                        "success": False,
                        "error": str(e)
                    }
            
            # After all tool calls are executed, add user continuation prompt
            # This is critical for Chat Completions API - the model needs a user prompt to continue
            yield {
                "type": "tool_execution_complete",
                "message": "All tools executed, adding continuation prompt",
                "iteration": loop_count
            }
            
            # Add user continuation message to prompt the model to continue
            conversation_messages.append({
                "role": "user",
                "content": "Continue with the analysis based on the tool results above."
            })
        
        # Max iterations reached
        yield {
            "type": "loop_error",
            "error": f"Maximum recursion depth reached ({self.max_recursive_calls})",
            "loop_count": loop_count,
            "conversation": conversation_messages
        }
    
    def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        available_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a single tool call"""
        tool_name = tool_call["function"]["name"]
        
        try:
            # Parse arguments
            if isinstance(tool_call["function"]["arguments"], str):
                arguments = json.loads(tool_call["function"]["arguments"])
            else:
                arguments = tool_call["function"]["arguments"]
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid tool arguments JSON: {e}",
                "tool_name": tool_name
            }
        
        # Find the tool definition for routing info
        tool_def = None
        for tool in available_tools:
            if tool["function"]["name"] == tool_name:
                tool_def = tool
                break
        
        if not tool_def:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in available tools",
                "tool_name": tool_name
            }
        
        # Execute the tool
        self.logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        try:
            result = tool_executor(tool_name, arguments, tool_def)
            
            # Ensure result is properly formatted
            if not isinstance(result, dict):
                result = {"success": True, "result": result}
            elif "success" not in result:
                result["success"] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def set_max_iterations(self, max_iterations: int):
        """Set maximum number of tool loop iterations"""
        self.max_recursive_calls = max_iterations
        self.logger.info(f"Max tool loop iterations set to {max_iterations}")
    
    def set_tool_timeout(self, timeout: int):
        """Set timeout for individual tool executions"""
        self.tool_timeout = timeout
        self.logger.info(f"Tool timeout set to {timeout} seconds")