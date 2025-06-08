#!/usr/bin/env python3
"""
GoldSpider API Service - FastAPI backend for gold news scraping
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from app.improved_scraper import ImprovedGoldScraper
from app.config import JSON_DB_PATH

# Initialize FastAPI app
app = FastAPI(
    title="Gold Spider API",
    description="API for fetching latest gold-related news",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create a scraper instance
scraper = ImprovedGoldScraper(use_proxies=False)

# Models
class Article(BaseModel):
    title: str
    link: str
    source: str
    pub_date: str
    fetched_at: str
    content: Optional[str] = ""
    summary: Optional[str] = None
    score: float

class ScrapeResponse(BaseModel):
    message: str
    count: int

# Background task for scraping
def run_scraper():
    scraper.run()

# Custom filter for date formatting
def format_date(date_str):
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str

# Root endpoint serving the index template
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Serve the main page with gold news articles
    """
    try:
        articles = await get_articles(limit=20)
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "articles": articles
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "articles": [],
                "error": str(e)
            }
        )

# Article detail endpoint
@app.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: int):
    """
    Show detailed view of a single article
    """
    try:
        all_articles = await get_articles(limit=100)
        if 0 <= article_id < len(all_articles):
            article = all_articles[article_id]
            return templates.TemplateResponse(
                "article_detail.html",
                {
                    "request": request,
                    "article": article,
                    "article_id": article_id
                }
            )
        else:
            return templates.TemplateResponse(
                "index.html", 
                {
                    "request": request,
                    "articles": all_articles,
                    "error": "Article not found"
                }
            )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "articles": [],
                "error": str(e)
            }
        )

@app.get("/articles", response_model=List[Article])
async def get_articles(limit: int = 50, days: int = 7):
    """
    Get recent gold news articles
    """
    try:
        if Path(JSON_DB_PATH).exists():
            with open(JSON_DB_PATH, 'r') as f:
                articles = json.load(f)
        else:
            articles = []
        
        # Filter by date if requested
        if days > 0:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            articles = [
                article for article in articles
                if article.get('fetched_at', '') > cutoff_date
            ]
        
        # Sort by score and date
        articles.sort(key=lambda x: (x.get('score', 0), x.get('fetched_at', '')), reverse=True)
        
        # Limit results
        return articles[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching articles: {str(e)}")

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_now(background_tasks: BackgroundTasks):
    """
    Trigger a new scraping job
    """
    try:
        # Run scraper in background
        background_tasks.add_task(run_scraper)
        return {
            "message": "Scraping job started in background",
            "count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting scrape job: {str(e)}")

# Register the format_date filter with Jinja2
templates.env.filters["format_date"] = format_date

if __name__ == "__main__":
    # Ensure log directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the FastAPI app with uvicorn
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True) 