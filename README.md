# Gold Spider 黄金新闻爬虫

Gold Spider 是一个专注于抓取全球黄金市场相关新闻的应用，提供实时更新的黄金价格和市场动态信息。

## 功能特点

- ✅ **多源新闻聚合** - RSS feeds + NewsAPI等专业数据源
- ✅ **实时数据更新** - 正确的时间戳，每20分钟自动更新
- ✅ **智能内容过滤** - 基于相关性评分筛选黄金市场新闻
- ✅ **现代Web界面** - 干净、响应式的用户界面
- ✅ **稳定的数据获取** - 避免反爬虫，确保服务稳定性
- ✅ **API支持** - 提供REST API端点
- ✅ **HTTPS安全访问** - SSL证书保护
- ✅ **生产环境优化** - 适合投资决策的可靠数据源

## 系统架构

- **后端**: FastAPI (Python) + 新闻聚合器
- **前端**: HTML/CSS/JavaScript (响应式设计)
- **数据源**: RSS Feeds + NewsAPI + 专业金融APIs
- **数据库**: JSON文件存储 (轻量级)
- **部署**: Nginx + SSL + Systemd + 进程管理
- **服务器**: 阿里云ECS CentOS (IP: 123.57.63.76)
- **域名**: goldenpricealive.com

## 目录结构

```
gold_spider/
├── app/                   # Python应用程序
│   ├── news_aggregator.py # 新闻聚合器 (RSS + API)
│   ├── improved_scraper.py # 传统爬虫 (备用)
│   ├── api.py             # FastAPI应用
│   ├── scheduler.py       # 定时任务调度器
│   ├── server.py          # Web服务器
│   ├── config.py          # 配置文件
│   └── production_config.py # 生产环境配置
├── static/                # 静态文件
│   └── css/               # CSS样式
├── templates/             # HTML模板
├── data/                  # 数据存储
├── logs/                  # 日志文件
├── nginx/                 # Nginx配置
├── systemd/               # Systemd服务配置
├── deploy.sh              # 自动部署脚本
├── run.py                 # 应用主入口
├── requirements.txt       # Python依赖
├── DEPLOYMENT.md          # 部署指南
└── API_SETUP.md           # API设置指南
```

## 部署指南

### 前提条件

- 阿里云ECS CentOS服务器 (已配置)
- 已安装Conda
- 已注册域名: goldenpricealive.com
- 域名已解析到服务器IP地址
- SSH访问服务器的权限

### 部署步骤

1. **连接服务器**

```bash
ssh root@123.57.63.76
```

2. **克隆代码库**

```bash
git clone https://github.com/yourusername/gold_spider.git
cd gold_spider
```

3. **使用部署脚本**

```bash
chmod +x deploy.sh
./deploy.sh
```

部署脚本会自动:
- 安装所需软件包
- 设置目录结构
- 配置Conda环境
- 设置Nginx
- 配置SSL证书
- 设置Systemd服务
- 启动应用程序

### 手动部署

如果需要手动部署，请按以下步骤操作：

1. **安装依赖**

```bash
sudo yum update -y
sudo yum install -y nginx epel-release
sudo yum install -y certbot python3-certbot-nginx
```

2. **设置Conda环境**

```bash
cd ~/gold_spider
conda create -y -n gold_spider python=3.9
conda activate gold_spider
pip install fastapi uvicorn jinja2 python-multipart aiofiles bs4 fake_useragent requests
```

3. **配置Nginx**

```bash
sudo cp nginx/goldspider.conf /etc/nginx/conf.d/
sudo sed -i "s|/root/gold_spider|$HOME/gold_spider|g" /etc/nginx/conf.d/goldspider.conf
sudo nginx -t
sudo systemctl restart nginx
```

4. **配置SSL**

```bash
sudo certbot --nginx -d goldenpricealive.com -d www.goldenpricealive.com
```

5. **设置Systemd服务**

```bash
sudo cp systemd/goldspider.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable goldspider
sudo systemctl start goldspider
```

## 使用说明

1. 访问 https://goldenpricealive.com 查看最新的黄金新闻
2. API端点:
   - `GET /articles` - 获取文章列表
   - `POST /scrape` - 触发新的抓取任务
   - `GET /status` - 查看服务状态

## 日志与监控

- 应用日志位于 `~/gold_spider/logs/`
- 服务日志可通过 `sudo journalctl -u goldspider` 查看
- Nginx日志位于 `/var/log/nginx/`

## 故障排除

1. **应用无法启动**
   - 检查日志文件: `cat logs/service.log`
   - 检查服务状态: `sudo systemctl status goldspider`
   - 检查Conda环境: `conda env list`

2. **网站无法访问**
   - 检查Nginx状态: `sudo systemctl status nginx`
   - 检查Nginx配置: `sudo nginx -t`
   - 检查防火墙: `sudo firewall-cmd --list-all`

3. **抓取失败**
   - 检查爬虫日志: `cat logs/scraper.log`
   - 手动触发抓取: `curl -X POST https://goldenpricealive.com/scrape`

## 维护

- **更新代码**: 拉取最新代码并重启服务
  ```bash
  cd ~/gold_spider
  git pull
  sudo systemctl restart goldspider
  ```

- **备份数据**: 定期备份数据目录
  ```bash
  cp -r ~/gold_spider/data ~/backups/gold_spider_data_$(date +%Y%m%d)
  ```

- **证书更新**: Let's Encrypt证书会自动更新

## CentOS特定配置

### 防火墙设置

```bash
# 允许HTTP和HTTPS流量
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SELinux配置

如果启用了SELinux，可能需要运行：

```bash
sudo setsebool -P httpd_can_network_connect 1
```

## 扩展计划

- 添加用户注册/登录功能
- 添加个性化推荐
- 集成电子邮件通知功能
- 支持多语言（中/英）
