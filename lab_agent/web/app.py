import streamlit as st
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from datetime import datetime
import json
import hashlib
from typing import List, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lab_agent.main import LabAgent
from lab_agent.utils import Config
from lab_agent.utils.tool_manager import ToolManager
from lab_agent.agents.arxiv_daily_agent import ArxivDailyAgent
from lab_agent.tools.arxiv_chat import ArxivChat
from lab_agent.tools.llm_chatbox import LLMChatbox
from lab_agent.web.playground_components import render_playground_tab

nest_asyncio.apply()


def load_auth_config():
    """Load authentication configuration"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'auth_config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load authentication config: {e}")
        return None


def check_password():
    """Returns True if password is correct"""
    
    # Load authentication config
    auth_config = load_auth_config()
    if not auth_config:
        st.error("Authentication configuration not available")
        return False
    
    auth_settings = auth_config.get("authentication", {})
    ui_settings = auth_config.get("ui", {})
    security_settings = auth_config.get("security", {})
    
    # Check if authentication is enabled
    if not auth_settings.get("enabled", True):
        return True  # Skip authentication if disabled
    
    CORRECT_PASSWORD_HASH = auth_settings.get("password_hash")
    if not CORRECT_PASSWORD_HASH:
        st.error("Password hash not configured")
        return False
    
    def password_entered():
        # Hash the entered password and compare
        entered_hash = hashlib.sha256(
            st.session_state["password"].encode()
        ).hexdigest()
        
        if entered_hash == CORRECT_PASSWORD_HASH:
            st.session_state["authenticated"] = True
            if security_settings.get("clear_password_on_auth", True):
                del st.session_state["password"]  # Don't store password
        else:
            st.session_state["authenticated"] = False
    
    # Return True if already authenticated
    if st.session_state.get("authenticated", False):
        return True
    
    # Show login form
    st.title(ui_settings.get("login_title", "🔒 Lab Agent System - Login"))
    st.markdown(ui_settings.get("login_subtitle", "Enter the password to access the Lab Agent System"))
    st.text_input("Password", type="password", on_change=password_entered, key="password")
    
    if st.session_state.get("authenticated") == False:
        st.error(ui_settings.get("error_message", "❌ Incorrect password"))
    
    return False


def add_system_log(level: str, message: str, component: str = "System"):
    """Add a log entry to the system logs"""
    if "system_logs" not in st.session_state:
        st.session_state.system_logs = []
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "component": component,
        "message": message
    }
    
    # Add to beginning of list (most recent first)
    st.session_state.system_logs.insert(0, log_entry)
    
    # Keep only last 500 logs to prevent memory issues
    if len(st.session_state.system_logs) > 500:
        st.session_state.system_logs = st.session_state.system_logs[:500]


def playground_interface():
    """Render the model playground interface"""
    try:
        render_playground_tab()
        add_system_log("info", "Playground interface accessed", "Playground")
    except Exception as e:
        st.error(f"Failed to load playground: {e}")
        add_system_log("error", f"Playground interface error: {e}", "Playground")


def main():
    load_dotenv()
    config = Config()
    
    st.set_page_config(
        page_title="Lab Agent System",
        page_icon="🧪",
        layout="wide"
    )
    
    # Authentication check
    if not check_password():
        st.stop()  # Stop execution if not authenticated
    
    # Add logout button in sidebar
    auth_config = load_auth_config()
    ui_settings = auth_config.get("ui", {}) if auth_config else {}
    
    with st.sidebar:
        st.markdown("### Session")
        logout_text = ui_settings.get("logout_button_text", "🚪 Logout")
        if st.button(logout_text, use_container_width=True):
            add_system_log("info", "User logged out", "Authentication")
            st.session_state["authenticated"] = False
            st.rerun()
    
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
    
    # Initialize LLM chatbox
    if "llm_chatbox" not in st.session_state:
        try:
            st.session_state.llm_chatbox = LLMChatbox()
        except Exception as e:
            st.error(f"Failed to initialize AI chatbox: {e}")
            st.session_state.llm_chatbox = None
    
    # Initialize overview chat messages
    if "overview_chat_messages" not in st.session_state:
        st.session_state.overview_chat_messages = []
    
    # Initialize tool manager
    if "tool_manager" not in st.session_state:
        st.session_state.tool_manager = ToolManager()
    
    # Initialize system logs
    if "system_logs" not in st.session_state:
        st.session_state.system_logs = []
        add_system_log("info", "Lab Agent System initialized successfully")
    
    # Main navigation
    tabs = st.tabs(["🏠 Overview", "📚 ArXiv Daily", "🔧 Tools", "🎮 Playground", "📋 Logs"])
    
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
                        "ArXiv Chat Model": models_data.get('chatModel', {}).get('name', 'gpt-5'),
                        "AI Chatbox": "gpt-4.1 (MCP enabled)",
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
                "🤖 AI Assistant - AI chatbox with MCP tools for ArXiv Daily & 2D Flakes"
            ]
            for tool in tools:
                st.markdown(f"- {tool}")
        
        with col3:
            llm_chatbox_interface()

    with tabs[1]:
        arxiv_daily_interface()
        
    with tabs[2]:
        tools_interface()
        
    with tabs[3]:
        playground_interface()
        
    with tabs[4]:
        logs_interface()


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
                add_system_log("info", "Daily report generation started", "ArXiv Daily")
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
                    add_system_log("info", f"Daily report retrieved from cache: {result['total_papers']} papers", "ArXiv Daily")
                else:
                    st.success(f"✅ {result['message']}")
                    add_system_log("info", f"Daily report generated successfully: {result['total_papers']} papers", "ArXiv Daily")
                
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
                add_system_log("error", f"Daily report generation failed: {result.get('error', 'Unknown error')}", "ArXiv Daily")
                
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
                # Assistant message with collapsible content for long responses
                with st.chat_message("assistant"):
                    render_collapsible_message(
                        content=message["content"],
                        message_list=st.session_state.chat_messages,
                        message=message,
                        prefix="expand_arxiv_msg"
                    )
    
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


def llm_chatbox_interface():
    """AI chatbox interface for general assistance and MCP tools"""
    if st.session_state.llm_chatbox is None:
        st.error("LLM chatbox not available. Please check your OpenAI API key.")
        return
    
    # Get UI configuration
    ui_config = st.session_state.llm_chatbox.get_ui_config()
    
    st.subheader(ui_config["title"])
    st.markdown(f"*{ui_config['subtitle']}*")
    
    # File Upload Section
    with st.expander("📁 File Upload & Management", expanded=False):
        st.markdown("Upload flake images for 2D material analysis. Once uploaded, you can reference them by name in your chat.")
        st.info("💡 **Usage:** After uploading, simply say 'Analyze [filename.jpg]' or 'Complete flake analysis for my_image.png'")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'],
            help="Upload images of 2D material flakes for analysis",
            key="main_file_upload"
        )
        
        if uploaded_file is not None:
            # Display preview and info
            col_preview, col_info = st.columns([1, 1])
            
            with col_preview:
                st.image(uploaded_file, caption=f"Preview: {uploaded_file.name}", width=200)
            
            with col_info:
                st.markdown(f"**File:** {uploaded_file.name}")
                st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
                st.markdown(f"**Type:** {uploaded_file.type}")
                
                # Check if file is already saved
                uploads_dir = os.path.join(os.getcwd(), "uploads", "flake_images")
                file_path = os.path.join(uploads_dir, uploaded_file.name)
                file_already_exists = os.path.exists(file_path)
                
                if file_already_exists:
                    st.info("✅ File already saved for analysis")
                    if st.button("🔄 Re-save", key="resave_main_upload"):
                        with st.spinner("Re-saving image..."):
                            success = save_uploaded_image(uploaded_file)
                            if success:
                                st.success(f"✅ Image re-saved! You can reference '{uploaded_file.name}' in your chat.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to re-save image")
                else:
                    # Save button
                    if st.button("💾 Save for Analysis", key="save_main_upload"):
                        with st.spinner("Saving image..."):
                            success = save_uploaded_image(uploaded_file)
                            if success:
                                st.success(f"✅ Image saved! You can now reference '{uploaded_file.name}' in your chat.")
                                add_system_log("info", f"Image uploaded and saved: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)", "File Upload")
                                # Small delay to ensure message is visible before rerun
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to save image")
                                add_system_log("error", f"Failed to save uploaded image: {uploaded_file.name}", "File Upload")
        
        # Show uploaded files
        uploaded_images = get_uploaded_images()
        if uploaded_images:
            st.markdown("---")
            st.markdown("**📋 Available Images:**")
            st.info("📁 = Pre-existing files (persistent across sessions) | 🆕 = Current session uploads")
            
            for img_info in uploaded_images:
                col_name, col_info, col_actions = st.columns([3, 1, 1])
                
                with col_name:
                    # Show file source indicator
                    source_icon = "📁" if img_info.get('source') == 'filesystem' else "🆕"
                    source_help = "Pre-existing file" if img_info.get('source') == 'filesystem' else "Current session"
                    
                    st.markdown(f"{source_icon} **{img_info['name']}**")
                    st.code(f"Analyze {img_info['name']}", language=None)  # Quick reference format
                
                with col_info:
                    st.text(img_info['size'])
                    # Show upload date
                    upload_date = img_info.get('uploaded_at', '')[:10] if img_info.get('uploaded_at') else 'Unknown'
                    st.caption(upload_date)
                
                with col_actions:
                    if st.button("🗑️", key=f"delete_main_{img_info['name']}", help="Delete image"):
                        if delete_uploaded_image(img_info['name']):
                            st.success(f"Deleted {img_info['name']}")
                            st.rerun()
                
                # Optional: Show image preview in expander
                with st.expander(f"Preview {img_info['name']}", expanded=False):
                    try:
                        st.image(img_info['path'], width=300)
                        st.caption(f"Uploaded: {img_info['uploaded_at'][:19]}")
                    except Exception as e:
                        st.error(f"Cannot preview image: {e}")
        else:
            st.info("No images uploaded yet. Upload images above to get started with flake analysis.")
    
    # Show MCP tools info
    mcp_info = st.session_state.llm_chatbox.get_mcp_tools_info()
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
            if st.session_state.llm_chatbox:
                st.session_state.llm_chatbox.clear_conversation()
            st.rerun()
    
    with col2:
        chat_summary = st.session_state.llm_chatbox.get_conversation_summary()
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
                # Assistant message with collapsible content for long responses
                with st.chat_message("assistant"):
                    render_collapsible_message(
                        content=message["content"],
                        message_list=st.session_state.overview_chat_messages,
                        message=message,
                        prefix="expand_overview_msg"
                    )
                    
                    # Show reasoning if available and enabled
                    if (message.get("reasoning") and 
                        st.session_state.llm_chatbox.enable_reasoning_display() and
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
        suggestions = st.session_state.llm_chatbox.get_suggested_prompts()
        
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
        with st.spinner("Model thinking..."):
            response = asyncio.run(st.session_state.llm_chatbox.chat(user_message))
        
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
        if uploaded_file is None:
            st.error("No file provided to save")
            return False
        
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.getcwd(), "uploads", "flake_images")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Check if file already exists
        file_path = os.path.join(uploads_dir, uploaded_file.name)
        if os.path.exists(file_path):
            st.warning(f"File '{uploaded_file.name}' already exists. Overwriting...")
        
        # Save file with original name
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        except Exception as write_error:
            st.error(f"Failed to write file: {write_error}")
            return False
        
        # Verify file was saved correctly
        if not os.path.exists(file_path):
            st.error("File was not saved correctly")
            return False
        
        # Check file size
        saved_size = os.path.getsize(file_path)
        if saved_size != uploaded_file.size:
            st.warning(f"File size mismatch: expected {uploaded_file.size}, got {saved_size}")
        
        # Store file info in session state for reference
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
                'uploaded_at': datetime.now().isoformat(),
                'source': 'session'
            })
        
        # st.success(f"File saved successfully: {file_path}")  # Remove duplicate success message
        return True
        
    except Exception as e:
        st.error(f"Unexpected error saving image: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return False

def get_uploaded_images() -> List[Dict]:
    """Get list of uploaded images from filesystem and session"""
    uploads_dir = os.path.join(os.getcwd(), "uploads", "flake_images")
    
    # Initialize session state if needed
    if "uploaded_flake_images" not in st.session_state:
        st.session_state.uploaded_flake_images = []
    
    # Scan actual filesystem for all image files
    all_images = {}  # Use dict to avoid duplicates, keyed by filename
    
    # Add files from filesystem
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            
            # Check if it's an image file
            if os.path.isfile(file_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp')):
                try:
                    file_stat = os.stat(file_path)
                    all_images[filename] = {
                        'name': filename,
                        'path': file_path,
                        'size': f"{file_stat.st_size / 1024:.1f} KB",
                        'type': f"image/{filename.split('.')[-1].lower()}",
                        'uploaded_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'source': 'filesystem'
                    }
                except Exception as e:
                    continue  # Skip files that can't be read
    
    # Update/merge with session state data (which may have additional metadata)
    for img_info in st.session_state.uploaded_flake_images:
        if os.path.exists(img_info['path']):
            filename = img_info['name']
            # Update with session metadata if available
            if filename in all_images:
                all_images[filename].update({
                    'uploaded_at': img_info.get('uploaded_at', all_images[filename]['uploaded_at']),
                    'source': 'session'
                })
            else:
                # File from session but not found in directory scan
                all_images[filename] = img_info
    
    # Convert back to list and sort by upload time (newest first)
    valid_images = list(all_images.values())
    valid_images.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
    
    # Update session state with merged data
    st.session_state.uploaded_flake_images = valid_images
    
    return valid_images

def render_collapsible_message(content: str, message_list: list, message: dict, prefix: str = "expand_msg") -> None:
    """Render a message with collapsible functionality for long content"""
    content_length = len(content)
    
    # Get threshold from configuration (default to 800 if not available)
    collapse_threshold = 800
    try:
        if hasattr(st.session_state, 'llm_chatbox') and st.session_state.llm_chatbox:
            collapse_threshold = st.session_state.llm_chatbox.config.get(
                "conversation_settings", {}
            ).get("auto_collapse_threshold", 800)
    except:
        pass  # Use default if config unavailable
    
    if content_length > collapse_threshold:
        # Show truncated version with expand option
        preview_length = min(300, collapse_threshold // 3)
        preview_text = content[:preview_length] + "..."
        
        # Show preview by default
        st.write(preview_text)
        
        # Add visual indicator for collapsed content
        st.caption(f"💬 {content_length:,} characters total - Click below to expand full response")
        
        # Collapsible full response
        with st.expander(f"📄 Show Full Response", expanded=False):
            st.write(content)
    else:
        # Short response - show directly
        st.write(content)


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

def check_fastmcp_connection_status():
    """Check if FastMCP tools are available and update connection status"""
    try:
        from lab_agent.mcp.client import get_mcp_client
        mcp_client = get_mcp_client()
        
        # Check if FastMCP tools are available
        available_tools = mcp_client.get_available_tools()
        fastmcp_tools = ['list_models', 'upload_image', 'predict_flake_quality', 'get_prediction_history']
        
        fastmcp_available = any(tool['name'] in fastmcp_tools for tool in available_tools)
        
        if fastmcp_available:
            # Try to call list_models to verify actual connectivity
            try:
                result = asyncio.run(mcp_client.call_tool("list_models", {}))
                if result.get("success"):
                    return "connected"
                else:
                    return "failed"
            except:
                return "failed"
        else:
            return "failed"
    except:
        return "failed"


def logs_interface():
    """System logs interface"""
    st.subheader("📋 System Logs")
    st.markdown("View real-time system activity and events")
    
    # Log controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        # Filter by log level
        log_levels = ["ALL", "INFO", "WARNING", "ERROR"]
        selected_level = st.selectbox("Filter by Level", log_levels, key="log_level_filter")
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.system_logs = []
            add_system_log("info", "System logs cleared by user", "System")
            st.success("Logs cleared")
            st.rerun()
    
    with col4:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=False)
        if auto_refresh:
            st.rerun()
    
    st.markdown("---")
    
    # Display logs
    logs = st.session_state.get("system_logs", [])
    
    if not logs:
        st.info("No logs available. Interact with the system to generate log entries.")
        return
    
    # Filter logs by level
    if selected_level != "ALL":
        logs = [log for log in logs if log["level"] == selected_level]
    
    # Show logs count
    st.caption(f"Showing {len(logs)} log entries (most recent first)")
    
    # Display logs in a scrollable container
    log_container = st.container()
    
    with log_container:
        for i, log in enumerate(logs[:100]):  # Show first 100 logs
            # Color coding for different log levels
            if log["level"] == "ERROR":
                st.error(f"🔴 **{log['timestamp']}** | {log['component']} | {log['message']}")
            elif log["level"] == "WARNING":
                st.warning(f"🟡 **{log['timestamp']}** | {log['component']} | {log['message']}")
            else:
                st.info(f"ℹ️ **{log['timestamp']}** | {log['component']} | {log['message']}")
    
    if len(logs) > 100:
        st.caption(f"Showing first 100 of {len(logs)} total logs")
    
    # Show external log file option
    st.markdown("---")
    st.markdown("### 📄 External Log Files")
    
    if st.button("📁 Load Conversation Logs", use_container_width=True):
        try:
            conversation_log_path = "logs/conversation_trace.log"
            if os.path.exists(conversation_log_path):
                with open(conversation_log_path, 'r') as f:
                    content = f.read()
                    # Show last 20 lines
                    lines = content.strip().split('\n')
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    
                st.text_area(
                    "Recent Conversation Log Entries", 
                    "\n".join(recent_lines), 
                    height=300,
                    help="Showing last 20 lines of conversation_trace.log"
                )
            else:
                st.warning("Conversation log file not found")
        except Exception as e:
            st.error(f"Error loading conversation logs: {e}")


def tools_interface():
    """Tools activation and management interface"""
    st.subheader("🔧 Tool Management")
    st.markdown("Activate or deactivate MCP tools for the Lab Agent system")
    
    tool_manager = st.session_state.tool_manager
    
    # Refresh tool manager state
    if st.button("🔄 Refresh Tool Status", use_container_width=True):
        st.session_state.tool_manager = ToolManager()
        # Also update FastMCP connection status
        if st.session_state.tool_manager.get_tool_status("flake_2d").get('active', False):
            current_url = st.session_state.tool_manager.get_tool_status("flake_2d").get('server_url', 'http://localhost:8000')
            connection_status = check_fastmcp_connection_status()
            st.session_state.tool_manager.set_flake_2d_server(current_url, connection_status)
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
                add_system_log("info", "ArXiv Daily tools deactivated", "Tool Management")
                st.success("ArXiv Daily tools deactivated")
                st.rerun()
        else:
            st.warning("🟡 Inactive")
            if st.button("Activate", key="activate_arxiv"):
                tool_manager.activate_tool("arxiv_daily")
                add_system_log("info", "ArXiv Daily tools activated", "Tool Management")
                st.success("ArXiv Daily tools activated")
                st.rerun()
    
    st.markdown("---")
    
    # 2D Flake Classification Tools section
    st.markdown("### 🔬 2D Flake Classification Tools")
    flake_status = tool_manager.get_tool_status("flake_2d")
    
    # Auto-update connection status if tools are active
    if flake_status.get('active', False) and flake_status.get('connection_status', 'failed') == 'failed':
        # Check if FastMCP tools are actually working
        connection_status = check_fastmcp_connection_status()
        if connection_status == 'connected':
            current_url = flake_status.get('server_url', 'http://localhost:8000')
            tool_manager.set_flake_2d_server(current_url, connection_status)
            flake_status = tool_manager.get_tool_status("flake_2d")  # Refresh status
    
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
                                    
                                    # Test connection using list_models (simplest FastMCP tool)
                                    result = asyncio.run(mcp_client.call_tool("list_models", {}))
                                    
                                    if result.get("success"):
                                        tool_manager.set_flake_2d_server(server_url, "connected")
                                        st.success(f"🟢 Successfully connected to {server_url}")
                                        add_system_log("info", f"Successfully connected to FastMCP server: {server_url}", "2D Flake Tools")
                                        
                                        # Show available models if data is available
                                        models_data = result.get('data', {})
                                        if models_data:
                                            available_models = models_data.get('models', [])
                                            if available_models:
                                                st.info(f"✅ Found {len(available_models)} available models: {', '.join(available_models[:3])}{'...' if len(available_models) > 3 else ''}")
                                                add_system_log("info", f"Found {len(available_models)} models on server", "2D Flake Tools")
                                            else:
                                                st.info("✅ Connection successful, server responding")
                                        else:
                                            st.info("✅ Connection successful")
                                        st.rerun()
                                    else:
                                        error_msg = result.get("error", "FastMCP server not responding")
                                        tool_manager.set_flake_2d_server(server_url, "failed")
                                        st.error(f"🔴 Connection failed: {error_msg}")
                                        add_system_log("error", f"FastMCP server connection failed: {error_msg}", "2D Flake Tools")
                                        
                                        # Show helpful debugging info
                                        st.info("💡 Make sure your FastMCP server is running on the specified URL")
                                        
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
        
        # Image management section (only show when tool is active)
        if flake_status.get('active', False):
            st.markdown("---")
            st.markdown("**📁 Image Management:**")
            st.info("💡 Upload flake images in the **Overview tab → File Upload & Management** section, then reference them by name in the AI Assistant chat.")
            
            # Show uploaded images
            uploaded_images = get_uploaded_images()
            if uploaded_images:
                st.markdown("**📋 Currently Available Images:**")
                st.caption("📁 = Persistent files | 🆕 = Current session")
                
                for img_info in uploaded_images:
                    col_name, col_info, col_actions = st.columns([2, 1, 1])
                    with col_name:
                        # Show file source indicator
                        source_icon = "📁" if img_info.get('source') == 'filesystem' else "🆕"
                        st.markdown(f"{source_icon} **{img_info['name']}**")
                    with col_info:
                        st.text(f"{img_info['size']}")
                        # Show date
                        upload_date = img_info.get('uploaded_at', '')[:10] if img_info.get('uploaded_at') else ''
                        if upload_date:
                            st.caption(upload_date)
                    with col_actions:
                        if st.button("🗑️", key=f"delete_tools_{img_info['name']}", help="Delete image"):
                            if delete_uploaded_image(img_info['name']):
                                st.success(f"Deleted {img_info['name']}")
                                st.rerun()
            else:
                st.warning("No images uploaded yet. Go to **Overview tab → File Upload & Management** to upload images.")
    
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
    - AI Assistant creates a new conversation
    
    Currently active tools are available to the AI Assistant for use.
    """)
    
    # Debug information (collapsible)
    with st.expander("🔧 Debug Information", expanded=False):
        st.json(tool_manager.activation_state)


if __name__ == "__main__":
    main()