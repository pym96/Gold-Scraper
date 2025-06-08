# API设置指南 - 获取实时、可靠的新闻数据

为了解决新闻爬取的问题，我们建议使用专业的新闻API服务，它们提供：
- ✅ 实时新闻数据
- ✅ 正确的时间戳
- ✅ 高质量内容
- ✅ 稳定的访问
- ✅ 不会被反爬虫阻止

## 推荐的API服务

### 1. NewsAPI (推荐)
- **网站**: https://newsapi.org/
- **免费额度**: 1000次请求/月
- **付费**: $449/月 (无限制)
- **特点**: 覆盖全球新闻源，包括金融媒体

**设置步骤**:
1. 访问 https://newsapi.org/register
2. 创建免费账户
3. 获取API密钥
4. 在 `app/config.py` 中设置: `NEWS_API_KEY = "你的密钥"`

### 2. Alpha Vantage (专业金融数据)
- **网站**: https://www.alphavantage.co/
- **免费额度**: 25次请求/天
- **付费**: $49.99/月起
- **特点**: 专注金融市场新闻

### 3. Finnhub (金融新闻)
- **网站**: https://finnhub.io/
- **免费额度**: 60次请求/分钟
- **特点**: 股市和金融新闻

### 4. Polygon.io (市场数据)
- **网站**: https://polygon.io/
- **免费额度**: 5次请求/分钟
- **特点**: 实时市场数据和新闻

## 快速设置NewsAPI (推荐)

1. **注册NewsAPI**:
   ```bash
   # 访问 https://newsapi.org/register
   # 填写邮箱和基本信息即可获得免费API密钥
   ```

2. **配置项目**:
   ```python
   # 在 app/config.py 中
   NEWS_API_KEY = "你从NewsAPI获得的密钥"
   ```

3. **测试**:
   ```bash
   python -m app.news_aggregator
   ```

## RSS方案 (无需API密钥)

如果暂时不想使用付费API，我们的新聚合器也支持RSS源：
- ✅ 完全免费
- ✅ 较为稳定
- ✅ 包含多个金融新闻源

当前已配置的RSS源包括：
- Bloomberg Markets
- CNBC Commodities  
- Yahoo Finance
- BullionVault News

## 效果对比

### 使用API前 (问题):
- ❌ 日期错误 (显示2025-06-07)
- ❌ 内容为空或不相关
- ❌ 经常被403/404阻止
- ❌ 抓取不稳定

### 使用API后 (解决):
- ✅ 正确的日期 (2025-06-07, 2025-06-06等)
- ✅ 高质量相关内容
- ✅ 稳定的数据访问
- ✅ 实时新闻更新

## 模仿对象的成功策略

你模仿的EZ.AI Listen Daily项目很可能采用了类似策略：

1. **多源聚合**: 同时使用API + RSS + 社交媒体
2. **专业服务**: 订阅NewsAPI、Bloomberg Terminal等
3. **实时更新**: 每15-30分钟更新一次
4. **内容过滤**: 基于关键词和相关性评分筛选
5. **AI处理**: 使用AI进行内容摘要和分析

投资决策需要准确、及时的信息，这正是专业API服务的价值所在！ 