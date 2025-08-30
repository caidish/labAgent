import streamlit as st
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from datetime import datetime
import json
from typing import List, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lab_agent.main import LabAgent
from lab_agent.utils import Config
from lab_agent.utils.tool_manager import ToolManager
from lab_agent.agents.arxiv_daily_agent import ArxivDailyAgent
from lab_agent.tools.arxiv_chat import ArxivChat
from lab_agent.tools.gpt5_mini_chatbox import GPT5MiniChatbox

nest_asyncio.apply()


def main():
    load_dotenv()
    config = Config()
    
    st.set_page_config(
        page_title="Lab Agent System",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 Lab Agent System")
    st.markdown("Multi-agent system for laboratory automation and research")
    
    # Initialize agents in session state
    if "agent" not in st.session_state:
        st.session_state.agent = LabAgent()
    
    if "arxiv_agent" not in st.session_state:
        try:
            st.session_state.arxiv_agent = ArxivDailyAgent({
                'reports_dir': './reports'
            })
            asyncio.run(st.session_state.arxiv_agent.initialize())
        except Exception as e:
            st.error(f"Failed to initialize ArXiv agent: {e}")
            st.session_state.arxiv_agent = None
    
    # Initialize ArXiv chat
    if "arxiv_chat" not in st.session_state:
        try:
            st.session_state.arxiv_chat = ArxivChat()
        except Exception as e:
            st.error(f"Failed to initialize ArXiv chat: {e}")
            st.session_state.arxiv_chat = None
    
    # Initialize chat messages
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Initialize GPT-5-mini chatbox
    if "gpt5_mini_chatbox" not in st.session_state:
        try:
            st.session_state.gpt5_mini_chatbox = GPT5MiniChatbox()
        except Exception as e:
            st.error(f"Failed to initialize GPT-5-mini chatbox: {e}")
            st.session_state.gpt5_mini_chatbox = None
    
    # Initialize overview chat messages
    if "overview_chat_messages" not in st.session_state:
        st.session_state.overview_chat_messages = []
    
    # Initialize tool manager
    if "tool_manager" not in st.session_state:
        st.session_state.tool_manager = ToolManager()
    
    # Main navigation
    tabs = st.tabs(["🏠 Overview", "📚 ArXiv Daily", "🔧 Tools", "📋 Logs"])
    
    with tabs[0]:
        col1, col2, col3 = st.columns([1, 1.5, 1.5])
        
        with col1:
            st.subheader("System Status")
            if st.button("Start System"):
                st.success("System started!")
                
            if st.button("Stop System"):
                st.info("System stopped!")
                
            st.subheader("Configuration")
            
            # Load model configuration to show actual models in use
            models_config = {}
            try:
                import json
                models_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lab_agent', 'config', 'models.json')
                with open(models_path, 'r') as f:
                    models_data = json.load(f)
                    models_config = {
                        "ArXiv Filter Model": models_data.get('arxivFilterModel', {}).get('name', 'gpt-5-mini'),
                        "Chat Model": models_data.get('chatModel', {}).get('name', 'gpt-5-mini'),
                        "GPT-5-mini Chatbox": "gpt-5-mini (MCP enabled)",
                        "Gemini Model": config.gemini_model,
                        "Debug Mode": config.debug,
                        "Log Level": config.log_level
                    }
            except Exception as e:
                # Fallback to basic config
                models_config = {
                    "Default OpenAI Model": config.openai_model,
                    "Gemini Model": config.gemini_model, 
                    "Debug Mode": config.debug,
                    "Log Level": config.log_level
                }
            
            st.json(models_config)
        
        with col2:
            st.subheader("System Overview")
            st.info("Lab Agent system ready for deployment")
            
            # ArXiv Daily Status
            st.markdown("### 📚 ArXiv Daily Status")
            arxiv_daily_status()
            
            st.markdown("### Available Tools")
            tools = [
                "📚 ArXiv Daily - Automated paper recommendations with AI scoring",
                "🔬 2D Flake Classification - AI-powered quality assessment via MCP server",
                "🕷️ Web Scraper - Extract data from web pages",
                "🔍 ArXiv Parser - Parse research papers from ArXiv API",
                "🤖 Multi-model AI - OpenAI GPT-4 and Google Gemini integration",
                "🤖 GPT-5-mini Assistant - AI chatbox with MCP tools for ArXiv Daily & 2D Flakes"
            ]
            for tool in tools:
                st.markdown(f"- {tool}")
        
        with col3:
            gpt5_mini_chatbox_interface()

    with tabs[1]:
        arxiv_daily_interface()
        
    with tabs[2]:
        tools_interface()
        
    with tabs[3]:
        st.subheader("System Logs")
        st.text_area("Logs", "System initialized successfully...", height=200)


def arxiv_daily_interface():
    st.header("📚 ArXiv Daily Paper Recommendations")
    st.markdown("Get AI-powered recommendations for papers relevant to your research interests")
    
    if st.session_state.arxiv_agent is None:
        st.error("ArXiv agent not available. Please check your OpenAI API key in .env file.")
        return
    
    # Create two main columns: reports and chat
    col_reports, col_chat = st.columns([1.2, 0.8])
    
    with col_reports:
        st.subheader("📊 Daily Reports")
        
        # Control buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🔄 Generate Daily Report", type="primary", use_container_width=True):
                generate_daily_report()
        
        with col2:
            if st.button("🗑️ Clear All Reports", use_container_width=True):
                clear_reports()
        
        with col3:
            if st.button("📋 Refresh Report List", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        # List existing reports
        try:
            result = st.session_state.arxiv_agent._list_reports()
            if result['success']:
                reports = result['reports']
                
                if reports:
                    # Display reports in a nice format
                    for date in reports:
                        with st.expander(f"📅 Report for {date}", expanded=False):
                            display_report(date)
                else:
                    st.info("No daily reports available. Click 'Generate Daily Report' to create your first report!")
            else:
                st.error(f"Error loading reports: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"Error loading reports: {e}")
    
    with col_chat:
        arxiv_chat_interface()


def generate_daily_report():
    """Generate a new daily report"""
    with st.spinner("Generating daily report... This may take a few minutes."):
        try:
            task = {
                'type': 'generate_daily_report',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': 'https://arxiv.org/list/cond-mat/new'
            }
            
            result = asyncio.run(st.session_state.arxiv_agent.process_task(task))
            
            if result['success']:
                if result.get('from_cache'):
                    st.info(f"📋 {result['message']}")  # Different icon for cached reports
                else:
                    st.success(f"✅ {result['message']}")
                
                # Handle both string and integer keys for priority counts
                priority_counts = result.get('priority_counts', {})
                p3 = priority_counts.get('3', priority_counts.get(3, 0))
                p2 = priority_counts.get('2', priority_counts.get(2, 0))
                p1 = priority_counts.get('1', priority_counts.get(1, 0))
                
                st.info(f"📊 Summary: {result['total_papers']} papers | "
                       f"Priority 3: {p3} | "
                       f"Priority 2: {p2} | "
                       f"Priority 1: {p1}")
                st.rerun()
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"❌ Error generating report: {e}")


def clear_reports():
    """Clear all stored reports"""
    try:
        result = st.session_state.arxiv_agent._clear_reports()
        if result['success']:
            st.success(f"✅ {result['message']}")
            st.rerun()
        else:
            st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        st.error(f"❌ Error clearing reports: {e}")


def display_report(date):
    """Display a specific report"""
    try:
        result = st.session_state.arxiv_agent._get_report(date)
        
        if result['success']:
            report_data = result['report']['json_data']
            html_content = result['report']['html_content']
            
            # Show summary
            summary = report_data['summary']
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Papers", summary['total_papers'])
            with col2:
                # Handle both string and integer keys for priority counts
                priority_3 = summary['priority_counts'].get('3', summary['priority_counts'].get(3, 0))
                st.metric("Priority 3", priority_3)
            with col3:
                priority_2 = summary['priority_counts'].get('2', summary['priority_counts'].get(2, 0))
                st.metric("Priority 2", priority_2)
            with col4:
                priority_1 = summary['priority_counts'].get('1', summary['priority_counts'].get(1, 0))
                st.metric("Priority 1", priority_1)
            
            # Show report options
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"📄 View HTML Report", key=f"html_{date}"):
                    st.components.v1.html(html_content, height=600, scrolling=True)
            
            with col2:
                if st.button(f"📋 View JSON Data", key=f"json_{date}"):
                    st.json(report_data)
            
            # Show top priority papers
            priority_counts = summary.get('priority_counts', {})
            papers_by_priority = report_data.get('papers_by_priority', {})
            
            # Handle both string and integer keys
            priority_3_count = priority_counts.get(3, priority_counts.get('3', 0))
            if priority_3_count > 0:
                st.markdown("### 🔴 Top Priority Papers")
                high_priority_papers = papers_by_priority.get('3', papers_by_priority.get(3, []))
                high_priority = high_priority_papers[:3]  # Show first 3
                
                for i, paper in enumerate(high_priority):
                    st.markdown(f"**{i+1}. {paper['title']}**")
                    st.markdown(f"*Authors:* {paper['authors']}")
                    st.markdown(f"*AI Assessment:* {paper['reason']}")
                    if paper.get('url'):
                        st.markdown(f"[📄 Abstract]({paper['url']}) | [📁 PDF]({paper['pdf_url']})")
                    st.markdown("---")
            
        else:
            st.error(f"Error loading report: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"Error displaying report: {e}")


def arxiv_chat_interface():
    """Chat interface for discussing today's papers with GPT-4o"""
    st.subheader("💬 Chat About Papers")
    st.markdown("*Discuss today's papers with AI*")
    
    if st.session_state.arxiv_chat is None:
        st.error("Chat not available. Please check your OpenAI API key.")
        return
    
    # Load today's papers into chat context if available
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        result = st.session_state.arxiv_agent._get_report(today)
        if result['success']:
            papers_data = result['report']['json_data']
            all_papers = papers_data.get('all_papers', [])
            
            # Set papers context if not already set
            if len(all_papers) > 0 and st.session_state.arxiv_chat.current_papers != all_papers:
                st.session_state.arxiv_chat.set_papers_context(all_papers)
                st.success(f"📄 Loaded {len(all_papers)} papers for discussion")
                
        else:
            st.info("💡 Generate today's report first to enable paper-specific discussions")
            
    except Exception as e:
        st.warning("Could not load today's papers for chat context")
    
    # Chat controls
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🆕 New Conversation", use_container_width=True):
            st.session_state.chat_messages = []
            if st.session_state.arxiv_chat:
                st.session_state.arxiv_chat.clear_conversation()
            st.rerun()
    
    with col2:
        chat_summary = st.session_state.arxiv_chat.get_conversation_summary()
        if chat_summary['conversation_active']:
            st.metric("Exchanges", chat_summary['total_exchanges'])
    
    # Display chat messages
    chat_container = st.container()
    
    with chat_container:
        # Show existing messages
        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])
    
    # Suggested questions
    if not st.session_state.chat_messages:
        st.markdown("**💡 Suggested questions:**")
        suggestions = st.session_state.arxiv_chat.get_suggested_questions()
        
        # Display suggestions as clickable buttons
        for i, suggestion in enumerate(suggestions[:4]):  # Show first 4
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                handle_chat_message(suggestion)
                st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about today's papers..."):
        handle_chat_message(prompt)
        st.rerun()


def handle_chat_message(user_message: str):
    """Handle a chat message from the user"""
    try:
        # Add user message to display
        st.session_state.chat_messages.append({
            "role": "user", 
            "content": user_message
        })
        
        # Get AI response
        with st.spinner("Thinking..."):
            response = st.session_state.arxiv_chat.chat(user_message)
        
        if response['success']:
            # Add assistant response to display
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response['response']
            })
        else:
            st.error(f"Chat error: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"Error in chat: {e}")


def gpt5_mini_chatbox_interface():
    """GPT-5-mini chatbox interface for general assistance and future MCP tools"""
    if st.session_state.gpt5_mini_chatbox is None:
        st.error("GPT-5-mini chatbox not available. Please check your OpenAI API key.")
        return
    
    # Get UI configuration
    ui_config = st.session_state.gpt5_mini_chatbox.get_ui_config()
    
    st.subheader(ui_config["title"])
    st.markdown(f"*{ui_config['subtitle']}*")
    
    # Show MCP tools info
    mcp_info = st.session_state.gpt5_mini_chatbox.get_mcp_tools_info()
    tool_expander_title = "🔧 MCP Tools" if mcp_info.get("enabled", False) else "🔧 Future MCP Tools"
    with st.expander(tool_expander_title, expanded=False):
        
        if mcp_info.get("enabled", False):
            st.success(mcp_info["status"])
            
            # Show ArXiv Daily tools
            arxiv_tools = mcp_info.get("arxiv_tools", [])
            if arxiv_tools:
                st.markdown("**📚 Active ArXiv Daily Tools:**")
                for tool in arxiv_tools:
                    status_icon = "🟢" if tool.get("status") == "active" else "🟡"
                    st.markdown(f"- {status_icon} **{tool['name']}**: {tool['description']}")
                st.markdown("---")
            
            # Show 2D Flake tools
            flake_tools = mcp_info.get("flake_2d_tools", [])
            if flake_tools:
                st.markdown("**🔬 Active 2D Flake Classification Tools:**")
                for tool in flake_tools:
                    status_icon = "🟢" if tool.get("status") == "active" else "🟡"
                    st.markdown(f"- {status_icon} **{tool['name']}**: {tool['description']}")
                st.markdown("---")
            
            # Show planned tools
            planned_tools = mcp_info.get("planned_tools", [])
            if planned_tools:
                st.markdown("**🟡 Planned Tools:**")
                for tool in planned_tools:
                    st.markdown(f"- 🟡 **{tool['name']}**: {tool['description']} ({tool['status']})")
        else:
            st.info(mcp_info["status"])
            planned_tools = mcp_info.get("planned_tools", [])
            if planned_tools:
                st.markdown("**Planned Tools:**")
                for tool in planned_tools:
                    st.markdown(f"- **{tool['name']}**: {tool['description']} ({tool['status']})")
    
    # Chat controls
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🆕 New Chat", key="overview_new_chat", use_container_width=True):
            st.session_state.overview_chat_messages = []
            if st.session_state.gpt5_mini_chatbox:
                st.session_state.gpt5_mini_chatbox.clear_conversation()
            st.rerun()
    
    with col2:
        chat_summary = st.session_state.gpt5_mini_chatbox.get_conversation_summary()
        if chat_summary['conversation_active']:
            st.metric("Exchanges", chat_summary['total_exchanges'])
    
    # Display chat messages in a container with fixed height
    chat_container = st.container()
    
    with chat_container:
        # Show existing messages
        for message in st.session_state.overview_chat_messages:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                # Assistant message with optional reasoning display
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    
                    # Show reasoning if available and enabled
                    if (message.get("reasoning") and 
                        st.session_state.gpt5_mini_chatbox.enable_reasoning_display() and
                        message["reasoning"].get("available")):
                        
                        with st.expander("🧠 Reasoning", expanded=False):
                            if message["reasoning"].get("summary"):
                                st.markdown("**Summary:**")
                                st.text(message["reasoning"]["summary"])
                            if message["reasoning"].get("encrypted_content"):
                                st.markdown("**Encrypted reasoning available**")
                    
                    # Show tool results if available
                    if message.get("tool_results"):
                        for tool_result in message["tool_results"]:
                            tool_name = tool_result.get("tool_name", "Unknown Tool")
                            with st.expander(f"🔧 {tool_name} Result", expanded=False):
                                if tool_result.get("summary"):
                                    st.markdown("**Summary:**")
                                    st.info(tool_result["summary"])
                                
                                if tool_result.get("data"):
                                    st.markdown("**Details:**")
                                    data = tool_result["data"]
                                    
                                    # Format different types of data nicely
                                    if isinstance(data, dict):
                                        # Pretty print dict data
                                        for key, value in data.items():
                                            if key in ['reports', 'high_priority_papers'] and isinstance(value, list):
                                                if value:
                                                    st.markdown(f"**{key.replace('_', ' ').title()}:**")
                                                    for item in value[:3]:  # Show first 3 items
                                                        if isinstance(item, dict) and 'title' in item:
                                                            st.markdown(f"- {item.get('title', 'N/A')}")
                                                        else:
                                                            st.markdown(f"- {item}")
                                                    if len(value) > 3:
                                                        st.markdown(f"... and {len(value) - 3} more")
                                            else:
                                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                                    else:
                                        st.text(str(data))
    
    # Suggested questions for new conversations
    if not st.session_state.overview_chat_messages:
        st.markdown("**💡 Suggested questions:**")
        suggestions = st.session_state.gpt5_mini_chatbox.get_suggested_prompts()
        
        # Display suggestions as clickable buttons in two columns
        suggestion_cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            col_idx = i % 2
            with suggestion_cols[col_idx]:
                if st.button(suggestion, key=f"overview_suggestion_{i}", use_container_width=True):
                    handle_overview_chat_message(suggestion)
                    st.rerun()
    
    # Chat input
    if prompt := st.chat_input(ui_config["placeholder_text"], key="overview_chat_input"):
        handle_overview_chat_message(prompt)
        st.rerun()


def handle_overview_chat_message(user_message: str):
    """Handle a chat message in the overview chatbox"""
    try:
        # Add user message to display
        st.session_state.overview_chat_messages.append({
            "role": "user", 
            "content": user_message
        })
        
        # Get AI response
        with st.spinner("GPT-5-mini thinking..."):
            response = asyncio.run(st.session_state.gpt5_mini_chatbox.chat(user_message))
        
        if response['success']:
            # Add assistant response to display
            st.session_state.overview_chat_messages.append({
                "role": "assistant",
                "content": response['response'],
                "reasoning": response.get('reasoning'),
                "metadata": response.get('metadata', {}),
                "tool_results": response.get('tool_results', [])
            })
        else:
            st.error(f"Chat error: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"Error in overview chat: {e}")


def arxiv_daily_status():
    """Display ArXiv Daily status in the System Overview"""
    if st.session_state.arxiv_agent is None:
        st.warning("ArXiv agent not initialized")
        return
    
    try:
        # Check today's report
        today = datetime.now().strftime('%Y-%m-%d')
        result = st.session_state.arxiv_agent._get_report(today)
        
        if result['success']:
            # Report exists for today
            report_data = result['report']['json_data']
            summary = report_data['summary']
            
            # Get priority 3 count (high priority papers)
            priority_counts = summary.get('priority_counts', {})
            priority_3_count = priority_counts.get('3', priority_counts.get(3, 0))
            total_papers = summary.get('total_papers', 0)
            
            if priority_3_count > 0:
                st.success(f"🔴 **{priority_3_count} high-priority papers** need your attention today!")
                st.info(f"📊 Total papers analyzed: {total_papers}")
            else:
                st.info(f"✅ No high-priority papers today ({total_papers} papers analyzed)")
            
            # Quick action button
            if st.button("📚 View Report Details", key="overview_view_report", use_container_width=True):
                # Show report preview in an expander
                with st.expander("📊 Report Details", expanded=True):
                    st.markdown(f"**Report Date:** {today}")
                    st.markdown(f"**Total Papers:** {summary.get('total_papers', 0)}")
                    
                    # Show priority breakdown
                    priority_counts = summary.get('priority_counts', {})
                    p3_count = priority_counts.get('3', priority_counts.get(3, 0))
                    p2_count = priority_counts.get('2', priority_counts.get(2, 0))  
                    p1_count = priority_counts.get('1', priority_counts.get(1, 0))
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🔴 Priority 3", p3_count)
                    with col2:
                        st.metric("🟡 Priority 2", p2_count)
                    with col3:
                        st.metric("🟢 Priority 1", p1_count)
                    
                    st.info("💡 **For the full interactive report with paper details, filtering, and AI chat:**\n\nGo to the **📚 ArXiv Daily** tab above")
                
        else:
            # No report for today
            st.info("📅 No ArXiv Daily report generated yet for today")
            if st.button("🔄 Generate Today's Report", key="overview_generate_report", use_container_width=True):
                generate_daily_report_quick()
    
    except Exception as e:
        st.warning(f"Could not load ArXiv Daily status: {str(e)[:50]}...")


def generate_daily_report_quick():
    """Generate daily report from overview (simplified version)"""
    if st.session_state.arxiv_agent is None:
        st.error("ArXiv agent not available")
        return
    
    with st.spinner("Generating today's ArXiv report... This may take a few minutes."):
        try:
            task = {
                'type': 'generate_daily_report',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': 'https://arxiv.org/list/cond-mat/new'
            }
            
            result = asyncio.run(st.session_state.arxiv_agent.process_task(task))
            
            if result['success']:
                if result.get('from_cache'):
                    st.info("📋 Report was already available")
                else:
                    st.success("✅ Report generated successfully!")
                
                # Show summary
                priority_counts = result.get('priority_counts', {})
                p3 = priority_counts.get('3', priority_counts.get(3, 0))
                
                if p3 > 0:
                    st.success(f"🔴 {p3} high-priority papers found!")
                else:
                    st.info("✅ No high-priority papers today")
                
                st.rerun()  # Refresh the page to show updated status
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"❌ Error generating report: {e}")


def save_uploaded_image(uploaded_file) -> bool:
    """Save uploaded image to uploads directory"""
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), "uploads", "flake_images")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save file with original name
        file_path = os.path.join(uploads_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Store file info in session state for GPT-5-mini reference
        if "uploaded_flake_images" not in st.session_state:
            st.session_state.uploaded_flake_images = []
        
        # Add to list if not already there
        existing_names = [img['name'] for img in st.session_state.uploaded_flake_images]
        if uploaded_file.name not in existing_names:
            st.session_state.uploaded_flake_images.append({
                'name': uploaded_file.name,
                'path': file_path,
                'size': f"{uploaded_file.size / 1024:.1f} KB",
                'type': uploaded_file.type,
                'uploaded_at': datetime.now().isoformat()
            })
        
        return True
    except Exception as e:
        st.error(f"Error saving image: {e}")
        return False

def get_uploaded_images() -> List[Dict]:
    """Get list of uploaded images"""
    if "uploaded_flake_images" not in st.session_state:
        st.session_state.uploaded_flake_images = []
    
    # Verify files still exist
    valid_images = []
    for img_info in st.session_state.uploaded_flake_images:
        if os.path.exists(img_info['path']):
            valid_images.append(img_info)
    
    st.session_state.uploaded_flake_images = valid_images
    return valid_images

def delete_uploaded_image(filename: str) -> bool:
    """Delete an uploaded image"""
    try:
        if "uploaded_flake_images" not in st.session_state:
            return False
        
        # Find and remove from session state
        img_to_remove = None
        for img_info in st.session_state.uploaded_flake_images:
            if img_info['name'] == filename:
                img_to_remove = img_info
                break
        
        if img_to_remove:
            # Remove file
            if os.path.exists(img_to_remove['path']):
                os.remove(img_to_remove['path'])
            
            # Remove from session state
            st.session_state.uploaded_flake_images.remove(img_to_remove)
            return True
        
        return False
    except Exception as e:
        st.error(f"Error deleting image: {e}")
        return False

def tools_interface():
    """Tools activation and management interface"""
    st.subheader("🔧 Tool Management")
    st.markdown("Activate or deactivate MCP tools for the Lab Agent system")
    
    tool_manager = st.session_state.tool_manager
    
    # Refresh tool manager state
    if st.button("🔄 Refresh Tool Status", use_container_width=True):
        st.session_state.tool_manager = ToolManager()
        st.rerun()
    
    # Get activation summary
    summary = tool_manager.get_activation_summary()
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tools", summary["total_tools"])
    with col2:
        st.metric("Active Tools", summary["active_tools"])
    with col3:
        st.metric("Inactive Tools", summary["inactive_tools"])
    
    st.markdown("---")
    
    # ArXiv Daily Tools section
    st.markdown("### 📚 ArXiv Daily Tools")
    arxiv_status = tool_manager.get_tool_status("arxiv_daily")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{arxiv_status.get('name', 'ArXiv Daily')}**")
        st.markdown(f"*{arxiv_status.get('description', 'Paper recommendations and analysis')}*")
    
    with col2:
        current_state = arxiv_status.get('active', False)
        if current_state:
            st.success("🟢 Active")
            if st.button("Deactivate", key="deactivate_arxiv"):
                tool_manager.deactivate_tool("arxiv_daily")
                st.success("ArXiv Daily tools deactivated")
                st.rerun()
        else:
            st.warning("🟡 Inactive")
            if st.button("Activate", key="activate_arxiv"):
                tool_manager.activate_tool("arxiv_daily")
                st.success("ArXiv Daily tools activated")
                st.rerun()
    
    st.markdown("---")
    
    # 2D Flake Classification Tools section
    st.markdown("### 🔬 2D Flake Classification Tools")
    flake_status = tool_manager.get_tool_status("flake_2d")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{flake_status.get('name', '2D Flake Classification')}**")
        st.markdown(f"*{flake_status.get('description', 'AI-powered material analysis')}*")
        
        # Server configuration for 2D flake tool
        if flake_status.get('active', False) or st.session_state.get('show_flake_config', False):
            st.markdown("**Server Configuration:**")
            
            current_url = flake_status.get('server_url', 'http://0.0.0.0:8000')
            server_url = st.text_input(
                "External MCP Server URL", 
                value=current_url,
                help="URL of the external 2D flake classification MCP server",
                key="flake_server_url"
            )
            
            col_test, col_save = st.columns(2)
            with col_test:
                if st.button("🔗 Test Connection", key="test_flake_connection"):
                    if server_url:
                        # Ensure flake_2d tools are activated before testing
                        if not flake_status.get('active', False):
                            st.warning("⚠️ Please activate 2D Flake tools first before testing connection")
                        else:
                            # Test actual MCP connection
                            with st.spinner(f"Testing connection to {server_url}..."):
                                try:
                                    # Get MCP client and test connection
                                    from lab_agent.mcp.client import get_mcp_client
                                    mcp_client = get_mcp_client()
                                    
                                    # Refresh tools to ensure flake tools are loaded
                                    mcp_client.refresh_tools()
                                    
                                    # Call the actual MCP tool to test connection
                                    result = asyncio.run(mcp_client.call_tool(
                                        "connect_2d_flake_server", 
                                        {"server_url": server_url, "test_connection": True}
                                    ))
                                    
                                    if result.get("success"):
                                        tool_manager.set_flake_2d_server(server_url, "connected")
                                        st.success(f"🟢 Successfully connected to {server_url}")
                                        st.info(f"ℹ️ Server response: {result.get('message', 'Connection successful')}")
                                        st.rerun()
                                    else:
                                        error_msg = result.get("error", "Unknown connection error")
                                        tool_manager.set_flake_2d_server(server_url, "failed")
                                        st.error(f"🔴 Connection failed: {error_msg}")
                                        
                                        # Show available tools for debugging
                                        available_tools = result.get('available_tools', [])
                                        if available_tools:
                                            st.info(f"Available MCP tools: {[tool.get('name') for tool in available_tools]}")
                                        
                                except Exception as e:
                                    tool_manager.set_flake_2d_server(server_url, "failed")
                                    st.error(f"🔴 Connection test failed: {str(e)}")
                                    st.error(f"Debug info: Check if MCP client is properly configured")
                    else:
                        st.error("Please enter a server URL")
            
            with col_save:
                if st.button("💾 Save Config", key="save_flake_config"):
                    if server_url:
                        tool_manager.set_flake_2d_server(server_url, "configured")
                        st.success("Configuration saved")
                        st.rerun()
                    else:
                        st.error("Please enter a server URL")
            
            # Show current connection status
            conn_status = flake_status.get('connection_status', 'disconnected')
            if conn_status == "connected":
                st.success(f"🟢 Connected to: {flake_status.get('server_url', 'N/A')}")
            elif conn_status == "configured":
                st.info(f"🟡 Configured: {flake_status.get('server_url', 'N/A')}")
            elif conn_status == "failed":
                st.error(f"🔴 Connection failed: {flake_status.get('server_url', 'N/A')}")
            else:
                st.warning("🔴 Not configured")
        
        # Image upload section (only show when tool is active)
        if flake_status.get('active', False):
            st.markdown("---")
            st.markdown("**📁 Image Upload:**")
            
            uploaded_file = st.file_uploader(
                "Upload 2D flake image for analysis",
                type=['jpg', 'jpeg', 'png', 'tiff', 'bmp'],
                help="Upload an image of your 2D material flake for quality classification",
                key="flake_image_upload"
            )
            
            if uploaded_file is not None:
                # Display image preview
                col_img, col_info = st.columns([1, 1])
                
                with col_img:
                    st.image(uploaded_file, caption=f"Preview: {uploaded_file.name}", width=200)
                
                with col_info:
                    st.markdown(f"**File:** {uploaded_file.name}")
                    st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
                    st.markdown(f"**Type:** {uploaded_file.type}")
                
                # Save uploaded file
                if st.button("💾 Save for Analysis", key="save_flake_image"):
                    if save_uploaded_image(uploaded_file):
                        st.success(f"✅ Image saved! You can now ask GPT-5-mini to analyze '{uploaded_file.name}'")
                        st.info("💡 **Try asking:** 'Analyze the uploaded flake image using the hBN_monolayer model'")
                    else:
                        st.error("❌ Failed to save image")
            
            # Show uploaded images
            uploaded_images = get_uploaded_images()
            if uploaded_images:
                st.markdown("**📋 Available Images:**")
                for img_info in uploaded_images:
                    col_name, col_actions = st.columns([3, 1])
                    with col_name:
                        st.markdown(f"• {img_info['name']} ({img_info['size']})")
                    with col_actions:
                        if st.button("🗑️", key=f"delete_{img_info['name']}", help="Delete image"):
                            if delete_uploaded_image(img_info['name']):
                                st.success(f"Deleted {img_info['name']}")
                                st.rerun()
    
    with col2:
        current_state = flake_status.get('active', False)
        if current_state:
            st.success("🟢 Active")
            if st.button("Deactivate", key="deactivate_flake"):
                tool_manager.deactivate_tool("flake_2d")
                st.success("2D Flake tools deactivated")
                st.rerun()
        else:
            st.warning("🟡 Inactive")
            if st.button("Activate", key="activate_flake"):
                tool_manager.activate_tool("flake_2d")
                st.session_state.show_flake_config = True
                st.success("2D Flake tools activated")
                st.rerun()
    
    # Show configuration button for inactive flake tool
    if not flake_status.get('active', False) and not st.session_state.get('show_flake_config', False):
        if st.button("⚙️ Configure 2D Flake Server", key="config_flake"):
            st.session_state.show_flake_config = True
            st.rerun()
    
    st.markdown("---")
    
    # Tool activation effects notice
    st.info("""
    **💡 Note:** Tool activation changes will take effect when:
    - The MCP server is restarted, or
    - GPT-5-mini creates a new conversation
    
    Currently active tools are available to GPT-5-mini for use.
    """)
    
    # Debug information (collapsible)
    with st.expander("🔧 Debug Information", expanded=False):
        st.json(tool_manager.activation_state)


if __name__ == "__main__":
    main()