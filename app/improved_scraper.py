#!/usr/bin/env python3
"""
Gold Spider - 改进版黄金新闻爬虫
专注于更稳定地抓取最新的黄金相关新闻
"""
import time
import json
import logging
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent  # 动态生成逼真的User-Agent

from app.config import (
    GOLD_NEWS_SOURCES,
    USER_AGENTS,
    REQUEST_TIMEOUT,
    REQUEST_RETRIES,
    REQUEST_DELAY,
    GOLD_KEYWORDS,
    SOURCE_WEIGHTS,
    JSON_DB_PATH
)
from app.proxy_manager import proxy_manager
from app.arch_compat import (
    is_apple_silicon, 
    apply_compatibility_settings, 
    get_compatible_user_agents
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gold_scraper")

class ImprovedGoldScraper:
    """改进的黄金新闻爬虫"""
    
    def __init__(self, use_proxies: bool = False):
        self.sources = GOLD_NEWS_SOURCES
        self.timeout = REQUEST_TIMEOUT
        self.max_retries = REQUEST_RETRIES
        self.delay = REQUEST_DELAY
        self.keywords = GOLD_KEYWORDS
        self.source_weights = SOURCE_WEIGHTS
        self.db_path = JSON_DB_PATH
        self.use_proxies = use_proxies
        
        # 确保数据目录存在
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        # 根据系统架构决定使用哪种User-Agent列表
        if is_apple_silicon():
            logger.info("使用ARM Mac兼容的User-Agent")
            self.user_agents = get_compatible_user_agents()
        else:
            self.user_agents = USER_AGENTS
        
        # 尝试创建更真实的UA
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"无法初始化fake_useragent，使用备用UA列表: {e}")
            self.ua = None
            
        # 创建会话并在所有请求中重复使用
        self.session = requests.Session()
        
        # 应用架构兼容性设置
        self.session = apply_compatibility_settings(self.session)
        
        # 添加常用headers
        self.default_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate", 
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        # 保存无效URLs
        self.invalid_urls = set()
        
        # 如果启用代理，设置代理管理器
        if self.use_proxies:
            proxy_manager.use_proxies = True
            proxy_manager.refresh_proxies()
            
        # 打印状态信息
        logger.info(f"爬虫初始化完成，使用 {len(self.sources)} 个新闻源")
        logger.info(f"使用架构兼容性支持: {is_apple_silicon()}")
        logger.info(f"使用代理: {self.use_proxies}")
        
    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        return random.choice(self.user_agents)
        
    def get_domain(self, url: str) -> str:
        """从URL中提取域名"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
        
    def make_request(self, url: str, headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """发送HTTP请求，包含重试机制"""
        if not headers:
            # 为每个域名创建一致的但独特的User-Agent
            domain = self.get_domain(url)
            domain_hash = hash(domain) % len(self.user_agents)
            consistent_ua = self.user_agents[domain_hash]
            
            headers = self.default_headers.copy()
            headers["User-Agent"] = consistent_ua
            
            # 添加合理的引用页
            parsed_url = urlparse(url)
            headers["Referer"] = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            
            # 设置Origin，模拟用户点击行为
            headers["Origin"] = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
        # 检查URL是否有效
        if url in self.invalid_urls:
            logger.warning(f"跳过已知无效URL: {url}")
            return None
            
        # 检查URL格式是否有效
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                logger.error(f"无效URL格式: {url}")
                self.invalid_urls.add(url)
                return None
        except Exception:
            logger.error(f"无法解析URL: {url}")
            self.invalid_urls.add(url)
            return None
        
        for attempt in range(self.max_retries):
            try:
                # 添加随机延迟以模拟人类行为
                if attempt > 0:
                    delay = self.delay * (1 + random.random()) * (attempt + 1)  # 指数退避
                    logger.info(f"重试请求 {url}，延迟 {delay:.2f} 秒...")
                    time.sleep(delay)
                
                # 使用代理管理器发送请求
                if self.use_proxies:
                    response, used_proxy = proxy_manager.make_request(
                        url=url,
                        headers=headers,
                        timeout=self.timeout,
                        max_retries=1  # 使用代理管理器自己的重试逻辑
                    )
                    
                    if response and response.status_code == 200:
                        return response
                        
                    if response and response.status_code in (403, 429):
                        # 代理被阻止，等待后继续尝试
                        logger.warning(f"代理请求被阻止 ({response.status_code}): {url}")
                        time.sleep(self.delay * 2)
                        continue
                else:
                    # 使用标准会话发送请求
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        timeout=self.timeout,
                        allow_redirects=True
                    )
                    
                    # 检查是否成功
                    if response.status_code == 200:
                        return response
                        
                    # 特殊处理403错误（访问禁止）
                    if response.status_code == 403:
                        logger.warning(f"访问被拒绝 (403): {url}")
                        
                        # 添加延迟并尝试不同的User-Agent
                        headers["User-Agent"] = self.get_random_user_agent()
                        
                        # 尝试使用新会话
                        if attempt == self.max_retries - 1:
                            logger.info("尝试创建新会话...")
                            self.session = requests.Session()
                            self.session = apply_compatibility_settings(self.session)
                            
                        # 增加更长的等待时间
                        wait_time = self.delay * 5 * (attempt + 1)
                        time.sleep(wait_time)
                    
                    # 处理404错误（资源不存在）
                    elif response.status_code == 404:
                        logger.error(f"资源不存在 (404): {url}")
                        self.invalid_urls.add(url)
                        return None
                    
                    # 特殊处理429错误（请求过多）
                    elif response.status_code == 429:
                        logger.warning(f"请求频率限制 (429)，等待更长时间后重试: {url}")
                        time.sleep(self.delay * 3 * (attempt + 1))  # 指数退避
                    else:
                        logger.warning(f"HTTP错误 {response.status_code}: {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt+1}/{self.max_retries}): {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误 (尝试 {attempt+1}/{self.max_retries}): {url}")
            except Exception as e:
                logger.error(f"请求出错: {url}, 错误: {e}")
                
        logger.error(f"达到最大重试次数，无法获取: {url}")
        # 如果所有尝试都失败，则将URL添加到无效列表
        self.invalid_urls.add(url)
        return None
        
    def extract_articles_from_html(self, html: str, source_url: str) -> List[Dict]:
        """从HTML中提取文章信息"""
        domain = self.get_domain(source_url)
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 通用选择器 - 从不同类型的页面结构中查找文章链接
        selectors = [
            "article a", "article h2 a", "article h3 a", "article .title a",  # 典型文章结构
            ".news-item a", ".news-title a", ".article-title a",               # 新闻列表结构
            ".post a", ".entry a", ".entry-title a",                           # 博客类结构
            "h2 a", "h3 a", ".headline a",                                     # 通用标题结构
            ".card a", ".item a", ".story a",                                  # 卡片式结构
            ".list a[href*=news]", ".list a[href*=article]"                    # 带新闻URL模式的链接
        ]
        
        # 从所有选择器收集链接
        all_links = []
        for selector in selectors:
            try:
                links = soup.select(selector)
                all_links.extend(links)
            except Exception as e:
                logger.debug(f"选择器错误 {selector}: {e}")
        
        # 去重链接
        seen_urls = set()
        unique_links = []
        for link in all_links:
            if not link.get('href'):
                continue
                
            url = link.get('href')
            if url.startswith('/'):  # 相对链接
                base_url = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"
                url = f"{base_url}{url}"
                
            # 跳过已处理的链接
            if url in seen_urls:
                continue
                
            seen_urls.add(url)
            unique_links.append((link, url))
        
        logger.info(f"在 {domain} 找到 {len(unique_links)} 个唯一链接")
        
        # 处理找到的链接
        for link, url in unique_links:
            try:
                # 提取标题
                title = link.get_text().strip()
                if not title and link.find('img') and link.find('img').get('alt'):
                    title = link.find('img').get('alt').strip()
                
                # 跳过无标题链接
                if not title:
                    continue
                    
                # 只保留包含关键词的文章
                if not self.is_related_to_gold(title):
                    continue
                
                # 试图查找日期
                pub_date = self.extract_date_near_element(link, soup)
                
                # 创建文章对象
                article = {
                    "title": self.clean_text(title),
                    "link": url,
                    "source": domain,
                    "pub_date": pub_date or datetime.now().strftime("%Y-%m-%d"),
                    "fetched_at": datetime.now().isoformat(),
                    "summarized": False,
                    "content": "",
                    "summary": None,
                    "score": self.calculate_relevance_score(title, domain)
                }
                
                articles.append(article)
                
            except Exception as e:
                logger.error(f"处理链接时出错: {e} - {url}")
                
        # 按相关性分数排序
        articles.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 只保留最相关的前10篇文章
        return articles[:10] if len(articles) > 10 else articles
        
    def is_related_to_gold(self, text: str) -> bool:
        """检查文本是否与黄金相关"""
        text = text.lower()
        # 核心关键词 - 任何一个都会直接匹配
        core_keywords = ["gold", "silver", "precious metal", "bullion", "xau"]
        for keyword in core_keywords:
            if keyword in text:
                return True
                
        # 次要关键词 - 至少需要两个匹配
        secondary_keywords = ["price", "market", "invest", "troy ounce", "etf", 
                            "trading", "inflation", "central bank", "fed", "safe haven"]
        matches = sum(1 for kw in secondary_keywords if kw in text)
        return matches >= 2
        
    def calculate_relevance_score(self, title: str, domain: str) -> float:
        """计算文章相关性分数 - 用于排序"""
        score = 0.0
        
        # 1. 域名权重 - 有些源更可信
        domain_base = domain.split('.')[-2] + '.' + domain.split('.')[-1]
        domain_score = self.source_weights.get(domain, 1.0)
        score += domain_score
        
        # 2. 标题关键词 - 标题越相关，分数越高
        title = title.lower()
        
        # 核心关键词给高分
        core_keywords = ["gold", "silver", "precious metal", "bullion", "xau"]
        for keyword in core_keywords:
            if keyword in title:
                score += 5.0
                # 如果在标题开头，额外加分
                if title.startswith(keyword):
                    score += 2.0
        
        # 价格相关额外加分
        price_keywords = ["price", "rally", "surge", "plunge", "drop", "rise", 
                         "soar", "jump", "fall", "crash", "record", "high", "low"]
        for keyword in price_keywords:
            if keyword in title:
                score += 1.0
        
        return score
        
    def extract_date_near_element(self, element, soup) -> Optional[str]:
        """尝试从元素附近提取日期"""
        # 检查元素附近的时间标签
        parent = element.parent
        for _ in range(3):  # 向上查找3层父节点
            if not parent:
                break
                
            # 查找时间标签
            time_tag = parent.find('time')
            if time_tag:
                date_str = time_tag.get('datetime') or time_tag.get_text().strip()
                if date_str:
                    return date_str
                    
            # 查找日期类的span
            date_spans = parent.select('span.date, span.time, .published, .timestamp')
            for span in date_spans:
                date_str = span.get_text().strip()
                if date_str:
                    return date_str
                    
            parent = parent.parent
            
        # 如果没找到，返回None
        return None
        
    def extract_content(self, article: Dict) -> str:
        """从文章URL提取正文内容"""
        url = article.get('link')
        logger.info(f"提取文章内容: {url}")
        
        response = self.make_request(url)
        if not response:
            logger.error(f"无法获取文章内容: {url}")
            return ""
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除无关元素
        for tag in soup.select('script, style, nav, header, footer, .ads, .banner, .comment, .social, .related, .sidebar'):
            tag.decompose()
            
        # 提取内容的方法
        content_extractors = [
            # 1. 尝试使用article标签
            lambda s: s.find('article'),
            
            # 2. 查找主要内容区
            lambda s: s.select_one('.content, .article-content, .entry-content, .post-content, .story-content'),
            
            # 3. 尝试使用明确的内容ID
            lambda s: s.select_one('#content, #article, #main-content, #post-content'),
            
            # 4. 使用文章正文选择器
            lambda s: s.select_one('.body, .article-body, .entry-body, .story-body'),
            
            # 5. 最后手段 - 提取长段落
            lambda s: s.find_all('p', lambda el: len(el.get_text()) > 100)
        ]
        
        # 尝试各种提取方法
        content = ""
        for extractor in content_extractors:
            try:
                result = extractor(soup)
                if result:
                    if isinstance(result, list):
                        content = "\n\n".join([p.get_text().strip() for p in result])
                    else:
                        # 获取段落
                        paragraphs = result.find_all('p')
                        if paragraphs:
                            content = "\n\n".join([p.get_text().strip() for p in paragraphs])
                        else:
                            content = result.get_text().strip()
                    
                    if content and len(content) > 200:  # 内容长度足够
                        break
            except Exception as e:
                logger.debug(f"提取内容失败: {e}")
                
        # 最终清理
        content = self.clean_text(content)
                
        return content
    
    def clean_text(self, text: str) -> str:
        """清理文本，移除多余空白和无关符号"""
        if not text:
            return ""
            
        # 替换HTML字符实体
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;|&#34;', '"', text)
        text = re.sub(r'&apos;|&#39;', "'", text)
        text = re.sub(r'&nbsp;|&#160;', ' ', text)
        
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 移除导航文本和其他常见无用内容
        text = re.sub(r'Home\s+>\s+.*?\s+>\s+.*?\s+>', '', text)
        text = re.sub(r'Menu\s+Search\s+.*?Sign in', '', text)
        text = re.sub(r'Toggle menu.*?Toggle search', '', text)
        text = re.sub(r'Share\s+on\s+(Facebook|Twitter|LinkedIn)', '', text)
        text = re.sub(r'Read more:.*', '', text)
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def scrape_all_sources(self) -> List[Dict]:
        """从所有源抓取文章"""
        all_articles = []
        
        # 在开始前重置会话
        self.session = requests.Session()
        
        for source_url in self.sources:
            try:
                logger.info(f"正在抓取源: {source_url}")
                domain = self.get_domain(source_url)
                
                # 检查是否是已知的无效URL
                if source_url in self.invalid_urls:
                    logger.warning(f"跳过已知无效源: {source_url}")
                    continue
                
                # 获取页面
                response = self.make_request(source_url)
                if not response:
                    continue
                    
                # 提取文章
                articles = self.extract_articles_from_html(response.text, source_url)
                logger.info(f"从 {domain} 提取了 {len(articles)} 篇相关文章")
                
                # 添加到结果列表
                all_articles.extend(articles)
                
                # 等待一小段时间后继续下一个源
                delay_time = self.delay * (1 + random.random())
                logger.debug(f"等待 {delay_time:.2f} 秒后继续下一个源")
                time.sleep(delay_time)
                
            except Exception as e:
                logger.error(f"处理源 {source_url} 时出错: {e}")
                # 记录此源为无效以避免将来再次尝试
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.HTTPError)):
                    self.invalid_urls.add(source_url) 
                
        # 按相关性分数排序
        all_articles.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"总共抓取了 {len(all_articles)} 篇文章")
        return all_articles
        
    def fetch_content_for_articles(self, articles: List[Dict]) -> List[Dict]:
        """获取文章的正文内容"""
        for i, article in enumerate(articles):
            # 跳过已有内容的文章
            if article.get('content') and len(article.get('content', '')) > 200:
                continue
            
            # 检查URL是否有效    
            url = article.get('link')
            if url in self.invalid_urls:
                logger.warning(f"跳过已知无效文章URL: {url}")
                continue
                
            # 获取内容
            content = self.extract_content(article)
            if content:
                article['content'] = content
                if not article.get('summary'):
                    # 提取前几句作为摘要
                    sentences = re.split(r'(?<=[.!?])\s+', content)
                    article['summary'] = ' '.join(sentences[:3]) if len(sentences) > 3 else content[:300]
                    
            # 友好地等待，避免请求过快
            if i < len(articles) - 1:  # 不是最后一篇
                # 添加随机延迟
                delay_time = self.delay * (0.5 + random.random())
                logger.debug(f"等待 {delay_time:.2f} 秒后继续下一篇文章")
                time.sleep(delay_time)
                
        return articles
    
    def update_database(self, articles: List[Dict]) -> None:
        """更新数据库，添加新文章"""
        existing_articles = []
        
        # 加载现有数据
        if Path(self.db_path).exists():
            try:
                with open(self.db_path, 'r') as f:
                    existing_articles = json.load(f)
                logger.info(f"从数据库加载了 {len(existing_articles)} 篇现有文章")
            except json.JSONDecodeError:
                logger.error("数据库文件格式错误，将创建新文件")
                
        # 过滤掉旧的文章（超过14天）
        two_weeks_ago = (datetime.now() - timedelta(days=14)).isoformat()
        existing_articles = [
            article for article in existing_articles
            if article.get('fetched_at', '') > two_weeks_ago
        ]
        
        # 检查URL去重
        existing_urls = {article.get('link') for article in existing_articles}
        new_articles = [article for article in articles if article.get('link') not in existing_urls]
        
        # 合并和排序
        updated_articles = new_articles + existing_articles
        
        # 保存数据库
        try:
            with open(self.db_path, 'w') as f:
                json.dump(updated_articles, f, indent=2)
            logger.info(f"添加了 {len(new_articles)} 篇新文章到数据库")
        except Exception as e:
            logger.error(f"保存数据库时出错: {e}")
            
        return new_articles
    
    def run(self) -> List[Dict]:
        """运行爬虫"""
        logger.info("开始抓取黄金新闻...")
        
        # 重置错误计数器和无效URL列表
        self.invalid_urls = set()
        
        # 抓取所有源
        articles = self.scrape_all_sources()
        
        # 获取内容
        if articles:
            articles = self.fetch_content_for_articles(articles)
            
        # 更新数据库
        new_articles = self.update_database(articles)
        
        # 记录无效URL数量
        if self.invalid_urls:
            logger.warning(f"本次抓取中有 {len(self.invalid_urls)} 个无效URL")
            
        logger.info("抓取完成!")
        return new_articles
        
if __name__ == "__main__":
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    
    # 是否使用代理（默认为False）
    use_proxies = False
    
    # 创建并运行爬虫
    scraper = ImprovedGoldScraper(use_proxies=use_proxies)
    new_articles = scraper.run()
    
    # 输出结果摘要
    print(f"抓取了 {len(new_articles)} 篇新文章")
    
    if new_articles:
        print("\n最高得分文章:")
        top_articles = sorted(new_articles, key=lambda x: x.get('score', 0), reverse=True)[:3]
        
        for i, article in enumerate(top_articles, 1):
            print(f"\n{i}. {article.get('title')}")
            print(f"   来源: {article.get('source')}")
            print(f"   日期: {article.get('pub_date')}")
            print(f"   相关性分数: {article.get('score', 0):.1f}")
            print(f"   链接: {article.get('link')}")
            
            if article.get('summary'):
                print(f"   摘要: {article.get('summary')[:150]}...") 