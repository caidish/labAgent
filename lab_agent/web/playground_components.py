"""
Playground UI Components - Streamlit components for the model playground
"""

import streamlit as st
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime
from ..playground import get_model_caps, get_available_models, REASONING_EFFORT_OPTIONS, VERBOSITY_OPTIONS
from ..playground import MCPManager, PlaygroundClient, get_supported_reasoning_efforts, supports_temperature_top_p


class PlaygroundUI:
    """Main UI component for the model playground"""
    
    def __init__(self):
        self.mcp_manager = MCPManager()
        self.playground_client = PlaygroundClient()
        self._session_initialized = False
    
    def _ensure_session_initialized(self):
        """Ensure session state is initialized (lazy initialization)"""
        if self._session_initialized:
            return
            
        try:
            self._init_session_state()
            self._session_initialized = True
        except Exception as e:
            # If session state initialization fails, continue without it
            # This prevents crashes during startup
            pass
    
    def _init_session_state(self):
        """Initialize Streamlit session state for playground"""
        # Initialize messages with validation
        if "playground_messages" not in st.session_state:
            st.session_state.playground_messages = []
        elif not isinstance(st.session_state.playground_messages, list):
            # Recovery: reset corrupted messages
            st.session_state.playground_messages = []
        
        # Initialize tool calls
        if "playground_tool_calls" not in st.session_state:
            st.session_state.playground_tool_calls = []
        elif not isinstance(st.session_state.playground_tool_calls, list):
            st.session_state.playground_tool_calls = []
        
        # Initialize selected model
        if "playground_selected_model" not in st.session_state:
            st.session_state.playground_selected_model = "gpt-4.1"
        
        # Initialize selected servers  
        if "playground_selected_servers" not in st.session_state:
            st.session_state.playground_selected_servers = ["arxiv_daily"]
        elif not isinstance(st.session_state.playground_selected_servers, list):
            st.session_state.playground_selected_servers = ["arxiv_daily"]
        
        # Initialize conversation metadata
        if "playground_conversation_metadata" not in st.session_state:
            st.session_state.playground_conversation_metadata = {
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0,
                "session_id": str(hash(datetime.now().isoformat()))[:8]
            }
    
    def render_model_selector(self) -> str:
        """Render model selection UI"""
        self._ensure_session_initialized()
        st.subheader("🤖 Model Configuration")
        
        available_models = get_available_models()
        model_options = list(available_models.keys())
        model_display_names = [available_models[key].display_name for key in model_options]
        
        selected_index = 0
        if st.session_state.playground_selected_model in model_options:
            selected_index = model_options.index(st.session_state.playground_selected_model)
        
        selected_index = st.selectbox(
            "Select Model",
            range(len(model_options)),
            format_func=lambda x: model_display_names[x],
            index=selected_index,
            help="Choose which AI model to use for the conversation"
        )
        
        selected_model = model_options[selected_index]
        st.session_state.playground_selected_model = selected_model
        
        # Display model info
        model_caps = available_models[selected_model]
        st.info(f"**{model_caps.display_name}**\n\n{model_caps.description}")
        
        return selected_model
    
    def render_model_parameters(self, model: str) -> Dict[str, Any]:
        """Render model-specific parameter controls"""
        st.subheader("⚙️ Parameters")
        
        caps = get_model_caps(model)
        if not caps:
            st.error(f"Unknown model: {model}")
            return {}
        
        config = {}
        
        # Check if this is a reasoning model
        is_reasoning = caps.supports.uses_completion_tokens
        
        if is_reasoning:
            # Reasoning model - show reasoning controls
            st.info("🧠 **Reasoning Model**: This model uses specialized reasoning parameters instead of temperature/top-p")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Reasoning effort (for reasoning models)
                if caps.supports.reasoning_effort:
                    supported_efforts = get_supported_reasoning_efforts(model)
                    default_effort = caps.defaults.reasoning_effort or "medium"
                    config["reasoning_effort"] = st.selectbox(
                        "Reasoning Effort",
                        supported_efforts,
                        index=supported_efforts.index(default_effort) if default_effort in supported_efforts else 0,
                        help="How much computational effort to spend on reasoning. Higher effort = better results but slower."
                    )
                
                # Token limit for reasoning models
                if caps.defaults.max_completion_tokens:
                    config["max_completion_tokens"] = st.slider(
                        "Max Completion Tokens",
                        min_value=100,
                        max_value=caps.defaults.max_completion_tokens * 2,
                        value=caps.defaults.max_completion_tokens,
                        step=100,
                        help="Maximum tokens for the model's response"
                    )
            
            with col2:
                # Verbosity (for GPT-5)
                if caps.supports.verbosity:
                    config["verbosity"] = st.selectbox(
                        "Verbosity", 
                        VERBOSITY_OPTIONS,
                        index=VERBOSITY_OPTIONS.index(caps.defaults.verbosity or "medium"),
                        help="How detailed the response should be"
                    )
        else:
            # Chat model - show traditional controls
            col1, col2 = st.columns(2)
            
            with col1:
                config["temperature"] = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=caps.defaults.temperature or 0.2,
                    step=0.1,
                    help="Controls randomness in responses. Lower = more focused, Higher = more creative"
                )
                
                # Token limit for chat models
                if caps.defaults.max_tokens:
                    config["max_tokens"] = st.slider(
                        "Max Tokens",
                        min_value=100,
                        max_value=caps.defaults.max_tokens * 2,
                        value=caps.defaults.max_tokens,
                        step=100,
                        help="Maximum tokens for the model's response"
                    )
            
            with col2:
                config["top_p"] = st.slider(
                    "Top-p",
                    min_value=0.0,
                    max_value=1.0,
                    value=caps.defaults.top_p or 1.0,
                    step=0.05,
                    help="Controls diversity via nucleus sampling"
                )
        
        return config
    
    def render_server_selector(self) -> List[str]:
        """Render MCP server selection UI"""
        self._ensure_session_initialized()
        st.subheader("🔧 MCP Servers")
        
        available_servers = self.mcp_manager.get_available_servers()
        
        # Build mappings between server IDs and display names
        server_options = []
        name_to_id = {}
        id_to_name = {}
        
        for server_id, config in available_servers.items():
            if config.get("enabled", True):
                display_name = f"{config.get('name', server_id)} ({config.get('category', 'general')})"
                server_options.append(display_name)
                name_to_id[display_name] = server_id
                id_to_name[server_id] = display_name
        
        if not server_options:
            st.warning("No MCP servers available")
            return []
        
        # Initialize or clean up session state for display names
        if "playground_server_display_names" not in st.session_state:
            # Convert current server IDs to display names for initial state
            default_display_names = []
            for server_id in st.session_state.playground_selected_servers:
                if server_id in id_to_name:
                    default_display_names.append(id_to_name[server_id])
            st.session_state.playground_server_display_names = default_display_names
        else:
            # Clean up any stale display names that no longer exist
            current_names = st.session_state.playground_server_display_names
            valid_names = [name for name in current_names if name in name_to_id]
            if len(valid_names) != len(current_names):
                st.session_state.playground_server_display_names = valid_names
        
        # Use direct session state binding for multiselect
        selected_display_names = st.multiselect(
            "Select MCP Servers",
            server_options,
            help="Choose which MCP servers to make available for tool calling",
            key="playground_server_display_names"
        )
        
        # Convert display names back to server IDs and update session state
        selected_servers = [name_to_id[name] for name in selected_display_names if name in name_to_id]
        st.session_state.playground_selected_servers = selected_servers
        
        # Show immediate feedback on selection changes
        if len(selected_servers) != len(selected_display_names):
            st.warning("⚠️ Some selected servers are no longer available")
        elif selected_servers:
            server_count = len(selected_servers)
            if server_count == 1:
                st.success(f"✅ {selected_servers[0]} selected")
            elif server_count <= 3:
                st.success(f"✅ {server_count} servers selected: {', '.join(selected_servers)}")
            else:
                st.success(f"✅ {server_count} servers selected: {', '.join(selected_servers[:2])}, and {server_count - 2} more")
        else:
            st.info("ℹ️ No servers selected - tool calling will be unavailable")
        
        # Show server status
        if selected_servers:
            with st.expander("🔍 Server Status", expanded=False):
                for server_id in selected_servers:
                    status = self.mcp_manager.check_server_health(server_id)
                    if status["status"] == "healthy":
                        st.success(f"✅ {server_id}: {status.get('tool_count', 0)} tools")
                    elif status["status"] == "planned":
                        st.info(f"📋 {server_id}: {status.get('message', 'Planned')}")
                    else:
                        st.error(f"❌ {server_id}: {status.get('error', 'Unknown error')}")
        
        return selected_servers
    
    def render_tool_controls(self):
        """Render tool-related controls"""
        st.subheader("🛠️ Tool Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_iterations = st.slider(
                "Max Tool Iterations",
                min_value=1,
                max_value=20,
                value=10,
                help="Maximum number of recursive tool calls"
            )
            # Note: max_iterations will be passed to playground_client when needed
        
        with col2:
            show_tool_details = st.checkbox(
                "Show Tool Details",
                value=True,
                help="Display detailed information about tool calls"
            )
        
        # Add collapsible message settings
        with st.expander("💬 Message Display Settings", expanded=False):
            collapse_threshold = st.slider(
                "Auto-collapse threshold (characters)",
                min_value=200,
                max_value=2000,
                value=800,
                step=100,
                help="Messages longer than this will be automatically collapsed"
            )
            
            show_character_count = st.checkbox(
                "Show character count for long messages",
                value=True,
                help="Display character count indicator for collapsed messages"
            )
        
        return {
            "max_iterations": max_iterations,
            "show_tool_details": show_tool_details,
            "collapse_threshold": collapse_threshold,
            "show_character_count": show_character_count
        }
    
    def render_chat_interface(self, model: str, config: Dict[str, Any], selected_servers: List[str], tool_settings: Dict[str, Any]):
        """Render the main chat interface"""
        self._ensure_session_initialized()
        st.header("🎮 Model Playground")
        
        # Display current configuration
        with st.expander("📋 Current Configuration", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.json({
                    "model": model,
                    "parameters": config
                })
            with col2:
                st.json({
                    "mcp_servers": selected_servers,
                    "tool_settings": tool_settings
                })
        
        # Chat history
        self._render_chat_history(tool_settings)
        
        # Chat input
        user_input = st.chat_input("Ask me anything...")
        
        if user_input:
            self._handle_user_input(user_input, model, config, selected_servers, tool_settings)
    
    def _render_chat_history(self, tool_settings: Dict[str, Any] = None):
        """Render the chat history"""
        for i, message in enumerate(st.session_state.playground_messages):
            # Skip continuation prompts in display (they are for API only)
            if (message["role"] == "user" and 
                message["content"] == "Continue with the analysis based on the tool results above."):
                continue
            
            # Skip empty assistant messages
            if (message["role"] == "assistant" and 
                not message.get("content", "").strip()):
                continue
                
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                elif message["role"] == "assistant":
                    # Use collapsible message for assistant responses
                    self._render_collapsible_message(
                        content=message["content"],
                        message_list=st.session_state.playground_messages,
                        message=message,
                        prefix="expand_playground_msg",
                        tool_settings=tool_settings
                    )
                    
                    # Show tool calls if any
                    if "tool_calls" in message and message["tool_calls"]:
                        with st.expander("🔧 Tool Calls", expanded=False):
                            for j, tool_call in enumerate(message["tool_calls"]):
                                st.code(json.dumps(tool_call, indent=2), language="json")
                
                elif message["role"] == "tool":
                    with st.expander(f"🛠️ Tool Result", expanded=False):
                        try:
                            result = json.loads(message["content"])
                            if isinstance(result, dict) and "success" in result:
                                if result["success"]:
                                    st.success("✅ Tool executed successfully")
                                else:
                                    st.error(f"❌ Tool failed: {result.get('error', 'Unknown error')}")
                                
                                if "result" in result:
                                    st.json(result["result"])
                            else:
                                st.json(result)
                        except json.JSONDecodeError:
                            st.text(message["content"])
    
    def _render_collapsible_message(self, content: str, message_list: list, message: dict, prefix: str = "expand_msg", tool_settings: Dict[str, Any] = None) -> None:
        """Render a message with collapsible functionality for long content"""
        content_length = len(content)
        
        # Get settings from tool_settings or use defaults
        if tool_settings:
            collapse_threshold = tool_settings.get("collapse_threshold", 800)
            show_character_count = tool_settings.get("show_character_count", True)
        else:
            collapse_threshold = 800
            show_character_count = True
        
        if content_length > collapse_threshold:
            # Show truncated version with expand option
            preview_length = min(300, collapse_threshold // 3)
            preview_text = content[:preview_length] + "..."
            
            # Show preview by default
            st.write(preview_text)
            
            # Add visual indicator for collapsed content
            if show_character_count:
                st.caption(f"💬 {content_length:,} characters total - Click below to expand full response")
            else:
                st.caption("📄 Click below to expand full response")
            
            # Collapsible full response
            with st.expander(f"📄 Show Full Response ({content_length:,} chars)", expanded=False):
                st.write(content)
        else:
            # Short response - show directly
            st.write(content)
    
    def _handle_user_input(self, user_input: str, model: str, config: Dict[str, Any], selected_servers: List[str], tool_settings: Dict[str, Any]):
        """Handle user input and generate response using non-streaming approach"""
        
        # Initialize playground client with current conversation
        self.playground_client.conversation_history = st.session_state.playground_messages.copy()
        
        # Get available tools
        available_tools = self.mcp_manager.get_all_tools(selected_servers)
        
        # Create tool executor
        def tool_executor(tool_name: str, arguments: Dict[str, Any], tool_def: Dict[str, Any]) -> Dict[str, Any]:
            return self.mcp_manager.execute_tool(tool_name, arguments, tool_def)
        
        # Set tools on client
        self.playground_client.set_tools(available_tools, tool_executor)
        
        # Show thinking indicator
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.info("🤔 Model is thinking...")
            
            try:
                # Get response using the new non-streaming client
                max_iterations = tool_settings.get("max_iterations", 10)
                result = asyncio.run(self.playground_client.chat(user_input, model, config, max_iterations))
                
                # Clear thinking indicator
                thinking_placeholder.empty()
                
                if result["success"]:
                    # Display response immediately
                    st.markdown(result["response"])
                    
                    # Show reasoning tokens for reasoning models
                    if result.get("reasoning_tokens") and result["reasoning_tokens"] > 0:
                        st.info(f"🧠 **Reasoning tokens used:** {result['reasoning_tokens']:,} (hidden thinking tokens)")
                    
                    # Show tool results if any
                    if result.get("tool_results"):
                        with st.expander("🔧 Tool Execution Details", expanded=tool_settings.get("show_tool_details", True)):
                            for i, tool_result in enumerate(result["tool_results"]):
                                tool_name = tool_result["tool_name"]
                                success = tool_result["success"]
                                
                                if success:
                                    st.success(f"✅ **{tool_name}** executed successfully")
                                else:
                                    st.error(f"❌ **{tool_name}** failed")
                                
                                with st.expander(f"View {tool_name} details", expanded=False):
                                    st.json(tool_result["result"])
                    
                    # Update session state with complete conversation history
                    st.session_state.playground_messages = result["conversation"]
                    
                    # Update conversation metadata
                    self._update_conversation_metadata()
                    
                    # Rerun to refresh the display
                    st.rerun()
                    
                else:
                    # Handle error
                    error_msg = result.get("error", "Unknown error")
                    st.error(f"❌ Error: {error_msg}")
                    
                    # Update conversation with error (conversation includes user message already)
                    st.session_state.playground_messages = result.get("conversation", st.session_state.playground_messages)
                    
                    # Add error message if not in conversation already
                    if not any(msg.get("content", "").startswith("Error:") for msg in st.session_state.playground_messages[-2:]):
                        st.session_state.playground_messages.append({
                            "role": "assistant",
                            "content": f"Error: {error_msg}"
                        })
                    
                    # Update conversation metadata
                    self._update_conversation_metadata()
                    
                    # Rerun to refresh the display
                    st.rerun()
                
            except Exception as e:
                thinking_placeholder.empty()
                st.error(f"❌ Failed to generate response: {e}")
                
                # Add user message and error to conversation
                if (not st.session_state.playground_messages or 
                    st.session_state.playground_messages[-1]["content"] != user_input):
                    st.session_state.playground_messages.append({
                        "role": "user",
                        "content": user_input
                    })
                
                st.session_state.playground_messages.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })
                
                # Update conversation metadata
                self._update_conversation_metadata()
                
                # Rerun to refresh the display
                st.rerun()
                
    def _validate_conversation_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean conversation messages"""
        validated_messages = []
        
        for message in messages:
            # Ensure message has required fields
            if not isinstance(message, dict) or "role" not in message or "content" not in message:
                continue
            
            # Validate role
            if message["role"] not in ["user", "assistant", "tool", "system"]:
                continue
            
            # Ensure content is a string
            if not isinstance(message["content"], str):
                message["content"] = str(message["content"])
            
            # For tool messages, ensure tool_call_id exists if needed
            if message["role"] == "tool" and "tool_call_id" not in message:
                # Skip orphaned tool messages without call ID
                continue
            
            validated_messages.append(message)
        
        return validated_messages
    
    def _update_conversation_metadata(self):
        """Update conversation metadata with current state"""
        if "playground_conversation_metadata" in st.session_state:
            metadata = st.session_state.playground_conversation_metadata
            metadata["last_activity"] = datetime.now().isoformat()
            metadata["message_count"] = len(st.session_state.playground_messages)
            st.session_state.playground_conversation_metadata = metadata
    
    def _export_conversation(self):
        """Export conversation to JSON format"""
        try:
            export_data = {
                "metadata": st.session_state.playground_conversation_metadata,
                "messages": st.session_state.playground_messages,
                "export_timestamp": datetime.now().isoformat()
            }
            
            # Format as downloadable JSON
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="⬇️ Download Conversation JSON",
                data=json_str,
                file_name=f"playground_chat_{export_data['metadata']['session_id']}.json",
                mime="application/json",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Failed to export conversation: {e}")
    
    def _copy_conversation_to_clipboard(self):
        """Copy conversation to clipboard as markdown"""
        try:
            markdown_content = self._format_conversation_as_markdown()
            st.code(markdown_content, language="markdown")
            st.info("💡 Copy the markdown content above to your clipboard")
            
        except Exception as e:
            st.error(f"Failed to format conversation: {e}")
    
    def _format_conversation_as_markdown(self) -> str:
        """Format conversation as markdown"""
        lines = []
        metadata = st.session_state.playground_conversation_metadata
        
        # Header
        lines.append(f"# Playground Conversation - Session {metadata['session_id']}")
        lines.append(f"**Created:** {metadata['created_at']}")
        lines.append(f"**Messages:** {len(st.session_state.playground_messages)}")
        lines.append("")
        
        # Messages
        for i, message in enumerate(st.session_state.playground_messages):
            role = message["role"].title()
            content = message.get("content", "")
            
            lines.append(f"## {role} {i+1}")
            lines.append("")
            lines.append(content)
            lines.append("")
            
            # Add tool calls if present
            if "tool_calls" in message and message["tool_calls"]:
                lines.append("### Tool Calls")
                for tool_call in message["tool_calls"]:
                    lines.append(f"- **{tool_call.get('function', {}).get('name', 'Unknown')}**")
                lines.append("")
        
        return "\n".join(lines)

    def render_playground_controls(self):
        """Render additional playground controls"""
        self._ensure_session_initialized()
        st.subheader("🎮 Playground Controls")
        
        # Display conversation status
        if "playground_conversation_metadata" in st.session_state:
            metadata = st.session_state.playground_conversation_metadata
            message_count = len(st.session_state.playground_messages)
            
            if message_count > 0:
                col_status1, col_status2 = st.columns(2)
                with col_status1:
                    st.metric("Messages", message_count)
                with col_status2:
                    last_activity = datetime.fromisoformat(metadata["last_activity"])
                    time_diff = datetime.now() - last_activity
                    if time_diff.total_seconds() < 60:
                        st.metric("Last Activity", "Just now")
                    elif time_diff.total_seconds() < 3600:
                        minutes = int(time_diff.total_seconds() / 60)
                        st.metric("Last Activity", f"{minutes}m ago")
                    else:
                        hours = int(time_diff.total_seconds() / 3600)
                        st.metric("Last Activity", f"{hours}h ago")
        
        # Control buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.playground_messages = []
                st.session_state.playground_tool_calls = []
                # Clear playground client conversation
                self.playground_client.clear_conversation()
                # Reset conversation metadata
                st.session_state.playground_conversation_metadata = {
                    "created_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat(),
                    "message_count": 0,
                    "session_id": str(hash(datetime.now().isoformat()))[:8]
                }
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh Servers", use_container_width=True):
                self.mcp_manager.refresh_connections()
                st.success("Servers refreshed!")
                time.sleep(1)
                st.rerun()
        
        # Additional features
        if len(st.session_state.playground_messages) > 0:
            col3, col4 = st.columns(2)
            with col3:
                if st.button("💾 Export Chat", use_container_width=True):
                    self._export_conversation()
            with col4:
                if st.button("📋 Copy Chat", use_container_width=True):
                    self._copy_conversation_to_clipboard()


def render_playground_tab():
    """Main function to render the playground tab"""
    # Use singleton pattern - store PlaygroundUI instance in session state
    if "playground_ui_instance" not in st.session_state:
        st.session_state.playground_ui_instance = PlaygroundUI()
    
    playground_ui = st.session_state.playground_ui_instance
    
    # Main layout: Configuration sidebar on left, chat interface on right
    config_col, chat_col = st.columns([1, 2])
    
    with config_col:
        # Configuration sections
        selected_model = playground_ui.render_model_selector()
        model_config = playground_ui.render_model_parameters(selected_model)
        
        st.markdown("---")
        selected_servers = playground_ui.render_server_selector()
        
        st.markdown("---")
        tool_settings = playground_ui.render_tool_controls()
        
        st.markdown("---")
        playground_ui.render_playground_controls()
    
    with chat_col:
        # Main chat interface
        playground_ui.render_chat_interface(selected_model, model_config, selected_servers, tool_settings)