import json
import logging
import os
import asyncio
from typing import List, Dict, Optional, Any
from .gpt5_mini_client import GPT5MiniClient
from ..utils.tool_manager import ToolManager


class GPT5MiniChatbox:
    """GPT-5-mini chatbox for general assistance and future MCP tool integration"""
    
    def __init__(self):
        self.logger = logging.getLogger("tools.gpt5_mini_chatbox")
        self.client = GPT5MiniClient()
        self.config = self._load_config()
        self.conversation_history = []
        self.mcp_client = None
        self.available_tools = []
        
        # Initialize MCP integration if enabled
        if self.config.get("mcp_integration", {}).get("enabled", False):
            self._initialize_mcp()
        
        # Initialize conversation with system prompt
        self._initialize_conversation()
    
    def _load_config(self) -> Dict:
        """Load chatbox configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'gpt5_mini_chatbox_config.json'
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
    
    def _prepare_tools_for_gpt5mini(self) -> List[Dict[str, Any]]:
        """Prepare MCP tools for GPT-5-mini responses API"""
        if not self.mcp_client:
            return []
        
        gpt5_tools = []
        
        # Get available tools from MCP client
        available_tools = self.mcp_client.get_available_tools()
        
        for tool in available_tools:
            # GPT-5-mini responses API format
            gpt5_tool = {
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
            gpt5_tools.append(gpt5_tool)
        
        return gpt5_tools
    
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
            
            # Prepare custom config with tools if MCP is enabled
            custom_config = self.config.get("config", {}).copy()
            
            if self.mcp_client and self.config.get("mcp_integration", {}).get("enabled", False):
                # Add MCP tools to the config
                mcp_tools = self._prepare_tools_for_gpt5mini()
                if mcp_tools:
                    custom_config["tools"] = mcp_tools
                    self.logger.info(f"🔧 Added {len(mcp_tools)} tools to GPT-5-mini request: {[t['name'] for t in mcp_tools]}")
                else:
                    self.logger.warning("⚠️  No MCP tools available to add to request")
            
            # Create response using GPT-5-mini client
            result = self.client.create_response(
                messages=self.conversation_history,
                use_case=self.config.get("purpose", "general_assistant"),
                custom_config=custom_config
            )
            
            if result['success']:
                # Check if GPT-5-mini made tool calls
                response_content = result['content']
                tool_call_results = []
                
                # Look for tool calls in the response metadata
                if result.get('metadata') and result['metadata'].get('tool_calls'):
                    self.logger.info(f"🔧 GPT-5-mini made tool calls: {result['metadata']['tool_calls']}")
                    
                    # Execute each tool call and collect results for follow-up
                    tool_results_for_followup = []
                    
                    for tool_call in result['metadata']['tool_calls']:
                        # Try both formats: responses API and standard format
                        tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name')
                        tool_args = tool_call.get('arguments', {}) or tool_call.get('function', {}).get('arguments', {})
                        
                        if tool_name:
                            self.logger.info(f"🚀 Executing tool call: {tool_name}")
                            tool_result = await self._execute_tool_call(tool_name, tool_args)
                            tool_call_results.append({
                                'tool_name': tool_name,
                                'arguments': tool_args,
                                'result': tool_result
                            })
                            
                            if tool_result.get('success'):
                                # Format tool result as collapsible section
                                result_summary = tool_result.get('message', 'Tool executed successfully')
                                result_data = tool_result.get('data', {})
                                
                                # Store detailed results for collapsible display
                                if not hasattr(self, '_tool_results'):
                                    self._tool_results = []
                                
                                self._tool_results.append({
                                    'tool_name': tool_name,
                                    'summary': result_summary,
                                    'data': result_data,
                                    'success': True
                                })
                                
                                # Prepare tool result for follow-up call to GPT-5-mini
                                tool_results_for_followup.append({
                                    'tool_call_id': tool_call.get('id', ''),
                                    'name': tool_name,
                                    'content': self._format_tool_result_for_gpt(tool_result)
                                })
                    
                    # If we have tool results, make a follow-up call to GPT-5-mini with the results
                    if tool_results_for_followup:
                        self.logger.info(f"📤 Sending tool results back to GPT-5-mini for analysis")
                        
                        # Add tool results as user messages for GPT-5-mini (doesn't support tool role)
                        tool_results_content = []
                        for tool_result in tool_results_for_followup:
                            tool_results_content.append(f"**{tool_result['name']} Result:**\n{tool_result['content']}")
                        
                        # Combine all tool results into a single user message
                        combined_tool_results = "\n\n".join(tool_results_content)
                        self.conversation_history.append({
                            "role": "user",
                            "content": f"Here are the results from the tools you called. Please analyze them and answer the original question:\n\n{combined_tool_results}"
                        })
                        
                        # Make follow-up call to get GPT-5-mini's analysis of the tool results
                        followup_config = self.config.get("config", {}).copy()
                        # Don't include tools in follow-up call to avoid infinite loops
                        followup_config.pop("tools", None)
                        
                        followup_result = self.client.create_response(
                            messages=self.conversation_history,
                            use_case=self.config.get("purpose", "general_assistant"),
                            custom_config=followup_config
                        )
                        
                        if followup_result['success']:
                            # Replace the initial response with the analyzed response
                            response_content = followup_result['content']
                        else:
                            # If follow-up fails, show brief summary
                            response_content += f"\n\n✅ Executed {len(tool_results_for_followup)} tools successfully (analysis unavailable)"
                
                # Add the final assistant response to history (either original or analyzed)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_content
                })
                
                # Keep conversation history manageable
                self._trim_conversation_history()
                
                # Get tool results and reset for next conversation
                current_tool_results = getattr(self, '_tool_results', [])
                self._tool_results = []  # Reset for next conversation
                
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