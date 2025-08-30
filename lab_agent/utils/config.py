import os
from typing import Optional, Any
from dotenv import load_dotenv


class Config:
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            load_dotenv(config_path)
        else:
            load_dotenv()
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        
        # Google Gemini Configuration
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        # Application Settings
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Web Interface Settings
        self.streamlit_port = int(os.getenv("STREAMLIT_PORT", "8501"))
        self.streamlit_host = os.getenv("STREAMLIT_HOST", "localhost")
        
        # WebSocket Settings
        self.websocket_port = int(os.getenv("WEBSOCKET_PORT", "8765"))
        self.websocket_host = os.getenv("WEBSOCKET_HOST", "localhost")
        
        # Database Settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///lab_agent.db")
        
        # External API Settings
        self.arxiv_base_url = os.getenv("ARXIV_BASE_URL", "http://export.arxiv.org/api/query")
        
        # Rate Limiting
        self.api_rate_limit = int(os.getenv("API_RATE_LIMIT", "60"))
        self.scraping_delay = float(os.getenv("SCRAPING_DELAY", "1.0"))
        
        # Timezone Settings
        self.default_timezone = os.getenv("DEFAULT_TIMEZONE", "UTC")
        
    def validate(self) -> bool:
        required_keys = ["OPENAI_API_KEY"]
        missing_keys = []
        
        for key in required_keys:
            if not getattr(self, key.lower()):
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Missing required configuration: {', '.join(missing_keys)}")
            return False
            
        return True
    
    def to_dict(self) -> dict:
        return {
            "openai_model": self.openai_model,
            "gemini_model": self.gemini_model,
            "debug": self.debug,
            "log_level": self.log_level,
            "streamlit_port": self.streamlit_port,
            "streamlit_host": self.streamlit_host,
            "websocket_port": self.websocket_port,
            "websocket_host": self.websocket_host,
            "database_url": self.database_url,
            "arxiv_base_url": self.arxiv_base_url,
            "api_rate_limit": self.api_rate_limit,
            "scraping_delay": self.scraping_delay,
            "default_timezone": self.default_timezone,
        }