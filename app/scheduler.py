#!/usr/bin/env python3
"""
定时任务调度器
负责定期运行新闻聚合任务
"""
import time
import logging
import schedule
from datetime import datetime
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduler")

def run_news_aggregation():
    """运行新闻聚合任务"""
    try:
        from app.news_aggregator import ReliableNewsAggregator
        
        logger.info("开始运行新闻聚合任务...")
        start_time = datetime.now()
        
        aggregator = ReliableNewsAggregator()
        articles = aggregator.run()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"新闻聚合完成，用时 {duration:.2f} 秒，获取 {len(articles)} 篇文章")
        return articles
        
    except Exception as e:
        logger.error(f"新闻聚合任务失败: {e}")
        return []

def run_scheduler_service(interval_minutes: float = 30.0):
    """运行调度服务"""
    logger.info(f"启动新闻聚合调度器，间隔 {interval_minutes} 分钟")
    
    # 立即运行一次
    logger.info("立即运行初始聚合...")
    articles = run_news_aggregation()
    logger.info(f"初始聚合完成，获取 {len(articles)} 篇文章")
    
    # 设置定时任务
    schedule.every(interval_minutes).minutes.do(run_news_aggregation)
    
    logger.info(f"开始定时调度，每 {interval_minutes} 分钟运行一次")
    
    # 运行调度循环
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("调度器被用户中断")
            break
        except Exception as e:
            logger.error(f"调度器运行出错: {e}")
            time.sleep(300)  # 出错后等待5分钟再继续

if __name__ == "__main__":
    # 直接运行时使用较短的间隔进行测试
    run_scheduler_service(interval_minutes=30.0)
