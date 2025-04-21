import os
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache configuration
app.config.from_mapping({
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": int(os.getenv("CACHE_TTL", 3600))  # 1 hour default
})
cache = Cache(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "100 per 15 minutes")]
)

# Browser setup - runs once at startup
_browser = None

def get_browser():
    global _browser
    if _browser is None or not _browser.is_connected():
        logger.info("Launching new browser instance")
        _browser = sync_playwright().start().chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
    return _browser

@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "service": "manga-proxy"
    })

@app.route('/fetch', methods=['POST'])
@limiter.limit("10 per minute")
@cache.cached(timeout=3600, query_string=True)
def fetch_proxy():
    data = request.get_json()
    url = data.get('url')
    wait_for = data.get('waitForSelector')
    timeout = int(data.get('timeout', 45000))
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        browser = get_browser()
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()
        
        # Set extra headers to mimic browser
        page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://lekmanga.net/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })
        
        logger.info(f"Fetching URL: {url}")
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        
        # Handle potential Cloudflare challenge
        if "Checking your browser before accessing" in page.content():
            logger.info("Cloudflare challenge detected, waiting...")
            page.wait_for_selector("div#cf-wrapper", state="hidden", timeout=15000)
        
        if wait_for:
            page.wait_for_selector(wait_for, timeout=15000)
        
        content = page.content()
        
        # Close resources
        page.close()
        context.close()
        
        return content
        
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return jsonify({
            "error": "Failed to fetch URL",
            "details": str(e),
            "url": url
        }), 500

@app.teardown_appcontext
def shutdown_browser(exception=None):
    global _browser
    if _browser is not None:
        logger.info("Closing browser instance")
        _browser.close()
        _browser = None

if __name__ == '__main__':
    port = int(os.getenv("PORT", 3000))
    app.run(host='0.0.0.0', port=port)