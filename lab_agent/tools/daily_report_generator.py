import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from jinja2 import Template


class DailyReportGenerator:
    def __init__(self, reports_dir: str = "./reports"):
        self.reports_dir = reports_dir
        self.logger = logging.getLogger("tools.daily_report_generator")
        
        # Create reports directory if it doesn't exist
        os.makedirs(reports_dir, exist_ok=True)
        
    def generate_daily_report(self, papers: List[Dict], date: str = None) -> Dict[str, str]:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
            
        # Check if report already exists
        report_path = os.path.join(self.reports_dir, f"{date}.json")
        if os.path.exists(report_path):
            self.logger.info(f"Report for {date} already exists")
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Separate papers by priority
        priority_papers = self._organize_by_priority(papers)
        
        # Generate HTML and JSON reports
        html_content = self._generate_html_report(priority_papers, date)
        json_data = self._generate_json_report(priority_papers, date)
        
        # Save reports
        html_path = os.path.join(self.reports_dir, f"{date}.html")
        json_path = os.path.join(self.reports_dir, f"{date}.json")
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Generated daily report for {date}: {len(papers)} papers")
        
        return {
            'date': date,
            'html_path': html_path,
            'json_path': json_path,
            'html_content': html_content,
            'json_data': json_data
        }
    
    def _organize_by_priority(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        priority_papers = {"1": [], "2": [], "3": []}
        
        for paper in papers:
            score = str(paper.get('score', 1))  # Convert to string
            if score in priority_papers:
                priority_papers[score].append(paper)
        
        return priority_papers
    
    def _generate_html_report(self, priority_papers: Dict[str, List[Dict]], date: str) -> str:
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>ArXiv Daily Report - {{ date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .priority-3 { border-left: 5px solid #e74c3c; }
        .priority-2 { border-left: 5px solid #f39c12; }
        .priority-1 { border-left: 5px solid #95a5a6; }
        .paper { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }
        .paper-title { font-weight: bold; font-size: 16px; color: #2c3e50; margin-bottom: 8px; }
        .paper-authors { color: #7f8c8d; font-size: 14px; margin-bottom: 8px; }
        .paper-abstract { margin: 10px 0; line-height: 1.5; }
        .paper-subjects { font-size: 12px; color: #95a5a6; margin: 8px 0; }
        .score-info { background: #ecf0f1; padding: 8px; border-radius: 3px; margin: 8px 0; font-size: 14px; }
        .links { margin: 10px 0; }
        .links a { margin-right: 15px; color: #3498db; text-decoration: none; }
        .links a:hover { text-decoration: underline; }
        .summary { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .no-papers { color: #7f8c8d; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 ArXiv Daily Report - {{ date }}</h1>
        
        <div class="summary">
            <strong>Summary:</strong> 
            {{ total_papers }} papers found | 
            Priority 3: {{ priority_counts['3'] }} papers | 
            Priority 2: {{ priority_counts['2'] }} papers | 
            Priority 1: {{ priority_counts['1'] }} papers
        </div>

        {% if priority_papers['3'] %}
        <h2>🔴 Priority 3 - High Relevance ({{ priority_counts['3'] }} papers)</h2>
        {% for paper in priority_papers['3'] %}
        <div class="paper priority-3">
            <div class="paper-title">{{ paper.title }}</div>
            <div class="paper-authors"><strong>Authors:</strong> {{ paper.authors }}</div>
            <div class="paper-subjects"><strong>Subjects:</strong> {{ paper.subjects }}</div>
            <div class="paper-abstract">{{ paper.abstract }}</div>
            <div class="score-info">
                <strong>AI Assessment:</strong> {{ paper.reason }}<br>
                <strong>Key Relevance:</strong> {{ paper.key_relevance }}
            </div>
            <div class="links">
                {% if paper.url %}<a href="{{ paper.url }}" target="_blank">📄 Abstract</a>{% endif %}
                {% if paper.pdf_url %}<a href="{{ paper.pdf_url }}" target="_blank">📁 PDF</a>{% endif %}
            </div>
        </div>
        {% endfor %}
        {% endif %}

        {% if priority_papers['2'] %}
        <h2>🟡 Priority 2 - Medium Relevance ({{ priority_counts['2'] }} papers)</h2>
        {% for paper in priority_papers['2'] %}
        <div class="paper priority-2">
            <div class="paper-title">{{ paper.title }}</div>
            <div class="paper-authors"><strong>Authors:</strong> {{ paper.authors }}</div>
            <div class="paper-subjects"><strong>Subjects:</strong> {{ paper.subjects }}</div>
            <div class="paper-abstract">{{ paper.abstract }}</div>
            <div class="score-info">
                <strong>AI Assessment:</strong> {{ paper.reason }}<br>
                <strong>Key Relevance:</strong> {{ paper.key_relevance }}
            </div>
            <div class="links">
                {% if paper.url %}<a href="{{ paper.url }}" target="_blank">📄 Abstract</a>{% endif %}
                {% if paper.pdf_url %}<a href="{{ paper.pdf_url }}" target="_blank">📁 PDF</a>{% endif %}
            </div>
        </div>
        {% endfor %}
        {% endif %}

        {% if priority_papers['1'] %}
        <h2>⚪ Priority 1 - Lower Relevance ({{ priority_counts['1'] }} papers)</h2>
        {% for paper in priority_papers['1'] %}
        <div class="paper priority-1">
            <div class="paper-title">{{ paper.title }}</div>
            <div class="paper-authors"><strong>Authors:</strong> {{ paper.authors }}</div>
            <div class="paper-subjects"><strong>Subjects:</strong> {{ paper.subjects }}</div>
            <div class="paper-abstract">{{ paper.abstract }}</div>
            <div class="score-info">
                <strong>AI Assessment:</strong> {{ paper.reason }}<br>
                <strong>Key Relevance:</strong> {{ paper.key_relevance }}
            </div>
            <div class="links">
                {% if paper.url %}<a href="{{ paper.url }}" target="_blank">📄 Abstract</a>{% endif %}
                {% if paper.pdf_url %}<a href="{{ paper.pdf_url }}" target="_blank">📁 PDF</a>{% endif %}
            </div>
        </div>
        {% endfor %}
        {% endif %}

        <div style="margin-top: 40px; padding: 20px; background: #ecf0f1; border-radius: 5px; text-align: center; color: #7f8c8d;">
            Generated on {{ generation_time }} | Source: <a href="https://arxiv.org/list/cond-mat/new" target="_blank">ArXiv cond-mat/new</a>
        </div>
    </div>
</body>
</html>
        """
        
        template = Template(html_template)
        
        priority_counts = {i: len(papers) for i, papers in priority_papers.items()}
        total_papers = sum(priority_counts.values())
        
        return template.render(
            date=date,
            priority_papers=priority_papers,
            priority_counts=priority_counts,
            total_papers=total_papers,
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def _generate_json_report(self, priority_papers: Dict[str, List[Dict]], date: str) -> Dict:
        priority_counts = {i: len(papers) for i, papers in priority_papers.items()}
        
        return {
            'date': date,
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_papers': sum(priority_counts.values()),
                'priority_counts': priority_counts
            },
            'papers_by_priority': priority_papers,
            'all_papers': [paper for papers in priority_papers.values() for paper in papers]
        }
    
    def list_existing_reports(self) -> List[str]:
        """List all existing daily reports"""
        if not os.path.exists(self.reports_dir):
            return []
            
        reports = []
        for filename in os.listdir(self.reports_dir):
            if filename.endswith('.json') and not filename.startswith('.'):
                date = filename[:-5]  # Remove .json extension
                reports.append(date)
        
        return sorted(reports, reverse=True)  # Most recent first
    
    def get_report(self, date: str) -> Optional[Dict]:
        """Get existing report for a specific date"""
        json_path = os.path.join(self.reports_dir, f"{date}.json")
        html_path = os.path.join(self.reports_dir, f"{date}.html")
        
        if not os.path.exists(json_path):
            return None
            
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        html_content = ""
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        return {
            'date': date,
            'json_data': json_data,
            'html_content': html_content,
            'html_path': html_path,
            'json_path': json_path
        }
    
    def clear_all_reports(self) -> int:
        """Clear all stored reports"""
        if not os.path.exists(self.reports_dir):
            return 0
            
        count = 0
        for filename in os.listdir(self.reports_dir):
            if filename.endswith(('.json', '.html')):
                os.remove(os.path.join(self.reports_dir, filename))
                count += 1
                
        self.logger.info(f"Cleared {count} report files")
        return count