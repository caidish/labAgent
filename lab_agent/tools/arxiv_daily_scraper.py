import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import re


class ArxivDailyScraper:
    def __init__(self):
        self.logger = logging.getLogger("tools.arxiv_daily_scraper")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_daily_papers(self, url: str = "https://arxiv.org/list/cond-mat/new") -> List[Dict[str, str]]:
        try:
            self.logger.info(f"Starting to fetch daily papers from: {url}")
            print(f"[DEBUG] Fetching papers from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            print(f"[DEBUG] Successfully fetched page, status: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            papers = []
            
            # Find all paper entries - try different selectors
            paper_entries = soup.find_all('dd')
            print(f"[DEBUG] Found {len(paper_entries)} dd elements")
            
            # If no dd elements, try alternative structure
            if not paper_entries:
                # Try finding paper entries by class
                paper_entries = soup.find_all('div', class_='list-entry')
                print(f"[DEBUG] Alternative search found {len(paper_entries)} div.list-entry elements")
            
            if not paper_entries:
                # Try any div with paper-like content
                paper_entries = soup.find_all('div', string=lambda text: text and 'Title:' in text)
                print(f"[DEBUG] Third attempt found {len(paper_entries)} elements with 'Title:'")
            
            for i, entry in enumerate(paper_entries):
                if i % 10 == 0:  # Progress update every 10 papers
                    print(f"[DEBUG] Processing entry {i+1}")
                paper = self._parse_paper_entry(entry)
                if paper and paper.get('title'):
                    papers.append(paper)
                    if len(papers) <= 5:  # Only show first 5 for debugging
                        print(f"[DEBUG] Successfully parsed paper: {paper['title'][:50]}...")
            
            self.logger.info(f"Found {len(papers)} valid papers")
            print(f"[DEBUG] Total valid papers found: {len(papers)}")
            return papers
            
        except Exception as e:
            self.logger.error(f"Error fetching papers: {e}")
            print(f"[DEBUG] ERROR: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return []
    
    def _parse_paper_entry(self, entry) -> Optional[Dict[str, str]]:
        try:
            # Initialize variables
            title = ""
            authors = ""
            abstract = ""
            subjects = ""
            arxiv_id = ""
            
            # Strategy 1: Look for standard ArXiv list structure
            title_elem = entry.find('div', class_='list-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
                # Remove "Title:" prefix - handle both with and without space
                if title.startswith('Title: '):
                    title = title[7:]
                elif title.startswith('Title:'):
                    title = title[6:]
            
            # Strategy 2: Look for text that starts with "Title:"
            if not title:
                text = entry.get_text()
                if 'Title:' in text:
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip().startswith('Title:'):
                            title = line.strip()[6:].strip()
                            break
            
            # Find authors
            authors_elem = entry.find('div', class_='list-authors')
            if authors_elem:
                authors = authors_elem.get_text(strip=True)
                if authors.startswith('Authors: '):
                    authors = authors[9:]
            
            # If no authors found via class, try text search
            if not authors:
                text = entry.get_text()
                if 'Authors:' in text:
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip().startswith('Authors:'):
                            authors = line.strip()[8:].strip()
                            break
            
            # Find abstract
            abstract_elem = entry.find('p', class_='mathjax')
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)
            
            # If no abstract found, look for any paragraph
            if not abstract:
                paragraphs = entry.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Assume abstracts are longer than 50 chars
                        abstract = text
                        break
            
            # Try to find arXiv ID from the previous dt element
            prev_dt = entry.find_previous_sibling('dt')
            if prev_dt:
                id_span = prev_dt.find('span', class_='list-identifier')
                if id_span:
                    id_link = id_span.find('a')
                    if id_link:
                        href = id_link.get('href', '')
                        match = re.search(r'/abs/(\d+\.\d+)', href)
                        if match:
                            arxiv_id = match.group(1)
            
            # Alternative: look for arXiv ID in text
            if not arxiv_id:
                text = entry.get_text()
                match = re.search(r'arXiv:(\d+\.\d+)', text, re.IGNORECASE)
                if match:
                    arxiv_id = match.group(1)
            
            # Find subjects
            subjects_elem = entry.find('div', class_='list-subjects')
            if subjects_elem:
                subjects = subjects_elem.get_text(strip=True)
                # Remove "Subjects:" prefix - handle both with and without space
                if subjects.startswith('Subjects: '):
                    subjects = subjects[10:]
                elif subjects.startswith('Subjects:'):
                    subjects = subjects[9:]
            
            # Only return if we have at least a title
            if not title:
                return None
            
            paper = {
                'id': arxiv_id,
                'title': title,
                'authors': authors,
                'abstract': abstract or "No abstract available",
                'subjects': subjects,
                'url': f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else '',
                'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf' if arxiv_id else '',
                'fetched_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return paper
            
        except Exception as e:
            self.logger.error(f"Error parsing paper entry: {e}")
            return None
    
    def close(self):
        self.session.close()