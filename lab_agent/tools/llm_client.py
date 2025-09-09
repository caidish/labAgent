import json
import logging
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from ..utils import Config


class LLMClient:
    """Client wrapper for OpenAI LLM models (GPT-4.1, GPT-5, etc.)"""
    
    def __init__(self):
        self.logger = logging.getLogger("tools.llm_client")
        self.config = Config()
        
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        
        self.client = OpenAI(api_key=self.config.openai_api_key)
        self.llm_config = self._load_llm_config()
        
    def _load_llm_config(self) -> Dict:
        """Load LLM-specific configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'llm_config.json'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"GPT-5-mini config not found at {config_path}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Fallback configuration if config file is missing"""
        return {
            "default_config": {
                "input": [],
                "text": {
                    "format": {"type": "text"},
                    "verbosity": "medium"
                },
                "reasoning": {
                    "effort": "medium",
                    "summary": "auto"
                },
                "tools": [],
                "store": True,
                "include": ["reasoning.encrypted_content"]
            }
        }
    
    def create_response(
        self, 
        messages: List[Dict[str, str]], 
        use_case: str = "default",
        custom_config: Optional[Dict] = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Create a response using appropriate API for the model
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            use_case: Configuration preset to use ('paper_scoring', 'chat_conversation', 'research_analysis')
            custom_config: Override default configuration
            model: Model to use (e.g., 'gpt-4.1', 'gpt-5-mini')
        """
        try:
            # Get configuration
            if custom_config:
                config = custom_config
            elif use_case in self.llm_config.get("use_cases", {}):
                base_config = self.llm_config["default_config"].copy()
                use_case_config = self.llm_config["use_cases"][use_case]
                base_config.update(use_case_config)
                config = base_config
            else:
                config = self.llm_config["default_config"]
            
            # Determine model to use
            model_name = model or config.get("model", "gpt-4.1")
            
            # Choose API based on model type
            if model_name.startswith("gpt-5"):
                # GPT-5 series uses responses API
                return self._create_responses_api(messages, model_name, config)
            else:
                # GPT-4.1 and other models use chat completions API
                return self._create_chat_completion(messages, model_name, config)
                
        except Exception as e:
            self.logger.error(f"Error creating response: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {"error": "API call failed"}
            }
    
    def _create_chat_completion(self, messages: List[Dict[str, str]], model: str, config: Dict) -> Dict[str, Any]:
        """Create response using chat completions API (for GPT-4.1, etc.)"""
        try:
            # Prepare API parameters for chat completions
            api_params = {
                "model": model,
                "messages": messages,
                "max_tokens": config.get("max_tokens", 4000),
                "temperature": config.get("temperature", 0.7)
            }
            
            # Add tools if provided
            tools = config.get("tools", [])
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"
                self.logger.info(f"🔧 Adding {len(tools)} tools to chat completion")
            
            self.logger.info(f"Making chat completions API call with model: {model}")
            self.logger.debug(f"API params: {api_params}")
            
            # Make the API call
            response = self.client.chat.completions.create(**api_params)
            
            self.logger.info(f"✅ Chat completion response received, type: {type(response)}")
            self.logger.debug(f"Response structure: {response}")
            
            # Extract response content and tool calls
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = message.tool_calls or []
            
            return {
                "success": True,
                "content": content,
                "reasoning": None,  # Chat completions doesn't have reasoning
                "metadata": {
                    "model": model,
                    "tool_calls": self._format_tool_calls_for_chat(tool_calls),
                    "usage": response.usage.model_dump() if response.usage else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Chat completions API error: {e}")
            raise
    
    def _create_responses_api(self, messages: List[Dict[str, str]], model: str, config: Dict) -> Dict[str, Any]:
        """Create response using responses API (for GPT-5 models)"""
        try:
            # Prepare input from messages
            input_data = []
            for msg in messages:
                input_data.append({
                    "type": "message",
                    "role": msg['role'],
                    "content": msg['content']
                })
            
            # Prepare API parameters
            api_params = {
                "model": model,
                "input": input_data,
                "text": config.get("text", {
                    "format": {"type": "text"},
                    "verbosity": "medium"
                }),
                "reasoning": config.get("reasoning", {
                    "effort": "medium",
                    "summary": "auto"
                }),
                "tools": config.get("tools", []),
                "store": config.get("store", True)
            }
            
            if "include" in config:
                api_params["include"] = config["include"]
            
            self.logger.info(f"Making responses API call with model: {model}")
            self.logger.debug(f"API params: {api_params}")
            
            # Make the API call
            response = self.client.responses.create(**api_params)
            
            self.logger.info(f"✅ Responses API response received, type: {type(response)}")
            self.logger.debug(f"Response structure: {response}")
            
            return {
                "success": True,
                "content": self._extract_content(response),
                "reasoning": self._extract_reasoning(response),
                "metadata": {
                    "model": model,
                    "reasoning_effort": config.get("reasoning", {}).get("effort", "medium"),
                    "tool_calls": self._extract_tool_calls(response)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Responses API error: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {"error": "Responses API call failed"}
            }
    
    def _extract_content(self, response) -> str:
        """Extract text content from GPT-5-mini response"""
        try:
            # GPT-5-mini returns Response object with output array
            if hasattr(response, 'output') and response.output:
                # Look for message type in output array
                for item in response.output:
                    if hasattr(item, 'type') and item.type == 'message':
                        if hasattr(item, 'content') and item.content:
                            # Content is an array of ResponseOutputText objects
                            for content_item in item.content:
                                if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                    return content_item.text
                                elif hasattr(content_item, 'text'):
                                    return content_item.text
            
            # Fallback: try other possible structures
            if hasattr(response, 'text') and hasattr(response.text, 'content'):
                return response.text.content
            elif hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            else:
                # Check if this response contains only tool calls (no text content)
                if hasattr(response, 'output') and response.output:
                    has_tool_calls = any(hasattr(item, 'type') and item.type == 'function_call' for item in response.output)
                    if has_tool_calls:
                        return "I'm executing the requested tools to help you."
                
                # Last resort: convert to string and try to extract readable content
                response_str = str(response)
                self.logger.warning(f"Using string fallback for response parsing")
                return response_str
                
        except Exception as e:
            self.logger.error(f"Could not extract content: {e}")
            # Return a more helpful error message
            return f"Error extracting response content: {e}"
    
    def _extract_reasoning(self, response) -> Optional[Dict]:
        """Extract reasoning information from GPT-5-mini response"""
        try:
            # Check for reasoning in output array
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == 'reasoning':
                        reasoning_data = {
                            "available": True,
                            "summary": None,
                            "encrypted_content": getattr(item, 'encrypted_content', None)
                        }
                        
                        # Extract summary if available
                        if hasattr(item, 'summary') and item.summary:
                            if isinstance(item.summary, list):
                                # Combine all summary texts
                                summary_texts = []
                                for summary_item in item.summary:
                                    if hasattr(summary_item, 'text'):
                                        summary_texts.append(summary_item.text)
                                reasoning_data["summary"] = "\n".join(summary_texts)
                            else:
                                reasoning_data["summary"] = str(item.summary)
                        
                        return reasoning_data
            
            # Fallback to direct reasoning attribute
            if hasattr(response, 'reasoning'):
                return {
                    "available": True,
                    "summary": getattr(response.reasoning, 'summary', None),
                    "encrypted_content": getattr(response.reasoning, 'encrypted_content', None)
                }
            return None
        except Exception as e:
            self.logger.warning(f"Could not extract reasoning: {e}")
            return None
    
    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from GPT-5-mini response"""
        try:
            tool_calls = []
            
            # GPT-5-mini responses structure: check for tool calls in output
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type'):
                        # Look for function_call type (actual GPT-5-mini format)
                        if item.type == 'function_call':
                            # Direct function call in responses API
                            arguments_str = getattr(item, 'arguments', '{}')
                            try:
                                # Parse JSON string arguments
                                import json
                                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
                            except:
                                arguments = arguments_str
                            
                            tool_calls.append({
                                'id': getattr(item, 'call_id', getattr(item, 'id', '')),
                                'name': getattr(item, 'name', ''),
                                'arguments': arguments
                            })
                        # Legacy format: tool_calls array
                        elif item.type == 'tool_calls' and hasattr(item, 'tool_calls'):
                            for tool_call in item.tool_calls:
                                if hasattr(tool_call, 'name'):
                                    tool_calls.append({
                                        'id': getattr(tool_call, 'id', ''),
                                        'name': tool_call.name,
                                        'arguments': getattr(tool_call, 'arguments', {})
                                    })
                                elif hasattr(tool_call, 'function'):
                                    # Fallback to function format
                                    tool_calls.append({
                                        'id': getattr(tool_call, 'id', ''),
                                        'name': tool_call.function.name,
                                        'arguments': tool_call.function.arguments if hasattr(tool_call.function, 'arguments') else {}
                                    })
            
            self.logger.info(f"Extracted {len(tool_calls)} tool calls from response")
            return tool_calls
            
        except Exception as e:
            self.logger.error(f"Could not extract tool calls: {e}")
            return []
    
    def _format_tool_calls_for_chat(self, tool_calls) -> List[Dict[str, Any]]:
        """Format tool calls from chat completions API to standard format"""
        formatted_calls = []
        try:
            for tool_call in tool_calls:
                formatted_call = {
                    'id': tool_call.id,
                    'name': tool_call.function.name,
                    'arguments': json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                }
                formatted_calls.append(formatted_call)
            return formatted_calls
        except Exception as e:
            self.logger.error(f"Could not format tool calls: {e}")
            return []
    
    def score_paper(self, paper_info: str) -> Dict[str, Any]:
        """Score a paper using optimized GPT-5-mini configuration"""
        messages = [
            {
                "role": "system",
                "content": "You are an expert research paper evaluator for a 2D materials physics laboratory."
            },
            {
                "role": "user", 
                "content": f"Rate this paper from 1-3 based on relevance:\n\n{paper_info}\n\nRespond with: Score: X, Reason: [brief explanation]"
            }
        ]
        
        return self.create_response(messages, use_case="paper_scoring")
    
    def chat_about_papers(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Chat about papers using enhanced reasoning configuration"""
        return self.create_response(messages, use_case="chat_conversation")
    
    def analyze_research(self, analysis_prompt: str) -> Dict[str, Any]:
        """Perform deep research analysis with high reasoning effort"""
        messages = [
            {
                "role": "system",
                "content": "You are an expert research analyst specializing in condensed matter physics and 2D materials."
            },
            {
                "role": "user",
                "content": analysis_prompt
            }
        ]
        
        return self.create_response(messages, use_case="research_analysis")
    
    def get_available_use_cases(self) -> List[str]:
        """Get list of available use case configurations"""
        return list(self.llm_config.get("use_cases", {}).keys())
    
    def get_use_case_info(self, use_case: str) -> Optional[Dict]:
        """Get information about a specific use case configuration"""
        return self.llm_config.get("use_cases", {}).get(use_case)