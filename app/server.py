"""
Gold Spider Web Application
Displays gold news articles in a web interface.
"""
import json
import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for

from app.config import JSON_DB_PATH

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

def load_articles():
    """Load articles from the JSON database"""
    try:
        if not Path(JSON_DB_PATH).exists():
            return []
            
        with open(JSON_DB_PATH, 'r') as f:
            articles = json.load(f)
            
        # Sort articles by publication date (newest first)
        articles.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)
        return articles
    except Exception as e:
        print(f"Error loading articles: {e}")
        return []

@app.route('/')
def index():
    """Main page displaying all articles"""
    articles = load_articles()
    return render_template('index.html', articles=articles)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    """Detail page for a specific article"""
    articles = load_articles()
    if 0 <= article_id < len(articles):
        return render_template('article.html', article=articles[article_id])
    return redirect(url_for('index'))

@app.route('/api/articles')
def api_articles():
    """API endpoint to get all articles as JSON"""
    articles = load_articles()
    return jsonify(articles)

@app.route('/api/article/<int:article_id>')
def api_article(article_id):
    """API endpoint to get a specific article as JSON"""
    articles = load_articles()
    if 0 <= article_id < len(articles):
        return jsonify(articles[article_id])
    return jsonify({"error": "Article not found"}), 404

@app.route('/source/<source>')
def by_source(source):
    """Filter articles by source"""
    articles = load_articles()
    results = [a for a in articles if a.get('source') == source]
    return render_template('source.html', articles=results, source=source)

@app.template_filter('format_date')
def format_date(date_string):
    """Format date string for display"""
    try:
        if not date_string:
            return ""
            
        # Handle ISO format dates
        if 'T' in date_string:
            dt = datetime.datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime('%Y年%m月%d日')
            
        # Return as is for other formats
        return date_string
    except Exception:
        return date_string

def run_server(host='0.0.0.0', port=8000, debug=True):
    """Run the web server"""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_server()
