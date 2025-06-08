"""
Summarizer Module

This module uses the local Ollama model to summarize gold news articles.
"""
import json
import logging
import subprocess
from typing import Dict, Optional, List, Any
import time
from pathlib import Path

from app.config import OLLAMA_MODEL, OLLAMA_HOST, SUMMARY_TEMPLATE, JSON_DB_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """
    A class to summarize gold news articles using Ollama
    """

    def __init__(self, model_name: str = OLLAMA_MODEL):
        self.model_name = model_name
        self.db_path = JSON_DB_PATH

    def summarize_article(self, title: str, content: str) -> Optional[str]:
        """
        Summarize an article using Ollama CLI
        
        Args:
            title (str): The article title
            content (str): The article content
            
        Returns:
            Optional[str]: Structured summary or None if summarization failed
        """
        logger.info(f"Summarizing article: {title}")
        
        # Prepare the prompt with the summary template
        prompt = SUMMARY_TEMPLATE.format(title=title)
        
        # Add content to the prompt
        full_prompt = f"{prompt}\n\nArticle Content:\n{content}"
        
        try:
            # Call Ollama using subprocess
            cmd = ["ollama", "run", self.model_name, full_prompt]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run the command with a timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Ollama command failed: {result.stderr}")
                return None
                
            summary = result.stdout.strip()
            logger.info(f"Successfully generated summary ({len(summary)} chars)")
            return summary
            
        except subprocess.TimeoutExpired:
            logger.error("Ollama command timed out")
            return None
        except Exception as e:
            logger.error(f"Error running Ollama: {e}")
            return None
    
    def summarize_with_ollama_api(self, title: str, content: str) -> Optional[str]:
        """
        Alternative method to summarize using Ollama API
        
        Args:
            title (str): The article title
            content (str): The article content
            
        Returns:
            Optional[str]: Structured summary or None if summarization failed
        """
        try:
            # Try to import ollama module
            import ollama
            
            logger.info(f"Using Ollama API to summarize: {title}")
            
            # Prepare the prompt
            prompt = SUMMARY_TEMPLATE.format(title=title)
            full_prompt = f"{prompt}\n\nArticle Content:\n{content}"
            
            # Call the Ollama API
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            if response and "message" in response and "content" in response["message"]:
                summary = response["message"]["content"].strip()
                logger.info(f"Successfully generated summary via API ({len(summary)} chars)")
                return summary
            else:
                logger.error(f"Unexpected response format from Ollama API: {response}")
                return None
                
        except ImportError:
            logger.warning("Ollama Python package not available, falling back to CLI")
            return self.summarize_article(title, content)
        except Exception as e:
            logger.error(f"Error using Ollama API: {e}")
            return None
    
    def process_articles(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Process unsummarized articles from the database
        
        Args:
            limit (int): Maximum number of articles to process
            
        Returns:
            List[Dict[str, Any]]: List of processed articles
        """
        # Read the database
        try:
            with open(self.db_path, "r") as f:
                articles = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error reading database: {e}")
            return []
        
        # Find unsummarized articles with content
        unsummarized = [
            article for article in articles 
            if not article.get("summarized") and article.get("content")
        ]
        
        logger.info(f"Found {len(unsummarized)} unsummarized articles")
        
        # Process articles up to the limit
        processed_articles = []
        for i, article in enumerate(unsummarized[:limit]):
            logger.info(f"Processing article {i+1}/{min(limit, len(unsummarized))}")
            
            # Try API first, fall back to CLI
            summary = self.summarize_with_ollama_api(article["title"], article["content"])
            
            if summary:
                # Update the article
                article["summary"] = summary
                article["summarized"] = True
                article["summarized_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                processed_articles.append(article)
            else:
                logger.warning(f"Failed to summarize article: {article['title']}")
            
            # Add a small delay between requests
            if i < min(limit, len(unsummarized)) - 1:
                time.sleep(1)
        
        # Update the database with processed articles
        if processed_articles:
            self._update_database(articles)
            logger.info(f"Updated {len(processed_articles)} articles in database")
        
        return processed_articles
    
    def _update_database(self, articles: List[Dict[str, Any]]) -> None:
        """
        Update the database with the modified articles
        
        Args:
            articles (List[Dict[str, Any]]): The full list of articles
        """
        try:
            with open(self.db_path, "w") as f:
                json.dump(articles, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating database: {e}")


if __name__ == "__main__":
    # Test the summarizer
    summarizer = ArticleSummarizer()
    processed = summarizer.process_articles(limit=2)
    
    print(f"Processed {len(processed)} articles")
    
    # Print a sample summary if available
    if processed:
        sample = processed[0]
        print(f"\nSample Summary for: {sample['title']}")
        print(f"\n{sample['summary']}")
