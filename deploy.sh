#!/bin/bash
# Gold Spider Deployment Script
# This script sets up the Gold Spider application on an AliCloud CentOS server

set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting Gold Spider deployment...${NC}"

# Update system packages
echo -e "${GREEN}Updating system packages...${NC}"
sudo yum update -y

# Install required packages
echo -e "${GREEN}Installing required packages...${NC}"
sudo yum install -y nginx epel-release
sudo yum install -y certbot python3-certbot-nginx

# Create directory structure if not exists
echo -e "${GREEN}Setting up directory structure...${NC}"
mkdir -p ~/gold_spider/static/css
mkdir -p ~/gold_spider/templates
mkdir -p ~/gold_spider/logs
mkdir -p ~/gold_spider/data

# Set up conda environment
echo -e "${GREEN}Setting up conda environment...${NC}"
cd ~/gold_spider

# Check if conda environment exists
if ! conda info --envs | grep -q "gold_spider"; then
    echo -e "${GREEN}Creating new conda environment 'gold_spider'...${NC}"
    conda create -y -n gold_spider python=3.9
fi

# Activate conda environment and install dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
conda activate gold_spider || source $(conda info --base)/etc/profile.d/conda.sh && conda activate gold_spider
pip install fastapi uvicorn jinja2 python-multipart aiofiles bs4 fake_useragent requests feedparser python-dateutil schedule

# Set up Nginx configuration
echo -e "${GREEN}Setting up Nginx configuration...${NC}"
sudo cp nginx/goldspider.conf /etc/nginx/conf.d/goldspider.conf
sudo sed -i "s|/path/to/gold_spider|$HOME/gold_spider|g" /etc/nginx/conf.d/goldspider.conf

# Set up the systemd service and adjust for conda
echo -e "${GREEN}Setting up systemd service...${NC}"
sudo cp systemd/goldspider.service /etc/systemd/system/
sudo sed -i "s|/home/ubuntu|$HOME|g" /etc/systemd/system/goldspider.service
# Update ExecStart to use conda
CONDA_PATH=$(which conda)
CONDA_BASE=$(dirname $(dirname $CONDA_PATH))
sudo sed -i "s|ExecStart=.*|ExecStart=/bin/bash -c 'source $CONDA_BASE/etc/profile.d/conda.sh \&\& conda activate gold_spider \&\& python -m app.service'|g" /etc/systemd/system/goldspider.service
sudo sed -i "s|Environment=.*||g" /etc/systemd/system/goldspider.service

# Create directory for Let's Encrypt verification
sudo mkdir -p /var/www/letsencrypt/.well-known/acme-challenge
sudo chown -R nginx:nginx /var/www/letsencrypt

# Reload systemd, enable and start the service
echo -e "${GREEN}Enabling and starting the Gold Spider service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable goldspider
sudo systemctl restart goldspider

# Make sure Nginx is enabled and running
echo -e "${GREEN}Enabling and starting Nginx...${NC}"
sudo systemctl enable nginx
sudo systemctl restart nginx

# Set up SSL certificate with Let's Encrypt
echo -e "${YELLOW}Do you want to set up SSL with Let's Encrypt now? (y/n)${NC}"
read setup_ssl

if [ "$setup_ssl" = "y" ]; then
    echo -e "${GREEN}Setting up SSL certificate with Let's Encrypt...${NC}"
    sudo certbot --nginx -d goldenpricealive.com -d www.goldenpricealive.com
    
    # Restart Nginx to apply SSL changes
    sudo systemctl restart nginx
fi

# Final adjustments
echo -e "${GREEN}Checking Nginx configuration...${NC}"
sudo nginx -t

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Restarting Nginx...${NC}"
    sudo systemctl restart nginx
else
    echo -e "${RED}Nginx configuration test failed. Please check the configuration.${NC}"
    exit 1
fi

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Your Gold Spider application should now be running at: https://goldenpricealive.com${NC}"

# Print status information
echo -e "${GREEN}Service status:${NC}"
sudo systemctl status goldspider --no-pager

echo -e "${YELLOW}Deployment completed. Don't forget to:${NC}"
echo -e "1. Set up a firewall to allow only ports 80, 443 and SSH"
echo -e "2. Check logs at ~/gold_spider/logs/ for any issues"
echo -e "3. To view service logs use: sudo journalctl -u goldspider" 