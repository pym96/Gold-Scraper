#!/usr/bin/env python3
"""
清理 Gold Spider 数据库
- 删除2022年的旧文章
- 只保留最新内容
"""

import json
import re
from datetime import datetime
from pathlib import Path

# 配置
DB_PATH = "data/news_db.json"
BACKUP_PATH = "data/backups/news_db_backup.json"

def clean_database():
    """清理数据库，删除旧内容"""
    # 加载当前数据库
    try:
        with open(DB_PATH, 'r') as f:
            articles = json.load(f)
        print(f"加载了 {len(articles)} 篇文章")
    except FileNotFoundError:
        print(f"数据库文件不存在: {DB_PATH}")
        return
    except json.JSONDecodeError:
        print("数据库文件格式错误")
        return
    
    # 创建备份
    Path("data/backups").mkdir(exist_ok=True)
    with open(BACKUP_PATH, 'w') as f:
        json.dump(articles, f, indent=2)
    print(f"已创建数据库备份：{BACKUP_PATH}")
    
    # 过滤旧文章
    filtered_articles = []
    removed_count = 0
    
    for article in articles:
        # 检查是否为2022年的文章
        pub_date = article.get("pub_date", "")
        fetched_at = article.get("fetched_at", "")
        
        # 删除条件
        should_remove = False
        
        # 条件1: 2022年的文章
        if "2022" in pub_date:
            should_remove = True
        
        # 条件2: 标题明确包含2022年的关键词
        title = article.get("title", "")
        if re.search(r'2022|FOMC Meetings', title):
            should_remove = True
            
        # 条件3: 内容包含大量网站导航文本（典型的联邦储备网站样式）
        content = article.get("content", "")
        if content and "Federal Reserve, the central bank" in content and "Board of Governors" in content:
            should_remove = True
            
        if should_remove:
            removed_count += 1
            print(f"删除: {article.get('title')} ({pub_date})")
        else:
            filtered_articles.append(article)
    
    # 保存过滤后的文章
    with open(DB_PATH, 'w') as f:
        json.dump(filtered_articles, f, indent=2)
    
    print(f"清理完成！删除了 {removed_count} 篇旧文章，保留了 {len(filtered_articles)} 篇文章。")

if __name__ == "__main__":
    clean_database() 