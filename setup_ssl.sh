#!/bin/bash

# SSL Setup Script for Gold Spider
# This script handles the proper SSL certificate setup

set -e  # Exit on any error

echo "🔧 Setting up Gold Spider with SSL..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Install required packages
echo -e "${YELLOW}📦 Installing required packages...${NC}"
sudo yum update -y
sudo yum install -y nginx epel-release
sudo yum install -y certbot python3-certbot-nginx

# Step 2: Create letsencrypt directory
echo -e "${YELLOW}📁 Creating Let's Encrypt directory...${NC}"
sudo mkdir -p /var/www/letsencrypt

# Step 3: Copy HTTP-only nginx config first
echo -e "${YELLOW}🌐 Setting up HTTP-only nginx configuration...${NC}"
sudo cp nginx/goldspider.conf /etc/nginx/conf.d/goldspider.conf

# Step 4: Test nginx config
echo -e "${YELLOW}🧪 Testing nginx configuration...${NC}"
sudo nginx -t

# Step 5: Start nginx
echo -e "${YELLOW}🚀 Starting nginx...${NC}"
sudo systemctl enable nginx
sudo systemctl start nginx

# Step 6: Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Step 7: Get SSL certificates
echo -e "${YELLOW}🔒 Obtaining SSL certificates...${NC}"
echo "This will obtain SSL certificates for goldenpricealive.com and www.goldenpricealive.com"
echo "Please make sure your domain is pointing to this server's IP address"
read -p "Press Enter to continue or Ctrl+C to cancel..."

sudo certbot certonly --webroot \
    -w /var/www/letsencrypt \
    -d goldenpricealive.com \
    -d www.goldenpricealive.com \
    --email admin@goldenpricealive.com \
    --agree-tos \
    --non-interactive

# Step 8: Update nginx config to use SSL
echo -e "${YELLOW}🔐 Updating nginx configuration with SSL...${NC}"
sudo cp nginx/goldspider-ssl.conf /etc/nginx/conf.d/goldspider.conf

# Step 9: Test new nginx config
echo -e "${YELLOW}🧪 Testing SSL-enabled nginx configuration...${NC}"
sudo nginx -t

# Step 10: Reload nginx
echo -e "${YELLOW}🔄 Reloading nginx...${NC}"
sudo systemctl reload nginx

# Step 11: Setup automatic certificate renewal
echo -e "${YELLOW}⏰ Setting up automatic certificate renewal...${NC}"
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

echo -e "${GREEN}✅ SSL setup completed successfully!${NC}"
echo -e "${GREEN}🌐 Your site should now be available at: https://goldenpricealive.com${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Set up your Python application"
echo "2. Configure systemd service"
echo "3. Start your application" 