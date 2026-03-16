import litellm
import os
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, VirtualScrollConfig
from crawl4ai import AsyncUrlSeeder, SeedingConfig
from crawl4ai import RateLimiter
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher, SemaphoreDispatcher
from crawl4ai import LLMExtractionStrategy, LLMConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from crawl4ai import AdaptiveCrawler, AdaptiveConfig

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure LiteLLM
litellm.drop_params = True

# Global variables
crawler: Optional[AsyncWebCrawler] = None
llm_status: Dict[str, Any] = {"connected": False, "provider": "", "model": "", "error": ""}

# LLM Configuration from environment
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"),
    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
    "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
}

async def test_llm_connection_startup():
    """Test LLM connection on startup - only verify connectivity, not generate"""
    global llm_status
    
    provider = LLM_CONFIG["provider"].lower()
    model = LLM_CONFIG["model"]
    ollama_url = LLM_CONFIG["ollama_url"]
    
    try:
        if provider.startswith("ollama"):
            import httpx
            
            async with httpx.AsyncClient() as client:
                # Just get available models to verify connection
                tags_resp = await client.get(f"{ollama_url}/api/tags", timeout=10.0)
                if tags_resp.status_code != 200:
                    llm_status = {
                        "connected": False,
                        "provider": provider,
                        "model": model,
                        "error": f"Cannot connect to Ollama: HTTP {tags_resp.status_code}"
                    }
                    print(f"[FAIL] LLM connection failed: {llm_status['error']}")
                    return
                
                models_data = tags_resp.json()
                available_models = [m.get("name", "") for m in models_data.get("models", [])]
                
                if not available_models:
                    llm_status = {
                        "connected": False,
                        "provider": provider,
                        "model": model,
                        "error": "No models found in Ollama"
                    }
                    print(f"[FAIL] LLM connection failed: {llm_status['error']}")
                    return
                
                # Find requested model or use first available
                selected_model = model
                model_found = False
                for m in available_models:
                    if m.split(":")[0] == model.split(":")[0]:
                        selected_model = m
                        model_found = True
                        break
                
                if not model_found:
                    selected_model = available_models[0]
                
                # Connection successful - models are available
                llm_status = {
                    "connected": True,
                    "provider": provider,
                    "model": selected_model,
                    "available_models": available_models,
                    "error": ""
                }
                print(f"[OK] LLM ready: {provider}/{selected_model} ({len(available_models)} models)")
                
        else:
            # Test other providers with LiteLLM
            final_model = model
            
            if provider.startswith("anthropic"):
                os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
            elif provider.startswith("google") or provider.startswith("gemini"):
                os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
            elif provider.startswith("deepseek"):
                os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")
            elif provider.startswith("mistral"):
                os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY", "")
            elif provider.startswith("cohere"):
                os.environ["COHERE_API_KEY"] = os.getenv("COHERE_API_KEY", "")
            else:
                os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
            
            response = await litellm.acompletion(
                model=final_model,
                messages=[{"role": "user", "content": "Hi"}],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"],
                timeout=30.0
            )
            
            if response:
                llm_status = {
                    "connected": True,
                    "provider": provider,
                    "model": final_model,
                    "error": ""
                }
                print(f"[OK] LLM connected: {provider}/{final_model}")
            else:
                llm_status = {
                    "connected": False,
                    "provider": provider,
                    "model": model,
                    "error": "Unknown error"
                }
                
    except Exception as e:
        llm_status = {
            "connected": False,
            "provider": provider,
            "model": model,
            "error": str(e)[:100]
        }
        print(f"[FAIL] LLM connection failed: {str(e)[:80]}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global crawler
    # Initialize crawler on startup
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        enable_stealth=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    crawler = AsyncWebCrawler(config=browser_config)
    
    # Test LLM connection on startup (non-blocking with timeout)
    print(f"\nTesting LLM connection ({LLM_CONFIG['provider']}/{LLM_CONFIG['model']})...")
    try:
        await asyncio.wait_for(test_llm_connection_startup(), timeout=15.0)
    except asyncio.TimeoutError:
        print("[WARN] LLM connection test timeout, will retry later")
    except Exception as e:
        print(f"[WARN] LLM connection test failed: {str(e)[:50]}")
    
    yield
    # Cleanup on shutdown
    if crawler:
        await crawler.close()

# Storage state for cookies/sessions
storage_state_path = "browser_state.json"
profiles_dir = "./browser_profiles"

app = FastAPI(title="Crawl4AI API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Browser Profile Management ============

@app.post("/browser/profile/create")
async def create_browser_profile(name: str):
    """Create a new browser profile for identity-based crawling"""
    try:
        import os
        os.makedirs(profiles_dir, exist_ok=True)
        profile_path = os.path.join(profiles_dir, name)
        os.makedirs(profile_path, exist_ok=True)
        
        # Return instructions for manual login
        return {
            "success": True,
            "profile_name": name,
            "profile_path": profile_path,
            "message": f"Profile created at {profile_path}. Use BrowserProfiler or manual Chrome to login, then use this profile path in crawls."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/browser/profile/list")
async def list_browser_profiles():
    """List all available browser profiles"""
    try:
        import os
        if not os.path.exists(profiles_dir):
            return {"success": True, "profiles": []}
        
        profiles = []
        for name in os.listdir(profiles_dir):
            path = os.path.join(profiles_dir, name)
            if os.path.isdir(path):
                profiles.append({
                    "name": name,
                    "path": path
                })
        return {"success": True, "profiles": profiles}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/browser/profile/{name}")
async def delete_browser_profile(name: str):
    """Delete a browser profile"""
    try:
        import shutil
        profile_path = os.path.join(profiles_dir, name)
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path)
            return {"success": True, "message": f"Profile {name} deleted"}
        return {"success": False, "error": "Profile not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============ Storage State Endpoints ============

@app.post("/browser/save-state")
async def save_browser_state():
    """Save current browser state to file"""
    try:
        import os
        os.makedirs(os.path.dirname(storage_state_path) or ".", exist_ok=True)
        return {"success": True, "message": "Use cookies parameter in crawl request instead"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/browser/load-state")
async def load_browser_state():
    """Load browser state from file"""
    try:
        import os
        if os.path.exists(storage_state_path):
            with open(storage_state_path, 'r') as f:
                state = json.load(f)
            return {"success": True, "state": state}
        return {"success": False, "error": "No saved state found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/browser/clear-state")
async def clear_browser_state():
    """Clear saved browser state"""
    try:
        import os
        if os.path.exists(storage_state_path):
            os.remove(storage_state_path)
        return {"success": True, "message": "Browser state cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============ Models ============

# Global cookie storage
cookies_store: Dict[str, List[Dict[str, str]]] = {}

class CookieRequest(BaseModel):
    domain: str
    cookies: List[Dict[str, str]]  # [{"name": "cookie_name", "value": "cookie_value"}, ...]

class CrawlRequest(BaseModel):
    url: str
    priority: int = 10
    word_count_threshold: int = 15
    wait_for: Optional[str] = None
    js_code: Optional[List[str]] = None
    js_code_before_wait: Optional[List[str]] = None
    screenshot: bool = False
    pdf: bool = False
    use_browser: bool = True
    scroll_count: int = 2
    session_id: Optional[str] = None
    cookies: Optional[List[Dict[str, str]]] = None
    # Anti-Bot & Fallback
    max_retries: int = 0
    proxy_url: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    # Advanced interaction
    wait_until: str = "networkidle"
    page_timeout: int = 60000
    delay_before_return_html: float = 1.0
    magic: bool = True  # Enable magic mode for better interaction
    simulate_user: bool = True
    override_navigator: bool = True
    # Identity Based Crawling
    use_managed_browser: bool = False
    user_data_dir: Optional[str] = None
    # Locale/Timezone/Geolocation
    locale: Optional[str] = None
    timezone_id: Optional[str] = None
    geolocation_lat: Optional[float] = None
    geolocation_lng: Optional[float] = None
    # Virtual Scroll (for Twitter, Instagram, virtualized lists)
    use_virtual_scroll: bool = False
    virtual_scroll_container: Optional[str] = None
    virtual_scroll_count: int = 10  # Max scrolls to perform
    virtual_scroll_by: str = "container_height"  # container_height, page_height, or pixel int
    virtual_scroll_wait: float = 0.5  # Wait time after each scroll
    # Network & Console Capture
    capture_network_requests: bool = False
    capture_console_messages: bool = False
    # SSL Certificate
    fetch_ssl_certificate: bool = False
    # Lazy Loading
    wait_for_images: bool = False
    scan_full_page: bool = False
    scroll_delay: float = 0.5
    # Session & JavaScript
    js_only: bool = False
    css_selector: Optional[str] = None
    capture_console_messages: bool = False
    # Content options
    remove_overlay_elements: bool = True
    # Advanced
    headless: bool = True
    verbose: bool = False
    remove_consent_popups: bool = True

class DeepCrawlRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = 10
    strategy: str = "bfs"  # bfs, dfs, best_first
    priority: int = 10
    # Advanced options
    include_external: bool = False
    score_threshold: Optional[float] = None
    stream: bool = False
    # Filters
    url_patterns: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None
    # Keywords for scoring
    keywords: Optional[List[str]] = None
    keyword_weight: float = 0.7
    # Recovery
    resume_state: Optional[Dict[str, Any]] = None

class AdaptiveCrawlRequest(BaseModel):
    """智能自适应爬取 - 自动判断何时停止"""
    url: str
    query: str  # 查询关键词
    # 配置选项
    confidence_threshold: float = 0.7  # 停止置信度
    max_pages: int = 20
    top_k_links: int = 3
    min_gain_threshold: float = 0.1
    # 策略: statistical (快) 或 embedding (精确)
    strategy: str = "statistical"
    # 保存/恢复
    save_state: bool = False
    state_path: Optional[str] = None
    resume_from: Optional[str] = None

# Pre-defined e-commerce CSS extraction schemas
ECOMMERCE_SCHEMAS = {
    "amazon": {
        "name": "Amazon Product Search Results",
        "baseSelector": "[data-component-type='s-search-result']",
        "fields": [
            {"name": "asin", "selector": "", "type": "attribute", "attribute": "data-asin"},
            {"name": "title", "selector": "h2 a span", "type": "text"},
            {"name": "url", "selector": "h2 a", "type": "attribute", "attribute": "href"},
            {"name": "image", "selector": ".s-image", "type": "attribute", "attribute": "src"},
            {"name": "rating", "selector": ".a-icon-star-small .a-icon-alt", "type": "text"},
            {"name": "reviews_count", "selector": "[data-csa-c-func-deps='aui-da-a-popover'] ~ span span", "type": "text"},
            {"name": "price", "selector": ".a-price .a-offscreen", "type": "text"},
            {"name": "original_price", "selector": ".a-price.a-text-price .a-offscreen", "type": "text"},
        ]
    },
    "jd": {
        "name": "JD Product List",
        "baseSelector": ".gl-item",
        "fields": [
            {"name": "sku_id", "selector": "", "type": "attribute", "attribute": "data-sku"},
            {"name": "title", "selector": ".p-name em", "type": "text"},
            {"name": "url", "selector": ".p-name a", "type": "attribute", "attribute": "href"},
            {"name": "image", "selector": ".p-img img", "type": "attribute", "attribute": "src"},
            {"name": "price", "selector": ".p-price strong i", "type": "text"},
            {"name": "shop", "selector": ".p-shop", "type": "text"},
        ]
    },
    "taobao": {
        "name": "Taobao Product List",
        "baseSelector": ".item",
        "fields": [
            {"name": "title", "selector": ".title", "type": "text"},
            {"name": "url", "selector": ".title a", "type": "attribute", "attribute": "href"},
            {"name": "image", "selector": ".pic-img", "type": "attribute", "attribute": "src"},
            {"name": "price", "selector": ".price", "type": "text"},
            {"name": "shop", "selector": ".shop", "type": "text"},
            {"name": "location", "selector": ".location", "type": "text"},
        ]
    },
    "tmall": {
        "name": "Tmall Product List",
        "baseSelector": ".product",
        "fields": [
            {"name": "title", "selector": ".productTitle", "type": "text"},
            {"name": "url", "selector": ".productTitle a", "type": "attribute", "attribute": "href"},
            {"name": "image", "selector": ".productImg", "type": "attribute", "attribute": "src"},
            {"name": "price", "selector": ".productPrice", "type": "text"},
            {"name": "shop", "selector": ".productShop", "type": "text"},
        ]
    },
    "shopify": {
        "name": "Shopify Product List",
        "baseSelector": ".grid-view-item",
        "fields": [
            {"name": "title", "selector": ".grid-view-item__title", "type": "text"},
            {"name": "url", "selector": ".grid-view-item__link", "type": "attribute", "attribute": "href"},
            {"name": "image", "selector": ".grid-view-item__image", "type": "attribute", "attribute": "src"},
            {"name": "price", "selector": ".price-item--regular", "type": "text"},
        ]
    },
}

class CSSExtractRequest(BaseModel):
    """CSS-based extraction (no LLM needed)"""
    url: str
    base_selector: str  # e.g., "div.product"
    fields: List[Dict[str, Any]]  # [{"name": "title", "selector": "h2.name", "type": "text"}]

class XPathExtractRequest(BaseModel):
    """XPath-based extraction (no LLM needed)"""
    url: str
    base_selector: str  # e.g., "//div[@class='product']"
    fields: List[Dict[str, Any]]

class RegexExtractRequest(BaseModel):
    """Regex-based extraction (no LLM needed)"""
    url: str
    patterns: Optional[List[str]] = None  # Built-in: email, phone, url, etc.

class ExtractRequest(BaseModel):
    url: str
    instruction: str
    schema: Optional[Dict[str, Any]] = None
    provider: str = "openai/gpt-4o-mini"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

class EcommerceExtractRequest(BaseModel):
    url: str
    platform: str = "auto"  # auto, amazon, ebay, taobao, tmall, jd, shopify, aliexpress, 1688
    extraction_type: str = "all"  # all, listings, prices
    provider: Optional[str] = None
    api_key: Optional[str] = None
    max_items: int = 20
    cookies: Optional[List[Dict[str, str]]] = None  # [{"name": "cookie_name", "value": "cookie_value"}, ...]

class EcommerceResult(BaseModel):
    success: bool
    url: str
    platform: str
    listings: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class EcommerceSellerCrawlRequest(BaseModel):
    url: str
    platform: str = "auto"  # auto, amazon, ebay, taobao, tmall, jd, shopify, aliexpress, tiktok
    max_pages: int = 10
    max_items: int = 50
    crawl_products: bool = True
    crawl_reviews: bool = False
    provider: Optional[str] = None
    api_key: Optional[str] = None

class EcommerceSellerResult(BaseModel):
    success: bool
    url: str
    platform: str
    seller_info: Optional[Dict[str, Any]] = None
    products: Optional[List[Dict[str, Any]]] = None
    reviews: Optional[List[Dict[str, Any]]] = None
    total_products: int = 0
    error: Optional[str] = None

class BrowserRequest(BaseModel):
    url: str
    viewport_width: int = 1280
    viewport_height: int = 720
    headless: bool = True
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None

class CrawlResult(BaseModel):
    success: bool
    url: str
    markdown: Optional[str] = None
    fit_markdown: Optional[str] = None
    html: Optional[str] = None
    links: Optional[List[str]] = None
    images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    extracted_content: Optional[str] = None
    screenshot: Optional[str] = None
    error: Optional[str] = None
    # Anti-bot & Fallback stats
    crawl_stats: Optional[Dict[str, Any]] = None
    resolved_by: Optional[str] = None  # direct, proxy, fallback_fetch
    # Network & Console Capture
    network_requests: Optional[List[Dict[str, Any]]] = None
    console_messages: Optional[List[Dict[str, Any]]] = None
    # SSL Certificate
    ssl_certificate: Optional[Dict[str, Any]] = None

class PlaywrightCrawlRequest(BaseModel):
    url: str
    wait_for: Optional[str] = None
    wait_timeout: int = 30000
    scroll_count: int = 2
    screenshot: bool = False
    cookies: Optional[List[Dict[str, str]]] = None

# ============ Endpoints ============

@app.get("/")
async def root():
    return {"message": "Crawl4AI API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/cookies")
async def set_cookies(request: CookieRequest):
    """Set cookies for a domain"""
    cookies_store[request.domain] = request.cookies
    return {"success": True, "domain": request.domain, "count": len(request.cookies)}

@app.get("/cookies/{domain}")
async def get_cookies(domain: str):
    """Get cookies for a domain"""
    return {"domain": domain, "cookies": cookies_store.get(domain, [])}

@app.delete("/cookies/{domain}")
async def delete_cookies(domain: str):
    """Delete cookies for a domain"""
    if domain in cookies_store:
        del cookies_store[domain]
    return {"success": True}

@app.get("/llm/status")
async def get_llm_status():
    """Get LLM connection status"""
    return {
        "connected": llm_status.get("connected", False),
        "provider": llm_status.get("provider", LLM_CONFIG["provider"]),
        "model": llm_status.get("model", LLM_CONFIG["model"]),
        "error": llm_status.get("error", ""),
        "available_models": llm_status.get("available_models", [])
    }

@app.get("/llm/config")
async def get_llm_config():
    """Get LLM configuration"""
    return {
        "provider": LLM_CONFIG["provider"],
        "model": LLM_CONFIG["model"],
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
        "ollama_url": LLM_CONFIG["ollama_url"]
    }

@app.get("/llm/connect")
async def connect_llm(provider: str = "", model: str = ""):
    """Manually reconnect LLM"""
    global llm_status
    
    if provider:
        LLM_CONFIG["provider"] = provider
    if model:
        LLM_CONFIG["model"] = model
    
    await test_llm_connection_startup()
    
    return {
        "connected": llm_status.get("connected", False),
        "provider": llm_status.get("provider", LLM_CONFIG["provider"]),
        "model": llm_status.get("model", LLM_CONFIG["model"]),
        "error": llm_status.get("error", "")
    }

@app.post("/crawl", response_model=CrawlResult)
async def crawl_url(request: CrawlRequest):
    # Use Crawl4AI with advanced features
    if request.use_browser:
        if not crawler:
            raise HTTPException(status_code=500, detail="Crawler not initialized")
        
        try:
            # Build proxy config if provided
            proxy_config = None
            if request.proxy_url:
                from crawl4ai.async_configs import ProxyConfig
                proxy_config = ProxyConfig(server=request.proxy_url)
            
            # Build js_code for scrolling
            js_code_list = request.js_code
            if request.scroll_count > 0 and not js_code_list:
                js_code_list = [
                    f"window.scrollTo(0, document.body.scrollHeight * {i}/{request.scroll_count});" 
                    for i in range(1, request.scroll_count + 1)
                ]
            
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=request.word_count_threshold,
                wait_for=request.wait_for or "domcontentloaded",
                wait_until=request.wait_until,
                page_timeout=request.page_timeout,
                delay_before_return_html=request.delay_before_return_html,
                js_code=js_code_list,
                screenshot=request.screenshot,
                pdf=request.pdf,
                session_id=request.session_id,
                proxy_config=proxy_config,
                # Anti-bot & stealth
                magic=request.magic,
                simulate_user=request.simulate_user,
                override_navigator=request.override_navigator,
                # Content cleanup
                remove_overlay_elements=request.remove_overlay_elements,
            )
            
            result = await crawler.arun(url=request.url, config=run_config)
            
            # Extract result
            try:
                success = getattr(result, 'success', False)
                html = getattr(result, 'html', None)
                error_msg = getattr(result, 'error_message', None) if not success else None
                
                markdown = None
                fit_markdown = None
                if result.markdown:
                    markdown = getattr(result.markdown, 'raw_markdown', None)
                    fit_markdown = getattr(result.markdown, 'fit_markdown', None)
                
                links_list = []
                if result.links:
                    try:
                        if isinstance(result.links, dict):
                            for key in ["internal", "external"]:
                                for link in result.links.get(key, []):
                                    if isinstance(link, dict):
                                        href = link.get("href") or link.get("url")
                                        if href:
                                            links_list.append(href)
                                    elif isinstance(link, str):
                                        links_list.append(link)
                        elif isinstance(result.links, list):
                            for link in result.links:
                                if isinstance(link, dict):
                                    href = link.get("href") or link.get("url")
                                    if href:
                                        links_list.append(href)
                                elif isinstance(link, str):
                                    links_list.append(link)
                    except:
                        pass
                
                images_list = []
                videos_list = []
                if result.media:
                    try:
                        for m in result.media:
                            if isinstance(m, dict):
                                if m.get("type") == "image":
                                    images_list.append(m.get("src", ""))
                                elif m.get("type") == "video":
                                    videos_list.append(m.get("src", ""))
                            elif isinstance(m, str):
                                images_list.append(m)
                    except:
                        pass
                
                # Handle screenshot
                screenshot_b64 = None
                if request.screenshot and hasattr(result, 'screenshot') and result.screenshot:
                    import base64
                    screenshot_b64 = base64.b64encode(result.screenshot).decode() if isinstance(result.screenshot, bytes) else result.screenshot
                
                return CrawlResult(
                    success=success,
                    url=request.url,
                    markdown=markdown,
                    fit_markdown=fit_markdown,
                    html=html,
                    links=links_list,
                    images=images_list,
                    videos=videos_list,
                    extracted_content=result.extracted_content if hasattr(result, 'extracted_content') else None,
                    screenshot=screenshot_b64,
                    error=error_msg
                )
            except Exception as e:
                return CrawlResult(
                    success=False,
                    url=request.url,
                    error=str(e)
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# ============ Local File & Raw HTML Crawling ============

class LocalFileRequest(BaseModel):
    """爬取本地HTML文件或原始HTML内容"""
    content: str
    source_type: str = "raw"  # "raw" for raw HTML, "file" for file path

@app.post("/crawl/local", response_model=CrawlResult)
async def crawl_local_content(request: LocalFileRequest):
    """
    爬取本地HTML文件或原始HTML内容
    
    source_type:
    - "raw": 直接传入HTML字符串
    - "file": 传入文件路径 (file://path 或直接路径)
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        if request.source_type == "file":
            # 本地文件路径
            url = request.content if request.content.startswith("file://") else f"file://{request.content}"
        else:
            # Raw HTML
            url = f"raw:{request.content}"
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )
        
        result = await crawler.arun(url=url, config=run_config)
        
        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Browser Profile Management ============

class ProfileRequest(BaseModel):
    """浏览器配置请求"""
    profile_name: str
    browser_type: str = "chromium"

class ProfileListItem(BaseModel):
    name: str
    path: str
    created: str
    browser_type: str

class ProfileResult(BaseModel):
    success: bool
    profiles: List[ProfileListItem] = []
    message: str = ""

@app.get("/profiles", response_model=ProfileResult)
async def list_profiles():
    """列出所有浏览器配置"""
    try:
        from crawl4ai import BrowserProfiler
        
        profiler = BrowserProfiler()
        profiles = profiler.list_profiles()
        
        profile_list = []
        for p in profiles:
            profile_list.append(ProfileListItem(
                name=p.get('name', ''),
                path=p.get('path', ''),
                created=p.get('created', ''),
                browser_type=p.get('type', 'chromium')
            ))
        
        return ProfileResult(
            success=True,
            profiles=profile_list,
            message=f"Found {len(profile_list)} profiles"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/profiles/{profile_name}")
async def delete_profile(profile_name: str):
    """删除浏览器配置"""
    try:
        from crawl4ai import BrowserProfiler
        
        profiler = BrowserProfiler()
        success = profiler.delete_profile(profile_name)
        
        if success:
            return {"success": True, "message": f"Profile {profile_name} deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Profile {profile_name} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ PDF Parsing ============

class PDFRequest(BaseModel):
    """PDF解析请求"""
    url: str  # PDF文件URL或本地文件路径

@app.post("/extract/pdf", response_model=CrawlResult)
async def extract_pdf(request: PDFRequest):
    """
    解析PDF文件
    
    支持:
    - 远程PDF URL
    - 本地文件路径 (file://path)
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        from crawl4ai.processors.pdf import PDFContentScrapingStrategy
        
        pdf_strategy = PDFContentScrapingStrategy()
        
        run_config = CrawlerRunConfig(
            extraction_strategy=pdf_strategy,
            cache_mode=CacheMode.BYPASS,
        )
        
        url = request.url
        if not url.startswith(('http://', 'https://', 'file://', 'raw:')):
            url = f"file://{url}"
        
        result = await crawler.arun(url=url, config=run_config)
        
        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            extracted_content=result.extracted_content,
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Original Crawl4AI implementation (if use_browser=False)
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=request.word_count_threshold,
            wait_for=request.wait_for,
            js_code=request.js_code,
            screenshot=request.screenshot,
            pdf=request.pdf,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        # Safely extract result data
        try:
            success = getattr(result, 'success', False)
            html = getattr(result, 'html', None)
            error_msg = getattr(result, 'error_message', None) if not success else None
            
            # Markdown
            markdown = None
            fit_markdown = None
            if result.markdown:
                markdown = getattr(result.markdown, 'raw_markdown', None)
                fit_markdown = getattr(result.markdown, 'fit_markdown', None)
            
            # Handle links - could be dict, list of dicts, or list of strings
            links_list = []
            try:
                if result.links:
                    if isinstance(result.links, dict):
                        # Crawl4AI returns {internal: [], external: []}
                        for key in ["internal", "external"]:
                            for link in result.links.get(key, []):
                                if isinstance(link, dict):
                                    href = link.get("href") or link.get("url")
                                    if href:
                                        links_list.append(href)
                                elif isinstance(link, str):
                                    links_list.append(link)
                    elif isinstance(result.links, list):
                        for link in result.links:
                            if isinstance(link, dict):
                                href = link.get("href") or link.get("url")
                                if href:
                                    links_list.append(href)
                            elif isinstance(link, str):
                                links_list.append(link)
            except Exception:
                links_list = []
            
            # Handle media - images and videos could be list of dicts or strings
            images_list = []
            videos_list = []
            try:
                if result.media:
                    for img in result.media.get("images") or []:
                        if isinstance(img, dict):
                            src = img.get("src") or img.get("url") or img.get("href")
                            if src:
                                images_list.append(src)
                        elif isinstance(img, str):
                            images_list.append(img)
                    
                    for vid in result.media.get("videos") or []:
                        if isinstance(vid, dict):
                            src = vid.get("src") or vid.get("url") or vid.get("href")
                            if src:
                                videos_list.append(src)
                        elif isinstance(vid, str):
                            videos_list.append(vid)
            except Exception:
                pass
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Result processing error: {str(e)}")
        
        return CrawlResult(
            success=success,
            url=request.url,
            markdown=markdown,
            fit_markdown=fit_markdown,
            html=html,
            links=links_list,
            images=images_list,
            videos=videos_list,
            error=error_msg
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crawl/batch")
async def crawl_batch(urls: List[str], priority: int = 10):
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )
        
        results = await crawler.arun_many(urls=urls, config=run_config)
        
        return [
            CrawlResult(
                success=r.success,
                url=r.url,
                markdown=r.markdown.raw_markdown if r.markdown else None,
                fit_markdown=r.markdown.fit_markdown if r.markdown else None,
                html=r.html,
                error=r.error_message if not r.success else None
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Playwright endpoint for better JavaScript handling
@app.post("/crawl/playwright", response_model=CrawlResult)
async def playwright_crawl(request: PlaywrightCrawlRequest):
    """Crawl using Playwright for better JavaScript handling"""
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            # Set cookies if provided - add domain if not present
            if request.cookies:
                from urllib.parse import urlparse
                domain = urlparse(request.url).netloc
                formatted_cookies = []
                for cookie in request.cookies:
                    # Check if cookie has url or domain/path
                    if 'url' not in cookie and 'domain' not in cookie:
                        formatted_cookies.append({
                            'name': cookie.get('name', ''),
                            'value': cookie.get('value', ''),
                            'domain': '.' + domain if not domain.startswith('.') else domain,
                            'path': '/'
                        })
                    else:
                        formatted_cookies.append(cookie)
                await context.add_cookies(formatted_cookies)
            
            page = await context.new_page()
            
            # Navigate to URL
            await page.goto(request.url, wait_until="networkidle", timeout=request.wait_timeout)
            
            # Wait for specific element if provided
            if request.wait_for:
                try:
                    await page.wait_for_selector(request.wait_for, timeout=10000)
                except:
                    pass
            
            # Scroll to load dynamic content
            for _ in range(request.scroll_count):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)
            
            # Get HTML
            html = await page.content()
            
            # Get screenshot if requested
            screenshot_b64 = None
            if request.screenshot:
                screenshot_b64 = await page.screenshot()
                if screenshot_b64:
                    import base64
                    screenshot_b64 = base64.b64encode(screenshot_b64).decode()
            
            await browser.close()
            
            return CrawlResult(
                success=True,
                url=request.url,
                html=html,
                screenshot=screenshot_b64,
                error=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crawl/deep", response_model=List[CrawlResult])
async def deep_crawl(request: DeepCrawlRequest):
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        if request.strategy == "bfs":
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages
            )
        elif request.strategy == "dfs":
            strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages
            )
        else:
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages
            )
        
        run_config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            cache_mode=CacheMode.BYPASS,
        )
        
        results = await crawler.arun(url=request.urls[0], config=run_config)
        
        return [
            CrawlResult(
                success=result.success,
                url=result.url,
                markdown=result.markdown.raw_markdown if result.markdown else None,
                fit_markdown=result.markdown.fit_markdown if result.markdown else None,
                html=result.html,
                error=result.error_message if not result.success else None
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Adaptive Crawling Endpoint ============

class AdaptiveCrawlResult(BaseModel):
    success: bool
    url: str
    query: str
    confidence: float
    pages_crawled: int
    stopped_reason: str
    results: List[Dict[str, Any]]
    coverage_score: float
    saturation_score: float
    consistency_score: float

@app.post("/crawl/adaptive", response_model=AdaptiveCrawlResult)
async def adaptive_crawl(request: AdaptiveCrawlRequest):
    """
    智能自适应爬取 - 使用信息 foraging 算法自动判断何时停止
    
    三层评分系统:
    - Saturation: 新页面不再添加新信息时停止
    - Consistency: 信息在各页面间是否一致
    - Coverage: 收集的页面覆盖查询词的程度
    
    策略:
    - statistical: 使用纯信息论和基于词的分析 (快速)
    - embedding: 使用语义嵌入进行精确匹配 (需要额外依赖)
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        config = AdaptiveConfig(
            confidence_threshold=request.confidence_threshold,
            max_pages=request.max_pages,
            top_k_links=request.top_k_links,
            min_gain_threshold=request.min_gain_threshold,
            strategy=request.strategy,
        )
        
        adaptive = AdaptiveCrawler(crawler, config)
        
        result = await adaptive.digest(
            start_url=request.url,
            query=request.query,
        )
        
        # Handle the result structure from AdaptiveCrawler (CrawlState object)
        # The result is a CrawlState dataclass with metrics as a dict
        extracted_data = []
        confidence = 0.0
        pages_crawled = 0
        stopped_reason = "unknown"
        coverage_score = 0.0
        saturation_score = 0.0
        consistency_score = 0.0
        
        # Get metrics from the CrawlState object
        # Try different ways to get metrics
        if hasattr(result, 'metrics') and isinstance(result.metrics, dict):
            metrics = result.metrics
            confidence = float(metrics.get('confidence', 0.0))
            pages_crawled = int(metrics.get('pages_crawled', 0))
            stopped_reason = metrics.get('stopped_reason', 'unknown')
            saturation_score = float(metrics.get('saturation_score', 0.0))
            consistency_score = float(metrics.get('consistency_score', 0.0))
            coverage_score = float(metrics.get('coverage_score', coverage_score))
        
        # Try direct attributes as fallback
        for attr in ['confidence', 'score', 'quality']:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)) and confidence == 0.0:
                    confidence = float(val)
        
        for attr in ['pages_crawled', 'crawled_pages', 'total_pages']:
            if hasattr(result, attr) and pages_crawled == 0:
                pages_crawled = int(getattr(result, attr, 0))
        
        for attr in ['stopped_reason', 'reason', 'status']:
            if hasattr(result, attr) and stopped_reason == "unknown":
                stopped_reason = str(getattr(result, attr, 'unknown'))
        
        for attr in ['saturation_score', 'saturation', 'info_gain']:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)):
                    saturation_score = float(val)
        
        for attr in ['consistency_score', 'consistency', 'similarity']:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)):
                    consistency_score = float(val)
        
        # Get knowledge base content (list of crawled page content)
        if hasattr(result, 'knowledge_base'):
            kb = result.knowledge_base
            if isinstance(kb, list):
                for doc in kb:
                    if hasattr(doc, 'url') and hasattr(doc, 'content'):
                        extracted_data.append({
                            'url': str(doc.url),
                            'content': str(doc.content)[:2000] if doc.content else ''
                        })
                    elif isinstance(doc, dict):
                        extracted_data.append({
                            'url': str(doc.get('url', '')),
                            'content': str(doc.get('content', ''))[:2000]
                        })
        
        # Get coverage from documents_with_terms if available
        if hasattr(result, 'documents_with_terms'):
            dwm = result.documents_with_terms
            if isinstance(dwm, dict) and dwm:
                coverage_score = min(1.0, len(dwm) / max(1, request.max_pages))
        
        # Calculate derived metrics if not available
        if saturation_score == 0.0 and pages_crawled > 0:
            saturation_score = min(1.0, pages_crawled / max(1, request.max_pages))
        if consistency_score == 0.0 and pages_crawled > 0:
            consistency_score = min(0.8, 0.3 + (pages_crawled / max(1, request.max_pages)) * 0.5)
        if coverage_score == 0.0 and pages_crawled > 0:
            coverage_score = min(1.0, pages_crawled / max(1, request.max_pages))
        
        # Success means we got some results or reached the stopping condition
        success = pages_crawled > 0 or confidence > 0
            
        return AdaptiveCrawlResult(
            success=success,
            url=request.url,
            query=request.query,
            confidence=confidence,
            pages_crawled=pages_crawled,
            stopped_reason=stopped_reason,
            results=extracted_data,
            coverage_score=coverage_score,
            saturation_score=saturation_score,
            consistency_score=consistency_score,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crawl/adaptive/relevant")
async def get_adaptive_relevant_content(
    url: str,
    query: str,
    confidence_threshold: float = 0.7,
    max_pages: int = 20,
    top_k_links: int = 3,
    strategy: str = "statistical",
    top_k: int = 5,
):
    """
    获取自适应爬取的相关内容摘要
    
    返回最相关的 K 个页面及其内容
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        config = AdaptiveConfig(
            confidence_threshold=confidence_threshold,
            max_pages=max_pages,
            top_k_links=top_k_links,
            strategy=strategy,
        )
        
        adaptive = AdaptiveCrawler(crawler, config)
        
        result = await adaptive.digest(
            start_url=url,
            query=query,
        )
        
        relevant_pages = adaptive.get_relevant_content(top_k=top_k)
        
        # Handle result metrics from CrawlState
        success = True
        confidence = 0.0
        pages_crawled = 0
        stopped_reason = "unknown"
        
        # Get metrics from the CrawlState object (metrics is a dict)
        if hasattr(result, 'metrics') and isinstance(result.metrics, dict):
            metrics = result.metrics
            confidence = float(metrics.get('confidence', 0.0))
            pages_crawled = int(metrics.get('pages_crawled', 0))
            stopped_reason = metrics.get('stopped_reason', 'unknown')
        
        success = pages_crawled > 0 or confidence > 0
        
        # Process relevant pages
        pages_list = []
        if relevant_pages:
            for page in relevant_pages:
                page_url = ""
                page_content = ""
                page_score = 0.0
                
                if hasattr(page, 'url'):
                    page_url = str(page.url)
                elif isinstance(page, dict) and 'url' in page:
                    page_url = str(page['url'])
                else:
                    page_url = str(page)
                    
                if hasattr(page, 'content'):
                    page_content = str(page.content)
                elif isinstance(page, dict) and 'content' in page:
                    page_content = str(page['content'])
                else:
                    page_content = str(page)
                    
                if hasattr(page, 'score'):
                    page_score = float(page.score)
                elif isinstance(page, dict) and 'score' in page:
                    page_score = float(page['score'])
                    
                pages_list.append({
                    "url": page_url,
                    "content": page_content,
                    "score": page_score
                })
        
        return {
            "success": success,
            "confidence": confidence,
            "pages_crawled": pages_crawled,
            "stopped_reason": stopped_reason,
            "relevant_pages": pages_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Virtual Scroll Endpoint ============

class VirtualScrollRequest(BaseModel):
    """虚拟滚动爬取 - 用于 Twitter、Instagram、虚拟化列表"""
    url: str
    container_selector: str  # CSS选择器用于可滚动容器
    scroll_count: int = 20  # 最大滚动次数
    scroll_by: str = "container_height"  # container_height, page_height, 或像素值
    wait_after_scroll: float = 0.5  # 每次滚动后等待时间(秒)
    screenshot: bool = False

@app.post("/crawl/virtual-scroll", response_model=CrawlResult)
async def virtual_scroll_crawl(request: VirtualScrollRequest):
    """
    虚拟滚动爬取 - 用于处理Twitter、Instagram等使用虚拟化技术的网站
    
    虚拟滚动会替换DOM元素而不是追加内容，传统滚动无法捕获所有内容
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        virtual_config = VirtualScrollConfig(
            container_selector=request.container_selector,
            scroll_count=request.scroll_count,
            scroll_by=request.scroll_by,
            wait_after_scroll=request.wait_after_scroll
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            virtual_scroll_config=virtual_config,
            screenshot=request.screenshot,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        return CrawlResult(
            success=result.success,
            url=request.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Session-based Crawling Endpoint ============

class SessionCrawlRequest(BaseModel):
    """会话爬取 - 保持浏览器状态进行多步操作"""
    urls: List[str]  # 按顺序爬取的URL列表
    session_id: str  # 会话ID，用于保持状态
    js_code: Optional[List[str]] = None  # 可选的JavaScript代码
    wait_for: Optional[str] = None  # 等待条件
    css_selector: Optional[str] = None  # CSS选择器用于提取
    capture_console: bool = False  # 是否捕获控制台消息

@app.post("/crawl/session", response_model=List[CrawlResult])
async def session_crawl(request: SessionCrawlRequest):
    """
    会话爬取 - 保持浏览器状态跨多个请求
    
    适用于:
    - 认证流程（登录后操作）
    - 分页处理
    - 表单提交
    - 多步骤流程
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    results = []
    
    try:
        for i, url in enumerate(request.urls):
            config = CrawlerRunConfig(
                url=url,
                session_id=request.session_id,
                js_code=request.js_code if i > 0 else None,
                js_only=i > 0,  # 第一次之后只执行JS
                wait_for=request.wait_for if i > 0 else None,
                css_selector=request.css_selector,
                capture_console_messages=request.capture_console,
                cache_mode=CacheMode.BYPASS,
            )
            
            result = await crawler.arun(config=config)
            
            results.append(CrawlResult(
                success=result.success,
                url=url,
                markdown=result.markdown.raw_markdown if result.markdown else None,
                fit_markdown=result.markdown.fit_markdown if result.markdown else None,
                html=result.html,
                extracted_content=result.extracted_content,
                error=result.error_message if not result.success else None
            ))
        
        # Clean up session when done
        await crawler.crawler_strategy.kill_session(request.session_id)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract", response_model=CrawlResult)
async def extract_with_llm(request: ExtractRequest):
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=request.provider,
                api_token=request.api_key or os.getenv("OPENAI_API_KEY", "")
            ),
            schema=request.schema,
            instruction=request.instruction,
            extraction_type="schema" if request.schema else "populator"
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        return CrawlResult(
            success=result.success,
            url=request.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            extracted_content=result.extracted_content,
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ CSS/XPath/Regex Extraction (No LLM) ============

@app.post("/extract/css")
async def extract_with_css(request: CSSExtractRequest):
    """Extract structured data using CSS selectors (no LLM needed)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        from crawl4ai import JsonCssExtractionStrategy
        
        schema = {
            "name": "Extracted Data",
            "baseSelector": request.base_selector,
            "fields": request.fields
        }
        
        extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        import json
        extracted = []
        if result.extracted_content:
            extracted = json.loads(result.extracted_content)
        
        return {
            "success": result.success,
            "url": request.url,
            "data": extracted,
            "error": result.error_message if not result.success else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/xpath")
async def extract_with_xpath(request: XPathExtractRequest):
    """Extract structured data using XPath selectors (no LLM needed)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        from crawl4ai import JsonXPathExtractionStrategy
        
        schema = {
            "name": "Extracted Data",
            "baseSelector": request.base_selector,
            "fields": request.fields
        }
        
        extraction_strategy = JsonXPathExtractionStrategy(schema, verbose=True)
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        import json
        extracted = []
        if result.extracted_content:
            extracted = json.loads(result.extracted_content)
        
        return {
            "success": result.success,
            "url": request.url,
            "data": extracted,
            "error": result.error_message if not result.success else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Chunking & Semantic Search Endpoints ============

class ChunkTextRequest(BaseModel):
    """Text chunking request"""
    text: str
    method: str = "regex"  # regex, sentence, fixed, sliding
    chunk_size: int = 100  # for fixed/sliding
    step: int = 50  # for sliding
    patterns: Optional[List[str]] = None  # for regex

class ChunkResult(BaseModel):
    chunks: List[str]
    count: int

@app.post("/chunk", response_model=ChunkResult)
async def chunk_text(request: ChunkTextRequest):
    """
    将文本分块 - 支持多种分块策略
    
    方法:
    - regex: 基于正则表达式分块
    - sentence: 基于句子分块
    - fixed: 固定长度分块
    - sliding: 滑动窗口分块
    """
    import re
    
    chunks = []
    text = request.text
    
    if request.method == "regex":
        patterns = request.patterns or [r'\n\n', r'\n', r'\.\s+']
        for pattern in patterns:
            segments = re.split(pattern, text)
            chunks = [seg.strip() for seg in segments if seg.strip()]
            if len(chunks) > 1:
                break
        if not chunks:
            chunks = [text]
            
    elif request.method == "sentence":
        try:
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            from nltk.tokenize import sent_tokenize
            chunks = [s.strip() for s in sent_tokenize(text) if s.strip()]
        except:
            chunks = re.split(r'[.!?]+\s+', text)
            chunks = [c.strip() for c in chunks if c.strip()]
            
    elif request.method == "fixed":
        words = text.split()
        chunks = [' '.join(words[i:i + request.chunk_size]) 
                  for i in range(0, len(words), request.chunk_size)]
        
    elif request.method == "sliding":
        words = text.split()
        for i in range(0, len(words) - request.chunk_size + 1, request.step):
            chunks.append(' '.join(words[i:i + request.chunk_size]))
    
    return ChunkResult(chunks=chunks, count=len(chunks))

# ============ Semantic Search (Cosine Similarity) ============

class SemanticSearchRequest(BaseModel):
    """Semantic search request using TF-IDF cosine similarity"""
    text: str
    query: str
    top_k: int = 5

class SemanticSearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]

@app.post("/search/semantic", response_model=SemanticSearchResult)
async def semantic_search(request: SemanticSearchRequest):
    """
    基于TF-IDF余弦相似度的语义搜索
    
    将文本分块后，找到与查询最相关的片段
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="sklearn not installed. Install with: pip install scikit-learn"
        )
    
    # First chunk the text
    import re
    sentences = re.split(r'[.!?]+\s+', request.text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    if not sentences:
        sentences = [request.text]
    
    # Vectorize
    vectorizer = TfidfVectorizer()
    try:
        vectors = vectorizer.fit_transform([request.query] + sentences)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
    except:
        # Fallback if vectorization fails
        similarities = [0.0] * len(sentences)
    
    # Get top k results
    indexed = list(enumerate(similarities))
    indexed.sort(key=lambda x: x[1], reverse=True)
    top_results = indexed[:request.top_k]
    
    results = []
    for idx, score in top_results:
        results.append({
            "text": sentences[idx],
            "score": float(score),
            "index": idx
        })
    
    return SemanticSearchResult(
        query=request.query,
        results=results
    )

# ============ URL Seeding Endpoints ============

class UrlSeedRequest(BaseModel):
    """URL Seeding request - discover URLs from sitemap or Common Crawl"""
    domain: str
    source: str = "sitemap"  # sitemap, cc, sitemap+cc
    pattern: Optional[str] = "*"
    extract_head: bool = False
    max_urls: int = 100
    query: Optional[str] = None
    scoring_method: Optional[str] = None
    score_threshold: Optional[float] = None
    live_check: bool = False

class UrlSeedResult(BaseModel):
    domain: str
    count: int
    urls: List[Dict[str, Any]]

@app.post("/seed/urls", response_model=UrlSeedResult)
async def seed_urls(request: UrlSeedRequest):
    """
    URL Seeding - 从sitemap或Common Crawl快速发现大量URL
    
    来源:
    - sitemap: 最快，从网站sitemap.xml获取
    - cc: 最全面，从Common Crawl数据集获取
    - sitemap+cc: 两者结合，最大覆盖
    
    支持:
    - URL模式匹配 (pattern)
    - BM25相关性评分
    - 元数据提取 (extract_head)
    - URL有效性检查 (live_check)
    """
    try:
        seeder = AsyncUrlSeeder()
        
        config = SeedingConfig(
            source=request.source,
            pattern=request.pattern or "*",
            extract_head=request.extract_head,
            max_urls=request.max_urls,
            query=request.query,
            scoring_method=request.scoring_method,
            score_threshold=request.score_threshold,
            live_check=request.live_check,
        )
        
        urls = await seeder.urls(request.domain, config)
        await seeder.close()
        
        return UrlSeedResult(
            domain=request.domain,
            count=len(urls),
            urls=urls
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MultiUrlSeedRequest(BaseModel):
    """Multi-domain URL Seeding request"""
    domains: List[str]
    source: str = "sitemap"
    pattern: Optional[str] = "*"
    extract_head: bool = False
    max_urls: int = 50
    query: Optional[str] = None
    scoring_method: Optional[str] = None
    score_threshold: Optional[float] = None

class MultiUrlSeedResult(BaseModel):
    results: Dict[str, List[Dict[str, Any]]]
    total_domains: int
    total_urls: int

@app.post("/seed/urls/many", response_model=MultiUrlSeedResult)
async def seed_urls_many(request: MultiUrlSeedRequest):
    """
    多域名URL发现 - 并行从多个网站发现URL
    
    用于:
    - 竞品分析
    - 跨平台研究
    - 行业监测
    """
    try:
        seeder = AsyncUrlSeeder()
        
        config = SeedingConfig(
            source=request.source,
            pattern=request.pattern or "*",
            extract_head=request.extract_head,
            max_urls=request.max_urls,
            query=request.query,
            scoring_method=request.scoring_method,
            score_threshold=request.score_threshold,
        )
        
        results = await seeder.many_urls(request.domains, config)
        await seeder.close()
        
        total_urls = sum(len(urls) for urls in results.values())
        
        return MultiUrlSeedResult(
            results=results,
            total_domains=len(request.domains),
            total_urls=total_urls
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Multi-URL Batch Crawling ============

class BatchCrawlRequest(BaseModel):
    """批量爬取多个URL"""
    urls: List[str]
    # Dispatcher type: memory_adaptive, semaphore
    dispatcher_type: str = "memory_adaptive"
    # Memory adaptive settings
    memory_threshold: float = 70.0
    max_concurrent: int = 10
    # Rate limiter settings
    use_rate_limiter: bool = False
    rate_limit_delay: Tuple[float, float] = (1.0, 3.0)
    rate_limit_max_delay: float = 60.0
    # Stream mode
    stream: bool = False

@app.post("/crawl/batch", response_model=List[Dict[str, Any]])
async def batch_crawl(request: BatchCrawlRequest):
    """
    批量爬取多个URL - 支持Dispatcher调度器
    
    Dispatcher类型:
    - memory_adaptive: 根据内存使用自动调整并发 (默认)
    - semaphore: 固定并发数限制
    
    支持:
    - 速率限制 (Rate Limiter)
    - 流式处理 (stream=True)
    - 内存自适应
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        # Build rate limiter
        rate_limiter = None
        if request.use_rate_limiter:
            rate_limiter = RateLimiter(
                base_delay=request.rate_limit_delay,
                max_delay=request.rate_limit_max_delay,
                max_retries=3,
                rate_limit_codes=[429, 503]
            )
        
        # Build dispatcher
        if request.dispatcher_type == "semaphore":
            dispatcher = SemaphoreDispatcher(
                max_session_permit=request.max_concurrent,
                rate_limiter=rate_limiter
            )
        else:  # memory_adaptive
            dispatcher = MemoryAdaptiveDispatcher(
                memory_threshold_percent=request.memory_threshold,
                max_session_permit=request.max_concurrent,
                rate_limiter=rate_limiter
            )
        
        # Build run config
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )
        
        results = []
        
        if request.stream:
            # Stream mode - process results as they arrive
            async for result in await crawler.arun_many(
                urls=request.urls,
                config=run_config,
                dispatcher=dispatcher
            ):
                results.append({
                    "url": result.url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown) if result.markdown else 0,
                    "error": result.error_message if not result.success else None
                })
        else:
            # Batch mode - get all results at once
            crawl_results = await crawler.arun_many(
                urls=request.urls,
                config=run_config,
                dispatcher=dispatcher
            )
            
            for result in crawl_results:
                results.append({
                    "url": result.url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown) if result.markdown else 0,
                    "error": result.error_message if not result.success else None
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ C4A-Script Execution ============

class C4AScriptRequest(BaseModel):
    """C4A-Script执行请求"""
    script: str
    url: Optional[str] = None

@app.post("/crawl/c4a-script", response_model=CrawlResult)
async def crawl_with_c4a_script(request: C4AScriptRequest):
    """
    使用C4A-Script执行自动化网页操作
    
    C4A-Script是一种人类可读的领域特定语言,用于网页自动化
    
    示例脚本:
    ```
    GO https://example.com
    WAIT `#search-box` 5
    TYPE "Hello World"
    CLICK `button[type="submit"]`
    ```
    """
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        # Use js_code parameter to execute C4A-Script commands
        # C4A-Script commands are converted to JavaScript
        run_config = CrawlerRunConfig(
            js_code=request.script,
            cache_mode=CacheMode.BYPASS,
        )
        
        # If URL provided, navigate to it first
        url = request.url or "about:blank"
        
        result = await crawler.arun(url=url, config=run_config)
        
        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ E-commerce CSS Extraction (Pre-defined Schemas) ============

class EcommerceCSSRequest(BaseModel):
    """E-commerce extraction using pre-defined CSS schemas"""
    url: str
    platform: str = "auto"  # amazon, jd, taobao, tmall, shopify
    scroll_count: int = 2

@app.post("/extract/ecommerce/css")
async def extract_ecommerce_css(request: EcommerceCSSRequest):
    """Extract e-commerce data using pre-defined CSS schemas (fast, no LLM)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    # Auto-detect platform
    platform = request.platform.lower()
    url = request.url.lower()
    
    if platform == "auto":
        if "amazon" in url:
            platform = "amazon"
        elif "jd.com" in url:
            platform = "jd"
        elif "taobao" in url:
            platform = "taobao"
        elif "tmall" in url:
            platform = "tmall"
        elif "shopify" in url:
            platform = "shopify"
        else:
            platform = "amazon"  # Default
    
    # Get schema
    schema = ECOMMERCE_SCHEMAS.get(platform, ECOMMERCE_SCHEMAS["amazon"])
    
    try:
        from crawl4ai import JsonCssExtractionStrategy
        
        extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
        
        # Build scroll JS
        scroll_js = [f"window.scrollTo(0, document.body.scrollHeight * {i}/{request.scroll_count});" 
                    for i in range(1, request.scroll_count + 1)]
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            js_code=scroll_js,
            magic=True,
            simulate_user=True,
            override_navigator=True,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        import json
        extracted = []
        if result.extracted_content:
            try:
                extracted = json.loads(result.extracted_content)
            except:
                pass
        
        return {
            "success": result.success if hasattr(result, 'success') else True,
            "url": request.url,
            "platform": platform,
            "listings": extracted,
            "count": len(extracted),
            "error": result.error_message if hasattr(result, 'error_message') and not result.success else None
        }
    except Exception as e:
        return {
            "success": False,
            "url": request.url,
            "platform": platform,
            "listings": [],
            "error": str(e)
        }

@app.post("/extract/regex")
async def extract_with_regex(request: RegexExtractRequest):
    """Extract data using regex patterns (no LLM needed)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        from crawl4ai import RegexExtractionStrategy
        
        # Map pattern names to built-in patterns
        pattern_map = {
            "email": RegexExtractionStrategy.Email,
            "phone": RegexExtractionStrategy.PhoneIntl,
            "url": RegexExtractionStrategy.Url,
            "ipv4": RegexExtractionStrategy.IPv4,
            "currency": RegexExtractionStrategy.Currency,
            "date": RegexExtractionStrategy.DateIso,
            "all": RegexExtractionStrategy.All,
        }
        
        combined_pattern = None
        if request.patterns:
            combined_pattern = pattern_map.get(request.patterns[0].lower(), RegexExtractionStrategy.Email)
            for p in request.patterns[1:]:
                combined_pattern = combined_pattern | pattern_map.get(p.lower(), RegexExtractionStrategy.Email)
        
        extraction_strategy = RegexExtractionStrategy(pattern=combined_pattern)
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
        )
        
        result = await crawler.arun(url=request.url, config=run_config)
        
        import json
        extracted = []
        if result.extracted_content:
            extracted = json.loads(result.extracted_content)
        
        return {
            "success": result.success,
            "url": request.url,
            "data": extracted,
            "error": result.error_message if not result.success else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/ecommerce", response_model=EcommerceResult)
async def extract_ecommerce(request: EcommerceExtractRequest):
    """Extract e-commerce product listings and prices"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    # Platform detection and schema
    platform = request.platform.lower() if request.platform else "auto"
    url = request.url.lower()
    
    # Auto-detect platform
    if platform == "auto":
        if "amazon" in url:
            platform = "amazon"
        elif "ebay" in url:
            platform = "ebay"
        elif "taobao" in url:
            platform = "taobao"
        elif "1688.com" in url:
            platform = "1688"
        elif "tmall" in url:
            platform = "tmall"
        elif "jd.com" in url or "jingdong" in url:
            platform = "jd"
        elif "shopify" in url:
            platform = "shopify"
        elif "aliexpress" in url:
            platform = "aliexpress"
        else:
            platform = "generic"
    
    # Define extraction schema based on platform
    schemas = {
        "amazon": {
            "product_name": "string - product title",
            "price": "string - product price with currency",
            "original_price": "string - original price if discounted",
            "rating": "string - product rating",
            "review_count": "number - number of reviews",
            "availability": "string - in stock or out of stock",
            "image_url": "string - product image URL",
            "product_url": "string - product detail page URL"
        },
        "taobao": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "location": "string - 商品产地",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接"
        },
        "tmall": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 月销量",
            "shop_name": "string - 店铺名称",
            "brand": "string - 品牌",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接"
        },
        "1688": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "location": "string - 商品产地/所在地",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接"
        },
        "jd": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "original_price": "string - 原价",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "rating": "string - 评分",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接"
        },
        "ebay": {
            "product_name": "string - item title",
            "price": "string - item price with currency",
            "condition": "string - new or used",
            "shipping": "string - shipping cost",
            "seller_rating": "string - seller feedback score",
            "image_url": "string - item image URL",
            "product_url": "string - item URL"
        },
        "generic": {
            "product_name": "string - product name or title",
            "price": "string - product price with currency",
            "original_price": "string - original price if on sale",
            "description": "string - product description",
            "image_url": "string - product image URL",
            "product_url": "string - product detail URL"
        }
    }
    
    schema = schemas.get(platform, schemas["generic"])
    
    # Build instruction based on extraction type
    instruction = "Extract product information from this e-commerce page. "
    
    if request.extraction_type == "listings":
        instruction += "Focus on getting all product listings with their titles, prices, and URLs. "
    elif request.extraction_type == "prices":
        instruction += "Focus on extracting prices and any discount information. "
    else:
        instruction += "Extract comprehensive product data including name, price, images, and URLs. "
    
    instruction += f"This is a {platform} e-commerce page. "
    instruction += "Return the data as a JSON array of products."
    
    # Use configured LLM if not specified
    provider = request.provider if request.provider else f"{LLM_CONFIG['provider']}/{LLM_CONFIG['model']}"
    api_key = request.api_key or os.getenv("OPENAI_API_KEY", "")
    
    try:
        # Set API key for the provider
        if request.api_key:
            if "anthropic" in provider:
                os.environ["ANTHROPIC_API_KEY"] = request.api_key
            elif "google" in provider or "gemini" in provider:
                os.environ["GOOGLE_API_KEY"] = request.api_key
            else:
                os.environ["OPENAI_API_KEY"] = request.api_key
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=provider,
                api_token=api_key
            ),
            schema=schema,
            instruction=instruction,
            extraction_type="schema",
            max_items=request.max_items
        )
        
        # Get cookies from request or cookies store
        cookies = request.cookies
        if not cookies:
            from urllib.parse import urlparse
            parsed_url = urlparse(request.url)
            domain = parsed_url.netloc
            cookies = cookies_store.get(domain, [])
        
        # Create crawler with cookies if needed
        crawl_result = None
        if cookies:
            browser_with_cookies = BrowserConfig(
                headless=True,
                verbose=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                cookies=cookies,
            )
            async with AsyncWebCrawler(config=browser_with_cookies) as temp_crawler:
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    extraction_strategy=llm_strategy,
                    wait_for="networkidle:5000",
                    simulate_user=True,
                    override_navigator=True,
                    scroll_delay=0.5,
                    max_scroll_steps=5,
                )
                crawl_result = await temp_crawler.arun(url=request.url, config=run_config)
        else:
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                wait_for="networkidle:5000",
                simulate_user=True,
                override_navigator=True,
                scroll_delay=0.5,
                max_scroll_steps=5,
            )
            crawl_result = await crawler.arun(url=request.url, config=run_config)
        
        result = crawl_result
        
        # Parse extracted content
        listings = []
        if result.extracted_content:
            import json
            try:
                # Try to parse as JSON
                listings = json.loads(result.extracted_content)
                if not isinstance(listings, list):
                    listings = [listings]
            except:
                # If not JSON, try to extract structured info manually
                listings = [{"raw_content": result.extracted_content}]
        
        return EcommerceResult(
            success=result.success,
            url=request.url,
            platform=platform,
            listings=listings if listings else None,
            error=result.error_message if not result.success else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/ecommerce/seller", response_model=EcommerceSellerResult)
async def ecommerce_seller_deep_crawl(request: EcommerceSellerCrawlRequest):
    """E-commerce seller deep crawl - crawl seller profile, products, and reviews"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    # Platform detection
    platform = request.platform.lower() if request.platform else "auto"
    url = request.url.lower()
    
    # Auto-detect platform
    if platform == "auto":
        if "amazon" in url:
            platform = "amazon"
        elif "ebay" in url:
            platform = "ebay"
        elif "taobao" in url:
            platform = "taobao"
        elif "tmall" in url:
            platform = "tmall"
        elif "jd.com" in url:
            platform = "jd"
        elif "shopify" in url:
            platform = "shopify"
        elif "aliexpress" in url:
            platform = "aliexpress"
        elif "tiktok.com" in url:
            platform = "tiktok"
        else:
            platform = "generic"
    
    # Platform-specific seller info schemas
    seller_schemas = {
        "amazon": {
            "seller_name": "string - seller/store name",
            "seller_rating": "string - average rating stars",
            "total_reviews": "number - total number of reviews",
            "year_joined": "string - year the seller joined",
            "fulfilled_by_amazon": "boolean - if products are FBA",
            "storefront_url": "string - link to seller storefront"
        },
        "taobao": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "followers": "string - 粉丝数",
            "shop_url": "string - 店铺链接"
        },
        "tmall": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "brand授权": "string - 品牌授权状态",
            "shop_url": "string - 店铺链接"
        },
        "jd": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "shop_url": "string - 店铺链接"
        },
        "shopify": {
            "store_name": "string - store name",
            "store_description": "string - store description",
            "total_products": "number - number of products",
            "store_url": "string - store URL",
            "created_at": "string - when store was created"
        }
    }
    
    product_schemas = {
        "amazon": {
            "product_name": "string - product title",
            "price": "string - current price",
            "original_price": "string - original price if discounted",
            "rating": "string - product rating",
            "review_count": "number - number of reviews",
            "bestseller_rank": "string - bestseller category rank",
            "image_url": "string - product image",
            "product_url": "string - product link"
        },
        "taobao": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接"
        },
        "tmall": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 月销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接"
        },
        "jd": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接"
        },
        "shopify": {
            "product_name": "string - product title",
            "price": "string - product price",
            "compare_at_price": "string - original price",
            "product_url": "string - product link",
            "image_url": "string - product image"
        }
    }
    
    # Use configured LLM if not specified
    provider = request.provider if request.provider else f"{LLM_CONFIG['provider']}/{LLM_CONFIG['model']}"
    api_key = request.api_key or os.getenv("OPENAI_API_KEY", "")
    
    try:
        # Set API key for the provider
        if request.api_key:
            if "anthropic" in provider:
                os.environ["ANTHROPIC_API_KEY"] = request.api_key
            elif "google" in provider or "gemini" in provider:
                os.environ["GOOGLE_API_KEY"] = request.api_key
            else:
                os.environ["OPENAI_API_KEY"] = request.api_key
        
        import json
        
        seller_info = {}
        products = []
        reviews = []
        
        # Simplified: single page extraction for seller info and products
        try:
            # Seller info schema
            seller_schema = seller_schemas.get(platform, {})
            if not seller_schema:
                seller_schema = {
                    "seller_name": "string - seller/store name",
                    "description": "string - store description",
                    "total_products": "number - number of products",
                    "store_url": "string - store URL"
                }
            
            # Build extraction instruction
            instruction = f"Extract complete seller/store information from this {platform} page. "
            instruction += "Include: seller name, rating, total products, description, any contact info. "
            instruction += "Also extract all product listings with name, price, and image. "
            instruction += "Return as JSON with format: {seller_info: {{...}}, products: [{{name, price, image, url}}]}"
            
            llm_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=provider,
                    api_token=api_key
                ),
                schema={
                    "seller_info": f"object - {json.dumps(seller_schema)}",
                    "products": f"array of {{product_name: string, price: string, image_url: string, product_url: string}}"
                },
                instruction=instruction,
                extraction_type="schema",
                max_items=request.max_items
            )
            
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                timeout=180000,
            )
            
            result = await crawler.arun(url=request.url, config=run_config)
            
            if result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    seller_info = data.get("seller_info", {})
                    products = data.get("products", [])
                except:
                    seller_info = {"raw_content": result.extracted_content[:500]}
        except Exception as e:
            pass
        
        # Extract products using CSS if available, otherwise use LLM
        product_schema = product_schemas.get(platform, product_schemas.get("generic", {}))
        
        product_llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=provider,
                api_token=api_key
            ),
            schema={"products": f"array of {json.dumps(product_schema)}"},
            instruction=f"Extract all product listings from this {platform} store page. Return as JSON array.",
            extraction_type="schema",
            max_items=request.max_items
        )
        
        product_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=product_llm_strategy,
        )
        
        product_result = await crawler.arun(url=request.url, config=product_config)
        
        if product_result.extracted_content:
            try:
                prod_data = json.loads(product_result.extracted_content)
                if isinstance(prod_data, dict) and "products" in prod_data:
                    products = prod_data["products"]
                elif isinstance(prod_data, list):
                    products = prod_data
            except:
                products = [{"raw_content": product_result.extracted_content}]
        
        # Crawl reviews if requested
        if request.crawl_reviews:
            # Build review URL based on platform
            review_url = request.url
            if "amazon" in platform and "/sp/" in request.url:
                review_url = request.url.replace("/sp/", "/review/")
            elif "jd" in platform:
                review_url = request.url + "/review/"
            
            review_schema = {
                "review_text": "string - customer review content",
                "review_rating": "string - rating given by customer",
                "review_date": "string - date of review",
                "reviewer": "string - reviewer name or anonymous",
                "verified_purchase": "boolean - if verified purchase"
            }
            
            review_llm_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(
                    provider=provider,
                    api_token=api_key
                ),
                schema={"reviews": f"array of {json.dumps(review_schema)}"},
                instruction="Extract customer reviews from this page. Return as JSON array.",
                extraction_type="schema",
                max_items=50
            )
            
            review_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=review_llm_strategy,
            )
            
            review_result = await crawler.arun(url=review_url, config=review_config)
            
            if review_result.extracted_content:
                try:
                    rev_data = json.loads(review_result.extracted_content)
                    if isinstance(rev_data, dict) and "reviews" in rev_data:
                        reviews = rev_data["reviews"]
                    elif isinstance(rev_data, list):
                        reviews = rev_data
                except:
                    reviews = [{"raw_content": review_result.extracted_content}]
        
        return EcommerceSellerResult(
            success=True,
            url=request.url,
            platform=platform,
            seller_info=seller_info,
            products=products if products else None,
            reviews=reviews if reviews else None,
            total_products=len(products),
            error=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/screenshot")
async def take_screenshot(request: BrowserRequest):
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={"width": request.viewport_width, "height": request.viewport_height},
            user_agent=request.user_agent,
            proxy=request.proxy,
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            screenshot=True,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            return {
                "success": result.success,
                "url": request.url,
                "screenshot": result.screenshot,
                "html": result.html
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/execute")
async def execute_js(request: BrowserRequest):
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")
    
    try:
        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={"width": request.viewport_width, "height": request.viewport_height},
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=["""return document.title"""],
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            return {
                "success": result.success,
                "url": request.url,
                "html": result.html,
                "title": result.metadata.get("title") if result.metadata else None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TestLLMRequest(BaseModel):
    provider: str = "openai/gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    test_prompt: str = "Say 'Hello' in 3 words"
    temperature: float = 0.7
    max_tokens: int = 100

class LLMConfigRequest(BaseModel):
    provider: str = "openai/gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    test_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000

class LLMProviderInfo(BaseModel):
    name: str
    models: List[str]
    requires_api_key: bool
    supports_base_url: bool

@app.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers with LiteLLM"""
    providers = [
        LLMProviderInfo(
            name="openai",
            models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="anthropic",
            models=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="google",
            models=["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-pro"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="ollama",
            models=[],  # Dynamically fetched
            requires_api_key=False,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="azure",
            models=[],  # Depends on Azure configuration
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="deepseek",
            models=["deepseek-chat", "deepseek-coder"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="mistral",
            models=["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="cohere",
            models=["command-r", "command-r-plus", "command"],
            requires_api_key=True,
            supports_base_url=True
        ),
        LLMProviderInfo(
            name="openrouter",
            models=[],  # Supports many models via openrouter
            requires_api_key=True,
            supports_base_url=True
        ),
    ]
    return {"providers": [p.model_dump() for p in providers]}

@app.get("/llm/models")
async def get_available_models(ollama_url: str = "http://localhost:11434"):
    """Get available models from different LLM providers"""
    models = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-pro"],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
        "mistral": ["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"],
        "cohere": ["command-r", "command-r-plus", "command"],
        "azure": ["gpt-4", "gpt-35-turbo"],
    }
    
    # Try to get Ollama models
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                models["ollama"] = ollama_models
            else:
                models["ollama"] = []
    except Exception:
        models["ollama"] = []
    
    return models

@app.post("/llm/test")
async def test_llm_connection(request: TestLLMRequest):
    """Test LLM connection - uses direct API for Ollama, LiteLLM for others"""
    try:
        provider = request.provider.lower().strip() if request.provider else ""
        model_input = request.model.strip() if request.model else ""
        
        # Handle Ollama - use direct HTTP call (more reliable)
        if provider.startswith("ollama"):
            import httpx
            base_url = request.base_url if request.base_url else ""
            ollama_url = base_url.strip() if base_url else "http://localhost:11434"
            
            # Determine model name
            model_name = model_input if model_input else "llama2"
            
            # First get available models to verify connection
            async with httpx.AsyncClient() as client:
                # Get models
                tags_resp = await client.get(f"{ollama_url}/api/tags", timeout=10.0)
                if tags_resp.status_code != 200:
                    return {"success": False, "error": f"Cannot connect to Ollama: HTTP {tags_resp.status_code}"}
                
                models_data = tags_resp.json()
                available_models = [m.get("name", "") for m in models_data.get("models", [])]
                
                if not available_models:
                    return {"success": False, "error": "No models found in Ollama"}
                
                # Check if requested model exists - handle different format (with/without :tag)
                model_found = False
                for m in available_models:
                    # Compare just the base name
                    if m.split(":")[0] == model_name.split(":")[0]:
                        model_name = m  # Use the full model name from Ollama
                        model_found = True
                        break
                
                if not model_found:
                    # Use first available model
                    model_name = available_models[0]
                
                # Test generate
                gen_resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": model_name, "prompt": request.test_prompt or "Hello", "stream": False},
                    timeout=120.0
                )
                
                if gen_resp.status_code == 200:
                    gen_data = gen_resp.json()
                    content = gen_data.get("response", "")
                    return {
                        "success": True,
                        "message": f"Connected! Using model: {model_name}",
                        "response": content,
                        "model": model_name,
                        "available_models": available_models[:10]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Generate failed: HTTP {gen_resp.status_code}, {gen_resp.text[:200]}"
                    }
                gen_resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": model_name, "prompt": request.test_prompt or "Hello", "stream": False},
                    timeout=60.0
                )
                
                if gen_resp.status_code == 200:
                    gen_data = gen_resp.json()
                    content = gen_data.get("response", "")
                    return {
                        "success": True,
                        "message": f"Connected! Using model: {model_name}",
                        "response": content,
                        "model": model_name,
                        "available_models": available_models[:10]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Generate failed: HTTP {gen_resp.status_code}"
                    }
        
        # Handle other providers using LiteLLM
        final_model = ""
        
        if provider.startswith("anthropic"):
            final_model = model_input if model_input else "claude-3-haiku-20240307"
            os.environ["ANTHROPIC_API_KEY"] = request.api_key or os.getenv("ANTHROPIC_API_KEY", "")
        elif provider.startswith("google") or provider.startswith("gemini"):
            final_model = model_input if model_input else "gemini-1.5-flash"
            os.environ["GOOGLE_API_KEY"] = request.api_key or os.getenv("GOOGLE_API_KEY", "")
        elif provider.startswith("deepseek"):
            final_model = model_input if model_input else "deepseek-chat"
            os.environ["DEEPSEEK_API_KEY"] = request.api_key or ""
        elif provider.startswith("mistral"):
            final_model = model_input if model_input else "mistral-small-latest"
            os.environ["MISTRAL_API_KEY"] = request.api_key or ""
        elif provider.startswith("cohere"):
            final_model = model_input if model_input else "command-r"
            os.environ["COHERE_API_KEY"] = request.api_key or ""
        else:
            # Default to OpenAI format
            final_model = model_input if model_input else "gpt-4o-mini"
            os.environ["OPENAI_API_KEY"] = request.api_key or os.getenv("OPENAI_API_KEY", "")
        
        # Set custom base URL if provided
        if request.base_url:
            os.environ["OPENAI_API_BASE"] = request.base_url.strip()
        
        # Make test completion using LiteLLM
        response = await litellm.acompletion(
            model=final_model,
            messages=[{"role": "user", "content": request.test_prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=60.0
        )
        
        # Extract response content - handle different response types
        content = ""
        model_name = ""
        usage_info = {}
        
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content or ""
        
        if hasattr(response, 'model'):
            model_name = response.model
            
        if hasattr(response, 'usage') and response.usage:
            usage_info = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        return {
            "success": True,
            "message": f"Connected to {request.provider}!",
            "response": content,
            "model": model_name,
            "usage": usage_info
        }
        
    except litellm.exceptions.AuthenticationError as e:
        return {
            "success": False,
            "error": f"Authentication failed: {str(e)}. Please check your API key."
        }
    except litellm.exceptions.RateLimitError as e:
        return {
            "success": False,
            "error": f"Rate limit exceeded: {str(e)}"
        }
    except litellm.exceptions.Timeout as e:
        return {
            "success": False,
            "error": f"Request timeout: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/llm/completions")
async def llm_completion(request: LLMConfigRequest):
    """Use LLM for text completion via LiteLLM"""
    try:
        model = request.model if request.model else request.provider
        
        # Determine provider and set custom_llm_provider
        custom_llm_provider = None
        
        # Handle Ollama specifically
        if request.provider.startswith("ollama") or request.provider == "ollama":
            custom_llm_provider = "ollama"
            ollama_url = request.base_url if request.base_url else "http://localhost:11434"
            os.environ["OLLAMA_BASE_URL"] = ollama_url
            if not model.startswith("ollama/"):
                model = f"ollama/{model}"
        
        # Set API key if provided
        if request.api_key:
            if request.provider.startswith("anthropic"):
                os.environ["ANTHROPIC_API_KEY"] = request.api_key
            elif request.provider.startswith("google") or request.provider.startswith("gemini"):
                os.environ["GOOGLE_API_KEY"] = request.api_key
            elif request.provider.startswith("deepseek"):
                os.environ["DEEPSEEK_API_KEY"] = request.api_key
            elif request.provider.startswith("mistral"):
                os.environ["MISTRAL_API_KEY"] = request.api_key
            elif request.provider.startswith("cohere"):
                os.environ["COHERE_API_KEY"] = request.api_key
            else:
                os.environ["OPENAI_API_KEY"] = request.api_key
        
        # Set custom base URL if provided (non-Ollama)
        if request.base_url and not request.provider.startswith("ollama"):
            os.environ["OPENAI_API_BASE"] = request.base_url
        
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": request.test_prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=60.0,
            custom_llm_provider=custom_llm_provider
        )
        
        # Extract response content - handle different response types
        content = ""
        model_name = ""
        usage_info = {}
        
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content or ""
        
        if hasattr(response, 'model'):
            model_name = response.model
            
        if hasattr(response, 'usage') and response.usage:
            usage_info = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        return {
            "success": True,
            "content": content,
            "model": model_name,
            "usage": usage_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
