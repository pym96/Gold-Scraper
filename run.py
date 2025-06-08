"""
Gold Spider 应用启动脚本
同时启动爬虫和Web界面
"""
import os
import sys
import threading
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 确保必要的目录存在
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

def run_scraper():
    """运行新闻聚合进程"""
    logger.info("启动新闻聚合进程...")
    from app.scheduler import run_scheduler_service
    run_scheduler_service()

def run_web():
    """运行Web服务器"""
    logger.info("启动Web服务器...")
    from app.server import run_server
    run_server(host="0.0.0.0", port=8000, debug=False)

def main():
    """主函数，启动所有组件"""
    print("="*50)
    print("Gold Spider 启动中...")
    print("="*50)
    
    # 检查是否已有数据，否则先运行一次聚合
    if not Path("data/news_db.json").exists():
        print("数据库不存在，正在首次聚合新闻...")
        from app.news_aggregator import ReliableNewsAggregator
        aggregator = ReliableNewsAggregator()
        aggregator.run()
        
    # 创建线程运行聚合器
    scraper_thread = threading.Thread(target=run_scraper)
    scraper_thread.daemon = True
    
    # 启动线程
    scraper_thread.start()
    
    # 主线程运行Web服务
    print("\n" + "="*50)
    print("Gold Spider 已启动!")
    print("新闻聚合正在后台运行")
    print("Web界面访问地址: http://localhost:8000")
    print("="*50 + "\n")
    
    try:
        run_web()
    except KeyboardInterrupt:
        print("\n正在关闭 Gold Spider...")
        sys.exit(0)

if __name__ == "__main__":
    main() 