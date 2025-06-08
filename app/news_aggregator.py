#!/usr/bin/env python3
"""
改进的新闻聚合器 - 使用RSS和API而非不可靠的网页爬取
专注于获取实时、准确的黄金市场新闻
"""
import json
import logging
import re
import requests
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

from app.config import (
    GOLD_RSS_FEEDS,
    NEWS_API_KEY,
    NEWS_API_URL,
    NEWS_API_QUERY,
    ALTERNATIVE_NEWS_APIS,
    GOLD_KEYWORDS,
    JSON_DB_PATH
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("news_aggregator")

class ReliableNewsAggregator:
    """可靠的新闻聚合器 - 使用RSS和API"""
    
    def __init__(self):
        self.rss_feeds = GOLD_RSS_FEEDS
        self.api_key = NEWS_API_KEY
        self.keywords = GOLD_KEYWORDS
        self.db_path = JSON_DB_PATH
        
    def fetch_from_newsapi(self) -> List[Dict]:
        """从NewsAPI获取新闻"""
        if not self.api_key or self.api_key == "YOUR_NEWS_API_KEY":
            logger.warning("NewsAPI密钥未设置，跳过API获取")
            return []
            
        try:
            params = {
                'q': NEWS_API_QUERY,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': 20,
                'apiKey': self.api_key
            }
            
            response = requests.get(NEWS_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if data.get('status') == 'ok':
                for item in data.get('articles', []):
                    # 跳过被删除的文章
                    if item.get('title') == '[Removed]':
                        continue
                        
                    article = {
                        'title': item.get('title', '').strip(),
                        'link': item.get('url', ''),
                        'source': urlparse(item.get('url', '')).netloc.replace('www.', ''),
                        'pub_date': self.parse_iso_date(item.get('publishedAt')),
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'content': item.get('description', '') + '\n\n' + (item.get('content') or ''),
                        'summary': item.get('description', ''),
                        'score': self.calculate_relevance_score(item.get('title', ''), item.get('description', '')),
                        'summarized': False
                    }
                    
                    if self.is_relevant_article(article):
                        articles.append(article)
                        
                logger.info(f"从NewsAPI获取了 {len(articles)} 篇相关文章")
                
            return articles
            
        except Exception as e:
            logger.error(f"NewsAPI获取失败: {e}")
            return []
    
    def fetch_from_rss(self) -> List[Dict]:
        """从RSS源获取新闻"""
        all_articles = []
        
        for rss_url in self.rss_feeds:
            try:
                logger.info(f"正在获取RSS: {rss_url}")
                
                # 设置User-Agent，避免被阻止
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                # 使用feedparser解析RSS
                feed = feedparser.parse(rss_url, request_headers=headers)
                
                if feed.bozo:
                    logger.warning(f"RSS解析警告: {rss_url} - {feed.bozo_exception}")
                    
                articles_from_feed = []
                
                for entry in feed.entries[:10]:  # 限制每个源最多10篇文章
                    article = {
                        'title': entry.get('title', '').strip(),
                        'link': entry.get('link', ''),
                        'source': urlparse(rss_url).netloc.replace('www.', ''),
                        'pub_date': self.parse_feed_date(entry),
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'content': self.extract_content_from_entry(entry),
                        'summary': entry.get('summary', ''),
                        'score': self.calculate_relevance_score(entry.get('title', ''), entry.get('summary', '')),
                        'summarized': False
                    }
                    
                    if self.is_relevant_article(article):
                        articles_from_feed.append(article)
                
                logger.info(f"从 {urlparse(rss_url).netloc} 获取了 {len(articles_from_feed)} 篇相关文章")
                all_articles.extend(articles_from_feed)
                
            except Exception as e:
                logger.error(f"RSS获取失败 {rss_url}: {e}")
                continue
                
        return all_articles
    
    def parse_iso_date(self, date_str: str) -> str:
        """解析ISO格式日期"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
            
        try:
            # 解析ISO 8601格式
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def parse_feed_date(self, entry) -> str:
        """解析RSS条目的日期"""
        # 尝试多种日期字段
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    time_struct = getattr(entry, field)
                    dt = datetime(*time_struct[:6], tzinfo=timezone.utc)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        
        # 尝试字符串日期字段
        string_fields = ['published', 'updated']
        for field in string_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    from dateutil import parser
                    dt = parser.parse(getattr(entry, field))
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        
        # 默认今天
        return datetime.now().strftime('%Y-%m-%d')
    
    def extract_content_from_entry(self, entry) -> str:
        """从RSS条目提取内容"""
        content_fields = ['content', 'summary', 'description']
        content = ""
        
        for field in content_fields:
            if hasattr(entry, field):
                field_value = getattr(entry, field)
                if isinstance(field_value, list) and field_value:
                    content += field_value[0].get('value', '') + '\n'
                elif isinstance(field_value, str):
                    content += field_value + '\n'
        
        # 清理HTML标签
        import re
        content = re.sub(r'<[^>]+>', '', content)
        return content.strip()
    
    def calculate_relevance_score(self, title: str, description: str) -> float:
        """计算文章相关性分数"""
        text = (title + ' ' + description).lower()
        score = 0.0
        
        # 黄金相关关键词权重
        gold_keywords = {
            'gold': 10, 'bullion': 8, 'precious metals': 8,
            'xau': 7, 'gold price': 12, 'gold market': 10,
            'central bank': 6, 'inflation': 5, 'safe haven': 8,
            'silver': 6, 'platinum': 5, 'palladium': 5
        }
        
        for keyword, weight in gold_keywords.items():
            if keyword in text:
                score += weight
        
        return min(score, 20.0)  # 最高20分
    
    def is_relevant_article(self, article: Dict) -> bool:
        """判断文章是否与黄金相关"""
        if not article.get('title') or not article.get('link'):
            return False
            
        # 最低相关性分数要求
        if article.get('score', 0) < 5:
            return False
            
        # 排除明显的广告或产品页面
        title_lower = article.get('title', '').lower()
        excluded_terms = ['buy gold', 'shop', 'store', 'purchase', 'order now', 'advertisement']
        
        if any(term in title_lower for term in excluded_terms):
            return False
            
        return True
    
    def remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """去除重复文章"""
        seen_urls = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('link', '')
            title = article.get('title', '').strip().lower()
            
            if url not in seen_urls and title not in seen_titles:
                seen_urls.add(url)
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles
    
    def load_existing_articles(self) -> List[Dict]:
        """加载现有文章"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_articles(self, articles: List[Dict]) -> None:
        """保存文章到数据库"""
        # 确保目录存在
        self.db_path.parent.mkdir(exist_ok=True)
        
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    
    def update_database(self, new_articles: List[Dict]) -> None:
        """更新数据库"""
        existing_articles = self.load_existing_articles()
        existing_urls = {article.get('link') for article in existing_articles}
        
        # 只添加新文章
        truly_new_articles = [
            article for article in new_articles 
            if article.get('link') not in existing_urls
        ]
        
        if truly_new_articles:
            # 合并文章并按日期排序
            all_articles = existing_articles + truly_new_articles
            all_articles.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
            
            # 限制总数量（保留最新的100篇）
            all_articles = all_articles[:100]
            
            self.save_articles(all_articles)
            logger.info(f"添加了 {len(truly_new_articles)} 篇新文章到数据库")
        else:
            logger.info("没有新文章需要添加")
    
    def run(self) -> List[Dict]:
        """运行新闻聚合"""
        logger.info("开始聚合黄金新闻...")
        
        all_articles = []
        
        # 从NewsAPI获取
        api_articles = self.fetch_from_newsapi()
        all_articles.extend(api_articles)
        
        # 从RSS获取
        rss_articles = self.fetch_from_rss()
        all_articles.extend(rss_articles)
        
        # 去重和排序
        unique_articles = self.remove_duplicates(all_articles)
        unique_articles.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"总共聚合了 {len(unique_articles)} 篇独特文章")
        
        # 更新数据库
        self.update_database(unique_articles)
        
        return unique_articles

if __name__ == "__main__":
    aggregator = ReliableNewsAggregator()
    articles = aggregator.run()
    print(f"聚合了 {len(articles)} 篇文章") 