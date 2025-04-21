import os
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging

# Initial setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache setup
cache = Cache(app, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": int(os.getenv("CACHE_TTL", 3600))
})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "100 per 15 minutes")]
)

@app.route('/')
def health_check():
    return jsonify({"status": "running", "version": "1.0.0"})

@app.route('/fetch', methods=['POST'])
@limiter.limit("10 per minute")
@cache.cached(timeout=3600, query_string=True)
def fetch_proxy():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.firefox.launch(
                headless=True,
                firefox_user_prefs={
                    "dom.webnotifications.enabled": False
                }
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            
            if "Checking your browser" in page.content():
                page.wait_for_selector("div#cf-wrapper", state="hidden", timeout=15000)
            
            content = page.content()
            
            page.close()
            context.close()
            browser.close()
            
            return content
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 3000)))