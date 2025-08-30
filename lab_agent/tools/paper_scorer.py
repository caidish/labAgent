import logging
import os
import json
from typing import List, Dict
from openai import OpenAI
from ..utils import Config
from .gpt5_mini_client import GPT5MiniClient


class PaperScorer:
    def __init__(self):
        self.logger = logging.getLogger("tools.paper_scorer")
        self.config = Config()
        
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        
        self.client = OpenAI(api_key=self.config.openai_api_key)
        self.prompt_template = self._load_prompt_template()
        
        # Load model configuration
        self.model_config = self._load_model_config()
        
        # Initialize GPT-5-mini client if needed
        if self.model_config.get('name') == 'gpt-5-mini':
            self.gpt5_mini_client = GPT5MiniClient()
        else:
            self.gpt5_mini_client = None
        
    def _load_model_config(self) -> Dict:
        """Load model configuration from models.json"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'models.json'
        )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                models_config = json.load(f)
                return models_config.get('arxivFilterModel', {})
        except FileNotFoundError:
            self.logger.warning(f"Models config not found at {config_path}, using GPT-4o")
            return {"name": "gpt-4o", "provider": "openai"}
    
    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'promptArxivRecommender.txt'
        )
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Prompt template not found at {prompt_path}")
            return self._default_prompt()
    
    def _default_prompt(self) -> str:
        return """Rate this arXiv paper from 1-3 based on relevance to 2D materials research:
        3 = High relevance (2D materials, graphene, TMDs, quantum devices)
        2 = Medium relevance (related condensed matter physics)
        1 = Low relevance (general interest only)
        
        Respond with: Score: X, Reason: [brief explanation]
        
        {PAPER_INFO}"""
    
    def score_papers(self, papers: List[Dict[str, str]]) -> List[Dict[str, any]]:
        print(f"[DEBUG] Starting to score {len(papers)} papers")
        scored_papers = []
        
        for i, paper in enumerate(papers):
            try:
                print(f"[DEBUG] Scoring paper {i+1}/{len(papers)}: {paper.get('title', 'No title')[:50]}...")
                score_data = self._score_single_paper(paper)
                paper_with_score = paper.copy()
                paper_with_score.update(score_data)
                scored_papers.append(paper_with_score)
                print(f"[DEBUG] Paper scored: {score_data.get('score', 'N/A')} - {score_data.get('reason', 'N/A')}")
                
            except Exception as e:
                self.logger.error(f"Error scoring paper {paper.get('id', 'unknown')}: {e}")
                print(f"[DEBUG] Scoring error for paper {i+1}: {e}")
                # Add paper with default score if scoring fails
                paper_with_score = paper.copy()
                paper_with_score.update({
                    'score': 1,
                    'reason': 'Error in scoring - defaulted to low priority',
                    'key_relevance': 'N/A'
                })
                scored_papers.append(paper_with_score)
        
        print(f"[DEBUG] Finished scoring all papers")
        return scored_papers
    
    def _score_single_paper(self, paper: Dict[str, str]) -> Dict[str, any]:
        # Format paper info for the prompt
        paper_info = f"""
Title: {paper.get('title', 'N/A')}
Authors: {paper.get('authors', 'N/A')}
Abstract: {paper.get('abstract', 'N/A')}
Subjects: {paper.get('subjects', 'N/A')}
"""
        
        prompt = self.prompt_template.replace('{PAPER_INFO}', paper_info)
        
        try:
            if self.gpt5_mini_client:
                # Use GPT-5-mini responses API
                print(f"[DEBUG] Making GPT-5-mini API call...")
                messages = [
                    {"role": "system", "content": "You are an expert research paper evaluator for a 2D materials physics laboratory."},
                    {"role": "user", "content": prompt}
                ]
                
                result = self.gpt5_mini_client.create_response(
                    messages=messages, 
                    use_case=self.model_config.get('purpose', 'paper_scoring')
                )
                
                if result['success']:
                    print(f"[DEBUG] GPT-5-mini API call successful")
                    response_text = result['content']
                    print(f"[DEBUG] Response: {response_text[:100]}...")
                    return self._parse_response(response_text)
                else:
                    raise Exception(result.get('error', 'Unknown GPT-5-mini API error'))
            else:
                # Use traditional chat completions API for GPT-4o
                print(f"[DEBUG] Making OpenAI chat completions API call...")
                model_name = self.model_config.get('name', 'gpt-4o')
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert research paper evaluator for a 2D materials physics laboratory."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.1
                )
                
                print(f"[DEBUG] OpenAI API call successful")
                response_text = response.choices[0].message.content
                print(f"[DEBUG] Response: {response_text[:100]}...")
                return self._parse_response(response_text)
            
        except Exception as e:
            self.logger.error(f"API error: {e}")
            print(f"[DEBUG] API error: {e}")
            raise
    
    def _parse_response(self, response_text: str) -> Dict[str, any]:
        # Parse the response to extract score, reason, and key relevance
        lines = response_text.strip().split('\n')
        
        score = 1
        reason = "Unable to parse response"
        key_relevance = "N/A"
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('score:') or line.lower().startswith('**score**:'):
                try:
                    score_part = line.split(':', 1)[1].strip()
                    # Extract the number from the score part
                    import re
                    score_match = re.search(r'(\d+)', score_part)
                    if score_match:
                        score = int(score_match.group(1))
                        score = max(1, min(3, score))  # Clamp between 1-3
                except:
                    pass
            elif line.lower().startswith('reason:') or line.lower().startswith('**reason**:'):
                reason = line.split(':', 1)[1].strip()
            elif line.lower().startswith('key relevance:') or line.lower().startswith('**key relevance**:'):
                key_relevance = line.split(':', 1)[1].strip()
        
        return {
            'score': score,
            'reason': reason,
            'key_relevance': key_relevance
        }
    
    def batch_score_papers(self, papers: List[Dict[str, str]], batch_size: int = 5) -> List[Dict[str, any]]:
        """Score papers in batches to manage API rate limits"""
        all_scored = []
        
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            self.logger.info(f"Scoring batch {i//batch_size + 1} ({len(batch)} papers)")
            
            scored_batch = self.score_papers(batch)
            all_scored.extend(scored_batch)
            
            # Brief pause between batches to respect rate limits
            import time
            time.sleep(1)
        
        return all_scored