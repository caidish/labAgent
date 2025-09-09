"""
OpenAI Responses API Client - Unified client for modern OpenAI models
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Iterator, Union, AsyncIterator
from openai import OpenAI
from ..utils import Config
from .model_capabilities import get_model_caps, ModelCapabilities


class ResponsesClient:
    """Unified OpenAI Responses API client supporting all modern models"""
    
    def __init__(self):
        self.logger = logging.getLogger("playground.responses_client")
        self.config = Config()
        
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        
        self.client = OpenAI(api_key=self.config.openai_api_key)
        self._load_playground_config()
    
    def _load_playground_config(self) -> None:
        """Load playground-specific configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'playground_models.json'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.playground_config = json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Playground config not found at {config_path}, using defaults")
            self.playground_config = self._default_playground_config()
    
    def _default_playground_config(self) -> Dict[str, Any]:
        """Default playground configuration"""
        return {
            "default_settings": {
                "temperature": 0.2,
                "top_p": 1.0,
                "stream": True,
                "max_retries": 3,
                "timeout": 60
            }
        }
    
    def _should_use_responses_api(self, model: str) -> bool:
        """Determine whether to use Responses API or Chat Completions API"""
        caps = get_model_caps(model)
        if not caps:
            return False
        
        # Currently, let's use Chat Completions API for all models
        # since it's more widely supported and stable
        return False
    
    def _prepare_chat_params(
        self, 
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Prepare parameters for Chat Completions API"""
        caps = get_model_caps(model)
        if not caps:
            raise ValueError(f"Unsupported model: {model}")

        # Base parameters for Chat Completions
        params = {
            "model": model,
            "messages": [{"role": msg["role"], "content": msg["content"]} for msg in messages],
            "temperature": config.get("temperature", caps.defaults.temperature) if config else caps.defaults.temperature,
            "top_p": config.get("top_p", caps.defaults.top_p) if config else caps.defaults.top_p,
        }
        
        # Add tools if supported and provided
        if tools and caps.supports.tools:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "parameters": tool["function"].get("parameters", {})
                    }
                }
                for tool in tools
            ]
            params["tool_choice"] = "auto"
        
        # Add reasoning effort for o-series models (Chat Completions supports this)
        if caps.supports.reasoning_effort and config and "reasoning_effort" in config:
            params["reasoning_effort"] = config["reasoning_effort"]
        
        # Add verbosity for GPT-5 if supported
        if caps.supports.verbosity and config and "verbosity" in config:
            params["verbosity"] = config["verbosity"]
        
        # Add max_tokens if specified (Chat Completions uses max_tokens)
        if config and "max_tokens" in config:
            params["max_tokens"] = config["max_tokens"]
        elif caps.defaults.max_tokens:
            params["max_tokens"] = caps.defaults.max_tokens
        
        # Add any additional kwargs
        params.update(kwargs)
        
        return params
    
    def _prepare_responses_params(
        self, 
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Prepare parameters for Responses API"""
        caps = get_model_caps(model)
        if not caps:
            raise ValueError(f"Unsupported model: {model}")

        # Base parameters for Responses API
        params = {
            "model": model,
            "input": [{"role": msg["role"], "content": msg["content"]} for msg in messages],
            "temperature": config.get("temperature", caps.defaults.temperature) if config else caps.defaults.temperature,
            "top_p": config.get("top_p", caps.defaults.top_p) if config else caps.defaults.top_p,
        }
        
        # Add tools if supported and provided
        if tools and caps.supports.tools:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "parameters": tool["function"].get("parameters", {})
                    }
                }
                for tool in tools
            ]
            params["tool_choice"] = "auto"
        
        # Add reasoning parameters if supported (Responses API format)
        if caps.supports.reasoning_effort and config and "reasoning_effort" in config:
            params["reasoning"] = {"effort": config["reasoning_effort"]}
        
        # Add verbosity for GPT-5 if supported
        if caps.supports.verbosity and config and "verbosity" in config:
            params["text"] = {"verbosity": config["verbosity"]}
        
        # Add max_output_tokens if specified (Responses API uses max_output_tokens)
        if config and "max_tokens" in config:
            params["max_output_tokens"] = config["max_tokens"]
        elif caps.defaults.max_tokens:
            params["max_output_tokens"] = caps.defaults.max_tokens
        
        # Add any additional kwargs
        params.update(kwargs)
        
        return params
    
    def create_response(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Create a response using the appropriate OpenAI API"""
        use_responses_api = self._should_use_responses_api(model)
        
        if use_responses_api:
            params = self._prepare_responses_params(model, messages, tools, config, **kwargs)
            api_name = "Responses API"
            
            self.logger.info(f"Making Responses API call to {model} with {len(messages)} messages")
            if tools:
                self.logger.info(f"Available tools: {[t['function']['name'] for t in tools]}")
            
            try:
                if stream:
                    return self.client.responses.stream(**params)
                else:
                    return self.client.responses.create(**params)
            except Exception as e:
                self.logger.error(f"Responses API call failed: {e}")
                raise
        else:
            params = self._prepare_chat_params(model, messages, tools, config, **kwargs)
            api_name = "Chat Completions API"
            
            self.logger.info(f"Making Chat Completions API call to {model} with {len(messages)} messages")
            if tools:
                self.logger.info(f"Available tools: {[t['function']['name'] for t in tools]}")
            
            try:
                if stream:
                    return self.client.chat.completions.create(stream=True, **params)
                else:
                    return self.client.chat.completions.create(**params)
            except Exception as e:
                self.logger.error(f"Chat Completions API call failed: {e}")
                raise
    
    def stream_response(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Stream response with simplified event format"""
        use_responses_api = self._should_use_responses_api(model)
        
        if use_responses_api:
            params = self._prepare_responses_params(model, messages, tools, config, **kwargs)
            
            self.logger.info(f"Starting Responses API streaming from {model}")
            
            try:
                with self.client.responses.stream(**params) as stream:
                    for event in stream:
                        # Convert OpenAI event to simplified format
                        yield self._convert_stream_event(event)
                    
                    # Get final response
                    final_response = stream.get_final_response()
                    yield {
                        "type": "final_response",
                        "response": final_response,
                        "done": True
                    }
                    
            except Exception as e:
                self.logger.error(f"Responses API streaming failed: {e}")
                yield {
                    "type": "error",
                    "error": str(e),
                    "done": True
                }
        else:
            params = self._prepare_chat_params(model, messages, tools, config, **kwargs)
            
            self.logger.info(f"Starting Chat Completions streaming from {model}")
            
            try:
                stream = self.client.chat.completions.create(stream=True, **params)
                
                # Accumulate content and tool calls from streaming chunks
                accumulated_content = ""
                accumulated_tool_calls = {}
                
                for chunk in stream:
                    # Convert chat completion chunk to simplified format
                    event = self._convert_chat_chunk(chunk)
                    
                    if event["type"] == "content_delta":
                        accumulated_content += event.get("content", "")
                        yield event
                    elif event["type"] == "tool_calls":
                        # Accumulate tool calls (they come in pieces)
                        for tool_call in event.get("tool_calls", []):
                            call_id = tool_call.get("id")
                            if call_id:
                                if call_id not in accumulated_tool_calls:
                                    accumulated_tool_calls[call_id] = {
                                        "id": call_id,
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    }
                                
                                # Update accumulated tool call
                                func = tool_call.get("function", {})
                                if func.get("name"):
                                    accumulated_tool_calls[call_id]["function"]["name"] = func["name"]
                                if func.get("arguments"):
                                    accumulated_tool_calls[call_id]["function"]["arguments"] += func["arguments"]
                    elif event["type"] == "finish":
                        if event.get("finish_reason") == "tool_calls" and accumulated_tool_calls:
                            # Send accumulated tool calls
                            yield {
                                "type": "tool_calls",
                                "tool_calls": list(accumulated_tool_calls.values()),
                                "done": False
                            }
                        break
                    else:
                        yield event
                
                # Mark as done
                yield {
                    "type": "final_response",
                    "final_content": accumulated_content,
                    "tool_calls": list(accumulated_tool_calls.values()) if accumulated_tool_calls else [],
                    "done": True
                }
                    
            except Exception as e:
                self.logger.error(f"Chat Completions streaming failed: {e}")
                yield {
                    "type": "error",
                    "error": str(e),
                    "done": True
                }
    
    def _convert_stream_event(self, event) -> Dict[str, Any]:
        """Convert OpenAI stream event to simplified format"""
        try:
            # Handle different event types from OpenAI streaming
            if hasattr(event, 'type'):
                if event.type == "response.delta":
                    return {
                        "type": "content_delta",
                        "content": getattr(event.delta, 'content', ''),
                        "done": False
                    }
                elif event.type == "response.tool_calls":
                    return {
                        "type": "tool_calls",
                        "tool_calls": event.tool_calls,
                        "done": False
                    }
                elif event.type == "response.reasoning":
                    return {
                        "type": "reasoning",
                        "reasoning": event.reasoning,
                        "done": False
                    }
            
            # Default handling
            return {
                "type": "unknown",
                "data": str(event),
                "done": False
            }
        except Exception as e:
            return {
                "type": "error",
                "error": f"Event conversion failed: {e}",
                "done": False
            }
    
    def _convert_chat_chunk(self, chunk) -> Dict[str, Any]:
        """Convert chat completion chunk to simplified format"""
        try:
            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta
                
                if hasattr(delta, 'content') and delta.content:
                    return {
                        "type": "content_delta",
                        "content": delta.content,
                        "done": False
                    }
                elif hasattr(delta, 'tool_calls') and delta.tool_calls:
                    # Convert ChoiceDeltaToolCall objects to dict format
                    formatted_tool_calls = []
                    for tool_call in delta.tool_calls:
                        formatted_call = {
                            "id": getattr(tool_call, 'id', None),
                            "type": getattr(tool_call, 'type', 'function'),
                            "function": {
                                "name": getattr(tool_call.function, 'name', '') if hasattr(tool_call, 'function') else '',
                                "arguments": getattr(tool_call.function, 'arguments', '') if hasattr(tool_call, 'function') else ''
                            }
                        }
                        formatted_tool_calls.append(formatted_call)
                    
                    return {
                        "type": "tool_calls",
                        "tool_calls": formatted_tool_calls,
                        "done": False
                    }
                elif hasattr(choice, 'finish_reason') and choice.finish_reason:
                    return {
                        "type": "finish",
                        "finish_reason": choice.finish_reason,
                        "done": choice.finish_reason in ["stop", "tool_calls"]
                    }
            
            # Default handling for unknown chunks
            return {
                "type": "chunk",
                "data": str(chunk),
                "done": False
            }
        except Exception as e:
            return {
                "type": "error",
                "error": f"Chat chunk conversion failed: {e}",
                "done": False
            }
    
    def continue_with_tool_outputs(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tool_outputs: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Continue conversation with tool outputs (for recursive tool calling)"""
        use_responses_api = self._should_use_responses_api(model)
        
        self.logger.info(f"Continuing with {len(tool_outputs)} tool outputs")
        
        if use_responses_api:
            # Responses API supports tool_outputs parameter
            params = self._prepare_responses_params(model, messages, tools, config, **kwargs)
            params["tool_outputs"] = tool_outputs
            
            try:
                if stream:
                    return self.client.responses.stream(**params)
                else:
                    return self.client.responses.create(**params)
            except Exception as e:
                self.logger.error(f"Responses API tool output continuation failed: {e}")
                raise
        else:
            # Chat Completions API: tool outputs are already included in messages
            # This method is typically not needed for Chat Completions as tool results
            # are handled by adding tool messages to the conversation
            return self.create_response(model, messages, tools, config, stream, **kwargs)
    
    def extract_tool_calls(self, response) -> List[Dict[str, Any]]:
        """Extract tool calls from a response"""
        tool_calls = []
        
        try:
            # Handle Responses API format
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "tool_call":
                        tool_calls.append({
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.function.name,
                                "arguments": item.function.arguments
                            }
                        })
            
            # Handle Chat Completions API format
            elif hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                    for tool_call in choice.message.tool_calls:
                        tool_calls.append({
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
                        
        except Exception as e:
            self.logger.warning(f"Failed to extract tool calls: {e}")
        
        return tool_calls
    
    def extract_text_content(self, response) -> str:
        """Extract text content from a response"""
        try:
            # Handle Responses API format
            if hasattr(response, 'output_text'):
                return response.output_text or ""
            elif hasattr(response, 'output') and response.output:
                # Extract text from output items
                text_parts = []
                for item in response.output:
                    if hasattr(item, 'type') and item.type == "text":
                        text_parts.append(str(item.content))
                return "".join(text_parts)
            
            # Handle Chat Completions API format
            elif hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content or ""
                    
        except Exception as e:
            self.logger.warning(f"Failed to extract text content: {e}")
        
        return ""
    
    def get_model_info(self, model: str) -> Optional[ModelCapabilities]:
        """Get information about a model"""
        return get_model_caps(model)