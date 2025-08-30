# Lab Agent - Multi-Agent System for Laboratory Automation

A multi-agent system for laboratory automation and research, specializing in automated research paper monitoring, device control, and AI-powered analysis for condensed matter physics labs.

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/caijiaqi/labAgent.git
cd labAgent

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

### 2. Configuration

Edit `.env` file with your API keys:

```bash
# Required for ArXiv Daily Updates and MCP Tools
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5

# Optional  
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Run the System

```bash
# Web Interface (Recommended)
streamlit run lab_agent/web/app.py

# Command Line Interface
python -m lab_agent.main
```

## ✨ Features

### 📚 ArXiv Daily Paper Recommendations (Ready)
- **Automated Scraping**: Fetches latest papers from arXiv cond-mat/new
- **AI-Powered Scoring**: GPT-4 rates paper relevance (1-3 priority levels) 
- **Smart Filtering**: Focuses on 2D materials, graphene, TMDs, quantum devices
- **Beautiful Reports**: Generates HTML reports with priority sections
- **Web Interface**: Manual trigger, report viewing, and management
- **No Database**: Simple file-based storage

**Usage**: Navigate to "📚 ArXiv Daily" tab → Click "Generate Daily Report"

### 🔬 Planned Features
- **MCP Server for Microscope Control**: Nikon glovebox microscope automation
- **Deep Learning Tool Integration**: Automated flake analysis and scoring  
- **Multi-Agent Coordination**: OpenAI and Google Gemini integration
- **Real-time Communication**: WebSocket support for agent coordination

## 📁 Project Structure

```
labAgent/
├── lab_agent/                     # Main package
│   ├── agents/                    # Agent implementations
│   │   ├── base_agent.py         # Abstract base class
│   │   └── arxiv_daily_agent.py  # ArXiv monitoring agent
│   ├── tools/                    # Agent capabilities
│   │   ├── arxiv_daily_scraper.py # Web scraping for ArXiv
│   │   ├── paper_scorer.py       # GPT-4 paper scoring
│   │   ├── daily_report_generator.py # HTML/JSON reports
│   │   ├── web_scraper.py        # General web scraping
│   │   └── arxiv_parser.py       # ArXiv API integration
│   ├── utils/                    # Utilities
│   │   ├── config.py             # Environment configuration
│   │   └── logger.py             # Logging setup
│   ├── config/                   # Configuration files
│   │   ├── interestKeywords.txt  # Research interest keywords
│   │   └── promptArxivRecommender.txt # GPT scoring prompts
│   └── web/                      # Streamlit interface
│       └── app.py                # Main web application
├── requirements.txt              # Python dependencies
├── setup.py                     # Package configuration
├── .env.example                 # Environment template
├── CLAUDE.md                    # Project context for Claude Code
├── TESTING_GUIDE.md            # Comprehensive testing protocol
└── README.md                   # This file
```

## 🧪 Testing

Follow the comprehensive testing guide in `TESTING_GUIDE.md`:

```bash
# Quick test - verify system works
streamlit run lab_agent/web/app.py
# → Go to ArXiv Daily tab → Generate Daily Report

# Full testing protocol
cat TESTING_GUIDE.md
```

## 🔧 Configuration

### Research Interest Keywords

Edit `lab_agent/config/interestKeywords.txt` to customize paper filtering:

```
# 2D Materials & Graphene
2D materials
graphene
monolayer graphene
transition metal dichalcogenides
van der Waals heterostructures
# ... add your research areas
```

### AI Scoring Prompts

Modify `lab_agent/config/promptArxivRecommender.txt` for different evaluation criteria.

## 📊 Usage Examples

### Generate Daily ArXiv Report

```python
from lab_agent.agents.arxiv_daily_agent import ArxivDailyAgent
import asyncio

# Initialize agent
agent = ArxivDailyAgent({'reports_dir': './reports'})
await agent.initialize()

# Generate report
task = {
    'type': 'generate_daily_report',
    'url': 'https://arxiv.org/list/cond-mat/new'
}
result = await agent.process_task(task)
print(f"Generated report with {result['total_papers']} papers")
```

### Use Web Interface

1. **Start Application**: `streamlit run lab_agent/web/app.py`
2. **Navigate**: Go to "📚 ArXiv Daily" tab
3. **Generate**: Click "🔄 Generate Daily Report" 
4. **View**: Expand report section to see results
5. **Manage**: Use "🗑️ Clear All Reports" to cleanup

## 🛠️ Development

### Install in Development Mode

```bash
pip install -e .

# Use console entry points
lab-agent        # CLI version
lab-agent-web    # Web version
```

### Architecture

- **Async-first**: All agents built on asyncio
- **Modular Design**: Separate agents, tools, and utilities
- **Configuration-driven**: Environment-based settings
- **Tool-based**: Agents use composable tools for capabilities

## 🔍 Troubleshooting

### Common Issues

**"ArXiv agent not available"**
- Check OpenAI API key in `.env` file
- Verify API key is valid and has credits

**"No papers found"** 
- Check internet connection
- Verify ArXiv website is accessible

**Slow GPT scoring**
- Normal for 20+ papers (includes rate limiting)
- Consider upgrading to higher tier OpenAI plan

**Permission errors**
- Ensure write permissions in project directory
- Check `./reports/` directory can be created

### Debug Mode

Enable detailed logging:

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG
```

## 🗺️ Roadmap

### Phase 1: Test (Current)
- ✅ **Milestone 0**: ArXiv Daily Update System
- 🚧 **Milestone 1**: MCP Server for Nikon Microscope
- 📋 **Milestone 2**: Deep Learning Tool Integration 
- 📋 **Milestone 3**: Multi-Agent SDK Wiring

### Phase 2: Framework
- General scaling framework and best practices

### Phase 3: AI-Ready Lab
- Advanced automation capabilities

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/caijiaqi/labAgent/issues)
- **Documentation**: See `CLAUDE.md` for detailed project context
- **Testing**: Follow `TESTING_GUIDE.md` for validation

---

**Built for condensed matter physics research labs** 🔬⚛️
