#!/bin/bash

SERVICE_NAME="goldspider"
APP_MODULE="app.service:app"
PYTHON_ENV="/root/anaconda3/envs/gold_spider/bin"
WORK_DIR="/root/Gold-Scraper"
PORT=8000
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🔧 创建 Systemd 服务: $SYSTEMD_PATH"

cat <<EOF > $SYSTEMD_PATH
[Unit]
Description=Gold Spider FastAPI Application
After=network.target

[Service]
User=root
WorkingDirectory=${WORK_DIR}
ExecStart=${PYTHON_ENV}/python -m app.service
Restart=always
RestartSec=10
Environment="PORT=${PORT}"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=goldspider

# Allow access to logs and data directories
ReadWritePaths=${WORK_DIR}/logs ${WORK_DIR}/data

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 重载 Systemd..."
systemctl daemon-reload

echo "🚀 启动服务..."
systemctl start $SERVICE_NAME

echo "📌 设置开机自启..."
systemctl enable $SERVICE_NAME

echo "✅ 状态检查："
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "📋 如果需要查看日志："
echo "sudo journalctl -u $SERVICE_NAME -f" 