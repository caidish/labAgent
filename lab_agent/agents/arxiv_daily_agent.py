import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BaseAgent
from ..tools.arxiv_daily_scraper import ArxivDailyScraper
from ..tools.paper_scorer import PaperScorer
from ..tools.daily_report_generator import DailyReportGenerator


class ArxivDailyAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ArxivDailyAgent", config)
        self.scraper = None
        self.scorer = None
        self.report_generator = None
        
    async def initialize(self) -> None:
        self.logger.info("Initializing ArXiv Daily Agent")
        
        try:
            self.scraper = ArxivDailyScraper()
            self.scorer = PaperScorer()
            self.report_generator = DailyReportGenerator(
                reports_dir=self.config.get('reports_dir', './reports')
            )
            
            self.logger.info("ArXiv Daily Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ArXiv Daily Agent: {e}")
            raise
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get('type', 'generate_daily_report')
        
        if task_type == 'generate_daily_report':
            return await self._generate_daily_report(task)
        elif task_type == 'list_reports':
            return self._list_reports()
        elif task_type == 'get_report':
            return self._get_report(task.get('date'))
        elif task_type == 'clear_reports':
            return self._clear_reports()
        else:
            return {'success': False, 'error': f'Unknown task type: {task_type}'}
    
    async def _generate_daily_report(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            date = task.get('date', datetime.now().strftime('%Y-%m-%d'))
            url = task.get('url', 'https://arxiv.org/list/cond-mat/new')
            
            self.logger.info(f"Starting daily report generation for {date}")
            
            # Check if report already exists
            existing_report = self.report_generator.get_report(date)
            if existing_report:
                self.logger.info(f"Report for {date} already exists, returning existing report")
                print(f"[DEBUG] Report for {date} already exists - skipping generation")
                
                # Calculate summary from existing data
                existing_data = existing_report['json_data']
                summary = existing_data.get('summary', {})
                
                return {
                    'success': True,
                    'date': date,
                    'total_papers': summary.get('total_papers', 0),
                    'priority_counts': summary.get('priority_counts', {'1': 0, '2': 0, '3': 0}),
                    'report_data': {
                        'date': date,
                        'html_content': existing_report['html_content'],
                        'json_data': existing_data
                    },
                    'message': f'Loaded existing daily report for {date} with {summary.get("total_papers", 0)} papers',
                    'from_cache': True
                }
            
            # Step 1: Fetch papers from ArXiv
            self.logger.info("Fetching papers from ArXiv...")
            print(f"[DEBUG] Starting paper fetch from {url}")
            papers = self.scraper.fetch_daily_papers(url)
            
            if not papers:
                print(f"[DEBUG] No papers found!")
                return {
                    'success': False, 
                    'error': 'No papers found or failed to fetch papers'
                }
            
            self.logger.info(f"Fetched {len(papers)} papers")
            print(f"[DEBUG] Successfully fetched {len(papers)} papers")
            
            # Step 2: Score papers using GPT
            self.logger.info("Scoring papers with AI...")
            print(f"[DEBUG] Starting AI scoring...")
            scored_papers = self.scorer.batch_score_papers(papers, batch_size=3)
            
            # Step 3: Generate daily report
            self.logger.info("Generating daily report...")
            report_data = self.report_generator.generate_daily_report(scored_papers, date)
            
            # Calculate summary statistics
            priority_counts = {1: 0, 2: 0, 3: 0}
            for paper in scored_papers:
                score = paper.get('score', 1)
                if score in priority_counts:
                    priority_counts[score] += 1
            
            self.logger.info(f"Daily report generated successfully for {date}")
            
            return {
                'success': True,
                'date': date,
                'total_papers': len(scored_papers),
                'priority_counts': priority_counts,
                'report_data': report_data,
                'message': f'Generated daily report with {len(scored_papers)} papers'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _list_reports(self) -> Dict[str, Any]:
        try:
            reports = self.report_generator.list_existing_reports()
            return {
                'success': True,
                'reports': reports,
                'count': len(reports)
            }
        except Exception as e:
            self.logger.error(f"Error listing reports: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_report(self, date: str) -> Dict[str, Any]:
        try:
            if not date:
                return {
                    'success': False,
                    'error': 'Date parameter is required'
                }
            
            report = self.report_generator.get_report(date)
            if report is None:
                return {
                    'success': False,
                    'error': f'No report found for date: {date}'
                }
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            self.logger.error(f"Error getting report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _clear_reports(self) -> Dict[str, Any]:
        try:
            count = self.report_generator.clear_all_reports()
            return {
                'success': True,
                'message': f'Cleared {count} report files',
                'count': count
            }
        except Exception as e:
            self.logger.error(f"Error clearing reports: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup(self) -> None:
        self.logger.info("Cleaning up ArXiv Daily Agent")
        
        if self.scraper:
            self.scraper.close()
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            'scraper_ready': self.scraper is not None,
            'scorer_ready': self.scorer is not None,
            'report_generator_ready': self.report_generator is not None,
            'reports_dir': self.config.get('reports_dir', './reports')
        })
        return status