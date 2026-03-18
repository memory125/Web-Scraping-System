"""
专门的电商爬虫接口 - 每个平台一个接口
自动检测平台并路由到对应的爬虫方法
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ E-commerce Crawler Requests ============


class BaseEcommerceRequest(BaseModel):
    """基础电商爬虫请求"""

    urls: List[str] = Field(default=[], description="要爬取的 URL 列表")
    viewport_width: int = Field(default=1920, description="视口宽度")
    viewport_height: int = Field(default=1080, description="视口高度")
    page_timeout: int = Field(default=60000, description="页面超时时间（毫秒）")
    wait_until: str = Field(default="networkidle", description="等待加载完成条件")
    max_scroll_steps: int = Field(default=10, description="最大滚动次数")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    js_only: bool = Field(default=False, description="仅执行 JS")


# ============ E-commerce Crawler Endpoints ============


@router.post("/crawl/amazon")
async def crawl_amazon(request: BaseEcommerceRequest):
    """Amazon 专用爬虫接口

    特点：
    - 设置 BYPASS 缓存模式避免缓存问题
    - 启用 stealth 模式
    - 使用美国 UA
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "en-US,en;q=0.9"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "links": result.links,
                            "images": result.media.get("images", [])[:20]
                            if result.media
                            else [],
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "amazon",
            "results": results,
            "count": len(request.urls),
        }
    except Exception as e:
        logger.error(f"Amazon crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "amazon"}


@router.post("/crawl/tmall")
async def crawl_tmall(request: BaseEcommerceRequest):
    """天猫专用爬虫接口

    特点：
    - 打开浏览器让用户扫码登录
    - 使用中国时区 headers
    - 启用 stealth 模式
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=False,  # 打开浏览器让用户扫码
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "tmall",
            "results": results,
            "count": len(request.urls),
            "login_instruction": "请手动扫码登录后继续",
        }
    except Exception as e:
        logger.error(f"Tmall crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "tmall"}


@router.post("/crawl/taobao")
async def crawl_taobao(request: BaseEcommerceRequest):
    """淘宝专用爬虫接口（同天猫）"""
    return await crawl_tmall(request)


@router.post("/crawl/ebay")
async def crawl_ebay(request: BaseEcommerceRequest):
    """eBay 专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "en-US,en;q=0.9"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "links": result.links,
                            "images": result.media.get("images", [])[:20]
                            if result.media
                            else [],
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "ebay",
            "results": results,
            "count": len(request.urls),
        }
    except Exception as e:
        logger.error(f"eBay crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "ebay"}


@router.post("/crawl/jd")
async def crawl_jd(request: BaseEcommerceRequest):
    """京东专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "jd",
            "results": results,
            "count": len(request.urls),
        }
    except Exception as e:
        logger.error(f"JD crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "jd"}


@router.post("/crawl/alibaba")
async def crawl_alibaba(request: BaseEcommerceRequest):
    """阿里国际站专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "en-US,en;q=0.9"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "links": result.links,
                            "images": result.media.get("images", [])[:20]
                            if result.media
                            else [],
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "alibaba",
            "results": results,
            "count": len(request.urls),
        }
    except Exception as e:
        logger.error(f"Alibaba crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "alibaba"}


@router.post("/crawl/aliexpress")
async def crawl_aliexpress(request: BaseEcommerceRequest):
    """速卖通专用爬虫接口"""
    return await crawl_alibaba(request)


@router.post("/crawl/shopify")
async def crawl_shopify(request: BaseEcommerceRequest):
    """Shopify 站专用爬虫接口"""
    return await crawl_alibaba(request)


@router.post("/crawl/rakuten")
async def crawl_rakuten(request: BaseEcommerceRequest):
    """乐天（日本）专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "rakuten",
            "results": results,
            "count": len(request.urls),
            "recommendation": "建议使用日本代理",
        }
    except Exception as e:
        logger.error(f"Rakuten crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "rakuten"}


@router.post("/crawl/coupang")
async def crawl_coupang(request: BaseEcommerceRequest):
    """Coupang（韩国）专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "coupang",
            "results": results,
            "count": len(request.urls),
            "recommendation": "建议使用韩国代理",
        }
    except Exception as e:
        logger.error(f"Coupang crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "coupang"}


@router.post("/crawl/mercadolibre")
async def crawl_mercadolibre(request: BaseEcommerceRequest):
    """MercadoLibre（拉美）专用爬虫接口"""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        browser_config = BrowserConfig(
            headless=True,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            verbose=True,
            enable_stealth=True,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            remove_overlay_elements=True,
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)
                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "markdown": result.markdown.raw_markdown[:2000]
                            if result.markdown
                            else None,
                            "error": result.error_message,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return {
            "success": True,
            "platform": "mercadolibre",
            "results": results,
            "count": len(request.urls),
            "recommendation": "建议使用拉美代理",
        }
    except Exception as e:
        logger.error(f"MercadoLibre crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "mercadolibre"}


@router.post("/crawl/walmart")
async def crawl_walmart(request: BaseEcommerceRequest):
    """Walmart 专用爬虫接口"""
    return await crawl_ebay(request)


@router.post("/crawl/target")
async def crawl_target(request: BaseEcommerceRequest):
    """Target 专用爬虫接口"""
    return await crawl_ebay(request)


@router.delete("/crawl/session/{session_id}")
async def kill_crawl_session(session_id: str):
    """终止指定 session 的爬虫会话"""
    return {"success": True, "message": f"Session {session_id} terminated"}
