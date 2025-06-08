import time
import json
import logging
import urllib.parse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
try:
    import cloudscraper
except ImportError:
    logging.warning("cloudscraper not installed, falling back to requests")
    cloudscraper = None

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from app.config import USER_AGENTS, JSON_DB_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class GoldScraper:
    def __init__(self):
        # Updated URLs with more accessible sources
        self.urls = [
            "https://www.kitco.com/market/",  # Main Kitco market page
            "https://www.investing.com/commodities/gold",  # Fixed investing.com URL
            "https://finance.yahoo.com/quote/GC=F",  # Yahoo Finance gold futures
            "https://www.marketwatch.com/investing/future/gc00",  # MarketWatch gold
            "https://www.cnbc.com/precious-metals/",  # CNBC precious metals
            "https://www.federalreserve.gov/newsevents/pressreleases.htm"  # Federal Reserve - updated to press releases
        ]
        
        self.selectors = {
            "kitco.com": {
                "article_list": "div.market-news-wrapper article, div.news-list div.news-item, div.article-list article.article-item",
                "title": "h3, a.news-title, a.article-title",
                "date": "span.date, span.news-date, span.article-date",
                "content": "div.article-body, div.article-content",
                "content_alt": "div.content",
                "summary": "div.lead, p.summary, .article-summary, meta[name='description']",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "investing.com": {
                "article_list": "#leftColumn article, .articleItem, .js-article-item",
                "title": ".title, h1, .articleHeader",
                "date": ".date, time",
                "content": ".articlePage, .WYSIWYG",
                "content_alt": "#fullArticle",
                "summary": ".articleText p:first-of-type, .article__summary",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "finance.yahoo.com": {
                "article_list": "ul.My\\(0\\) li",
                "title": "h3, a",
                "date": "span.C\\(\\#959595\\), .C\\(\\$c-fuji-grey-c\\)",
                "content": ".caas-body",
                "content_alt": "article",
                "summary": ".caas-description",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "marketwatch.com": {
                "article_list": ".article__content, .collection__elements article",
                "title": "h3.article__headline a, .link, h2 a",
                "date": "span.article__timestamp, .timestamp",
                "content": ".article__body, .article-wrap",
                "content_alt": ".column--primary",
                "summary": ".article__summary, .summary, .paywall-desc",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "cnbc.com": {
                "article_list": ".Card-standardBreakerCard, .Card, article",
                "title": ".Card-title, h3 a, .title",
                "date": "time, .Card-time",
                "content": ".ArticleBody-articleBody, .group",
                "content_alt": "article",
                "summary": ".SummaryList-item, .summary",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "federalreserve.gov": {
                "article_list": "div.item, article.news-item, .row.news-row",
                "title": "h4 a, h3 a, .title a",
                "date": "time, p.news-date, .date",
                "content": "div.col-xs-12 div.row, .content-block",
                "content_alt": "div.content",
                "summary": ".lead, .summary, p:first-of-type",
                "meta_description": "meta[name='description'], meta[property='og:description']"
            },
            "wsj.com": {
                "summary": ".article-summary, .paywall-desc, .wsj-summary, #article_slice p:first-of-type",
                "meta_description": "meta[name='description'], meta[property='og:description']",
                "paywall_indicator": ".wsj-paywall, .paywall-overlay, .snippet-promotion"
            }
        }
        
        self.keywords = ["gold", "federal reserve", "wall street", "precious metals", "commodities", "bullion", "XAU", "silver", "platinum"]
        self.headers = {
            "User-Agent": USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "TE": "Trailers",
            "DNT": "1"
        }
        self.db_path = JSON_DB_PATH
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        # Maximum age for articles (in days)
        self.max_article_age = 30  # Only fetch articles from last 30 days

    def get_domain(self, url: str) -> str:
        """Extract domain from URL for selector mapping"""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain

    def get_article_list(self) -> List[Dict]:
        all_articles = []
        
        for url in self.urls:
            domain = self.get_domain(url)
            logger.info(f"Fetching article list from {url} (domain: {domain})")
            
            if domain not in self.selectors:
                logger.warning(f"No selectors defined for domain {domain}, skipping...")
                continue
            
            selectors = self.selectors[domain]
            
            try:
                # First try with cloudscraper if available (for sites with anti-bot protection)
                if cloudscraper is not None:
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, headers=self.headers, timeout=15)
                else:
                    response = requests.get(url, headers=self.headers, timeout=15)
                    
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                articles_section = soup.select(selectors["article_list"])
                
                if not articles_section:
                    logger.warning(f"No articles found with requests for {domain}, trying Selenium")
                    # Log a snippet of the HTML to debug selector issues
                    logger.debug(f"HTML snippet for {domain}: {soup.prettify()[:1000]}")
                    
                    # Use Selenium for dynamic content
                    options = Options()
                    options.add_argument("--headless")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument(f"user-agent={USER_AGENTS[0]}")
                    
                    # Add additional Chrome options to avoid detection
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option("useAutomationExtension", False)
                    
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                    
                    # Set window size to desktop size
                    driver.set_window_size(1920, 1080)
                    
                    # Add a script to help bypass bot detection
                    driver.execute_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    """)
                    
                    driver.get(url)
                    
                    try:
                        # Wait for articles to load with a longer timeout
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selectors["article_list"].split(',')[0].strip()))
                        )
                    except Exception as e:
                        logger.warning(f"Timeout waiting for articles to load: {e}")
                    
                    # Scroll down to load lazy-loaded content
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(2)
                    
                    soup = BeautifulSoup(driver.page_source, "lxml")
                    driver.quit()
                    articles_section = soup.select(selectors["article_list"])
                
                logger.info(f"Found {len(articles_section)} article elements for {domain}")
                articles = []
                
                for article in articles_section:
                    try:
                        # Try multiple selector variations (split by comma)
                        title_selectors = selectors["title"].split(',')
                        title_element = None
                        
                        for selector in title_selectors:
                            title_element = article.select_one(selector.strip())
                            if title_element:
                                break
                                
                        if not title_element:
                            continue
                            
                        title = title_element.text.strip()
                        
                        # Filter by keywords
                        if not any(keyword.lower() in title.lower() for keyword in self.keywords):
                            continue
                            
                        rel_link = title_element.get("href")
                        
                        if not rel_link:
                            continue
                            
                        # Make relative URL absolute
                        if rel_link.startswith("/"):
                            base_url = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}"
                            link = f"{base_url}{rel_link}"
                        else:
                            link = rel_link
                            
                        # Try multiple date selectors
                        date_selectors = selectors["date"].split(',')
                        date_element = None
                        
                        for selector in date_selectors:
                            date_element = article.select_one(selector.strip())
                            if date_element:
                                break
                                
                        pub_date = date_element.text.strip() if date_element else datetime.now().strftime("%Y-%m-%d")
                        
                        # Skip articles that are too old
                        if not self.is_recent_article(pub_date):
                            logger.info(f"Skipping older article: {title} ({pub_date})")
                            continue
                        
                        # Try to extract a summary directly from the article listing
                        summary = ""
                        summary_element = None
                        if "summary" in selectors:
                            summary_selectors = selectors["summary"].split(',')
                            for selector in summary_selectors:
                                summary_element = article.select_one(selector.strip())
                                if summary_element:
                                    summary = summary_element.text.strip()
                                    break
                        
                        # Clean up the title and summary text
                        title = self.clean_text(title)
                        summary = self.clean_text(summary) if summary else ""
                        
                        articles.append({
                            "title": title,
                            "link": link,
                            "source": domain,
                            "pub_date": pub_date,
                            "fetched_at": datetime.now().isoformat(),
                            "summarized": False,
                            "content": summary if summary else "",
                            "summary": summary if summary else None
                        })
                    except Exception as e:
                        logger.error(f"Error extracting article info from {domain}: {e}")
                
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} matching articles from {domain}")
                
            except Exception as e:
                logger.error(f"Error fetching article list from {url}: {e}")
        
        # Sort articles by date (newest first)
        all_articles.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
        return all_articles
        
    def extract_text_from_meta_tags(self, soup: BeautifulSoup, meta_selector: str) -> str:
        """Extract text from meta tags that often contain article descriptions"""
        meta_tags = soup.select(meta_selector)
        for tag in meta_tags:
            content = tag.get("content")
            if content and len(content) > 20:  # Ensure it's not an empty or tiny description
                return content.strip()
        return ""
        
    def extract_article_preview(self, soup: BeautifulSoup, domain: str) -> Tuple[str, bool]:
        """Extract preview/header content from articles, including paywalled ones"""
        selectors = self.selectors.get(domain, {})
        
        # Check for paywall
        is_paywalled = False
        if "paywall_indicator" in selectors:
            paywall_elements = soup.select(selectors["paywall_indicator"])
            is_paywalled = len(paywall_elements) > 0
            
        # Try to get summary content
        summary = ""
        
        # Method 1: Look for specific summary elements
        if "summary" in selectors:
            summary_selectors = selectors["summary"].split(',')
            for selector in summary_selectors:
                summary_elements = soup.select(selector.strip())
                if summary_elements:
                    summary = "\n".join([elem.text.strip() for elem in summary_elements])
                    break
        
        # Method 2: Extract from meta description tags
        if not summary and "meta_description" in selectors:
            summary = self.extract_text_from_meta_tags(soup, selectors["meta_description"])
            
        # Method 3: Get first paragraph or sentence
        if not summary:
            # Try first paragraph
            first_p = soup.select_one("p")
            if first_p:
                summary = first_p.text.strip()
                
            # If summary is too long, limit to first few sentences
            if len(summary) > 300:
                sentences = re.split(r'(?<=[.!?])\s+', summary)
                summary = " ".join(sentences[:3]) if sentences else summary[:300] + "..."
                
        return self.clean_text(summary.strip()), is_paywalled

    def get_yahoo_finance_data(self) -> Dict:
        """Get real-time gold price data from Yahoo Finance API"""
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        logger.info("Fetching real-time gold price data from Yahoo Finance")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant data
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("previousClose")
            change = price - prev_close if price and prev_close else None
            change_percent = (change / prev_close * 100) if change and prev_close else None
            
            gold_data = {
                "title": f"Gold Price Update: ${price:.2f} ({change_percent:+.2f}%)",
                "link": "https://finance.yahoo.com/quote/GC=F",
                "source": "yahoo_finance_api",
                "pub_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fetched_at": datetime.now().isoformat(),
                "summarized": False,
                "content": f"Current Gold Price: ${price:.2f}\nChange: ${change:+.2f} ({change_percent:+.2f}%)\nPrevious Close: ${prev_close:.2f}",
                "summary": f"Gold is trading at ${price:.2f}, {change_percent:+.2f}% {('up' if change > 0 else 'down')} from yesterday's close of ${prev_close:.2f}.",
                "data": {
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "prev_close": prev_close,
                    "currency": "USD",
                    "unit": "troy ounce"
                }
            }
            
            logger.info(f"Fetched real-time gold price: ${price:.2f}")
            return gold_data
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance gold data: {e}")
            return None

    def get_fed_reports(self) -> List[Dict]:
        """Get Federal Reserve reports specifically"""
        # Try more direct sources for Federal Reserve gold-related content
        urls = [
            "https://www.federalreserve.gov/newsevents/pressreleases.htm",
            "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        ]
        
        articles = []
        
        for url in urls:
            logger.info(f"Fetching Fed reports from {url}")
            
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                
                # For press releases page
                if "pressreleases" in url:
                    # Focus on the press release content area
                    content_area = soup.select_one("div#article")
                    if content_area:
                        items = content_area.select("div.row.item")
                        
                        for item in items:
                            date_elem = item.select_one("div.col-xs-2")
                            link_elem = item.select_one("div.col-xs-10 a")
                            
                            if date_elem and link_elem:
                                pub_date = date_elem.text.strip()
                                title = link_elem.text.strip()
                                
                                # Only include if matches keywords and is recent
                                if (any(keyword.lower() in title.lower() for keyword in self.keywords) and 
                                    self.is_recent_article(pub_date)):
                                    
                                    rel_link = link_elem.get("href")
                                    if rel_link:
                                        if rel_link.startswith("/"):
                                            full_link = f"https://www.federalreserve.gov{rel_link}"
                                        else:
                                            full_link = rel_link
                                            
                                        # Clean up the title
                                        title = self.clean_text(title)
                                        
                                        articles.append({
                                            "title": title,
                                            "link": full_link,
                                            "source": "federalreserve.gov",
                                            "pub_date": pub_date,
                                            "fetched_at": datetime.now().isoformat(),
                                            "summarized": False,
                                            "content": "",
                                            "summary": f"Federal Reserve release: {title} from {pub_date}",
                                            "is_paywalled": False
                                        })
                
                # For FOMC calendars page
                else:
                    meetings = soup.select("div.panel-default")
                    
                    for meeting in meetings:
                        heading = meeting.select_one("div.panel-heading")
                        if not heading:
                            continue
                            
                        date_text = heading.text.strip()
                        
                        # Skip if not a recent meeting
                        if not self.is_recent_article(date_text):
                            continue
                            
                        links = meeting.select("a")
                        
                        for link in links:
                            title = link.text.strip()
                            if any(keyword.lower() in title.lower() for keyword in self.keywords):
                                rel_link = link.get("href")
                                if not rel_link:
                                    continue
                                    
                                if rel_link.startswith("/"):
                                    full_link = f"https://www.federalreserve.gov{rel_link}"
                                else:
                                    full_link = rel_link
                                    
                                # Clean up the title
                                title = self.clean_text(title)
                                    
                                articles.append({
                                    "title": title,
                                    "link": full_link,
                                    "source": "federalreserve.gov",
                                    "pub_date": date_text,
                                    "fetched_at": datetime.now().isoformat(),
                                    "summarized": False,
                                    "content": "PDF report" if full_link.endswith(".pdf") else "",
                                    "summary": f"Federal Reserve report: {title} from {date_text}",
                                    "is_paywalled": False
                                })
                
                logger.info(f"Fetched {len(articles)} Fed reports from {url}")
                
            except Exception as e:
                logger.error(f"Error fetching Fed reports from {url}: {e}")
                
        return articles

    def get_article_content(self, article: Dict) -> Optional[str]:
        article_url = article["link"]
        domain = article["source"]
        logger.info(f"Fetching content from {article_url}")
        
        # Skip PDF documents
        if article_url.endswith(".pdf"):
            logger.info(f"Skipping PDF document: {article_url}")
            return "PDF document - content not extracted"
        
        # Handle special case domains manually
        base_domain = self.get_domain(article_url)
        if base_domain not in self.selectors and domain in self.selectors:
            base_domain = domain
            
        try:
            time.sleep(1)  # Polite delay
            
            # Use cloudscraper if available
            if cloudscraper is not None:
                scraper = cloudscraper.create_scraper()
                response = scraper.get(article_url, headers=self.headers, timeout=15)
            else:
                response = requests.get(article_url, headers=self.headers, timeout=15)
                
            if response.status_code == 403 or response.status_code == 401:
                logger.warning(f"Access restricted (status {response.status_code}) for {article_url}, trying to extract summary only")
                preview_content, is_paywalled = "", True
                article["is_paywalled"] = True
                return "Access restricted - paywall detected"
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            
            # First, try to extract a preview/summary even if full content isn't available
            preview_content, is_paywalled = self.extract_article_preview(soup, base_domain)
            article["is_paywalled"] = is_paywalled
            
            if preview_content:
                article["summary"] = preview_content
                
            # If paywalled, return just the preview
            if is_paywalled:
                logger.info(f"Paywall detected for {article_url}, using preview content")
                return preview_content
                
            # If no paywall, continue with full content extraction
            if base_domain not in self.selectors:
                logger.warning(f"No selectors defined for domain {base_domain}, using summary only")
                return preview_content
                
            selectors = self.selectors[base_domain]
            
            # Try multiple content selectors
            content_selectors = selectors["content"].split(',')
            content_div = None
            
            for selector in content_selectors:
                content_div = soup.select_one(selector.strip())
                if content_div:
                    break
            
            if not content_div:
                content_selectors = selectors["content_alt"].split(',')
                for selector in content_selectors:
                    content_div = soup.select_one(selector.strip())
                    if content_div:
                        break
            
            if content_div:
                # Remove unwanted elements
                for unwanted in content_div.select("div.related-articles, div.ads, div.ad-container, aside, .share-tools, .newsletter-signup, .subscription-signup, nav, header, footer, .cookie-notice"):
                    unwanted.decompose()
                
                paragraphs = content_div.select("p")
                if paragraphs:
                    content = "\n\n".join([p.get_text().strip() for p in paragraphs])
                else:
                    # If no paragraphs found, get all text
                    content = content_div.get_text().strip()
                
                # Clean the content
                content = self.clean_text(content)
                return content
                
            # If we couldn't extract full content but have a preview, return that
            if preview_content:
                return preview_content
                
            return None
            
        except Exception as e:
            logger.error(f"Error fetching article content from {article_url}: {e}")
            return None

    def update_database(self, articles: List[Dict]):
        existing_articles = []
        
        if Path(self.db_path).exists():
            try:
                with open(self.db_path, "r") as f:
                    existing_articles = json.load(f)
            except json.JSONDecodeError:
                logger.error("Error reading database file, starting with empty database")
                existing_articles = []
        
        # 清理现有文章，移除2022年的内容
        existing_articles = [
            article for article in existing_articles 
            if "2022" not in article.get("pub_date", "") and 
               not re.search(r'2022|FOMC Meetings', article.get("title", ""))
        ]
        
        existing_urls = {article["link"] for article in existing_articles}
        new_articles = [article for article in articles if article["link"] not in existing_urls]
        
        updated_articles = new_articles + existing_articles
        
        # 确保最新的文章排在前面（按抓取时间排序）
        updated_articles.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
        
        try:
            with open(self.db_path, "w") as f:
                json.dump(updated_articles, f, indent=2)
            logger.info(f"Added {len(new_articles)} new articles to database")
        except Exception as e:
            logger.error(f"Error updating database: {e}")
    
    def scrape(self, fetch_content: bool = False) -> List[Dict]:
        articles = self.get_article_list()
        
        # Add Federal Reserve specific reports
        fed_reports = self.get_fed_reports()
        articles.extend(fed_reports)
        
        # Add real-time gold price data
        gold_price_data = self.get_yahoo_finance_data()
        if gold_price_data:
            articles.append(gold_price_data)
        
        if fetch_content and articles:
            for article in articles:
                # Skip if it's already identified as a PDF or already has content
                if article.get("content") == "PDF report" or (article.get("content") and len(article.get("content")) > 200):
                    continue
                    
                content = self.get_article_content(article)
                if content:
                    article["content"] = content
        
        # Final cleanup and sorting
        for article in articles:
            if article.get("title"):
                article["title"] = self.clean_text(article["title"])
            if article.get("content"):
                article["content"] = self.clean_text(article["content"])
            if article.get("summary"):
                article["summary"] = self.clean_text(article["summary"])
        
        # Sort by date (newest first)
        articles.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
        
        self.update_database(articles)
        return articles
        
    def extract_missing_content(self):
        """Extract content for articles that are missing it in the database"""
        logger.info("Extracting missing content for articles in the database")
        
        try:
            # Load existing database
            if not Path(self.db_path).exists():
                logger.error(f"Database file {self.db_path} does not exist")
                return
                
            with open(self.db_path, "r") as f:
                articles = json.load(f)
                
            articles_updated = 0
            for article in articles:
                # Skip if content is already populated or is a PDF
                if article.get("content") and article.get("content") != "" and article.get("content") != "PDF report":
                    continue
                
                # Skip PDF reports
                if article.get("link", "").endswith(".pdf"):
                    article["content"] = "PDF document - content not extracted"
                    articles_updated += 1
                    continue
                    
                logger.info(f"Fetching missing content for article: {article['title']}")
                content = self.get_article_content(article)
                if content:
                    article["content"] = content
                    articles_updated += 1
                    
            # Save updated database
            with open(self.db_path, "w") as f:
                json.dump(articles, f, indent=2)
                
            logger.info(f"Updated content for {articles_updated} articles in the database")
            
        except Exception as e:
            logger.error(f"Error extracting missing content: {e}")

    def clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace, weird symbols, and HTML remnants"""
        if not text:
            return ""
            
        # Replace HTML entities
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;|&#34;', '"', text)
        text = re.sub(r'&apos;|&#39;', "'", text)
        text = re.sub(r'&nbsp;|&#160;', ' ', text)
        
        # Remove bizarre Unicode control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove navigation text patterns often seen in scraped content
        text = re.sub(r'Home\s+>\s+.*?\s+>\s+.*?\s+>', '', text)
        text = re.sub(r'Menu\s+Search\s+.*?Sign in', '', text)
        text = re.sub(r'Toggle menu.*?Toggle search', '', text)
        
        # 更严格地过滤掉联邦储备网站的导航元素
        text = re.sub(r'Board of Governors of the Federal Reserve System.*?Financial System', '', text, flags=re.DOTALL)
        text = re.sub(r'Federal Open Market Committee.*?Resources for Consumers', '', text, flags=re.DOTALL)
        text = re.sub(r'An official website of the United States Government.*?secure websites\.', '', text, flags=re.DOTALL)
        
        # 移除特殊字符
        text = re.sub(r'ï»¿', '', text)  # Remove BOM character
        
        # Replace multiple whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats into datetime object"""
        date_str = date_str.strip()
        
        # Common date formats found on financial news sites
        formats = [
            '%Y-%m-%d',                     # 2022-05-01
            '%Y-%m-%dT%H:%M:%S',            # 2022-05-01T12:30:45
            '%Y-%m-%dT%H:%M:%SZ',           # 2022-05-01T12:30:45Z
            '%Y-%m-%d %H:%M:%S',            # 2022-05-01 12:30:45
            '%b %d, %Y',                    # May 01, 2022
            '%B %d, %Y',                    # May 01, 2022
            '%d %b %Y',                     # 01 May 2022
            '%d %B %Y',                     # 01 May 2022
            '%m/%d/%Y',                     # 05/01/2022
            '%d/%m/%Y',                     # 01/05/2022
            '%Y年%m月%d日',                  # 2022年05月01日
            '%a, %d %b %Y %H:%M:%S %z',     # Mon, 01 May 2022 12:30:45 +0000
        ]
        
        # Handle "X hours/days ago" format
        time_ago_match = re.search(r'(\d+)\s+(hour|day|minute|second|min|hr|h|d)s?\s+ago', date_str, re.IGNORECASE)
        if time_ago_match:
            amount = int(time_ago_match.group(1))
            unit = time_ago_match.group(2).lower()
            
            now = datetime.now()
            if unit in ['hour', 'hr', 'h']:
                return now - timedelta(hours=amount)
            elif unit in ['day', 'd']:
                return now - timedelta(days=amount)
            elif unit in ['minute', 'min']:
                return now - timedelta(minutes=amount)
            elif unit in ['second', 'sec', 's']:
                return now - timedelta(seconds=amount)
                
        # Try each format
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If all formats fail, try to extract a date with regex
        date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', date_str)
        if date_match:
            try:
                return datetime.strptime(date_match.group(1), '%Y-%m-%d')
            except ValueError:
                try:
                    return datetime.strptime(date_match.group(1), '%Y/%m/%d')
                except ValueError:
                    pass
        
        # Could not parse the date
        return None

    def is_recent_article(self, date_str: str) -> bool:
        """Check if an article is recent based on its date string"""
        if not date_str:
            return True  # If no date, assume it's recent to avoid missing content
            
        # 明确拒绝带有2022年标记的文章
        if "2022" in date_str:
            return False
            
        parsed_date = self.parse_date(date_str)
        if not parsed_date:
            return True  # If can't parse, assume it's recent
            
        # 减少接受的文章时间范围为7天（比之前的30天更严格）
        cutoff_date = datetime.now() - timedelta(days=7)
        return parsed_date >= cutoff_date

if __name__ == "__main__":
    scraper = GoldScraper()
    
    # Command line arguments can be used to control behavior
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--update-existing":
        # Only update existing articles without scraping new ones
        scraper.extract_missing_content()
    else:
        # Normal scraping operation
        new_articles = scraper.scrape(fetch_content=True)
        print(f"Scraped {len(new_articles)} new articles")
        if new_articles:
            sample = new_articles[0]
            print(f"\nSample Article:")
            print(f"Title: {sample['title']}")
            print(f"Source: {sample['source']}")
            print(f"Link: {sample['link']}")
            print(f"Published: {sample['pub_date']}")
            
            if sample.get("is_paywalled"):
                print(f"[PAYWALLED CONTENT]")
                
            if sample.get("summary"):
                print(f"\nSummary: {sample['summary']}")
                
            if sample.get("content"):
                print(f"\nContent (excerpt): {sample['content'][:200]}...")