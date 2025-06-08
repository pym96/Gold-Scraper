#!/usr/bin/env python3
"""
URL验证工具 - 检查配置中的URL是否有效，并建议修复
"""
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/url_validator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("url_validator")

class URLValidator:
    """URL验证工具类"""
    
    def __init__(self, config_path: str = "app/config.py"):
        self.config_path = config_path
        self.user_agent = UserAgent().random
        self.timeout = 15
        self.delay = 2
        
        # 确保日志目录存在
        Path("logs").mkdir(exist_ok=True)
    
    def read_config(self) -> str:
        """读取配置文件"""
        with open(self.config_path, 'r') as f:
            return f.read()
    
    def write_config(self, content: str) -> None:
        """写入配置文件"""
        with open(self.config_path, 'w') as f:
            f.write(content)
    
    def extract_urls(self, config_content: str) -> List[str]:
        """从配置文件中提取URL列表"""
        # 正则表达式匹配GOLD_NEWS_SOURCES列表中的URL
        pattern = r'GOLD_NEWS_SOURCES\s*=\s*\[(.*?)\]'
        match = re.search(pattern, config_content, re.DOTALL)
        
        if not match:
            logger.error("无法在配置文件中找到GOLD_NEWS_SOURCES")
            return []
            
        # 提取URL
        urls_text = match.group(1)
        url_pattern = r'"(https?://[^"]+)"'
        urls = re.findall(url_pattern, urls_text)
        
        return urls
    
    def check_url(self, url: str) -> Tuple[bool, int, str]:
        """检查URL是否有效"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            status_code = response.status_code
            
            if status_code == 200:
                # 检查页面内容是否有效
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.text if soup.title else "No title"
                return True, status_code, title
            else:
                return False, status_code, f"HTTP错误: {status_code}"
                
        except requests.exceptions.Timeout:
            return False, 0, "请求超时"
        except requests.exceptions.ConnectionError:
            return False, 0, "连接错误"
        except Exception as e:
            return False, 0, f"错误: {str(e)}"
    
    def find_alternative_url(self, url: str) -> str:
        """尝试查找替代URL"""
        # 提取域名
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if not domain_match:
            return ""
            
        domain = domain_match.group(1)
        root_url = f"https://{domain}"
        
        # 尝试访问根域名
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        try:
            response = requests.get(root_url, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                return ""
                
            # 解析页面，查找可能的黄金/商品新闻链接
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 关键词列表，用于识别可能的黄金新闻链接
            keywords = [
                "gold", "precious metal", "bullion", "commodity", "commodities", 
                "market", "markets", "news", "investing"
            ]
            
            # 查找所有链接
            best_match = ""
            best_score = 0
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text().lower()
                
                # 如果链接不完整，构建完整URL
                if href.startswith('/'):
                    href = f"{root_url}{href}"
                elif not href.startswith('http'):
                    continue
                
                # 排除外部链接
                if domain not in href:
                    continue
                    
                # 计算关键词匹配得分
                score = sum(2 for kw in keywords if kw in href.lower())
                score += sum(1 for kw in keywords if kw in text)
                
                # 更新最佳匹配
                if score > best_score:
                    best_score = score
                    best_match = href
            
            return best_match
            
        except Exception:
            return ""
    
    def update_urls(self) -> None:
        """验证并更新配置中的URL"""
        config_content = self.read_config()
        urls = self.extract_urls(config_content)
        
        if not urls:
            logger.error("无法提取URL，退出")
            return
            
        logger.info(f"从配置中提取了 {len(urls)} 个URL")
        
        valid_urls = []
        replacements = {}
        
        for url in urls:
            logger.info(f"检查URL: {url}")
            is_valid, status_code, message = self.check_url(url)
            
            if is_valid:
                logger.info(f"有效URL: {url} - {message}")
                valid_urls.append(url)
            else:
                logger.warning(f"无效URL: {url} - {message}")
                
                # 尝试查找替代URL
                alternative = self.find_alternative_url(url)
                if alternative:
                    # 验证替代URL
                    alt_valid, alt_status, alt_message = self.check_url(alternative)
                    if alt_valid:
                        logger.info(f"找到替代URL: {alternative} - {alt_message}")
                        replacements[url] = alternative
                        valid_urls.append(alternative)
                    else:
                        logger.warning(f"替代URL也无效: {alternative} - {alt_status}")
            
            # 友好地等待
            time.sleep(self.delay)
        
        # 更新配置文件
        if replacements:
            logger.info(f"将更新 {len(replacements)} 个URL")
            
            for old_url, new_url in replacements.items():
                config_content = config_content.replace(f'"{old_url}"', f'"{new_url}"')
                
            self.write_config(config_content)
            logger.info("配置文件已更新")
        else:
            logger.info("无需更新配置文件")
            
        # 输出有效URL列表
        logger.info(f"有效URL列表 ({len(valid_urls)}/{len(urls)}):")
        for url in valid_urls:
            logger.info(f"  - {url}")
        
        # 输出无效URL列表
        invalid_urls = [url for url in urls if url not in valid_urls and url not in replacements]
        if invalid_urls:
            logger.warning(f"无效URL列表 ({len(invalid_urls)}/{len(urls)}):")
            for url in invalid_urls:
                logger.warning(f"  - {url}")
                
def main():
    """主函数"""
    validator = URLValidator()
    validator.update_urls()
    
if __name__ == "__main__":
    main() 