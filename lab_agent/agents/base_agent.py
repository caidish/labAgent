import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseAgent(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"agent.{name}")
        self.is_running = False
        
    @abstractmethod
    async def initialize(self) -> None:
        pass
        
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        pass
        
    async def start(self) -> None:
        if self.is_running:
            self.logger.warning(f"Agent {self.name} is already running")
            return
            
        self.logger.info(f"Starting agent {self.name}")
        await self.initialize()
        self.is_running = True
        
    async def stop(self) -> None:
        if not self.is_running:
            self.logger.warning(f"Agent {self.name} is not running")
            return
            
        self.logger.info(f"Stopping agent {self.name}")
        self.is_running = False
        await self.cleanup()
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "running": self.is_running,
            "config": self.config
        }