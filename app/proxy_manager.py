#!/usr/bin/env python3
"""
代理管理器 - 用于轮换IP地址，避免反爬措施
"""
import logging
import random
import time
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("proxy_manager")

class ProxyManager:
    """代理IP管理器，用于轮换请求IP"""
    
    def __init__(self, use_proxies: bool = False):
        """初始化代理管理器"""
        self.use_proxies = use_proxies
        self.proxy_list = []
        self.working_proxies = []
        self.failed_proxies = {}  # 记录代理失败次数
        self.last_refresh = 0
        self.refresh_interval = 30 * 60  # 30分钟刷新一次代理列表
        
        if self.use_proxies:
            self.refresh_proxies()
    
    def refresh_proxies(self) -> None:
        """刷新代理列表"""
        current_time = time.time()
        
        # 如果距离上次刷新不到指定时间，则跳过
        if current_time - self.last_refresh < self.refresh_interval and self.working_proxies:
            return
            
        logger.info("刷新代理列表...")
        
        # 方法1: 从公共API获取免费代理
        free_proxies = self._get_free_proxies()
        
        # 重置代理列表
        self.proxy_list = free_proxies
        self.working_proxies = []
        self.failed_proxies = {}
        
        # 测试代理并保留工作正常的
        self._test_proxies()
        
        self.last_refresh = current_time
        logger.info(f"代理刷新完成, 找到 {len(self.working_proxies)} 个可用代理")
    
    def _get_free_proxies(self) -> List[Dict]:
        """从公共API获取免费代理列表"""
        proxies = []
        
        # 来源1: ProxyScrape API
        try:
            response = requests.get(
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                timeout=10
            )
            if response.status_code == 200:
                proxy_list = response.text.strip().split("\r\n")
                for proxy in proxy_list:
                    if proxy:
                        proxies.append({
                            "http": f"http://{proxy}",
                            "https": f"http://{proxy}"
                        })
        except Exception as e:
            logger.warning(f"无法从ProxyScrape获取代理: {e}")
        
        # 来源2: PubProxy API
        try:
            response = requests.get(
                "http://pubproxy.com/api/proxy?limit=20&format=json&https=true",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    for item in data["data"]:
                        proxy = f"{item['ip']}:{item['port']}"
                        proxies.append({
                            "http": f"http://{proxy}",
                            "https": f"http://{proxy}"
                        })
        except Exception as e:
            logger.warning(f"无法从PubProxy获取代理: {e}")
        
        # 如果代理列表为空，则添加无代理选项
        if not proxies:
            proxies.append(None)  # None表示不使用代理
            
        return proxies
    
    def _test_proxies(self) -> None:
        """测试代理可用性"""
        test_url = "https://www.google.com"
        
        for proxy in self.proxy_list:
            try:
                if proxy is None:
                    # 添加无代理选项
                    self.working_proxies.append(None)
                    continue
                    
                # 测试代理
                response = requests.get(
                    test_url,
                    proxies=proxy,
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.working_proxies.append(proxy)
                    logger.debug(f"可用代理: {proxy}")
            except Exception:
                pass
        
        # 如果没有找到可用代理，则添加无代理选项
        if not self.working_proxies:
            self.working_proxies.append(None)
    
    def get_proxy(self) -> Optional[Dict]:
        """获取一个可用的代理"""
        if not self.use_proxies:
            return None
            
        # 如果没有可用代理，则刷新代理列表
        if not self.working_proxies:
            self.refresh_proxies()
        
        # 如果仍然没有可用代理，则返回None
        if not self.working_proxies:
            return None
            
        # 随机选择一个可用代理
        return random.choice(self.working_proxies)
    
    def report_failure(self, proxy: Optional[Dict]) -> None:
        """报告代理失败"""
        if proxy is None or not self.use_proxies:
            return
            
        # 增加失败次数
        proxy_str = str(proxy)
        self.failed_proxies[proxy_str] = self.failed_proxies.get(proxy_str, 0) + 1
        
        # 如果失败次数超过阈值，则从可用代理列表中移除
        if self.failed_proxies[proxy_str] >= 3:
            try:
                self.working_proxies.remove(proxy)
                logger.warning(f"代理 {proxy} 已被移除 (失败次数达到上限)")
            except ValueError:
                pass
    
    def make_request(self, url: str, headers: Optional[Dict] = None, 
                    method: str = "GET", timeout: int = 10, 
                    max_retries: int = 3) -> Tuple[Optional[requests.Response], Optional[Dict]]:
        """使用代理发送请求"""
        if not self.use_proxies:
            try:
                response = requests.request(
                    method, 
                    url, 
                    headers=headers, 
                    timeout=timeout
                )
                return response, None
            except Exception as e:
                logger.error(f"请求错误 {url}: {e}")
                return None, None
        
        # 尝试使用不同代理
        for attempt in range(max_retries):
            proxy = self.get_proxy()
            
            try:
                response = requests.request(
                    method, 
                    url, 
                    headers=headers, 
                    proxies=proxy, 
                    timeout=timeout
                )
                
                # 检查是否成功
                if response.status_code == 200:
                    return response, proxy
                    
                # 特殊处理403和429错误
                if response.status_code in (403, 429):
                    logger.warning(f"代理请求失败 ({response.status_code}): {url}")
                    self.report_failure(proxy)
                else:
                    return response, proxy
                    
            except Exception as e:
                logger.error(f"代理请求错误: {url}, 代理: {proxy}, 错误: {e}")
                self.report_failure(proxy)
        
        return None, None

# 单例实例
proxy_manager = ProxyManager(use_proxies=False)  # 默认不使用代理

def enable_proxies():
    """启用代理"""
    global proxy_manager
    proxy_manager.use_proxies = True
    proxy_manager.refresh_proxies()
    
def disable_proxies():
    """禁用代理"""
    global proxy_manager
    proxy_manager.use_proxies = False 