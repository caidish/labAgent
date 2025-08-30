import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

from .utils import Config, setup_logger
from .agents import BaseAgent


class LabAgent:
    def __init__(self, config_path: Optional[str] = None):
        load_dotenv()
        self.config = Config(config_path)
        self.logger = setup_logger(self.config.log_level)
        self.agents = []
        
    async def initialize(self):
        self.logger.info("Initializing Lab Agent system...")
        
    async def run(self):
        await self.initialize()
        self.logger.info("Lab Agent system started")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Shutting down Lab Agent system...")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        self.logger.info("Cleaning up Lab Agent system...")
        

def main():
    agent = LabAgent()
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()