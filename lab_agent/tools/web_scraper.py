import asyncio
import logging
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse


class WebScraper:
    def __init__(self, delay: float = 1.0, timeout: int = 30):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logging.getLogger("tools.web_scraper")
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_url(self, url: str, parse_method: str = "html.parser") -> Optional[BeautifulSoup]:
        try:
            self.logger.info(f"Scraping URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, parse_method)
            time.sleep(self.delay)
            
            return soup
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return None
    
    def extract_text(self, soup: BeautifulSoup, selector: Optional[str] = None) -> List[str]:
        if selector:
            elements = soup.select(selector)
            return [elem.get_text(strip=True) for elem in elements]
        else:
            return [soup.get_text(strip=True)]
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            links.append({
                'text': link.get_text(strip=True),
                'url': absolute_url
            })
        return links
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        metadata = {}
        
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)
        
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            if meta.get('name'):
                metadata[meta.get('name')] = meta.get('content', '')
            elif meta.get('property'):
                metadata[meta.get('property')] = meta.get('content', '')
                
        return metadata
    
    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        results = []
        for url in urls:
            soup = self.scrape_url(url)
            if soup:
                result = {
                    'url': url,
                    'soup': soup,
                    'metadata': self.extract_metadata(soup),
                    'links': self.extract_links(soup, url)
                }
                results.append(result)
        return results
    
    def close(self):
        self.session.close()