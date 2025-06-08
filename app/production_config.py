"""
Production configuration for Gold Spider
Optimized settings for server deployment
"""
import os

# Production settings
DEBUG = False
HOST = "0.0.0.0"
PORT = 8000

# News API settings (production)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWS_API_KEY")
NEWS_API_QUERY = "gold OR \"precious metals\" OR bullion OR XAU OR \"gold price\" OR \"gold market\""
NEWS_API_LANGUAGE = "en"
NEWS_API_PAGE_SIZE = 50  # More articles for production

# Enhanced RSS feeds for production
GOLD_RSS_FEEDS = [
    # Primary financial news RSS
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://finance.yahoo.com/rss/topfinstories",
    
    # Gold-specific RSS feeds
    "https://www.kitco.com/news/category/gold-news/feed/",
    "https://www.gold.org/news-and-events/news/rss",
    "https://bullionvault.com/gold-news/feed/",
    
    # Additional financial RSS
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.ft.com/rss/feed/fastft",
    "https://www.marketwatch.com/rss/topstories",
]

# Production optimization
REQUEST_TIMEOUT = 15
REQUEST_RETRIES = 2
REQUEST_DELAY = 2
SCRAPE_INTERVAL = 20  # Minutes - more frequent updates for production

# Enhanced gold keywords for better filtering
GOLD_KEYWORDS = [
    "gold", "silver", "platinum", "palladium", "precious metals", "bullion", 
    "XAU", "XAG", "troy ounce", "gold price", "spot gold", "gold futures", 
    "gold investment", "gold market", "gold ETF", "physical gold", 
    "gold bars", "gold coins", "gold reserves", "central bank", 
    "inflation", "safe haven", "store of value", "gold mining",
    "gold demand", "gold supply", "gold rally", "gold bull market"
]

# Source weights for relevance scoring
SOURCE_WEIGHTS = {
    "bloomberg.com": 10,
    "reuters.com": 9,
    "cnbc.com": 8,
    "marketwatch.com": 8,
    "kitco.com": 10,
    "gold.org": 10,
    "bullionvault.com": 9,
    "yahoo.com": 7,
    "ft.com": 8
}

# Logging configuration for production
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/production.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "detailed",
            "level": "INFO"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "level": "WARNING"  # Only warnings and errors to console in production
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["file", "console"]
    }
} 