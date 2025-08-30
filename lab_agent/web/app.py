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
    
    # Main navigation
    tabs = st.tabs(["🏠 Overview", "📚 ArXiv Daily", "🔧 Tools", "📋 Logs"])
    
    with tabs[0]:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("System Status")
            if st.button("Start System"):
                st.success("System started!")
                
            if st.button("Stop System"):
                st.info("System stopped!")
                
            st.subheader("Configuration")
            st.json({
                "OpenAI Model": config.openai_model,
                "Gemini Model": config.gemini_model,
                "Debug Mode": config.debug,
                "Log Level": config.log_level
            })
        
        with col2:
            st.subheader("System Overview")
            st.info("Lab Agent system ready for deployment")
            
            st.markdown("### Available Tools")
            tools = [
                "📚 ArXiv Daily - Automated paper recommendations with AI scoring",
                "🕷️ Web Scraper - Extract data from web pages",
                "🔍 ArXiv Parser - Parse research papers from ArXiv API",
                "🤖 Multi-model AI - OpenAI GPT-4 and Google Gemini integration"
            ]
            for tool in tools:
                st.markdown(f"- {tool}")

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


if __name__ == "__main__":
    main()