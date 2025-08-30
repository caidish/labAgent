import logging
from typing import Dict, List, Optional, Any
import feedparser
import requests
from datetime import datetime
import pytz


class ArxivParser:
    def __init__(self, base_url: str = "http://export.arxiv.org/api/query"):
        self.base_url = base_url
        self.logger = logging.getLogger("tools.arxiv_parser")
        
    def search_papers(
        self, 
        query: str, 
        max_results: int = 10,
        sort_by: str = "submittedDate",
        sort_order: str = "descending"
    ) -> List[Dict[str, Any]]:
        try:
            params = {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order
            }
            
            self.logger.info(f"Searching ArXiv for: {query}")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            papers = []
            for entry in feed.entries:
                paper = self._parse_entry(entry)
                papers.append(paper)
                
            self.logger.info(f"Found {len(papers)} papers")
            return papers
            
        except Exception as e:
            self.logger.error(f"Error searching ArXiv: {e}")
            return []
    
    def _parse_entry(self, entry) -> Dict[str, Any]:
        authors = []
        if hasattr(entry, 'authors'):
            authors = [author.name for author in entry.authors]
        elif hasattr(entry, 'author'):
            authors = [entry.author]
            
        categories = []
        if hasattr(entry, 'arxiv_primary_category'):
            categories.append(entry.arxiv_primary_category.term)
        if hasattr(entry, 'tags'):
            categories.extend([tag.term for tag in entry.tags])
            
        published_date = None
        if hasattr(entry, 'published'):
            try:
                published_date = datetime.strptime(
                    entry.published, 
                    "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)
            except ValueError:
                pass
                
        updated_date = None
        if hasattr(entry, 'updated'):
            try:
                updated_date = datetime.strptime(
                    entry.updated, 
                    "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)
            except ValueError:
                pass
        
        paper = {
            "id": entry.id,
            "title": entry.title.replace('\n', ' ').strip(),
            "summary": entry.summary.replace('\n', ' ').strip(),
            "authors": authors,
            "categories": categories,
            "published_date": published_date,
            "updated_date": updated_date,
            "link": entry.link,
            "pdf_link": None
        }
        
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.type == 'application/pdf':
                    paper["pdf_link"] = link.href
                    break
        
        return paper
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        try:
            self.logger.info(f"Fetching ArXiv paper: {arxiv_id}")
            params = {
                "id_list": arxiv_id,
                "max_results": 1
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                return self._parse_entry(feed.entries[0])
            else:
                self.logger.warning(f"Paper {arxiv_id} not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching paper {arxiv_id}: {e}")
            return None
    
    def search_by_category(
        self, 
        category: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        query = f"cat:{category}"
        return self.search_papers(query, max_results)
    
    def search_by_author(
        self, 
        author: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        query = f"au:{author}"
        return self.search_papers(query, max_results)