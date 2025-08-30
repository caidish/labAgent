import streamlit as st
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from datetime import datetime
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lab_agent.main import LabAgent
from lab_agent.utils import Config
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
                "🕷️ Web Scraper - Extract data from web pages",
                "🔍 ArXiv Parser - Parse research papers from ArXiv API",
                "🤖 Multi-model AI - OpenAI GPT-4 and Google Gemini integration",
                "🤖 GPT-5-mini Assistant - AI chatbox with active MCP tools for ArXiv Daily"
            ]
            for tool in tools:
                st.markdown(f"- {tool}")
        
        with col3:
            gpt5_mini_chatbox_interface()

    with tabs[1]:
        arxiv_daily_interface()
        
    with tabs[2]:
        st.subheader("Available Tools")
        st.info("Individual tool interfaces will be added here")
        
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
            
            # Show active tools
            active_tools = mcp_info.get("active_tools", [])
            if active_tools:
                st.markdown("**🟢 Active ArXiv Daily Tools:**")
                for tool in active_tools:
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


if __name__ == "__main__":
    main()