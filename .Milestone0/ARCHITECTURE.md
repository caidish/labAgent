# ArXiv Daily Update System Architecture

## System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │  ArXiv Agent    │    │   Notifier      │
│  (Daily Timer)  │───▶│  (Fetch & Filter)│───▶│ (Email/Web/File)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Storage        │
                       │ (Papers DB)     │
                       └─────────────────┘
```

## Components

### 1. ArXiv Daily Agent (`arxiv_daily_agent.py`)
- **Purpose**: Main orchestrator for daily ArXiv monitoring
- **Extends**: `BaseAgent`
- **Responsibilities**:
  - Schedule daily paper fetching
  - Coordinate filtering and relevance scoring
  - Trigger notifications
  - Handle error recovery and logging

### 2. Enhanced ArXiv Parser (`enhanced_arxiv_parser.py`)
- **Purpose**: Extended ArXiv parser with daily update features
- **Extends**: `ArxivParser`
- **New Features**:
  - Date-based filtering (last N days)
  - Relevance scoring based on keywords
  - Duplicate detection
  - Author priority weighting

### 3. Relevance Filter (`relevance_filter.py`)
- **Purpose**: Intelligent filtering for PJH lab relevance
- **Features**:
  - Keyword matching with TF-IDF scoring
  - Category-based filtering
  - Author priority scoring
  - Combined relevance score calculation

### 4. Daily Report Generator (`daily_report.py`)
- **Purpose**: Generate formatted daily reports
- **Output Formats**:
  - HTML (for email/web viewing)
  - Markdown (for documentation)
  - JSON (for programmatic access)
  - CSV (for data analysis)

### 5. Notification System (`notifier.py`)
- **Purpose**: Handle various notification channels
- **Channels**:
  - Email (SMTP)
  - File output
  - Web dashboard update
  - Optional: Slack/Discord webhooks

### 6. Storage Layer (`paper_storage.py`)
- **Purpose**: Persistent storage for processed papers
- **Features**:
  - SQLite database for paper metadata
  - Duplicate detection
  - Historical tracking
  - Search and retrieval

## Data Flow

1. **Daily Trigger**: Scheduler activates ArXiv Daily Agent
2. **Fetch Papers**: Enhanced parser fetches new papers from ArXiv
3. **Filter & Score**: Relevance filter scores papers for PJH lab relevance
4. **Store**: Papers stored in local database with metadata
5. **Generate Report**: Daily report generated in configured formats
6. **Notify**: Report sent via configured notification channels
7. **Cleanup**: Old papers archived/cleaned based on retention policy

## Configuration Structure

```python
ARXIV_DAILY_CONFIG = {
    "enabled": True,
    "schedule": "09:00",  # Daily at 9 AM
    "lookback_days": 1,   # Papers from last N days
    "min_relevance_score": 0.3,
    "max_papers_per_report": 20,
    
    "research_interests": {
        "keywords": ["2D materials", "graphene", "quantum dots"],
        "arxiv_categories": ["cond-mat.mes-hall", "physics.app-ph"],
        "key_authors": ["Smith J", "Johnson M"],
        "weights": {
            "keyword_match": 0.4,
            "category_match": 0.3, 
            "author_match": 0.3
        }
    },
    
    "notifications": {
        "email": {
            "enabled": True,
            "recipients": ["pjh@lab.edu"],
            "subject_template": "Daily ArXiv Update - {date}"
        },
        "file_output": {
            "enabled": True,
            "directory": "./reports/daily",
            "formats": ["html", "json"]
        },
        "web_dashboard": {
            "enabled": True,
            "update_streamlit": True
        }
    },
    
    "storage": {
        "database_path": "./data/arxiv_papers.db",
        "retention_days": 365,
        "archive_old_papers": True
    }
}
```

## Database Schema

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,           -- ArXiv ID (e.g., "2301.12345")
    title TEXT NOT NULL,
    authors TEXT NOT NULL,         -- JSON array of authors
    abstract TEXT NOT NULL,
    categories TEXT NOT NULL,      -- JSON array of categories
    published_date TEXT NOT NULL,
    updated_date TEXT,
    pdf_url TEXT,
    relevance_score REAL,          -- Calculated relevance (0.0-1.0)
    processed_date TEXT NOT NULL,  -- When we processed this paper
    included_in_reports TEXT,      -- JSON array of report dates
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_reports (
    date TEXT PRIMARY KEY,         -- YYYY-MM-DD
    paper_count INTEGER,
    avg_relevance_score REAL,
    report_html TEXT,
    report_json TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## File Structure

```
lab_agent/
├── agents/
│   ├── arxiv_daily_agent.py      # Main daily update agent
│   └── __init__.py
├── tools/
│   ├── enhanced_arxiv_parser.py   # Extended ArXiv parser
│   ├── relevance_filter.py        # Relevance scoring system
│   ├── daily_report.py            # Report generation
│   ├── notifier.py                # Notification handling
│   ├── paper_storage.py           # Database operations
│   └── __init__.py
├── data/                          # Created at runtime
│   ├── arxiv_papers.db           # SQLite database
│   └── config/
│       └── research_interests.json
└── reports/                       # Created at runtime
    └── daily/
        ├── 2025-08-29.html
        ├── 2025-08-29.json
        └── archive/
```

---
**Next Steps**: 
1. Get user configuration (research interests, notification preferences)
2. Implement core components in priority order
3. Test with sample data before full deployment