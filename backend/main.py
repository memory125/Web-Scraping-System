import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import LLMExtractionStrategy, LLMConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstDeepCrawlStrategy

# Global crawler instance
crawler: Optional[AsyncWebCrawler] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global crawler
    # Initialize crawler on startup
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
    )
    crawler = AsyncWebCrawler(config=browser_config)
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
        
        return CrawlResult(
            success=result.success,
            url=request.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            links=result.links,
            images=result.media.get("images") if result.media else None,
            videos=result.media.get("videos") if result.media else None,
            error=result.error_message if not result.success else None
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
            strategy = BestFirstDeepCrawlStrategy(
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
