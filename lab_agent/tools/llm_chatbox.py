import json
import logging
import os
import asyncio
from typing import List, Dict, Optional, Any
from .llm_client import LLMClient
from ..utils.tool_manager import ToolManager


class LLMChatbox:
    """LLM chatbox for general assistance and MCP tool integration"""
    
    def __init__(self):
        self.logger = logging.getLogger("tools.llm_chatbox")
        self.client = LLMClient()
        self.config = self._load_config()
        self.conversation_history = []
        self.mcp_client = None
        self.available_tools = []
        
        # Initialize detailed conversation logging to file
        self._setup_conversation_logging()
        
        # Initialize MCP integration if enabled
        if self.config.get("mcp_integration", {}).get("enabled", False):
            self._initialize_mcp()
        
        # Initialize conversation with system prompt
        self._initialize_conversation()
    
    def _setup_conversation_logging(self):
        """Setup detailed conversation logging to file"""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Setup conversation logger that writes to file
        self.conversation_logger = logging.getLogger("conversation_trace")
        self.conversation_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.conversation_logger.handlers[:]:
            self.conversation_logger.removeHandler(handler)
        
        # File handler for detailed conversation logs
        log_file = os.path.join(logs_dir, "conversation_trace.log")
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.conversation_logger.addHandler(file_handler)
        
        # Prevent propagation to root logger to avoid console output
        self.conversation_logger.propagate = False
        
        self.conversation_logger.info("=" * 80)
        self.conversation_logger.info("NEW CHATBOX SESSION STARTED")
        self.conversation_logger.info("=" * 80)
    
    def _log_conversation_state(self, context: str):
        """Log the current state of conversation history"""
        self.conversation_logger.info(f"CONVERSATION STATE - {context}")
        self.conversation_logger.info(f"Total messages: {len(self.conversation_history)}")
        
        for i, msg in enumerate(self.conversation_history):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            content_preview = content[:100].replace('\n', ' ') + ('...' if len(content) > 100 else '')
            
            extra_info = ""
            if 'tool_calls' in msg:
                extra_info = f" [HAS TOOL_CALLS: {len(msg['tool_calls'])}]"
            elif 'tool_call_id' in msg:
                extra_info = f" [TOOL_RESULT for {msg['tool_call_id']}]"
            
            self.conversation_logger.info(f"  [{i}] {role.upper()}: {content_preview}{extra_info}")
        
        self.conversation_logger.info("-" * 50)
    
    async def _handle_iterative_tool_calling(self, initial_result: Dict, config: Dict, tool_call_results: List) -> str:
        """Handle multiple rounds of tool calls until LLM provides final response"""
        current_result = initial_result
        api_call_count = 1
        
        # Get max iterations from config (default to 20)
        max_iterations = self.config.get("conversation_settings", {}).get("max_tool_call_iterations", 20)
        self.conversation_logger.info(f"MAX TOOL CALL ITERATIONS SET TO: {max_iterations}")
        
        while api_call_count <= max_iterations:
            tool_calls = current_result.get('metadata', {}).get('tool_calls', [])
            if not tool_calls:
                # No more tool calls - this is the final response
                final_content = current_result.get('content', '')
                self.conversation_logger.info(f"FINAL RESPONSE AFTER {api_call_count} API CALLS - Length: {len(final_content)} chars")
                
                # Add final assistant response to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_content
                })
                return final_content
            
            self.logger.info(f"Executing {len(tool_calls)} tool calls (round {api_call_count})")
            self.conversation_logger.info(f"API CALL #{api_call_count} TOOL CALLS: {len(tool_calls)} tools")
            for i, tc in enumerate(tool_calls):
                tool_name = tc.get('name') or tc.get('function', {}).get('name')
                self.conversation_logger.info(f"  Tool {i+1}: {tool_name}")
            
            # STEP 1: Add assistant message with tool calls to conversation history
            assistant_message = {
                "role": "assistant",
                "content": current_result.get('content', '')
            }
            
            # Add tool calls to assistant message (for proper OpenAI format)
            if tool_calls:
                formatted_tool_calls = []
                for tool_call in tool_calls:
                    # Handle different formats from responses API vs chat completions
                    if 'function' in tool_call:
                        formatted_tool_calls.append(tool_call)
                    else:
                        formatted_tool_calls.append({
                            "id": tool_call.get('id', f"call_{len(formatted_tool_calls)}"),
                            "type": "function",
                            "function": {
                                "name": tool_call.get('name'),
                                "arguments": json.dumps(tool_call.get('arguments', {}))
                            }
                        })
                assistant_message["tool_calls"] = formatted_tool_calls
            
            self.conversation_history.append(assistant_message)
            self.conversation_logger.info(f"ADDED ASSISTANT MESSAGE #{api_call_count} WITH TOOL CALLS")
            
            # STEP 2: Execute tools and add results as "tool" role messages
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name')
                tool_args = tool_call.get('arguments', {}) or tool_call.get('function', {}).get('arguments', {})
                tool_call_id = tool_call.get('id') or f"call_{i}"
                
                if tool_name:
                    self.logger.info(f"Executing {tool_name}")
                    self.conversation_logger.info(f"EXECUTING TOOL #{api_call_count}: {tool_name} with args: {tool_args}")
                    tool_result = await self._execute_tool_call(tool_name, tool_args)
                    self.conversation_logger.info(f"TOOL RESULT #{api_call_count}: Success={tool_result.get('success')}, Message={tool_result.get('message', 'No message')}")
                    
                    # Store results for UI display
                    tool_call_results.append({
                        'tool_name': tool_name,
                        'arguments': tool_args,
                        'result': tool_result
                    })
                    
                    # Store detailed results for collapsible display in UI
                    if not hasattr(self, '_tool_results'):
                        self._tool_results = []
                    
                    if tool_result.get('success'):
                        self._tool_results.append({
                            'tool_name': tool_name,
                            'summary': tool_result.get('message', 'Tool executed successfully'),
                            'data': tool_result.get('data', {}),
                            'success': True
                        })
                        tool_result_content = self._format_tool_result_for_gpt(tool_result)
                    else:
                        self._tool_results.append({
                            'tool_name': tool_name,
                            'summary': f"Tool failed: {tool_result.get('error', 'Unknown error')}",
                            'data': {},
                            'success': False
                        })
                        tool_result_content = f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"
                    
                    # Add tool result to conversation history (OpenAI standard)
                    self.conversation_history.append({
                        "role": "tool",
                        "content": tool_result_content,
                        "tool_call_id": tool_call_id
                    })
            
            # STEP 3: Add user message to prompt GPT to continue
            self.conversation_history.append({
                "role": "user",
                "content": "Continue with the analysis. If you need to call more tools to complete the user's request, do so. If the analysis is complete, provide your final response."
            })
            self.conversation_logger.info(f"ADDED USER CONTINUE MESSAGE AFTER API CALL #{api_call_count}")
            self._log_conversation_state(f"After tool execution round {api_call_count}")
            
            # STEP 4: Make next API call
            api_call_count += 1
            self.logger.info(f"Making API call #{api_call_count}")
            self.conversation_logger.info(f"MAKING API CALL #{api_call_count}")
            
            current_result = self.client.create_response(
                messages=self.conversation_history,
                use_case=config.get("purpose", "general_assistant"),
                custom_config=config
            )
            
            # Log API call result
            self.conversation_logger.info(f"API CALL #{api_call_count} RESULT:")
            self.conversation_logger.info(f"  Success: {current_result.get('success')}")
            self.conversation_logger.info(f"  Content length: {len(current_result.get('content', ''))}")
            self.conversation_logger.info(f"  Has tool calls: {bool(current_result.get('metadata', {}).get('tool_calls'))}")
            
            if not current_result.get('success'):
                # API call failed
                error_msg = f"API call #{api_call_count} failed: {current_result.get('error', 'Unknown error')}"
                self.conversation_logger.info(f"ERROR: {error_msg}")
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"I executed tools successfully, but encountered an error in follow-up processing: {current_result.get('error', 'Unknown error')}"
                })
                return f"Tool execution completed, but processing error occurred: {current_result.get('error', 'Unknown error')}"
        
        # Max iterations reached
        self.conversation_logger.info(f"MAX ITERATIONS ({max_iterations}) REACHED - Stopping tool calling loop")
        final_content = f"Completed tool execution after {max_iterations} rounds, but the analysis workflow is still requesting more tools. Please check the tool results above."
        self.conversation_history.append({
            "role": "assistant",
            "content": final_content
        })
        return final_content
    
    def _load_config(self) -> Dict:
        """Load chatbox configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'llm_chatbox_config.json'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Chatbox config not found at {config_path}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration if config file is missing"""
        return {
            "purpose": "general_assistant",
            "config": {
                "text": {"format": {"type": "text"}, "verbosity": "high"},
                "reasoning": {"effort": "medium", "summary": "auto"},
                "tools": [],
                "store": True,
                "include": ["reasoning.encrypted_content"]
            },
            "system_prompt": "You are a helpful AI assistant for laboratory management.",
            "conversation_settings": {
                "max_exchanges": 50,
                "context_window": 10,
                "enable_reasoning_display": True
            },
            "ui_settings": {
                "title": "AI Assistant",
                "placeholder_text": "Ask me anything...",
                "suggested_prompts": ["Help me with research questions"]
            }
        }
    
    def _initialize_mcp(self):
        """Initialize MCP client and tools"""
        try:
            # Import MCP client here to avoid circular imports
            from ..mcp.client import get_mcp_client
            
            self.mcp_client = get_mcp_client()
            self.logger.info("MCP client initialized")
            
            # Start MCP connection in background
            # Note: In production, this should be handled by the web app
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client: {e}")
            self.mcp_client = None
    
    def _initialize_conversation(self):
        """Initialize conversation with system prompt"""
        system_prompt = self.config.get("system_prompt", "You are a helpful AI assistant.")
        
        # Add MCP tools information to system prompt if available
        if self.mcp_client and self.config.get("mcp_integration", {}).get("enabled", False):
            tools_info = self._get_tools_context()
            enhanced_prompt = f"{system_prompt}\n\n{tools_info}"
        else:
            enhanced_prompt = system_prompt
        
        self.conversation_history = [
            {
                "role": "system",
                "content": enhanced_prompt
            }
        ]
    
    def _get_tools_context(self) -> str:
        """Get MCP tools context for system prompt"""
        mcp_config = self.config.get("mcp_integration", {})
        
        tools_context = """
## Available Tools

You have access to the following MCP tools for ArXiv Daily reports:

"""
        
        # Add active ArXiv Daily tools
        arxiv_tools = mcp_config.get("arxiv_daily_tools", [])
        if arxiv_tools:
            tools_context += "### ArXiv Daily Tools (Active)\n"
            for tool in arxiv_tools:
                if tool.get("status") == "active":
                    tools_context += f"- **{tool['name']}**: {tool['description']}\n"
            tools_context += "\n"
        
        # Add usage instructions
        tools_context += """### Tool Usage
When users ask about ArXiv papers, reports, or want to generate new reports, you can:
- Use `read_daily_report` to read existing reports and provide analysis
- Use `generate_daily_report` to create new daily reports
- Use `list_available_reports` to show available reports

Always provide helpful context and summaries when using these tools.
"""
        
        return tools_context
    
    def _prepare_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Prepare MCP tools for LLM API"""
        if not self.mcp_client:
            return []
        
        llm_tools = []
        
        # Get available tools from MCP client
        available_tools = self.mcp_client.get_available_tools()
        
        # Check what model we're using to format tools correctly
        model = self.config.get("model", "gpt-4.1")
        
        for tool in available_tools:
            if model.startswith("gpt-5"):
                # Responses API format (simpler format)
                llm_tool = {
                    "type": "function",
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            else:
                # Chat completions API format (nested function format) - for GPT-4.1
                llm_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool.get("inputSchema", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                }
            llm_tools.append(llm_tool)
        
        return llm_tools
    
    async def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool call"""
        if not self.mcp_client:
            return {
                "success": False,
                "error": "MCP client not available"
            }
        
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Send a message to GPT-5-mini and get response"""
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Log user message
            self.conversation_logger.info(f"USER MESSAGE: {user_message}")
            self._log_conversation_state("After adding user message")
            
            # Prepare custom config with tools if MCP is enabled
            custom_config = self.config.get("config", {}).copy()
            
            if self.mcp_client and self.config.get("mcp_integration", {}).get("enabled", False):
                # Add MCP tools to the config
                mcp_tools = self._prepare_tools_for_llm()
                if mcp_tools:
                    custom_config["tools"] = mcp_tools
                    # Extract tool names for logging (handle both formats)
                    tool_names = []
                    for t in mcp_tools:
                        if 'function' in t:
                            tool_names.append(t['function']['name'])
                        else:
                            tool_names.append(t['name'])
                    self.logger.info(f"🔧 Added {len(mcp_tools)} tools to LLM request: {tool_names}")
                else:
                    self.logger.warning("⚠️  No MCP tools available to add to request")
            
            # Log API call details
            self.conversation_logger.info(f"MAKING API CALL #1 - Model: {custom_config.get('model', 'default')}")
            self.conversation_logger.info(f"Tools available: {len(custom_config.get('tools', []))}")
            
            # Create response using LLM client
            result = self.client.create_response(
                messages=self.conversation_history,
                use_case=self.config.get("purpose", "general_assistant"),
                custom_config=custom_config
            )
            
            # Log API response
            self.conversation_logger.info(f"API CALL #1 RESPONSE - Success: {result['success']}")
            if result['success']:
                self.conversation_logger.info(f"Content: {result['content'][:200]}...")
                self.conversation_logger.info(f"Tool calls detected: {bool(result.get('metadata', {}).get('tool_calls'))}")
            
            if result['success']:
                # Handle tool calls using proper OpenAI pattern
                response_content = result['content']
                tool_call_results = []
                
                # Look for tool calls in the response metadata
                self.logger.info(f"Response received, tool calls: {bool(result.get('metadata', {}).get('tool_calls'))}")
                
                if result.get('metadata') and result['metadata'].get('tool_calls'):
                    # Handle iterative tool calling until no more tool calls are made
                    response_content = await self._handle_iterative_tool_calling(
                        result, custom_config, tool_call_results
                    )
                else:
                    # No tool calls - direct response from LLM
                    self.logger.info(f"ℹ️ Direct response from LLM (no tool calls)")
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response_content
                    })
                
                # Keep conversation history manageable
                self._trim_conversation_history()
                self._log_conversation_state("Final conversation state")
                
                # Get tool results and reset for next conversation
                current_tool_results = getattr(self, '_tool_results', [])
                self._tool_results = []  # Reset for next conversation
                
                # Log successful completion
                self.conversation_logger.info(f"CHAT COMPLETED SUCCESSFULLY - Response length: {len(response_content)} chars")
                self.conversation_logger.info("=" * 50)
                
                return {
                    "success": True,
                    "response": response_content,
                    "reasoning": result.get('reasoning'),
                    "metadata": result.get('metadata', {}),
                    "tool_calls": tool_call_results,
                    "tool_results": current_tool_results,
                    "conversation_length": len(self.conversation_history) - 1  # Exclude system message
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "response": f"Error: {result.get('error', 'Unknown error')}",
                    "reasoning": None,
                    "metadata": {}
                }
                
        except Exception as e:
            import traceback
            self.logger.error(f"Chat error: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Error: {e}",
                "reasoning": None,
                "metadata": {}
            }
    
    def _trim_conversation_history(self):
        """Keep conversation history within limits"""
        max_exchanges = self.config.get("conversation_settings", {}).get("max_exchanges", 50)
        context_window = self.config.get("conversation_settings", {}).get("context_window", 10)
        
        # Keep system message + last N exchanges (each exchange = user + assistant message)
        if len(self.conversation_history) > 1 + (context_window * 2):
            # Keep system message + last context_window exchanges
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-(context_window * 2):]
    
    def clear_conversation(self):
        """Clear conversation history and start fresh"""
        self._initialize_conversation()
        self.logger.info("Conversation history cleared")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation"""
        # Exclude system message from count
        message_count = len(self.conversation_history) - 1
        exchanges = message_count // 2
        
        return {
            "total_messages": message_count,
            "total_exchanges": exchanges,
            "conversation_active": exchanges > 0,
            "max_exchanges": self.config.get("conversation_settings", {}).get("max_exchanges", 50)
        }
    
    def get_suggested_prompts(self) -> List[str]:
        """Get suggested prompts for the user"""
        return self.config.get("ui_settings", {}).get("suggested_prompts", [
            "Help me with research questions",
            "Explain scientific concepts",
            "Suggest lab improvements"
        ])
    
    def get_ui_config(self) -> Dict[str, str]:
        """Get UI configuration"""
        ui_settings = self.config.get("ui_settings", {})
        return {
            "title": ui_settings.get("title", "AI Assistant"),
            "subtitle": ui_settings.get("subtitle", "AI Assistant"),
            "placeholder_text": ui_settings.get("placeholder_text", "Ask me anything...")
        }
    
    def get_mcp_tools_info(self) -> Dict[str, Any]:
        """Get information about MCP tools (only show activated tools)"""
        mcp_config = self.config.get("mcp_integration", {})
        enabled = mcp_config.get("enabled", False)
        
        if enabled:
            # Check activation status using ToolManager
            tool_manager = ToolManager()
            
            # Only include tools that are currently activated
            arxiv_tools = []
            flake_tools = []
            
            if tool_manager.is_tool_active("arxiv_daily"):
                arxiv_tools = mcp_config.get("arxiv_daily_tools", [])
            
            if tool_manager.is_tool_active("flake_2d"):
                flake_tools = mcp_config.get("flake_2d_tools", [])
            
            planned_tools = mcp_config.get("planned_tools", [])
            
            # Combine active tools from both categories
            all_active_tools = []
            
            # Add ArXiv tools with category label (only if activated)
            for tool in arxiv_tools:
                tool_with_category = tool.copy()
                tool_with_category["category"] = "ArXiv Daily"
                all_active_tools.append(tool_with_category)
            
            # Add 2D flake tools with category label (only if activated)
            for tool in flake_tools:
                tool_with_category = tool.copy()
                tool_with_category["category"] = "2D Flake Classification"
                all_active_tools.append(tool_with_category)
            
            # Build status message based on actually active tools
            status_parts = []
            if arxiv_tools:
                status_parts.append(f"{len(arxiv_tools)} ArXiv Daily tools")
            if flake_tools:
                status_parts.append(f"{len(flake_tools)} 2D Flake tools")
            
            if status_parts:
                status = f"MCP integration active with {' and '.join(status_parts)}"
            else:
                status = "MCP integration enabled but no tools are activated"
            
            # Get activation summary for additional info
            activation_summary = tool_manager.get_activation_summary()
            
            return {
                "enabled": True,
                "active_tools": all_active_tools,
                "arxiv_tools": arxiv_tools,
                "flake_2d_tools": flake_tools,
                "planned_tools": planned_tools,
                "status": status,
                "mcp_client_available": self.mcp_client is not None,
                "activation_summary": activation_summary
            }
        else:
            return {
                "enabled": False,
                "active_tools": [],
                "arxiv_tools": [],
                "flake_2d_tools": [],
                "planned_tools": mcp_config.get("planned_tools", []),
                "status": "MCP integration disabled"
            }
    
    def enable_reasoning_display(self) -> bool:
        """Check if reasoning display is enabled"""
        return self.config.get("conversation_settings", {}).get("enable_reasoning_display", True)
    
    def _format_tool_result_for_gpt(self, tool_result: Dict[str, Any]) -> str:
        """Format tool result data for GPT-5-mini to analyze"""
        if not tool_result.get('success'):
            return f"Tool execution failed: {tool_result.get('error', 'Unknown error')}"
        
        # Get the data from the tool result
        data = tool_result.get('data', {})
        message = tool_result.get('message', 'Tool executed successfully')
        
        # Format the content for GPT-5-mini analysis
        content_parts = [f"Tool Result: {message}"]
        
        if isinstance(data, dict):
            # Format different types of data
            for key, value in data.items():
                if key == 'high_priority_papers' and isinstance(value, list):
                    content_parts.append(f"\nHigh Priority Papers ({len(value)} papers):")
                    for i, paper in enumerate(value, 1):
                        if isinstance(paper, dict):
                            title = paper.get('title', 'N/A')
                            authors = paper.get('authors', 'N/A') 
                            abstract = paper.get('abstract', 'N/A')[:200] + "..." if len(paper.get('abstract', '')) > 200 else paper.get('abstract', 'N/A')
                            reason = paper.get('ai_assessment', 'N/A')
                            
                            content_parts.append(f"\n{i}. Title: {title}")
                            content_parts.append(f"   Authors: {authors}")
                            content_parts.append(f"   Abstract: {abstract}")
                            content_parts.append(f"   AI Assessment: {reason}")
                
                elif key == 'search_results' and isinstance(value, dict):
                    # Handle search results from search_papers_by_author
                    matching_papers = value.get('matching_papers', [])
                    total_searched = value.get('total_papers_searched', 0)
                    content_parts.append(f"\nAuthor Search Results:")
                    content_parts.append(f"Papers searched: {total_searched}")
                    content_parts.append(f"Papers found: {len(matching_papers)}")
                    
                    if matching_papers:
                        content_parts.append(f"\nMatching Papers:")
                        for i, paper in enumerate(matching_papers, 1):
                            if isinstance(paper, dict):
                                title = paper.get('title', 'N/A')
                                authors = paper.get('authors', 'N/A')
                                abstract = paper.get('abstract', 'N/A')[:200] + "..." if len(paper.get('abstract', '')) > 200 else paper.get('abstract', 'N/A')
                                priority = paper.get('priority', 'N/A')
                                reason = paper.get('ai_assessment', 'N/A')
                                
                                content_parts.append(f"\n{i}. Title: {title}")
                                content_parts.append(f"   Authors: {authors}")
                                content_parts.append(f"   Priority: {priority}")
                                content_parts.append(f"   Abstract: {abstract}")
                                content_parts.append(f"   AI Assessment: {reason}")
                
                elif key == 'search_query' and isinstance(value, dict):
                    # Handle search query info
                    author_name = value.get('author_name', 'N/A')
                    match_type = value.get('match_type', 'N/A')
                    date = value.get('date', 'N/A')
                    content_parts.append(f"\nSearch Query:")
                    content_parts.append(f"Author: {author_name}")
                    content_parts.append(f"Match Type: {match_type}")
                    content_parts.append(f"Report Date: {date}")
                
                elif key == 'reports' and isinstance(value, list):
                    content_parts.append(f"\nAvailable Reports ({len(value)} reports):")
                    for report in value:
                        if isinstance(report, dict):
                            date = report.get('date', 'N/A')
                            total = report.get('total_papers', 0)
                            priority_3 = report.get('priority_3_count', 0)
                            content_parts.append(f"- {date}: {total} papers ({priority_3} high priority)")
                
                elif key == 'summary' and isinstance(value, dict):
                    content_parts.append(f"\nSummary:")
                    for summary_key, summary_value in value.items():
                        formatted_key = summary_key.replace('_', ' ').title()
                        content_parts.append(f"- {formatted_key}: {summary_value}")
                
                else:
                    # Generic formatting for other data types
                    if isinstance(value, (dict, list)):
                        content_parts.append(f"\n{key.replace('_', ' ').title()}: {str(value)}")
                    else:
                        content_parts.append(f"\n{key.replace('_', ' ').title()}: {value}")
        
        elif isinstance(data, list):
            content_parts.append(f"\nData ({len(data)} items): {str(data)}")
        else:
            content_parts.append(f"\nData: {str(data)}")
        
        return '\n'.join(content_parts)