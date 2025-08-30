"""
ArXiv Daily MCP Tools for Lab Agent.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from mcp import Tool
from mcp.types import TextContent

from .base_tool import BaseTool


class ArxivDailyTools(BaseTool):
    """MCP tools for ArXiv Daily functionality"""
    
    def __init__(self):
        super().__init__("arxiv_daily", "Tools for ArXiv Daily report management")
        self.arxiv_agent = None
        self._agent_initialized = False
    
    async def _initialize_arxiv_agent(self):
        """Initialize ArXiv Daily agent"""
        if self._agent_initialized:
            return
            
        try:
            # Import here to avoid circular imports
            from ...agents.arxiv_daily_agent import ArxivDailyAgent
            
            self.arxiv_agent = ArxivDailyAgent({
                'reports_dir': './reports'
            })
            # Initialize the agent asynchronously - same as web interface
            await self.arxiv_agent.initialize()
            self._agent_initialized = True
            self.logger.info("ArXiv Daily agent initialized for MCP tools")
        except Exception as e:
            self.logger.error(f"Failed to initialize ArXiv agent: {e}")
            self.arxiv_agent = None
    
    def get_tool_definitions(self) -> List[Tool]:
        """Get all tool definitions for this tool group"""
        return [
            Tool(
                name="read_daily_report",
                description="Read and analyze an existing ArXiv Daily report",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date of report to read (YYYY-MM-DD, 'today', 'yesterday')",
                            "default": "today"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="generate_daily_report",
                description="Generate a new ArXiv Daily report",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date for report generation (YYYY-MM-DD, 'today')",
                            "default": "today"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force regeneration even if report exists",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="list_available_reports",
                description="List available ArXiv Daily reports with metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of reports to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="search_papers_by_author",
                description="Search for papers by author name in ArXiv Daily reports",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "author_name": {
                            "type": "string",
                            "description": "Author name to search for (e.g., 'Liang Fu', 'John Smith')"
                        },
                        "date": {
                            "type": "string", 
                            "description": "Date of report to search (YYYY-MM-DD, 'today', 'yesterday')",
                            "default": "today"
                        },
                        "match_type": {
                            "type": "string",
                            "description": "How to match the author name: 'exact', 'contains', or 'fuzzy'",
                            "enum": ["exact", "contains", "fuzzy"],
                            "default": "contains"
                        }
                    },
                    "required": ["author_name"]
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool"""
        self.logger.info(f"Executing tool: {tool_name}")
        
        # Initialize agent if not already done
        if not self._agent_initialized:
            await self._initialize_arxiv_agent()
            
        if self.arxiv_agent is None:
            return self.format_error_response("ArXiv Daily agent not available")
        
        try:
            if tool_name == "read_daily_report":
                return await self._read_daily_report(arguments)
            elif tool_name == "generate_daily_report":
                return await self._generate_daily_report(arguments)
            elif tool_name == "list_available_reports":
                return await self._list_available_reports(arguments)
            elif tool_name == "search_papers_by_author":
                return await self._search_papers_by_author(arguments)
            else:
                return self.format_error_response(f"Unknown tool: {tool_name}")
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            return self.format_error_response(str(e))
    
    async def _read_daily_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Read and analyze an existing ArXiv Daily report"""
        date_str = arguments.get("date", "today")
        parsed_date = self._parse_date(date_str)
        
        try:
            # Get report from ArXiv agent
            result = self.arxiv_agent._get_report(parsed_date)
            
            if not result['success']:
                return self.format_error_response(
                    f"No report found for {parsed_date}",
                    {"date": parsed_date, "available": False}
                )
            
            # Extract and format report data
            report_data = result['report']['json_data']
            summary = report_data['summary']
            papers_by_priority = report_data.get('papers_by_priority', {})
            
            # Get priority counts (handle both string and integer keys)
            priority_counts = summary.get('priority_counts', {})
            p3_count = priority_counts.get('3', priority_counts.get(3, 0))
            p2_count = priority_counts.get('2', priority_counts.get(2, 0))
            p1_count = priority_counts.get('1', priority_counts.get(1, 0))
            
            # Format high-priority papers for AI consumption
            high_priority_papers = []
            high_priority_list = papers_by_priority.get('3', papers_by_priority.get(3, []))
            
            for paper in high_priority_list[:5]:  # Top 5 high-priority papers
                paper_info = {
                    "title": paper.get('title', 'N/A'),
                    "authors": paper.get('authors', 'N/A'),
                    "abstract": paper.get('abstract', 'N/A')[:300] + "..." if len(paper.get('abstract', '')) > 300 else paper.get('abstract', 'N/A'),
                    "subjects": paper.get('subjects', 'N/A'),
                    "url": paper.get('url', ''),
                    "pdf_url": paper.get('pdf_url', ''),
                    "ai_assessment": paper.get('reason', 'N/A')
                }
                high_priority_papers.append(paper_info)
            
            response_data = {
                "date": parsed_date,
                "summary": {
                    "total_papers": summary.get('total_papers', 0),
                    "priority_3_count": p3_count,
                    "priority_2_count": p2_count,
                    "priority_1_count": p1_count
                },
                "high_priority_papers": high_priority_papers,
                "report_available": True
            }
            
            return self.format_success_response(
                response_data,
                f"Successfully read report for {parsed_date}"
            )
            
        except Exception as e:
            return self.format_error_response(
                f"Error reading report: {str(e)}",
                {"date": parsed_date}
            )
    
    async def _generate_daily_report(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new ArXiv Daily report"""
        date_str = arguments.get("date", "today")
        force = arguments.get("force", False)
        parsed_date = self._parse_date(date_str)
        
        self.logger.info(f"🚀 MCP: Starting daily report generation for {parsed_date} (force={force})")
        
        try:
            # Check if report already exists (unless forced)
            if not force:
                self.logger.info(f"📋 MCP: Checking if report exists for {parsed_date}")
                existing_result = self.arxiv_agent._get_report(parsed_date)
                if existing_result['success']:
                    self.logger.info(f"📋 MCP: Report already exists for {parsed_date}")
                    return self.format_success_response(
                        {"date": parsed_date, "from_cache": True},
                        f"Report for {parsed_date} already exists (use force=true to regenerate)"
                    )
            
            # Generate new report
            task = {
                'type': 'generate_daily_report',
                'date': parsed_date,
                'url': 'https://arxiv.org/list/cond-mat/new'
            }
            
            self.logger.info(f"📝 MCP: Generating new report with task: {task}")
            result = await self.arxiv_agent.process_task(task)
            self.logger.info(f"📊 MCP: Report generation result: {result.get('success', False)} - {result.get('message', 'No message')}")
            
            if result['success']:
                # Extract summary information
                priority_counts = result.get('priority_counts', {})
                p3_count = priority_counts.get('3', priority_counts.get(3, 0))
                p2_count = priority_counts.get('2', priority_counts.get(2, 0))
                p1_count = priority_counts.get('1', priority_counts.get(1, 0))
                
                response_data = {
                    "date": parsed_date,
                    "total_papers": result.get('total_papers', 0),
                    "priority_counts": {
                        "priority_3": p3_count,
                        "priority_2": p2_count,
                        "priority_1": p1_count
                    },
                    "from_cache": result.get('from_cache', False),
                    "generation_successful": True
                }
                
                return self.format_success_response(
                    response_data,
                    f"Successfully generated report for {parsed_date}"
                )
            else:
                return self.format_error_response(
                    f"Failed to generate report: {result.get('error', 'Unknown error')}",
                    {"date": parsed_date}
                )
                
        except Exception as e:
            return self.format_error_response(
                f"Error generating report: {str(e)}",
                {"date": parsed_date}
            )
    
    async def _list_available_reports(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available ArXiv Daily reports"""
        limit = arguments.get("limit", 10)
        limit = max(1, min(50, limit))  # Clamp between 1 and 50
        
        try:
            # Get list of reports from ArXiv agent
            result = self.arxiv_agent._list_reports()
            
            if not result['success']:
                return self.format_error_response("Failed to list reports")
            
            reports = result.get('reports', [])
            reports_info = []
            
            # Get information for each report (up to limit)
            for date in reports[:limit]:
                try:
                    report_result = self.arxiv_agent._get_report(date)
                    if report_result['success']:
                        report_data = report_result['report']['json_data']
                        summary = report_data['summary']
                        
                        # Handle priority counts
                        priority_counts = summary.get('priority_counts', {})
                        p3_count = priority_counts.get('3', priority_counts.get(3, 0))
                        p2_count = priority_counts.get('2', priority_counts.get(2, 0))
                        p1_count = priority_counts.get('1', priority_counts.get(1, 0))
                        
                        report_info = {
                            "date": date,
                            "total_papers": summary.get('total_papers', 0),
                            "priority_3_count": p3_count,
                            "priority_2_count": p2_count,
                            "priority_1_count": p1_count,
                            "has_high_priority": p3_count > 0
                        }
                        reports_info.append(report_info)
                except Exception as e:
                    self.logger.warning(f"Error loading report {date}: {e}")
                    continue
            
            response_data = {
                "reports": reports_info,
                "total_available": len(reports),
                "returned_count": len(reports_info),
                "limit": limit
            }
            
            return self.format_success_response(
                response_data,
                f"Found {len(reports_info)} reports"
            )
            
        except Exception as e:
            return self.format_error_response(f"Error listing reports: {str(e)}")
    
    async def _search_papers_by_author(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for papers by author name in full ArXiv Daily report"""
        author_name = arguments.get("author_name", "").strip()
        date_str = arguments.get("date", "today")
        match_type = arguments.get("match_type", "contains").lower()
        
        if not author_name:
            return self.format_error_response("Author name is required")
        
        parsed_date = self._parse_date(date_str)
        
        self.logger.info(f"🔍 MCP: Searching for author '{author_name}' in report for {parsed_date} (match_type: {match_type})")
        
        try:
            # Get the full report
            result = self.arxiv_agent._get_report(parsed_date)
            
            if not result['success']:
                return self.format_error_response(
                    f"No report found for {parsed_date}",
                    {"date": parsed_date, "available": False}
                )
            
            # Get the full report data including ALL papers
            report_data = result['report']['json_data']
            papers_by_priority = report_data.get('papers_by_priority', {})
            
            # Search through ALL papers in all priority levels
            matching_papers = []
            total_searched = 0
            
            for priority in ['3', '2', '1', 3, 2, 1]:  # Handle both string and int keys
                priority_papers = papers_by_priority.get(priority, [])
                total_searched += len(priority_papers)
                
                for paper in priority_papers:
                    authors = paper.get('authors', '')
                    if self._author_matches(authors, author_name, match_type):
                        matching_paper = {
                            "title": paper.get('title', 'N/A'),
                            "authors": authors,
                            "abstract": paper.get('abstract', 'N/A')[:300] + "..." if len(paper.get('abstract', '')) > 300 else paper.get('abstract', 'N/A'),
                            "subjects": paper.get('subjects', 'N/A'),
                            "url": paper.get('url', ''),
                            "pdf_url": paper.get('pdf_url', ''),
                            "ai_assessment": paper.get('reason', 'N/A'),
                            "priority": str(priority)
                        }
                        matching_papers.append(matching_paper)
            
            # Prepare response
            response_data = {
                "search_query": {
                    "author_name": author_name,
                    "match_type": match_type,
                    "date": parsed_date
                },
                "search_results": {
                    "total_papers_searched": total_searched,
                    "matching_papers_count": len(matching_papers),
                    "matching_papers": matching_papers
                }
            }
            
            if matching_papers:
                message = f"Found {len(matching_papers)} paper(s) by '{author_name}' in report for {parsed_date}"
            else:
                message = f"No papers found by '{author_name}' in report for {parsed_date} (searched {total_searched} papers)"
            
            return self.format_success_response(response_data, message)
            
        except Exception as e:
            return self.format_error_response(
                f"Error searching for author: {str(e)}",
                {"author_name": author_name, "date": parsed_date}
            )
    
    def _author_matches(self, authors_str: str, search_name: str, match_type: str) -> bool:
        """Check if author name matches based on match type"""
        if not authors_str or not search_name:
            return False
        
        authors_lower = authors_str.lower()
        search_lower = search_name.lower()
        
        if match_type == "exact":
            # Split authors by common separators and check for exact match
            import re
            author_list = re.split(r'[,;&]|\sand\s', authors_str)
            return any(author.strip().lower() == search_lower for author in author_list)
        
        elif match_type == "contains":
            # Simple substring match (default)
            return search_lower in authors_lower
        
        elif match_type == "fuzzy":
            # More flexible matching - split search name and check for all parts
            search_parts = search_lower.split()
            return all(part in authors_lower for part in search_parts if len(part) > 1)
        
        else:
            # Default to contains
            return search_lower in authors_lower
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if date_str.lower() == "today":
            return datetime.now().strftime('%Y-%m-%d')
        elif date_str.lower() == "yesterday":
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Validate date format
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD, 'today', or 'yesterday'")
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Base class execute method - not used directly"""
        raise NotImplementedError("Use execute_tool method instead")
    
    def get_tool_definition(self) -> Tool:
        """Base class method - not used directly"""
        raise NotImplementedError("Use get_tool_definitions method instead")