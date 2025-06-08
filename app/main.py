#!/usr/bin/env python3
"""
Gold Spider - 主程序
处理命令行参数并运行爬虫
"""
import argparse
import logging
import sys
from pathlib import Path

from app.improved_scraper import ImprovedGoldScraper
from app.proxy_manager import enable_proxies, disable_proxies
from app.arch_compat import is_apple_silicon, get_system_report
from app.url_validator import URLValidator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Gold Spider - 黄金新闻爬虫")
    
    parser.add_argument("--proxy", action="store_true", help="使用代理轮换IP地址")
    parser.add_argument("--validate-urls", action="store_true", help="验证并修复配置中的URL")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    parser.add_argument("--disable-compat", action="store_true", help="禁用架构兼容性支持")
    parser.add_argument("--legacy", action="store_true", help="使用旧版爬虫")
    
    return parser.parse_args()

def setup_environment(args):
    """设置运行环境"""
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("已启用调试模式")
    
    # 启用代理（如果指定）
    if args.proxy:
        logger.info("启用代理IP轮换")
        enable_proxies()
    else:
        disable_proxies()
        
    # 打印系统信息
    if is_apple_silicon() and not args.disable_compat:
        logger.info("已启用ARM Mac兼容性支持")
        logger.info(get_system_report())
    elif args.disable_compat:
        logger.info("已手动禁用架构兼容性支持")

def run_improved_scraper(args):
    """运行改进的爬虫"""
    # 验证URL
    if args.validate_urls:
        logger.info("开始验证URL...")
        validator = URLValidator()
        validator.update_urls()
        logger.info("URL验证完成")
    
    # 创建并运行爬虫
    logger.info("开始运行改进版爬虫...")
    scraper = ImprovedGoldScraper(use_proxies=args.proxy)
    new_articles = scraper.run()
    
    # 输出结果摘要
    logger.info(f"抓取了 {len(new_articles)} 篇新文章")
    
    if new_articles:
        logger.info("最高得分文章:")
        top_articles = sorted(new_articles, key=lambda x: x.get('score', 0), reverse=True)[:3]
        
        for i, article in enumerate(top_articles, 1):
            logger.info(f"{i}. {article.get('title')}")
            logger.info(f"   来源: {article.get('source')}")
            logger.info(f"   相关性分数: {article.get('score', 0):.1f}")
            
    return len(new_articles)

def run_legacy_scraper():
    """运行旧版爬虫"""
    try:
        from app.gold_scraper import GoldScraper
        logger.info("开始运行旧版爬虫...")
        scraper = GoldScraper()
        articles = scraper.scrape(fetch_content=True)
        logger.info(f"抓取了 {len(articles)} 篇文章")
        return len(articles)
    except ImportError as e:
        logger.error(f"无法导入旧版爬虫: {e}")
        return 0

def main():
    """主函数"""
    args = parse_args()
    setup_environment(args)
    
    try:
        if args.legacy:
            return run_legacy_scraper()
        else:
            return run_improved_scraper(args)
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
        return 0
    except Exception as e:
        logger.error(f"运行出错: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 