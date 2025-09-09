"""
Streaming Utilities - Helper functions for streaming responses and tool calls
"""

import json
import time
import streamlit as st
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime


class StreamingDisplay:
    """Utilities for displaying streaming responses in Streamlit"""
    
    def __init__(self):
        self.current_content = ""
        self.tool_calls = []
        self.reasoning_content = ""
        self.cursor_states = ["|", "/", "-", "\\"]
        self.cursor_index = 0
    
    def get_cursor(self) -> str:
        """Get animated cursor for streaming display"""
        cursor = self.cursor_states[self.cursor_index]
        self.cursor_index = (self.cursor_index + 1) % len(self.cursor_states)
        return cursor
    
    def format_streaming_content(self, content: str, show_cursor: bool = True) -> str:
        """Format content for streaming display with cursor"""
        if show_cursor:
            return content + self.get_cursor()
        return content
    
    def display_tool_call_start(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Display tool call initiation"""
        with st.container():
            st.info(f"🔧 Calling tool: **{tool_name}**")
            with st.expander("View arguments", expanded=False):
                st.json(arguments)
    
    def display_tool_call_progress(self, tool_name: str, message: str = "Executing...") -> None:
        """Display tool call progress"""
        st.info(f"⚡ {tool_name}: {message}")
    
    def display_tool_call_result(self, tool_name: str, result: Dict[str, Any], success: bool = True) -> None:
        """Display tool call result"""
        if success:
            st.success(f"✅ {tool_name} completed successfully")
        else:
            st.error(f"❌ {tool_name} failed")
        
        # Show result in expandable section
        with st.expander("View result", expanded=not success):
            if isinstance(result, dict):
                st.json(result)
            else:
                st.text(str(result))
    
    def display_reasoning_item(self, reasoning: Dict[str, Any]) -> None:
        """Display reasoning content for reasoning models"""
        reasoning_type = reasoning.get("type", "unknown")
        
        if reasoning_type == "reasoning":
            st.info("🧠 Model is reasoning...")
            
            # Show reasoning summary if available
            if "summary" in reasoning:
                with st.expander("💭 Reasoning Summary", expanded=False):
                    st.markdown(reasoning["summary"])
        
        elif reasoning_type == "reflection":
            with st.expander("🔍 Reflection", expanded=False):
                st.markdown(reasoning.get("content", "No reflection content"))


class StreamingEventProcessor:
    """Process streaming events and update UI accordingly"""
    
    def __init__(self):
        self.display = StreamingDisplay()
        self.message_placeholder = None
        self.tool_placeholder = None
        self.reasoning_placeholder = None
        self.current_content = ""
    
    def setup_placeholders(self):
        """Setup Streamlit placeholders for different content types"""
        self.message_placeholder = st.empty()
        self.tool_placeholder = st.empty()
        self.reasoning_placeholder = st.empty()
    
    def process_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a streaming event and update display
        Returns True if event was handled, False otherwise
        """
        event_type = event.get("type", "unknown")
        
        if event_type == "content_delta":
            return self._handle_content_delta(event)
        elif event_type == "tool_calls":
            return self._handle_tool_calls(event)
        elif event_type == "tool_executing":
            return self._handle_tool_executing(event)
        elif event_type == "tool_result":
            return self._handle_tool_result(event)
        elif event_type == "reasoning":
            return self._handle_reasoning(event)
        elif event_type == "loop_iteration":
            return self._handle_loop_iteration(event)
        elif event_type == "final_response":
            return self._handle_final_response(event)
        elif event_type == "error":
            return self._handle_error(event)
        elif event_type == "loop_error":
            return self._handle_loop_error(event)
        else:
            # Unknown event type
            return False
    
    def _handle_content_delta(self, event: Dict[str, Any]) -> bool:
        """Handle content delta events"""
        delta_content = event.get("content", "")
        self.current_content += delta_content
        
        if self.message_placeholder:
            formatted_content = self.display.format_streaming_content(self.current_content)
            self.message_placeholder.markdown(formatted_content)
        
        return True
    
    def _handle_tool_calls(self, event: Dict[str, Any]) -> bool:
        """Handle tool calls events"""
        tool_calls = event.get("tool_calls", [])
        
        if self.tool_placeholder:
            with self.tool_placeholder.container():
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    arguments = tool_call.get("function", {}).get("arguments", {})
                    
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {"raw": arguments}
                    
                    self.display.display_tool_call_start(tool_name, arguments)
        
        return True
    
    def _handle_tool_executing(self, event: Dict[str, Any]) -> bool:
        """Handle tool execution events"""
        tool_name = event.get("tool_name", "unknown")
        message = f"Executing... ({event.get('tool_index', 1)}/{event.get('total_tools', 1)})"
        
        if self.tool_placeholder:
            with self.tool_placeholder.container():
                self.display.display_tool_call_progress(tool_name, message)
        
        return True
    
    def _handle_tool_result(self, event: Dict[str, Any]) -> bool:
        """Handle tool result events"""
        tool_name = event.get("tool_name", "unknown")
        result = event.get("result", {})
        success = event.get("success", True)
        
        if self.tool_placeholder:
            with self.tool_placeholder.container():
                self.display.display_tool_call_result(tool_name, result, success)
        
        return True
    
    def _handle_reasoning(self, event: Dict[str, Any]) -> bool:
        """Handle reasoning events"""
        reasoning = event.get("reasoning", {})
        
        if self.reasoning_placeholder:
            with self.reasoning_placeholder.container():
                self.display.display_reasoning_item(reasoning)
        
        return True
    
    def _handle_loop_iteration(self, event: Dict[str, Any]) -> bool:
        """Handle tool loop iteration events"""
        iteration = event.get("iteration", 1)
        message = event.get("message", f"Starting iteration {iteration}")
        
        if self.tool_placeholder:
            self.tool_placeholder.info(f"🔄 {message}")
        
        return True
    
    def _handle_final_response(self, event: Dict[str, Any]) -> bool:
        """Handle final response events"""
        final_content = event.get("final_content", self.current_content)
        
        if self.message_placeholder:
            # Remove cursor and show final content
            self.message_placeholder.markdown(final_content)
        
        # Clear tool and reasoning placeholders
        if self.tool_placeholder:
            self.tool_placeholder.empty()
        if self.reasoning_placeholder:
            self.reasoning_placeholder.empty()
        
        return True
    
    def _handle_error(self, event: Dict[str, Any]) -> bool:
        """Handle error events"""
        error_msg = event.get("error", "Unknown error occurred")
        
        st.error(f"❌ Error: {error_msg}")
        
        # Clear placeholders
        if self.tool_placeholder:
            self.tool_placeholder.empty()
        if self.reasoning_placeholder:
            self.reasoning_placeholder.empty()
        
        return True
    
    def _handle_loop_error(self, event: Dict[str, Any]) -> bool:
        """Handle tool loop error events"""
        error_msg = event.get("error", "Tool loop error occurred")
        loop_count = event.get("loop_count", "unknown")
        
        st.error(f"🔄 Tool Loop Error (iteration {loop_count}): {error_msg}")
        
        # Clear placeholders
        if self.tool_placeholder:
            self.tool_placeholder.empty()
        if self.reasoning_placeholder:
            self.reasoning_placeholder.empty()
        
        return True


def create_streaming_chat_response(
    events: Iterator[Dict[str, Any]], 
    show_tool_details: bool = True,
    show_reasoning: bool = True
) -> Dict[str, Any]:
    """
    Create a streaming chat response display in Streamlit
    
    Args:
        events: Iterator of streaming events
        show_tool_details: Whether to show detailed tool information
        show_reasoning: Whether to show reasoning content
    
    Returns:
        Final response data
    """
    processor = StreamingEventProcessor()
    
    # Setup display areas
    message_container = st.empty()
    
    if show_tool_details:
        tool_container = st.empty()
    else:
        tool_container = None
    
    if show_reasoning:
        reasoning_container = st.empty()
    else:
        reasoning_container = None
    
    # Setup processor placeholders
    processor.message_placeholder = message_container
    processor.tool_placeholder = tool_container
    processor.reasoning_placeholder = reasoning_container
    
    final_data = {}
    
    try:
        for event in events:
            # Process the event
            handled = processor.process_event(event)
            
            # Store final data
            if event.get("type") == "loop_complete":
                final_data = event
                break
            elif event.get("type") == "final_response":
                final_data = event
                break
            elif event.get("type") == "error":
                final_data = event
                break
            elif event.get("type") == "loop_error":
                final_data = event
                break
            elif event.get("done", False):
                final_data = event
                break
            
            # Small delay for smooth streaming effect
            time.sleep(0.05)
    
    except Exception as e:
        st.error(f"Streaming error: {e}")
        final_data = {"type": "error", "error": str(e)}
    
    return final_data


def format_tool_signature(tool: Dict[str, Any]) -> str:
    """Format tool signature for display"""
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
            param_str = f"**{param_str}**"
        param_strs.append(param_str)
    
    params_str = ", ".join(param_strs)
    return f"`{name}({params_str})`\n\n{description}"