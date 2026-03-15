import litellm
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import LLMExtractionStrategy, LLMConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy

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

app = FastAPI(title="Crawl4AI API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Models ============

class CrawlRequest(BaseModel):
    url: str
    priority: int = 10
    word_count_threshold: int = 15
    wait_for: Optional[str] = None
    js_code: Optional[List[str]] = None
    screenshot: bool = False
    pdf: bool = False

class DeepCrawlRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = 10
    strategy: str = "bfs"  # bfs, dfs, best_first
    priority: int = 10

class ExtractRequest(BaseModel):
    url: str
    instruction: str
    schema: Optional[Dict[str, Any]] = None
    provider: str = "openai/gpt-4o-mini"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

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

# ============ Endpoints ============

@app.get("/")
async def root():
    return {"message": "Crawl4AI API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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
    import sys
    import io
    # Set UTF-8 encoding for stdout/stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    uvicorn.run(app, host="0.0.0.0", port=8000)
