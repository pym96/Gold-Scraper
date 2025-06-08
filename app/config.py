"""
Configuration settings for the Gold Spider application.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# News API settings
NEWS_API_KEY = "YOUR_NEWS_API_KEY"  # Replace with your actual API key
NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_API_QUERY = "gold OR \"precious metals\" OR bullion OR XAU"
NEWS_API_SORT = "publishedAt"
NEWS_API_LANGUAGE = "en"
NEWS_API_PAGE_SIZE = 20

# Alpha Vantage API for financial data
ALPHA_VANTAGE_API_KEY = "YOUR_ALPHA_VANTAGE_KEY"
ALPHA_VANTAGE_NEWS_URL = "https://www.alphavantage.co/query"

# Reliable RSS Feeds for Gold News (更可靠的RSS源)
GOLD_RSS_FEEDS = [
    # 主要金融新闻RSS
    "https://www.kitco.com/news/category/gold-news/feed/",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.ft.com/rss/feed/fastft",
    
    # 黄金专业网站RSS
    "https://goldprice.org/rss/gold-news",
    "https://www.gold.org/news-and-events/news/rss",
    "https://bullionvault.com/gold-news/feed/",
    
    # 财经媒体RSS
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Commodities
    "https://finance.yahoo.com/rss/topfinstories",
]

# 可靠的新闻API备选方案
ALTERNATIVE_NEWS_APIS = {
    "finnhub": {
        "url": "https://finnhub.io/api/v1/news",
        "api_key": "YOUR_FINNHUB_KEY",
        "category": "general"
    },
    "polygon": {
        "url": "https://api.polygon.io/v2/reference/news",
        "api_key": "YOUR_POLYGON_KEY"
    }
}

# Scraper settings - 更新了黄金新闻源列表，移除了无效和频繁拒绝的URL
GOLD_NEWS_SOURCES = [
    # 更可靠的黄金新闻专门网站
    "https://www.kitco.com/news/category/gold-news/",
    "https://www.gold.org/news-and-events/news",
    "https://goldprice.org/gold-news.html",
    
    # 主流金融网站的黄金/大宗商品栏目
    "https://www.reuters.com/markets/commodities/",
    "https://www.bloomberg.com/markets/commodities/futures/metals",
    "https://www.investing.com/news/commodities-news",
    "https://www.ft.com/commodities",
    
    # 专业贵金属交易网站
    "https://www.bullionvault.com/gold-news",
    "https://www.moneymetals.com/news",
    "https://www.apmex.com/blog/category/market-updates"
]

# 每个新闻源的权重（用于排序）- 更高的权重表示更专注于黄金
SOURCE_WEIGHTS = {
    "kitco.com": 10,
    "gold.org": 10,
    "goldprice.org": 9,
    "bullionvault.com": 8,
    "moneymetals.com": 8,
    "apmex.com": 7,
    "reuters.com": 6,
    "bloomberg.com": 6,
    "investing.com": 5,
    "ft.com": 5
}

# 增加浏览器指纹多样性的用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57"
]

# 请求参数设置
REQUEST_TIMEOUT = 25  # 增加超时时间
REQUEST_RETRIES = 3   # 添加重试次数
REQUEST_DELAY = 3     # 添加请求间隔秒数

# 摘要关键词 - 筛选文章内容中包含这些关键词的段落
GOLD_KEYWORDS = [
    "gold", "silver", "precious metals", "bullion", "XAU", "troy ounce",
    "gold price", "spot gold", "gold futures", "gold investment", "gold market",
    "gold ETF", "physical gold", "gold bars", "gold coins", "gold reserves",
    "central bank", "inflation", "safe haven", "store of value"
]

SCRAPE_INTERVAL = 60  # minutes - 增加抓取间隔以防止封禁

# Ollama settings
OLLAMA_MODEL = "llama2"  # Using available model
OLLAMA_HOST = "http://localhost:11434"

# Summary format
SUMMARY_TEMPLATE = """
Based on the title and content of the article, provide a structured summary with the following format:

Title: {title}

Core Summary (50 words or less): 
[Provide a concise summary of the key points]

Assets Involved: 
[List the main assets/commodities mentioned]

Risk Alert: 
[Highlight any potential risks or warnings mentioned]
"""

# Storage settings
STORAGE_TYPE = "json"  # "json" or "sqlite"
JSON_DB_PATH = BASE_DIR / "data" / "news_db.json"
SQLITE_DB_PATH = BASE_DIR / "data" / "news_db.sqlite"

# Ensure data directory exists
os.makedirs(BASE_DIR / "data", exist_ok=True)

# API settings
API_PREFIX = "/api"
