# 🚀 Gold Spider 生产环境部署指南

## 📋 部署前准备

### 服务器要求
- ✅ 阿里云ECS CentOS 7/8
- ✅ 公网IP: 123.57.63.76  
- ✅ 域名: goldenpricealive.com
- ✅ 至少2GB内存，20GB存储

### 本地准备
确保你的代码是最新版本：
```bash
# 提交所有更改
git add .
git commit -m "Updated Gold Spider with reliable news aggregator"
git push origin main
```

## 🛠️ 部署步骤

### 1. 连接到服务器
```bash
ssh root@123.57.63.76
# 或使用你的SSH密钥
ssh -i your-key.pem root@123.57.63.76
```

### 2. 克隆或更新代码
```bash
# 如果是首次部署
git clone https://github.com/yourusername/gold_spider.git
cd gold_spider

# 如果已有代码，更新
cd gold_spider
git pull origin main
```

### 3. 运行部署脚本
```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置NewsAPI密钥 (可选但推荐)
```bash
# 编辑配置文件
nano app/config.py

# 将 YOUR_NEWS_API_KEY 替换为真实密钥
NEWS_API_KEY = "你的NewsAPI密钥"
```

### 5. 重启服务
```bash
sudo systemctl restart goldspider
sudo systemctl restart nginx
```

## 🔧 手动部署步骤 (如果自动脚本失败)

### 1. 安装系统依赖
```bash
sudo yum update -y
sudo yum install -y nginx epel-release
sudo yum install -y certbot python3-certbot-nginx
```

### 2. 设置Conda环境
```bash
cd ~/gold_spider
conda create -y -n gold_spider python=3.9
conda activate gold_spider
pip install -r requirements.txt
```

### 3. 配置Nginx
```bash
sudo cp nginx/goldspider.conf /etc/nginx/conf.d/
sudo sed -i "s|/root/gold_spider|$HOME/gold_spider|g" /etc/nginx/conf.d/goldspider.conf
sudo nginx -t
sudo systemctl restart nginx
```

### 4. 配置Systemd服务
```bash
sudo cp systemd/goldspider.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable goldspider
sudo systemctl start goldspider
```

### 5. 设置SSL证书
```bash
sudo certbot --nginx -d goldenpricealive.com -d www.goldenpricealive.com
```

## 📊 验证部署

### 1. 检查服务状态
```bash
# 检查Gold Spider服务
sudo systemctl status goldspider

# 检查Nginx状态  
sudo systemctl status nginx

# 查看服务日志
sudo journalctl -u goldspider -f
```

### 2. 检查端口
```bash
# 确认端口8000被监听
sudo netstat -tlnp | grep 8000

# 确认Nginx监听80和443
sudo netstat -tlnp | grep nginx
```

### 3. 测试访问
```bash
# 测试本地访问
curl http://localhost:8000

# 测试外网访问
curl http://goldenpricealive.com
curl https://goldenpricealive.com
```

## 🛡️ 安全配置

### 1. 防火墙设置
```bash
# 允许HTTP和HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# 或者使用iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo service iptables save
```

### 2. 定期备份
```bash
# 添加到crontab
crontab -e

# 每天备份数据
0 2 * * * cp -r ~/gold_spider/data ~/backups/gold_spider_$(date +\%Y\%m\%d)
```

## 📈 性能优化

### 1. 设置NewsAPI密钥
获取NewsAPI密钥以提升数据质量：
1. 访问 https://newsapi.org/register
2. 注册免费账户
3. 获取API密钥
4. 更新 `app/config.py` 中的 `NEWS_API_KEY`

### 2. 调整更新频率
```bash
# 编辑调度器设置
nano app/scheduler.py

# 调整间隔时间（生产环境建议15-30分钟）
run_scheduler_service(interval_minutes=20.0)
```

## 🔍 故障排除

### 常见问题

**1. 服务无法启动**
```bash
# 查看详细错误
sudo journalctl -u goldspider --no-pager

# 检查Python依赖
conda activate gold_spider
python -c "import app.news_aggregator"
```

**2. Nginx 502 错误**
```bash
# 检查Gold Spider是否运行
ps aux | grep python

# 重启服务
sudo systemctl restart goldspider
```

**3. SSL证书问题**
```bash
# 续期证书
sudo certbot renew

# 检查证书状态
sudo certbot certificates
```

**4. 内存不足**
```bash
# 监控内存使用
free -h
top

# 重启服务释放内存
sudo systemctl restart goldspider
```

## 📞 支持

如果遇到问题：
1. 检查日志：`~/gold_spider/logs/`
2. 查看系统日志：`sudo journalctl -u goldspider`
3. 检查Nginx日志：`/var/log/nginx/goldspider.error.log`

## 🎉 部署成功确认

如果一切正常，你应该能够：
- ✅ 访问 https://goldenpricealive.com
- ✅ 看到实时的黄金新闻
- ✅ 文章具有正确的日期时间
- ✅ 每20分钟自动更新新闻

恭喜！你的Gold Spider现在已经成功部署到生产环境！🚀 