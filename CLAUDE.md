# Claude Code Context - Lab Agent

## Project Overview
Multi-agent system for laboratory automation and research based on **labAgent Framework v1** - a pragmatic, lab-ready architecture for condensed-matter experiment lab with MCP-connected instruments.

## Framework Architecture (v1)

### Control Plane (LangGraph Implementation)
- **LangGraph Planner:** ✅ **IMPLEMENTED** - Single entrypoint using LangGraph that converts intents/events into Task Graphs (DAG). Owns decomposition, routing, and approvals.
- **Agent Pods (LangGraph Nodes):** ✅ **IMPLEMENTED**
  - **Workers:** Instrument workflows via instrMCP/QCoDeS/RedPitaya/Nikon
  - **Assistants:** Admin ops (receipts, emails, onboarding/offboarding, calendar, travel)
  - **Science Consultants:** Literature triage + wiki maintenance with citations
  - **Information Center:** Rolling briefs; "state of the experiment"
- **Shared Services:** Event Bus, Memory Layer, Policy/Safety, Observability, Playground

### Data Plane
Structured logs, datasets, plots, reports, and wiki diffs flow through a content-addressed artifact store with traceable lineage.

### Memory System (4-Layer Architecture)
1. **Episodic (TTL):** Run logs, chat turns, task graphs. KV + retention (30–90 days)
2. **Semantic (Vector/RAG):** Papers, wiki pages, lab notes, schematics; chunked with signed citations
3. **Procedural (State):** Resumable checkpoints for workflows/instruments
4. **Artifacts:** Datasets, plots, reports, invoices, email threads — content-addressed URIs

## Current Status
✅ **COMPLETED**
- **Basic project structure** with proper Python packaging
- **Streamlit web interface** with playground and ArXiv integration
- **Core modules**: agents, tools, utils, web, playground, mcp, planner
- **Configuration system** with environment variables and JSON configs
- **ArXiv Daily System** - Production ready with GPT-4 scoring and chat interface
- **Model Playground** - Multi-model testing with MCP tool integration
- **FastMCP Integration** - HTTP client with ephemeral connections
- **Custom Server Persistence** - Automatic saving to config files
- **LangGraph Planner** - Complete task orchestration system with agent pods
- **LangChain/LangGraph Integration** - Advanced workflow management

🚧 **IN PROGRESS** 
- Framework v1 implementation roadmap (M0-M4)
- Project 1.1: MCP Server for Glovebox Nikon Microscope

## 🗺️ PROJECT ROADMAP

### **Framework v1 Rollout (M0→M4)**

#### **M0 — Baseline Wiring** ✅ **COMPLETED**
- [x] **LangGraph Planner**: Complete task decomposition and routing using LangGraph workflows
- [x] **Worker Nodes**: Instrument simulation and real hardware control through MCP
- [x] **Assistant Nodes**: Admin operations (receipts, emails, forms)
- [x] **Consultant Nodes**: ArXiv integration and knowledge management
- [x] **Info Center Nodes**: Brief generation and status reporting
- [x] **Episodic memory**: Task state management and execution logging
- [x] **Agent State System**: Complete state management with TypedDict
- [x] **Conditional Routing**: Smart routing between agent pods based on conditions
- [x] **MCP Integration**: Seamless integration with existing MCP server infrastructure
- [x] **Error Handling**: Comprehensive error handling with retries and escalation

#### **M1 — Safety & Live Operations**
- [ ] **Interlocks + runlevels**: dry-run → sim → live progression
- [ ] **First live overnight scan**: Actual instrument control
- [ ] **Artifact store**: Content-addressed data storage
- [ ] **Morning brief v1**: With plots and status updates

#### **M2 — Knowledge & Ops Automation**
- [ ] **Science Consultant**: Auto-updates wiki with citations
- [ ] **Assistants**: Complete receipts/email drafts E2E
- [ ] **Enhanced memory**: Semantic search and RAG

#### **M3 — Reliability**
- [ ] **Retries & checkpoint resume**: Robust workflow execution
- [ ] **SLA alerts**: Monitoring and notifications
- [ ] **Anomaly detection**: Automated issue identification
- [ ] **Approvals dashboard**: Human-in-the-loop controls

#### **M4 — Scale & Polish**
- [ ] **Multi-device scheduling**: Conflict resolution
- [ ] **Resource budgets**: Cost and time management
- [ ] **Full evaluation loop**: Comprehensive testing and metrics

### **Project 1: Instrument Integration**

#### **Milestone 0: ArXiv Daily Update Model**
✅ **COMPLETED** - 2025-08-29

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

**Features:**
- **ArXiv Daily Scraper**: Scrapes https://arxiv.org/list/cond-mat/new for new papers
- **GPT-4 Scoring System**: AI-powered paper relevance scoring (1-3 priority levels)
- **Daily Report Generator**: Beautiful HTML reports with priority sections
- **Web Interface**: Manual trigger, report viewing, and clear functionality
- **Smart Chat System**: GPT-4o chat interface for discussing papers
- **Configuration**: Complete config system with keywords, prompts, and models
- **Duplicate Prevention**: Won't regenerate existing daily reports
- **No Database**: File-based storage for simplicity

**Performance:**
- New reports: 2-4 minutes (scraping + AI scoring)
- Cached reports: <1 second (duplicate prevention)
- Chat responses: 2-5 seconds per message
- Typical daily volume: 20-50 papers processed

**Status**: ✅ **PRODUCTION READY** - Science Consultant agent foundation

#### **Project 1.1: MCP Server for Glovebox Nikon Microscope**

**M0 — Discovery & Control Audit (1-2 days)** 🚧 **IN PROGRESS**

**Overview**: Establish foundation for microscope automation by understanding available hardware and control interfaces.

**Phase 1: Lab Environment Setup** (User Responsibility)
- [ ] Deploy development environment on lab computer
- [ ] Install Nikon SDK/NIS-Elements (if available)
- [ ] Test basic camera connectivity and manual control
- [ ] Document lab computer specifications and OS

**Phase 2: Hardware Discovery & Inventory**
- [ ] **Camera Control**: Inventory Nikon camera capabilities
  - Model, resolution, exposure controls
  - Connection type (USB/PCIe/Ethernet)
  - Available APIs (NIS-Elements SDK, direct camera API)
- [ ] **Stage Systems**: Map motorized components
  - X, Y, Z stage controllers
  - Movement ranges, precision, speed limits
  - Control interfaces (serial, USB, proprietary)
- [ ] **Illumination & Optics**: Document optical path
  - Light sources and intensity controls
  - Filter wheels, objectives, apertures
  - Automated vs manual components
- [ ] **Safety & Interlocks**: Identify safety systems
  - Glovebox door sensors
  - Emergency stops
  - Z-axis collision protection
  - Environmental sensors (pressure, humidity)

**Phase 3: Control Interface Mapping**
- [ ] **Transport Layer**: Determine hardware communication
  - USB/Serial port assignments
  - Network interfaces (if applicable)
  - Required drivers and permissions
- [ ] **Software Stack**: Map available control software
  - NIS-Elements integration capabilities
  - Vendor SDKs and APIs
  - Python/direct programming interfaces
- [ ] **Command Discovery**: Document control commands
  - Camera: snap, exposure, gain settings
  - Stage: move, home, position queries
  - Illumination: on/off, intensity control

**Phase 4: Proof of Concept Testing**
- [ ] **Basic Camera Script**: Write minimal camera control
  - Connect to camera
  - Set exposure/gain parameters
  - Capture and save image
- [ ] **Stage Movement Test**: Create stage control script
  - Initialize stage controllers
  - Execute absolute/relative movements
  - Query current position
- [ ] **Integration Test**: Combined operation sequence
  - Home stages → Move to position → Snap image
  - Verify repeatability and accuracy

**Deliverables**:
1. **Hardware Inventory Document** (`docs/hardware_inventory.md`)
2. **Command Reference** (`docs/command_reference.md`)
3. **Test Scripts** (`scripts/proof_of_concept/`)
4. **Technical Specification** (`docs/M0_technical_spec.md`)

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
- [x] Choose models (segmentation/classification), input contract, output JSON
- [x] **Deliverable**: I/O spec + versioning plan
- [x] **Accept**: Sample request/response pair agreed

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

### **Cross-Cutting Requirements (All Projects)**
- [ ] **Config & Secrets**: .env + profiles (dev/glovebox/CI)
- [ ] **Data Layout**: /raw, /processed, /exports, checksums
- [ ] **CI/CD Tests**: Schema, contracts, linting
- [ ] **Security & Docs**: Least-privilege, quickstart runbooks

## LangGraph Task Orchestration System ✅ **IMPLEMENTED**

### Architecture Overview
The labAgent Framework v1 uses **LangGraph** for robust task orchestration with the following components:

- **StateGraph**: Main workflow graph with conditional routing
- **Agent Nodes**: Individual agent pod implementations (Worker, Assistant, Consultant, Info Center)
- **Agent State**: Comprehensive state management using TypedDict
- **Conditional Routing**: Smart decision logic for agent pod transitions
- **MCP Integration**: Seamless tool execution through existing MCP servers
- **Checkpointing**: Persistent state storage for workflow resumption

### LangGraph Workflow Structure
```python
# Main workflow nodes
intake → precheck → approval_gate → [agent_pods] → finalizer → END

# Agent pod routing (conditional)
worker ↔ assistant ↔ consultant → info_center → complete
  ↓         ↓         ↓              ↓
error_handler ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← 
  ↓
retry/escalate/abort
```

### Agent State Management
```python
class AgentState(TypedDict):
    # Core task information
    task_spec: TaskSpec
    task_graph: Dict[str, TaskNode]
    current_node: Optional[str]
    
    # Execution state
    status: TaskStatus
    runlevel: RunLevel
    approved: bool
    
    # Memory and artifacts
    memory_namespace: str
    artifacts: Dict[str, str]
    execution_log: List[Dict[str, Any]]
    
    # Error handling
    errors: List[str]
    retry_count: int
    max_retries: int
```

### Task Execution Flow
1. **Intake**: Parse user request → generate TaskSpec → create TaskGraph
2. **Precheck**: Validate constraints, resources, budget, time windows
3. **Approval Gate**: Handle runlevel elevation and human approvals
4. **Agent Pod Execution**: Route between Worker/Assistant/Consultant/Info Center
5. **Error Handling**: Automatic retries, escalation, and recovery
6. **Finalization**: Resource cleanup, artifact storage, brief generation

### Demo Usage
```python
from lab_agent.planner import TaskGraphPlanner
from lab_agent.planner.agent_state import TaskSpec, RunLevel

# Initialize planner
planner = TaskGraphPlanner(mcp_manager)

# Create task from natural language
task_spec = await planner.create_task_from_request(
    "Cooldown device D14, then 2D gate map at 20 mK",
    owner="user",
    runlevel=RunLevel.DRY_RUN
)

# Execute workflow
result = await planner.execute_task(task_spec)
print(f"Status: {result.status}, Artifacts: {len(result.artifacts)}")
```

## Task Graph System

### TaskSpec Format (JSON)
```json
{
  "task_id": "tg_2025-09-10_1532Z_001",
  "goal": "Cooldown device D14, then 2D gate map at 20 mK",
  "constraints": ["runlevel:live", "window:21:00-07:00", "max_power=2mW"],
  "artifacts": ["device_map/D14.json"],
  "owner": "jiaqi",
  "sla": "P1D",
  "tags": ["experiment", "cooldown", "gate-scan"]
}
```

### TaskGraph Node Format
```json
{
  "node_id": "cooldown_D14",
  "agent": "worker.cooldown",
  "tools": ["instrMCP.qcodes", "instrMCP.cryostat"],
  "params": {"target_T": "20 mK", "rate": "<=5 mK/min"},
  "guards": ["interlock.cryostat_ok", "shift=night"],
  "on_success": ["scan_gatemap_D14"],
  "on_fail": ["notify_owner", "attach_logs"]
}
```

## Safety & Governance

### Runlevels
- **dry-run** (default): Simulation mode, no hardware interaction
- **sim**: Hardware simulation with realistic responses
- **live**: Actual hardware control (explicit elevation + approval required)

### Capability Tokens
Fine-grained permissions per MCP tool:
- DAC voltage limits (e.g., ≤ 50 mV)
- Read-only magnet operations
- Temperature ramp rate restrictions

### Policy Configuration
```yaml
approvals:
  live_magnet_ramp: [pi, safety_officer]
limits:
  dac_vmax: 0.05   # Volts
  temp_cool_rate: 5e-3  # K/s
windows:
  night_ops: "21:00-07:00"
```

## Inter-Agent Protocol

### Message Format
```json
{
  "msg_id": "evt_2025-09-10_1602Z_42",
  "type": "task.dispatch|status.update|artifact.new|alert",
  "sender": "planner|worker.cooldown|assistant.finance|consultant.lit",
  "task_id": "tg_...|null",
  "ns": "devices/D14|admin/receipts",
  "payload": {"...": "..."},
  "requires_ack": true,
  "priority": "low|normal|high",
  "visibility": "lab|owner|pi-only"
}
```

## Memory System Contracts

### Memory Namespace Convention
```
ns = devices/<ID>/experiments/<YYYY-MM-DD>
ns = admin/receipts/<YYYY>/<MM>
ns = labwiki/<topic>
ns = papers/<arxiv_id>
```

### Memory Write Contract
```json
{
  "who": "worker.gatemap",
  "when": "2025-09-10T15:42:12Z",
  "ns": "devices/D14/experiments/2025-09-10",
  "type": "artifact.pointer",
  "keys": ["dataset", "plot", "logbook_entry"],
  "data": {
    "dataset": "s3://lab/D14/2025-09-10/gatemap.h5",
    "log": "obs://runs/tg_.../cooldown_D14.log",
    "summary_md": "obs://runs/tg_.../summary.md"
  },
  "lineage": {"task_id": "tg_...", "parents": ["cooldown_D14"]},
  "visibility": "lab"
}
```

## Meeting Automation

### Daily Brief Schema
```json
{
  "brief_id": "brief_2025-09-10_lab",
  "sections": [
    {"title": "Experiment status", "bullets": ["..."]},
    {"title": "New results", "links": ["..."]},
    {"title": "Blockers/risks", "bullets": ["..."]},
    {"title": "ArXiv to read", "citations": ["..."]},
    {"title": "Admin", "bullets": ["..."]}
  ]
}
```

## Tech Stack

### AI Models & APIs
- **OpenAI GPT-4** - Primary AI model for agents and planning
- **Google Gemini API** - Secondary model for evaluation/comparison

### Agent Orchestration (NEW)
- **LangChain >= 0.2.0** - Agent framework and tool integration
- **LangGraph >= 0.1.0** - Workflow orchestration and state management
- **LangSmith >= 0.1.0** - Observability and debugging

### Core Python Libraries
- **Web Scraping**: requests, beautifulsoup4, lxml
- **Utilities**: tqdm, pytz, holidays
- **Research**: feedparser (ArXiv RSS/Atom parsing)
- **AI Integration**: openai library
- **MCP Integration**: fastmcp >= 2.0.0
- **State Management**: pydantic >= 2.0.0 (for type-safe state)

### Multi-Agent Extensions
- **Web Interface**: streamlit
- **Real-time Communication**: websockets
- **Async Support**: nest-asyncio
- **Task Management**: asyncio queues and locks
- **Workflow Engine**: LangGraph StateGraph with conditional routing

### Framework Components
- **LangGraph Planner**: Task orchestration with agent pod coordination
- **Playground**: Multi-model testing with tool calling
- **MCP Manager**: Server connection and tool discovery
- **Memory Layer**: Multi-tier storage and retrieval
- **Safety Systems**: Interlocks and approval workflows

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

## Project Structure (Framework v1)
```
labAgent/
├── lab_agent/              # Main package
│   ├── main.py            # Main entry point and LabAgent class
│   ├── planner/           # ✅ LangGraph-based task orchestration
│   │   ├── __init__.py    # Planner exports
│   │   ├── task_graph_planner.py # Main LangGraph workflow engine
│   │   ├── agent_state.py # TypedDict state management
│   │   ├── routing.py     # Conditional routing logic
│   │   ├── nodes.py       # Agent pod implementations (Worker/Assistant/Consultant/InfoCenter)
│   │   └── mcp_integration.py # MCP tool execution bridge
│   ├── agents/            # Agent implementations
│   │   ├── base_agent.py  # Abstract base class for all agents
│   │   ├── arxiv_daily_agent.py # Science Consultant (✅ completed)
│   │   ├── worker/        # [PLANNED] Instrument control agents
│   │   ├── assistant/     # [PLANNED] Administrative operations
│   │   ├── consultant/    # [PLANNED] Knowledge curation agents
│   │   └── info_center/   # [PLANNED] Rolling intelligence
│   ├── tools/             # Agent capabilities
│   │   ├── web_scraper.py # Web scraping with requests/BeautifulSoup
│   │   ├── arxiv_parser.py# Research paper parsing from ArXiv
│   │   ├── arxiv_daily_scraper.py # ArXiv daily automation
│   │   ├── paper_scorer.py # GPT-4 paper relevance scoring
│   │   ├── daily_report_generator.py # HTML/JSON reports
│   │   └── arxiv_chat.py  # GPT-4o chat interface
│   ├── mcp/               # MCP server integrations
│   │   ├── mcp_server.py  # ArXiv Daily MCP server
│   │   └── tools/         # MCP client tools
│   ├── playground/        # ✅ Model testing environment
│   │   ├── model_capabilities.py # Model feature definitions
│   │   ├── playground_client.py # Multi-model client
│   │   ├── responses_client.py # OpenAI Responses API
│   │   ├── tool_adapter.py # MCP to OpenAI tool conversion
│   │   ├── tool_loop.py   # Recursive tool execution
│   │   ├── mcp_manager.py # MCP server management
│   │   ├── fastmcp_http_client.py # FastMCP HTTP client
│   │   └── streaming.py   # Response streaming utilities
│   ├── memory/            # [PLANNED] Multi-layer memory system
│   │   ├── episodic/      # [PLANNED] TTL storage
│   │   ├── semantic/      # [PLANNED] Vector/RAG storage
│   │   └── artifacts/     # [PLANNED] Content-addressed storage
│   ├── safety/            # [PLANNED] Interlocks and governance
│   ├── utils/             # Shared utilities
│   │   ├── config.py      # Environment-based configuration
│   │   ├── logger.py      # Logging setup
│   │   └── __init__.py
│   └── web/               # Streamlit web interface
│       ├── app.py         # Main Streamlit dashboard
│       └── playground_components.py # Playground UI
├── examples/              # ✅ Demo scripts and examples
│   └── langgraph_planner_demo.py # LangGraph planner demonstration
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies (includes LangChain/LangGraph)
├── setup.py              # Package configuration
├── .env.example          # Environment variables template
├── PLAYGROUND.md         # Playground documentation
├── RAGs_example.md       # Task DAG examples and visualizations
├── labagent_framework_v_1.md # Framework specification
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

### Framework Configuration Files
- `lab_agent/config/playground_models.json` - Model and MCP server configurations
- `lab_agent/config/custom_mcp_servers.json` - Persistent custom server storage
- `lab_agent/config/models.json` - Model configuration for ArXiv system
- `lab_agent/config/*.txt` - Prompt templates and keywords

## Architecture Notes

### Agent System
- **BaseAgent**: Abstract base class in `lab_agent/agents/base_agent.py`
- Agents are async-first with lifecycle management (start/stop/cleanup)
- Each agent has name, config, and task processing capabilities
- Agent Pods will implement role-specific behaviors (Worker, Assistant, Consultant, Information Center)

### Tools System
- **WebScraper**: Handles web scraping with rate limiting and error handling
- **ArxivParser**: Parses research papers from ArXiv API using feedparser
- **MCP Integration**: Tools accessible through Model Context Protocol
- Tools are designed to be used by agents for specific capabilities

### Playground System (✅ Production Ready)
- **Multi-model Support**: GPT-4.1, GPT-4o, o-series, GPT-5
- **MCP Tool Integration**: ArXiv Daily, 2D Flake Classification, Custom FastMCP
- **Streaming Responses**: Real-time response display
- **Tool Call Visualization**: See tool execution in real-time
- **Custom Server Persistence**: Automatic saving of custom MCP servers

### Configuration
- Environment-based configuration in `lab_agent/utils/config.py`
- Validation for required API keys
- Support for development and production settings
- JSON-based configuration for models and MCP servers

## Metrics & Evaluation

### Experiment Metrics
- Uptime and success rate
- Scan throughput and SNR
- Drift measurements
- % dry-run vs live operations
- Incident tracking

### Knowledge Metrics
- Citation coverage
- Hallucination rate
- Brief freshness
- Time-to-insight

### Administrative Metrics
- Receipt cycle time
- Email SLA compliance
- Error rates

### Cost Metrics
- Token usage
- Storage costs
- Instrument time
- Consumables tracking

## Common Issues & Solutions

### Import Errors
- Ensure you're running from project root
- Use `python -m lab_agent.main` instead of direct file execution
- Web app uses absolute imports with sys.path modification

### Missing Dependencies
- Run `pip install -r requirements.txt` if you get import errors
- Use virtual environment to avoid conflicts
- For MCP features: `pip install fastmcp>=2.0.0`

### MCP Connection Issues
- Check FastMCP server is running at localhost:8123/mcp
- Verify server configuration in playground_models.json
- Check custom_mcp_servers.json for persistent server storage

## Development Workflow
1. Create feature branch: `git checkout -b feature/new-agent`
2. Implement changes following existing patterns
3. Test with both CLI and web interface
4. Update this CLAUDE.md if architecture changes
5. Commit with descriptive messages
6. Merge to main when stable

---
**Last Updated**: 2025-09-10  
**Claude Code Session**: Framework v1 integration and comprehensive architecture documentation

**Update CLAUDE.md when:**
- Major features are completed
- Architecture changes  
- New dependencies are added
- Project status changes significantly
- Milestones are reached
- New projects/phases begin
- Framework components are implemented
- always use langchain llm api rather than openai ones
- use venv by default