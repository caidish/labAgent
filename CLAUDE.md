# Claude Code Context - Lab Agent

## Project Overview
Multi-agent system for laboratory automation and research using OpenAI GPT-4, Google Gemini, and various tools for web scraping, research paper analysis, and real-time communication.

## Current Status
✅ **COMPLETED**
- Basic project structure with proper Python packaging
- All dependencies installed and working
- Streamlit web interface functional
- Core modules created: agents, tools, utils, web
- Configuration system with environment variables
- Base agent framework implemented
- Web scraping tool with BeautifulSoup
- ArXiv research paper parser
- Logging system

🚧 **IN PROGRESS**
- Project 1.1: MCP Server for Glovebox Nikon Microscope

## 🗺️ PROJECT ROADMAP

### **Project 1: Test Phase** 

#### **Milestone 0: ArXiv Daily Update Model**
✅ **COMPLETED** - 2025-08-29
- **ArXiv Daily Scraper**: Scrapes https://arxiv.org/list/cond-mat/new for new papers
- **GPT-4 Scoring System**: AI-powered paper relevance scoring (1-3 priority levels)
- **Daily Report Generator**: Beautiful HTML reports with priority sections
- **Web Interface**: Manual trigger, report viewing, and clear functionality
- **Smart Chat System**: GPT-4o chat interface for discussing papers
- **Configuration**: Complete config system with keywords, prompts, and models
- **Duplicate Prevention**: Won't regenerate existing daily reports
- **No Database**: File-based storage for simplicity

**Key Components:**
- `lab_agent/tools/arxiv_daily_scraper.py` - Web scraping for ArXiv
- `lab_agent/tools/paper_scorer.py` - GPT-4 integration for scoring
- `lab_agent/tools/daily_report_generator.py` - HTML/JSON report generation
- `lab_agent/tools/arxiv_chat.py` - GPT-4o chat interface
- `lab_agent/agents/arxiv_daily_agent.py` - Main orchestration agent
- `lab_agent/web/app.py` - Streamlit interface with ArXiv Daily + Chat
- `lab_agent/config/interestKeywords.txt` - Research interest keywords
- `lab_agent/config/promptArxivRecommender.txt` - GPT scoring prompts
- `lab_agent/config/arXivChatPrompt.txt` - Chat system prompts  
- `lab_agent/config/models.json` - Model configuration (GPT-4o)

**Performance:**
- New reports: 2-4 minutes (scraping + AI scoring)
- Cached reports: <1 second (duplicate prevention)
- Chat responses: 2-5 seconds per message
- Typical daily volume: 20-50 papers processed

**Status**: ✅ **PRODUCTION READY** - Fully functional with chat interface

#### **Project 1.1: MCP Server for Glovebox Nikon Microscope**

**M0 — Discovery & Control Audit (1-2 days)**
- [ ] Inventory control paths: vendor SDK (NIS-Elements/Nikon SDK), camera API, stages, illumination, filter wheels
- [ ] Decide transport to hardware (USB/serial/ethernet) and OS host
- [ ] **Deliverable**: Device map + command table document
- [ ] **Accept**: Can manually move stage, snap image from script

**M1 — MCP Skeleton & Tool Contracts (2-3 days)**
- [ ] Stand up MCP server (Node/TS or Python) with health check + list_tools
- [ ] Define core tools:
  - [ ] `microscope.snap_image({exposure_ms, gain, save_path})`
  - [ ] `stage.move({x,y,z, speed})`, `stage.home()`
  - [ ] `focus.autofocus({mode})`
  - [ ] `illum.set({channel, intensity})`
  - [ ] `objective.set({mag})`
- [ ] **Deliverable**: Repo + OpenAPI/JSON schemas for tools
- [ ] **Accept**: Client can call each tool; stubbed responses OK

**M2 — Real Hardware Binding (3-5 days)**
- [ ] Implement bindings to SDK/driver; add robust error mapping to MCP errors
- [ ] Add configuration profile: camera ID, stage limits, soft guards for glovebox
- [ ] **Deliverable**: Live tool calls perform physical actions & capture files
- [ ] **Accept**: 10/10 success for scripted sequence (home → move → autofocus → snap)

**M3 — Reliability & Safety (2-3 days)**
- [ ] Interlocks: Z-limit, door sensors, cooldowns, emergency stop tool
- [ ] Observability: structured logs, metrics (latency, error codes), dry-run mode
- [ ] **Deliverable**: Safety policy + tests
- [ ] **Accept**: Fuzz test of invalid params never moves hardware; alarms logged

**M4 — Smart Routines (3-4 days)**
- [ ] Composite tools: `scan.grid()`, `scan.spiral()`, `focus.stack()`; batched snaps
- [ ] Metadata sidecar (JSON) per image: stage, optics, lighting, timestamp, hash
- [ ] **Deliverable**: Scan of 2×2 mm area with stitched overview
- [ ] **Accept**: Mosaic preview generated; metadata complete and consistent

#### **Project 1.2: MCP Server for Deep-Learning Tool**

**M0 — Model Pipeline Spec (1 day)**
- [ ] Choose models (segmentation/classification), input contract, output JSON
- [ ] **Deliverable**: I/O spec + versioning plan
- [ ] **Accept**: Sample request/response pair agreed

**M1 — MCP Skeleton & Tools (2 days)**
- [ ] Tools:
  - [ ] `analyze.image({path, tasks:[segmentation, thickness, cleanliness]})`
  - [ ] `analyze.batch({paths[], max_concurrency})`
  - [ ] `dataset.add({path, label, notes})`
  - [ ] `model.status()` / `model.version()`
- [ ] **Deliverable**: Repo with mocked outputs
- [ ] **Accept**: Client can run end-to-end mock analysis

**M2 — Inference Engine Integration (3-4 days)**
- [ ] Wire to local GPU/cluster/Vertex/SageMaker; streaming progress events
- [ ] Standardize outputs: mask URI(s), scalar metrics (flake area, aspect, edges), QC flags
- [ ] **Deliverable**: Real masks + CSV/JSON summaries
- [ ] **Accept**: 20-image batch completes ≤ target time; outputs pass schema checks

**M3 — Post-processing & Scoring (2-3 days)**
- [ ] Heuristics for "candidate 2D flakes": size ranges, uniformity, contamination score
- [ ] Export pack: cropped tiles, masks, metrics table
- [ ] **Deliverable**: export/candidates_yyyymmdd/… folder with artifacts
- [ ] **Accept**: At least N correctly flagged candidates in known test set

**M4 — Caching, Reproducibility, Observability (2-3 days)**
- [ ] Content-hash cache, run manifests, model+code digests, metric dashboards
- [ ] **Deliverable**: "Rerun with manifest" reproduces identical results
- [ ] **Accept**: Byte-for-byte identical JSON on rerun

#### **Project 1.3: Agent SDK Wiring (OpenAI / Google)**

**M0 — Agent Plans & Prompts (1-2 days)**
- [ ] Write role/policy prompts for: Scout (microscope ops), Analyst (DL results), Planner (scan → analyze loop)
- [ ] **Deliverable**: Prompt pack + guardrails (cost, safety, timeouts)
- [ ] **Accept**: Dry-run plans are sensible on synthetic inputs

**M1 — Tool Adapters (2-3 days)**
- [ ] Register both MCP servers with agent runtime; implement auth + rate limits
- [ ] Normalize tool schemas to SDK's tool/function calling format
- [ ] **Deliverable**: Agent can call scan.grid → analyze.batch
- [ ] **Accept**: One-click "scan+analyze" demo completes on small area

**M2 — In-Context Learning Workflows (2-3 days)**
- [ ] Few-shot exemplars: "Given overview + metadata, pick ROIs; justify selection"
- [ ] Retrieval: store previous good/bad flakes and operator notes; auto-include
- [ ] **Deliverable**: .jsonl exemplar bank + retrieval hook
- [ ] **Accept**: Agent prioritizes regions similar to previous successes

**M3 — Evaluation Harness (2 days)**
- [ ] Define KPIs: yield of usable flakes per hour, false-positive rate, mean time to candidate, human-time saved
- [ ] Scripted eval scenes (simulated microscope or recorded scans)
- [ ] **Deliverable**: Leaderboard report per model/agent config
- [ ] **Accept**: Reproducible eval run outputs KPI table

**M4 — Operator UX & Safety (2-3 days)**
- [ ] "Dry-run/confirm" mode before physical moves; auto-summaries after runs
- [ ] Cost & token budget guards; escalation to human when uncertainty high
- [ ] **Deliverable**: Simple CLI or web panel + transcripts + artifact links
- [ ] **Accept**: Demo with human-in-the-loop confirmation works end-to-end

#### **Cross-Cutting Requirements (All Projects)**
- [ ] **Config & Secrets**: .env + profiles (dev/glovebox/CI)
- [ ] **Data Layout**: /raw, /processed, /exports, checksums
- [ ] **CI/CD Tests**: Schema, contracts, linting
- [ ] **Security & Docs**: Least-privilege, quickstart runbooks

### **Project 2: General Framework & Best Practices**
- [ ] Layout general framework for scaling this protocol
- [ ] Document best practices for lab automation
- [ ] Create reusable patterns and templates

### **Project 3: AI-Ready Lab (2-Nano Move)**
- [ ] TBD - Advanced lab automation capabilities

## 📋 **IMMEDIATE NEXT STEPS**
- [ ] Start with Project 1 Milestone 0: ArXiv daily update automation
- [ ] Begin MCP server discovery phase for Nikon microscope
- [ ] Set up development environment for MCP server development

## Tech Stack

### AI Models & APIs
- **OpenAI GPT-4** - Primary AI model for agents
- **Google Gemini API** - Secondary model for evaluation/comparison

### Core Python Libraries
- **Web Scraping**: requests, beautifulsoup4, lxml
- **Utilities**: tqdm, pytz, holidays
- **Research**: feedparser (ArXiv RSS/Atom parsing)
- **AI Integration**: openai library

### Multi-Agent Extensions
- **Web Interface**: streamlit
- **Real-time Communication**: websockets
- **Async Support**: nest-asyncio

## Quick Start Commands

### Installation
```bash
pip install -r requirements.txt
```

### Run Web Interface
```bash
streamlit run lab_agent/web/app.py
```

### Run CLI
```bash
python -m lab_agent.main
```

### Development
```bash
# Install in development mode
pip install -e .

# Run with console entry point
lab-agent        # CLI version
lab-agent-web    # Web version
```

## Project Structure
```
labAgent/
├── lab_agent/              # Main package
│   ├── main.py            # Main entry point and LabAgent class
│   ├── agents/            # Agent implementations
│   │   ├── base_agent.py  # Abstract base class for all agents
│   │   └── __init__.py
│   ├── tools/             # Agent capabilities
│   │   ├── web_scraper.py # Web scraping with requests/BeautifulSoup
│   │   ├── arxiv_parser.py# Research paper parsing from ArXiv
│   │   └── __init__.py
│   ├── utils/             # Shared utilities
│   │   ├── config.py      # Environment-based configuration
│   │   ├── logger.py      # Logging setup
│   │   └── __init__.py
│   └── web/               # Streamlit web interface
│       ├── app.py         # Main Streamlit dashboard
│       └── __init__.py
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
├── setup.py              # Package configuration
├── .env.example          # Environment variables template
└── .gitignore           # Git ignore rules
```

## Configuration

### Required Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
# Essential
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here  # Optional

# Optional with defaults
OPENAI_MODEL=gpt-4
GEMINI_MODEL=gemini-pro
DEBUG=false
LOG_LEVEL=INFO
```

## Architecture Notes

### Agent System
- **BaseAgent**: Abstract base class in `lab_agent/agents/base_agent.py`
- Agents are async-first with lifecycle management (start/stop/cleanup)
- Each agent has name, config, and task processing capabilities

### Tools System
- **WebScraper**: Handles web scraping with rate limiting and error handling
- **ArxivParser**: Parses research papers from ArXiv API using feedparser
- Tools are designed to be used by agents for specific capabilities

### Configuration
- Environment-based configuration in `lab_agent/utils/config.py`
- Validation for required API keys
- Support for development and production settings

## Common Issues & Solutions

### Import Errors
- Ensure you're running from project root
- Use `python -m lab_agent.main` instead of direct file execution
- Web app uses absolute imports with sys.path modification

### Missing Dependencies
- Run `pip install -r requirements.txt` if you get import errors
- Use virtual environment to avoid conflicts

## Development Workflow
1. Create feature branch: `git checkout -b feature/new-agent`
2. Implement changes following existing patterns
3. Test with both CLI and web interface
4. Update this CLAUDE.md if architecture changes
5. Commit with descriptive messages
6. Merge to main when stable

---
**Last Updated**: 2025-08-29  
**Claude Code Session**: Initial project setup completed, comprehensive roadmap added

**Update CLAUDE.md when:**
- Major features are completed
- Architecture changes  
- New dependencies are added
- Project status changes significantly
- Milestones are reached
- New projects/phases begin