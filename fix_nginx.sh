#!/bin/bash

# Quick fix for the current nginx SSL issue
# This script will temporarily fix the nginx configuration

echo "🔧 Quick fix for nginx SSL issue..."

# Remove the problematic SSL config
echo "📝 Removing problematic SSL configuration..."
sudo rm -f /etc/nginx/conf.d/goldspider.conf

# Copy the HTTP-only config from the repo
echo "📋 Copying HTTP-only configuration..."
sudo cp /root/Gold-Scraper/nginx/goldspider.conf /etc/nginx/conf.d/goldspider.conf

# Test the configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx
    
    echo "✅ Nginx has been fixed and reloaded!"
    echo "🌐 Your site should now be accessible at: http://goldenpricealive.com"
    echo ""
    echo "📝 Next steps:"
    echo "1. Run ./setup_ssl.sh to properly set up SSL certificates"
    echo "2. Or manually run: sudo certbot --nginx -d goldenpricealive.com -d www.goldenpricealive.com"
else
    echo "❌ Nginx configuration test failed!"
    echo "Please check the configuration manually."
fi 