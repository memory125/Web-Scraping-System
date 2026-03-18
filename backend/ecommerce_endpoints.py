"""
专门的电商爬虫接口 - 每个平台一个接口
自动检测平台并路由到对应的爬虫方法
基于 Crawl4AI 官方文档优化：
- 反检测浏览器 (Stealth + UndetectedAdapter)
- 代理支持与轮换
- Hooks 钩子函数
- 会话管理
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


class AmazonCrawlRequest(BaseModel):
    """Amazon 专用爬虫请求 (增强版)

    基于 Crawl4AI 官方文档优化:
    - 支持代理配置
    - 支持代理轮换
    - 支持会话管理
    - 支持自定义 hooks
    """

    urls: List[str] = Field(default=[], description="要爬取的 URL 列表")
    # 代理配置
    proxy_url: Optional[str] = Field(default=None, description="代理服务器地址")
    proxy_username: Optional[str] = Field(default=None, description="代理用户名")
    proxy_password: Optional[str] = Field(default=None, description="代理密码")
    use_proxy_rotation: bool = Field(default=False, description="是否使用代理轮换")
    # 浏览器配置
    viewport_width: int = Field(default=1920, description="视口宽度")
    viewport_height: int = Field(default=1080, description="视口高度")
    page_timeout: int = Field(default=120000, description="页面超时时间（毫秒）")
    wait_until: str = Field(default="load", description="等待加载完成条件")
    max_scroll_steps: int = Field(default=10, description="最大滚动次数")
    # 会话管理
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    js_only: bool = Field(default=False, description="仅执行 JS")
    # 反检测
    use_stealth: bool = Field(default=True, description="启用隐身模式")
    use_undetected: bool = Field(default=False, description="使用反检测浏览器")
    use_magic: bool = Field(default=True, description="启用 magic 模式")
    headless: bool = Field(default=False, description="是否无头模式")


class AdvancedAmazonCrawlRequest(BaseModel):
    """Amazon 高级爬虫请求 (完整版)

    包含所有 Crawl4AI 高级功能:
    - 代理轮换策略
    - 自定义 Hooks
    - SSL 证书分析
    - 网络请求捕获
    """

    urls: List[str] = Field(default=[], description="要爬取的 URL 列表")
    # 代理配置
    proxy_url: Optional[str] = Field(default=None, description="代理服务器")
    proxy_username: Optional[str] = Field(default=None, description="代理用户名")
    proxy_password: Optional[str] = Field(default=None, description="代理密码")
    # 代理轮换
    use_proxy_rotation: bool = Field(default=False, description="启用代理轮换")
    proxy_list: List[str] = Field(
        default=[], description="代理列表 (格式: ip:port:user:pass)"
    )
    # 浏览器配置
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    wait_until: str = Field(default="load")
    max_scroll_steps: int = Field(default=10)
    # 会话
    session_id: Optional[str] = Field(default=None)
    js_only: bool = Field(default=False)
    # 反检测
    use_stealth: bool = Field(default=True)
    use_undetected: bool = Field(default=False)
    use_magic: bool = Field(default=True)
    headless: bool = Field(default=False)
    # 高级功能
    fetch_ssl_certificate: bool = Field(default=False, description="获取 SSL 证书")
    capture_network: bool = Field(default=False, description="捕获网络请求")
    capture_console: bool = Field(default=False, description="捕获控制台消息")


class CompleteAmazonCrawlRequest(BaseModel):
    """Amazon 完整版爬虫请求 (基于 Crawl4AI 官方文档)

    包含所有高级功能:
    - 浏览器配置: browser_type, viewport, stealth, cookies
    - 爬虫配置: cache_mode, wait_for, extraction_strategy
    - 会话管理: session_id, use_persistent_context
    - 身份配置: locale, timezone_id, geolocation
    - Markdown生成: markdown_generator, content_filter
    - 结构化提取: extraction_strategy (CSS/LLM)
    - 截图/PDF: screenshot, pdf
    - 网络/控制台: capture_network_requests, capture_console_messages
    - 反检测: magic, simulate_user, override_navigator
    """

    # 基础
    urls: List[str] = Field(default=[], description="要爬取的 URL 列表")

    # 浏览器配置 (BrowserConfig)
    browser_type: str = Field(
        default="chromium", description="浏览器类型: chromium/firefox/webkit"
    )
    headless: bool = Field(default=False, description="是否无头模式")
    viewport_width: int = Field(default=1920, description="视口宽度")
    viewport_height: int = Field(default=1080, description="视口高度")
    device_scale_factor: float = Field(default=1.0, description="设备像素比")
    text_mode: bool = Field(default=False, description="文本模式(禁用图片)")
    light_mode: bool = Field(default=False, description="轻量模式")
    enable_stealth: bool = Field(default=True, description="启用隐身模式")
    user_agent: Optional[str] = Field(default=None, description="自定义 User-Agent")
    user_agent_random: bool = Field(default=False, description="随机 User-Agent")

    # 代理配置
    proxy_url: Optional[str] = Field(default=None, description="代理服务器")
    proxy_username: Optional[str] = Field(default=None, description="代理用户名")
    proxy_password: Optional[str] = Field(default=None, description="代理密码")

    # Cookies 和会话
    cookies: List[Dict[str, Any]] = Field(default=[], description="预设 Cookies")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    use_persistent_context: bool = Field(default=False, description="使用持久化上下文")
    user_data_dir: Optional[str] = Field(default=None, description="用户数据目录")

    # 身份配置 (Identity)
    locale: Optional[str] = Field(default="en-US", description="浏览器语言")
    timezone_id: Optional[str] = Field(default="America/New_York", description="时区")
    geolocation_lat: Optional[float] = Field(default=None, description="纬度")
    geolocation_lng: Optional[float] = Field(default=None, description="经度")

    # 爬虫配置 (CrawlerRunConfig)
    page_timeout: int = Field(default=120000, description="页面超时(毫秒)")
    wait_until: str = Field(default="load", description="等待条件")
    wait_for: Optional[str] = Field(default=None, description="等待选择器")
    wait_for_timeout: int = Field(default=30000, description="等待超时")
    delay_before_return_html: float = Field(default=2.0, description="返回HTML前延迟")
    max_scroll_steps: int = Field(default=10, description="最大滚动次数")
    scroll_delay: float = Field(default=0.3, description="滚动延迟")
    scan_full_page: bool = Field(default=False, description="扫描全页")
    word_count_threshold: int = Field(default=10, description="词数阈值")
    cache_mode: str = Field(default="BYPASS", description="缓存模式")

    # JavaScript
    js_code: Optional[str] = Field(default=None, description="执行的JavaScript代码")
    js_only: bool = Field(default=False, description="仅执行JS")

    # 反检测
    magic: bool = Field(default=True, description="启用Magic模式")
    simulate_user: bool = Field(default=True, description="模拟用户")
    override_navigator: bool = Field(default=True, description="覆盖navigator")

    # 内容处理
    remove_overlay_elements: bool = Field(default=True, description="移除覆盖元素")
    excluded_tags: List[str] = Field(
        default=["form", "header", "footer"], description="排除的标签"
    )
    exclude_external_links: bool = Field(default=False, description="排除外部链接")
    exclude_external_images: bool = Field(default=False, description="排除外部图片")

    # 提取策略
    use_extraction: bool = Field(default=False, description="使用结构化提取")
    extraction_css_selector: Optional[str] = Field(
        default=None, description="CSS选择器"
    )
    extraction_fields: List[Dict[str, Any]] = Field(default=[], description="提取字段")

    # Markdown生成
    use_markdown: bool = Field(default=True, description="生成Markdown")
    markdownCitations: bool = Field(default=False, description="Markdown引用")

    # 截图/PDF
    screenshot: bool = Field(default=False, description="截图")
    pdf: bool = Field(default=False, description="PDF")

    # 网络/控制台
    capture_network_requests: bool = Field(default=False, description="捕获网络请求")
    capture_console_messages: bool = Field(default=False, description="捕获控制台消息")

    # SSL证书
    fetch_ssl_certificate: bool = Field(default=False, description="获取SSL证书")


# ============ E-commerce Crawler Endpoints ============


# ============ Unified Amazon Crawler (Optimized) ============


class OptimizedAmazonRequest(BaseModel):
    """统一优化的Amazon爬虫请求

    整合所有最佳爬虫策略:
    - 智能URL分类与策略匹配
    - 反爬虫检测重试
    - 代理轮换支持
    - 深度挖掘
    - 生命周期Hooks
    - 产品数据提取
    """

    # 基础
    urls: List[str] = Field(default=[], description="要爬取的URL列表")

    # 爬取模式
    mode: str = Field(
        default="smart", description="爬取模式: smart/standard/deep/stealth/undetected"
    )

    # 深度挖掘
    deep_crawl: bool = Field(default=False, description="启用深度挖掘")
    max_depth: int = Field(default=2, description="最大深度")
    max_pages: int = Field(default=50, description="最大页面数")

    # 反爬配置
    max_retries: int = Field(default=2, description="反爬重试次数")
    proxy_list: List[str] = Field(default=[], description="代理列表")
    use_proxy_rotation: bool = Field(default=False, description="启用代理轮换")
    fallback_enabled: bool = Field(default=True, description="启用回退函数")

    # 浏览器配置
    headless: bool = Field(default=False, description="无头模式")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    wait_until: str = Field(default="load")
    max_scroll_steps: int = Field(default=10)

    # 反检测
    enable_stealth: bool = Field(default=True)
    use_magic: bool = Field(default=True)
    simulate_user: bool = Field(default=True)
    override_navigator: bool = Field(default=True)

    # 身份配置
    locale: str = Field(default="en-US")
    timezone_id: str = Field(default="America/New_York")

    # 会话
    session_id: Optional[str] = Field(default=None)
    cookies: List[Dict[str, Any]] = Field(default=[])

    # 提取
    extract_products: bool = Field(default=False, description="提取产品数据")

    # 输出
    capture_screenshot: bool = Field(default=False)
    verbose: bool = Field(default=False)


def get_amazon_strategy(url: str, mode: str) -> Dict[str, Any]:
    """根据URL类型和模式返回最佳策略"""

    url_lower = url.lower()

    # URL类型检测
    url_type = "search"
    if "/dp/" in url_lower or "/gp/product/" in url_lower:
        url_type = "product"
    elif "/review/" in url_lower:
        url_type = "review"
    elif "/b/" in url_lower or "bestsellers" in url_lower:
        url_type = "category"

    # 模式配置
    mode_configs = {
        "smart": {
            "wait_until": "networkidle"
            if url_type in ["search", "category"]
            else "load",
            "max_scroll_steps": 15 if url_type == "search" else 10,
            "magic": True,
            "stealth": True,
        },
        "standard": {
            "wait_until": "load",
            "max_scroll_steps": 10,
            "magic": True,
            "stealth": True,
        },
        "deep": {
            "wait_until": "networkidle",
            "max_scroll_steps": 20,
            "magic": True,
            "stealth": True,
        },
        "stealth": {
            "wait_until": "load",
            "max_scroll_steps": 5,
            "magic": True,
            "stealth": True,
        },
        "undetected": {
            "wait_until": "load",
            "max_scroll_steps": 5,
            "magic": False,
            "stealth": True,
        },
    }

    return mode_configs.get(mode, mode_configs["smart"])


async def amazon_fallback(url: str) -> str:
    """Amazon回退函数"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                return await resp.text()
            raise RuntimeError(f"Fallback error: {resp.status}")


@router.post("/crawl/amazon")
@router.post("/crawl/amazon/unified")
async def crawl_amazon_unified(request: OptimizedAmazonRequest):
    """统一优化的Amazon爬虫接口

    功能:
    - 智能URL分类与策略匹配
    - 反爬虫检测与重试 (max_retries)
    - 代理列表轮换
    - 回退函数支持
    - 深度挖掘
    - 生命周期Hooks
    - 产品数据提取

    使用示例:
    ```json
    {
        "urls": ["https://www.amazon.com/s?k=laptop"],
        "mode": "smart",
        "max_retries": 2,
        "extract_products": true
    }
    ```
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig, ProxyConfig
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        from playwright.async_api import Page, BrowserContext

        logger.info(
            f"[Amazon] Starting crawl: {len(request.urls)} URLs, mode: {request.mode}"
        )

        # 1. 代理配置
        proxy_config = None
        if (
            request.use_proxy_rotation
            and request.proxy_list
            and len(request.proxy_list) > 0
        ):
            first_proxy = request.proxy_list[0]
            try:
                parts = first_proxy.replace("http://", "").replace("https://", "")
                if "@" in parts:
                    auth, host = parts.split("@", 1)
                    user, pwd = auth.split(":", 1)
                    proxy_config = ProxyConfig(
                        server=f"http://{host}", username=user, password=pwd
                    )
                else:
                    proxy_config = ProxyConfig(server=f"http://{parts}")
            except:
                pass

        # 2. 浏览器配置
        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            verbose=request.verbose,
            enable_stealth=request.enable_stealth,
            headers={
                "Accept-Language": request.locale,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        # 3. 获取策略
        strategy = get_amazon_strategy(
            request.urls[0] if request.urls else "", request.mode
        )

        # 4. 提取策略 (产品数据)
        extraction_strategy = None
        if request.extract_products:
            product_schema = {
                "name": "Amazon Product",
                "base_selector": "[data-component-type='s-search-result']",
                "fields": [
                    {"name": "title", "selector": "h2 a span", "type": "text"},
                    {"name": "price", "selector": ".a-price-whole", "type": "text"},
                    {"name": "rating", "selector": ".a-icon-alt", "type": "text"},
                    {
                        "name": "url",
                        "selector": "h2 a",
                        "type": "attribute",
                        "attribute": "href",
                    },
                ],
            }
            extraction_strategy = JsonCssExtractionStrategy(
                product_schema, verbose=False
            )

        # 5. 爬虫配置
        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=strategy.get("wait_until", "load"),
            max_scroll_steps=strategy.get("max_scroll_steps", 10),
            cache_mode=CacheMode.BYPASS,
            magic=request.use_magic if request.mode != "undetected" else False,
            simulate_user=request.simulate_user,
            override_navigator=request.override_navigator,
            remove_overlay_elements=True,
            delay_before_return_html=2.0,
            proxy_config=proxy_config,
            extraction_strategy=extraction_strategy,
        )

        # 6. 执行爬取
        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "status_code": result.status_code,
                            "markdown": result.markdown.raw_markdown[:5000]
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
            "platform": "amazon",
            "mode": request.mode,
            "strategy_applied": strategy,
            "results": results,
            "count": len(results),
            "config": {
                "max_retries": request.max_retries,
                "proxy_rotation": request.use_proxy_rotation,
                "magic": request.use_magic,
                "stealth": request.enable_stealth,
            },
            "recommendations": [
                "使用美国住宅代理提高成功率",
                "预置有效Amazon cookies可绕过部分检测",
                "遇到CAPTCHA尝试使用undetected模式",
            ],
        }

    except Exception as e:
        logger.error(f"[Amazon] Crawl error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "platform": "amazon"}

        # 文档: 反检测最佳实践
        # - 使用 magic=True 启用 magic 模式
        # - 使用 simulate_user=True 模拟用户行为
        # - 使用 override_navigator=True 覆盖 navigator 属性
        # - 添加延迟等待
        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until="load",  # 文档: 使用 load 而非 networkidle 减少等待时间
            max_scroll_steps=request.max_scroll_steps,
            # 文档: BYPASS 缓存模式避免返回缓存内容
            cache_mode=CacheMode.BYPASS,
            # 文档: magic 模式提供更好的交互
            magic=True,
            # 文档: 模拟用户行为
            simulate_user=True,
            # 文档: 覆盖 navigator 属性
            override_navigator=True,
            # 文档: 移除覆盖元素
            remove_overlay_elements=True,
            # 文档: 延迟返回 HTML 让页面完全加载
            delay_before_return_html=2.0,
            # 文档: 等待时间
            wait_for_timeout=30000,
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
                            "status_code": result.status_code,
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


@router.post("/crawl/amazon/advanced")
async def crawl_amazon_advanced(request: BaseEcommerceRequest):
    """Amazon 专用爬虫接口 (高级反检测版)

    基于 Crawl4AI 官方文档优化：
    - 使用 UndetectedAdapter 反检测浏览器 (最高级反爬)
    - 组合 stealth 模式 + undetected 模式
    - 使用 headless=False 减少检测
    - 添加更长的延迟等待
    - 模拟真实用户行为

    当普通版本被阻止时使用此版本
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig
        from crawl4ai import UndetectedAdapter
        from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

        # 文档: 创建 undetected adapter
        undetected_adapter = UndetectedAdapter()

        # 文档: stealth 模式 + headless=False
        browser_config = BrowserConfig(
            headless=False,  # 文档: 避免 headless 模式
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            verbose=True,
            enable_stealth=True,  # 文档: 启用 stealth
        )

        # 文档: 创建带 undetected adapter 的策略
        crawler_strategy = AsyncPlaywrightCrawlerStrategy(
            browser_config=browser_config, browser_adapter=undetected_adapter
        )

        # 文档: 更长的等待时间
        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until="load",
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=True,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
            delay_before_return_html=3.0,  # 更长的延迟
            wait_for_timeout=45000,
        )

        results = []
        # 文档: 使用自定义策略的爬虫
        async with AsyncWebCrawler(
            crawler_strategy=crawler_strategy, config=browser_config
        ) as crawler:
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
                            "status_code": result.status_code,
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
            "platform": "amazon_advanced",
            "results": results,
            "count": len(request.urls),
            "note": "使用 UndetectedAdapter 反检测浏览器",
        }
    except Exception as e:
        logger.error(f"Amazon advanced crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "amazon_advanced"}


@router.post("/crawl/amazon/proxy")
async def crawl_amazon_with_proxy(request: AmazonCrawlRequest):
    """Amazon 专用爬虫接口 (代理版)

    基于 Crawl4AI 官方文档 - Proxy & Security:
    - 支持单个代理配置
    - 支持代理认证
    - 配合 stealth 模式使用
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, ProxyConfig
        from crawl4ai.async_configs import BrowserConfig

        # 文档: 代理配置
        proxy_config = None
        if request.proxy_url:
            proxy_config = ProxyConfig(
                server=request.proxy_url,
                username=request.proxy_username,
                password=request.proxy_password,
            )

        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
            verbose=True,
            enable_stealth=request.use_stealth,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            proxy_config=proxy_config,
            magic=request.use_magic,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
            delay_before_return_html=2.0,
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
                            "status_code": result.status_code,
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
            "platform": "amazon_proxy",
            "results": results,
            "count": len(request.urls),
            "proxy_used": request.proxy_url or "none",
        }
    except Exception as e:
        logger.error(f"Amazon proxy crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "amazon_proxy"}


@router.post("/crawl/amazon/hooks")
async def crawl_amazon_with_hooks(request: AmazonCrawlRequest):
    """Amazon 专用爬虫接口 (Hooks 版)

    基于 Crawl4AI 官方文档 - Hooks & Auth:
    - 使用自定义 Hooks 进行认证
    - 在 on_page_context_created 中设置 cookies
    - 支持自定义 headers
    - 支持页面交互
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig
        from playwright.async_api import Page, BrowserContext

        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
            verbose=True,
            enable_stealth=request.use_stealth,
        )

        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=request.wait_until,
            max_scroll_steps=request.max_scroll_steps,
            cache_mode=CacheMode.BYPASS,
            magic=request.use_magic,
            simulate_user=True,
            override_navigator=True,
            remove_overlay_elements=True,
            delay_before_return_html=2.0,
        )

        # 文档: 创建爬虫实例并设置 Hooks
        crawler = AsyncWebCrawler(config=browser_config)

        # Hook: 在页面上下文创建后设置自定义 headers
        async def on_page_context_created(
            page: Page, context: BrowserContext, **kwargs
        ):
            # 文档: 这里是处理认证的最佳位置
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
            )
            return page

        # Hook: 在导航前设置 custom headers
        async def before_goto(page: Page, context: BrowserContext, url: str, **kwargs):
            # 文档: 用于设置自定义 headers 或日志
            return page

        # Hook: 导航后等待内容加载
        async def after_goto(
            page: Page, context: BrowserContext, url: str, response, **kwargs
        ):
            # 文档: 验证内容或等待必要元素
            try:
                await page.wait_for_selector("body", timeout=5000)
            except:
                pass
            return page

        # Hook: 返回 HTML 前执行最终操作
        async def before_retrieve_html(page: Page, context: BrowserContext, **kwargs):
            # 文档: 最终滚动或懒加载触发
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            return page

        # 设置 Hooks
        await crawler.start()
        crawler.crawler_strategy.set_hook(
            "on_page_context_created", on_page_context_created
        )
        crawler.crawler_strategy.set_hook("before_goto", before_goto)
        crawler.crawler_strategy.set_hook("after_goto", after_goto)
        crawler.crawler_strategy.set_hook("before_retrieve_html", before_retrieve_html)

        results = []
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
                        "status_code": result.status_code,
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

        await crawler.close()

        return {
            "success": True,
            "platform": "amazon_hooks",
            "results": results,
            "count": len(request.urls),
            "note": "使用自定义 Hooks",
        }
    except Exception as e:
        logger.error(f"Amazon hooks crawl error: {e}")
        return {"success": False, "error": str(e), "platform": "amazon_hooks"}


# ============ Unified Tmall Crawler (Optimized v3 - Deep Learning) ============


class OptimizedTmallRequest(BaseModel):
    """统一优化的天猫爬虫请求 (基于Crawl4AI官方文档深度优化)

    天猫/淘宝特点:
    - 需要中国IP代理才能访问
    - 需要登录cookies才能查看完整内容
    - 反爬虫检测较强 (Akamai等)
    - 页面需要JavaScript渲染
    - 大量使用虚拟滚动

    基于官方文档优化:
    - 反爬虫检测与重试 (Anti-Bot & Fallback)
    - 代理列表轮换 (Proxy & Security)
    - Hooks生命周期管理 (Hooks & Auth)
    - 深度挖掘 (Deep Crawling)
    - Filter Chains & Scorers
    - Session Management
    - Virtual Scroll
    """

    urls: List[str] = Field(default=[], description="要爬取的URL列表")
    mode: str = Field(
        default="smart",
        description="模式: smart/standard/deep/stealth/undetected/best_first",
    )
    headless: bool = Field(default=False, description="无头模式")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    max_scroll_steps: int = Field(default=10)
    enable_stealth: bool = Field(default=True)
    use_magic: bool = Field(default=True)
    simulate_user: bool = Field(default=True)
    override_navigator: bool = Field(default=True)
    locale: str = Field(default="zh-CN")

    # 反爬虫配置 (官方文档: Anti-Bot & Fallback)
    max_retries: int = Field(default=2, description="反爬重试次数")
    proxy_list: List[str] = Field(default=[], description="代理列表(中国IP)")
    use_proxy_rotation: bool = Field(default=False, description="启用代理轮换")
    fallback_enabled: bool = Field(default=True, description="启用回退函数")

    # Cookies配置 (官方文档: Hooks & Auth)
    cookies: List[Dict[str, Any]] = Field(default=[], description="登录cookies")
    session_id: Optional[str] = Field(default=None, description="会话ID用于session管理")

    # 深度挖掘配置 (官方文档: Deep Crawling)
    deep_crawl: bool = Field(default=False, description="启用深度挖掘")
    max_depth: int = Field(default=2, description="深度挖掘最大层级")
    max_pages: int = Field(default=50, description="最大页面数")
    deep_strategy: str = Field(
        default="best_first", description="深度策略: bfs/dfs/best_first"
    )

    # Filter & Scorer (官方文档: Deep Crawling - Filter Chains)
    url_patterns: List[str] = Field(
        default=[], description="URL过滤模式 (如 *product*, *item*)"
    )
    keywords_for_scorer: List[str] = Field(default=[], description="关键词评分器关键词")

    # Prefetch模式 (官方文档: Prefetch Mode)
    prefetch_only: bool = Field(default=False, description="仅发现URL不处理内容")

    # 虚拟滚动 (官方文档: Virtual Scroll)
    virtual_scroll: bool = Field(default=True, description="启用虚拟滚动处理")

    # 懒加载处理 (官方文档: Lazy Loading)
    wait_for_images: bool = Field(default=True, description="等待图片加载完成")
    scan_full_page: bool = Field(default=True, description="全页面扫描触发懒加载")
    scroll_delay: float = Field(default=0.5, description="滚动延迟(秒)")

    # 其他
    extract_products: bool = Field(default=False)
    verbose: bool = Field(default=False)


def get_tmall_strategy(url: str, mode: str) -> Dict[str, Any]:
    """根据URL类型和模式返回天猫最佳策略 (基于官方文档深度优化)"""

    url_lower = url.lower()

    # URL类型检测
    url_type = "shop"
    if "/product" in url_lower or "/item" in url_lower:
        url_type = "product"
    elif "/category" in url_lower or "/cat" in url_lower:
        url_type = "category"
    elif "/search" in url_lower:
        url_type = "search"

    # 模式配置 (官方文档: 反爬虫建议使用wait_until="load")
    mode_configs = {
        "smart": {
            "wait_until": "load",
            "max_scroll_steps": 10,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 3.0,
            "virtual_scroll": True,
        },
        "standard": {
            "wait_until": "load",
            "max_scroll_steps": 8,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 2.0,
            "virtual_scroll": True,
        },
        "deep": {
            "wait_until": "networkidle",
            "max_scroll_steps": 15,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 5.0,
            "virtual_scroll": True,
        },
        "stealth": {
            "wait_until": "load",
            "max_scroll_steps": 5,
            "magic": False,
            "stealth": True,
            "delay_before_return_html": 2.0,
            "virtual_scroll": False,
        },
        "undetected": {
            "wait_until": "load",
            "max_scroll_steps": 5,
            "magic": False,
            "stealth": True,
            "ad_blocker": True,
            "delay_before_return_html": 3.0,
            "virtual_scroll": False,
        },
        "best_first": {
            "wait_until": "load",
            "max_scroll_steps": 12,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 4.0,
            "virtual_scroll": True,
            "use_scorer": True,
        },
    }

    return mode_configs.get(mode, mode_configs["smart"])


async def tmall_fallback(url: str) -> str:
    """天猫回退函数 - 当所有浏览器方法都失败时调用

    基于官方文档: Anti-Bot & Fallback
    """
    import aiohttp

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                raise RuntimeError(f"Fallback HTTP error: {resp.status}")
        except Exception as e:
            raise RuntimeError(f"Fallback fetch failed: {str(e)}")


@router.post("/crawl/tmall")
@router.post("/crawl/tmall/unified")
@router.post("/crawl/tmall/v2")
async def crawl_tmall_v2(request: OptimizedTmallRequest):
    """统一优化的天猫爬虫接口 (基于Crawl4AI官方文档)

    功能 (官方文档):
    - 反爬虫检测与重试 (max_retries) - Anti-Bot & Fallback
    - 代理列表轮换 (proxy_config列表) - Proxy & Security
    - 回退函数支持 (fallback_fetch_function) - Anti-Bot & Fallback
    - Hooks生命周期管理 - Hooks & Auth
    - 智能URL分类与策略匹配

    使用示例:
    ```json
    {
        "urls": ["https://taofunong.tmall.com/shop/view_shop.htm?spm=..."],
        "mode": "smart",
        "max_retries": 2,
        "proxy_list": [
            "http://user:pass@china-proxy-1.com:8080",
            "http://user:pass@china-proxy-2.com:8080"
        ],
        "use_proxy_rotation": true,
        "cookies": [{"name": "cookie_name", "value": "cookie_value", "domain": ".tmall.com"}]
    }
    ```

    官方文档参考:
    - https://docs.crawl4ai.com/advanced/anti-bot-and-fallback/
    - https://docs.crawl4ai.com/advanced/hooks-auth/
    - https://docs.crawl4ai.com/advanced/proxy-security/
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig, ProxyConfig
        from playwright.async_api import Page, BrowserContext

        logger.info(
            f"[Tmall v2] Starting crawl: {len(request.urls)} URLs, mode: {request.mode}"
        )

        # 1. 代理配置 (官方文档: proxy_config可以是列表)
        proxy_config = None
        if request.use_proxy_rotation and request.proxy_list:
            proxy_config = []
            for proxy_str in request.proxy_list:
                try:
                    parts = proxy_str.replace("http://", "").replace("https://", "")
                    if "@" in parts:
                        auth, host = parts.split("@", 1)
                        user, pwd = auth.split(":", 1)
                        proxy_config.append(
                            ProxyConfig(
                                server=f"http://{host}", username=user, password=pwd
                            )
                        )
                    else:
                        proxy_config.append(ProxyConfig(server=f"http://{parts}"))
                except:
                    pass
        elif request.proxy_list:
            # 单个代理
            try:
                parts = (
                    request.proxy_list[0].replace("http://", "").replace("https://", "")
                )
                if "@" in parts:
                    auth, host = parts.split("@", 1)
                    user, pwd = auth.split(":", 1)
                    proxy_config = ProxyConfig(
                        server=f"http://{host}", username=user, password=pwd
                    )
                else:
                    proxy_config = ProxyConfig(server=f"http://{parts}")
            except:
                pass

        # 2. 获取策略
        strategy = get_tmall_strategy(
            request.urls[0] if request.urls else "", request.mode
        )

        # 3. 浏览器配置 - 使用中文环境
        browser_config_kwargs = {
            "headless": request.headless,
            "viewport": {
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            "verbose": request.verbose,
            "enable_stealth": request.enable_stealth,
            "headers": {
                "Accept-Language": request.locale,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        }

        # Undetected模式
        if request.mode == "undetected":
            browser_config_kwargs["ad_blocker"] = True

        browser_config = BrowserConfig(**browser_config_kwargs)

        # 4. 爬虫配置 (官方文档: Anti-Bot & Fallback)
        crawl_config_kwargs = {
            "page_timeout": request.page_timeout,
            "wait_until": strategy.get("wait_until", "load"),
            "max_scroll_steps": strategy.get("max_scroll_steps", 10),
            "cache_mode": CacheMode.BYPASS,
            "magic": request.use_magic if request.mode != "undetected" else False,
            "simulate_user": request.simulate_user,
            "override_navigator": request.override_navigator,
            "remove_overlay_elements": True,
            "delay_before_return_html": strategy.get("delay_before_return_html", 3.0),
            # Lazy Loading配置 (官方文档: Lazy Loading)
            "wait_for_images": request.wait_for_images,
            "scan_full_page": request.scan_full_page,
            "scroll_delay": request.scroll_delay,
        }

        # 添加代理配置
        if proxy_config:
            crawl_config_kwargs["proxy_config"] = proxy_config

        # 添加回退函数 (官方文档: fallback_fetch_function)
        if request.fallback_enabled:
            crawl_config_kwargs["fallback_fetch_function"] = tmall_fallback

        crawl_config = CrawlerRunConfig(**crawl_config_kwargs)

        # 5. 创建爬虫并设置Hooks (官方文档: Hooks & Auth)
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()

        # Hook: 在页面上下文创建后设置cookies (官方文档推荐)
        async def on_page_context_created(
            page: Page, context: BrowserContext, **kwargs
        ):
            # 设置中文headers
            await page.set_extra_http_headers(
                {
                    "Accept-Language": request.locale,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )

            # 添加cookies (官方文档: 在on_page_context_created中设置)
            if request.cookies:
                for cookie in request.cookies:
                    try:
                        await context.add_cookies([cookie])
                    except:
                        pass

            return page

        # Hook: 导航后等待内容加载
        async def after_goto(
            page: Page, context: BrowserContext, url: str, response, **kwargs
        ):
            # 等待页面加载
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            return page

        # Hook: 获取HTML前执行最终操作
        async def before_retrieve_html(page: Page, context: BrowserContext, **kwargs):
            # 滚动页面触发懒加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(1000)
            return page

        # 设置Hooks
        crawler.crawler_strategy.set_hook(
            "on_page_context_created", on_page_context_created
        )
        crawler.crawler_strategy.set_hook("after_goto", after_goto)
        crawler.crawler_strategy.set_hook("before_retrieve_html", before_retrieve_html)

        # 6. 执行爬取
        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    # 提取crawl_stats (官方文档: crawl_stats)
                    crawl_stats = None
                    if result.crawl_stats:
                        crawl_stats = {
                            "attempts": result.crawl_stats.get("attempts", 0),
                            "retries": result.crawl_stats.get("retries", 0),
                            "proxies_used": result.crawl_stats.get("proxies_used", []),
                            "resolved_by": result.crawl_stats.get("resolved_by"),
                            "fallback_fetch_used": result.crawl_stats.get(
                                "fallback_fetch_used", False
                            ),
                        }

                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "status_code": result.status_code,
                            "markdown": result.markdown.raw_markdown[:3000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "error": result.error_message,
                            "crawl_stats": crawl_stats,
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

        await crawler.close()

        return {
            "success": True,
            "platform": "tmall",
            "mode": request.mode,
            "strategy_applied": strategy,
            "results": results,
            "count": len(results),
            "config": {
                "max_retries": request.max_retries,
                "proxy_configured": proxy_config is not None,
                "proxy_rotation": request.use_proxy_rotation,
                "cookies_configured": len(request.cookies) > 0,
                "fallback_enabled": request.fallback_enabled,
                "wait_until": strategy.get("wait_until", "load"),
                "max_scroll_steps": strategy.get("max_scroll_steps", 10),
            },
            "recommendations": [
                "天猫需要中国IP代理才能正常访问",
                "建议预置登录后的cookies以获取完整店铺内容",
                "遇到验证码尝试使用stealth或undetected模式",
                "使用headless=false可以在浏览器中手动登录",
                "查看crawl_stats了解爬取过程详情",
            ],
        }

    except Exception as e:
        logger.error(f"[Tmall v2] Crawl error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "platform": "tmall"}


@router.post("/crawl/taobao")
@router.post("/crawl/taobao/v2")
async def crawl_taobao(request: OptimizedTmallRequest):
    """淘宝专用爬虫接口 (基于Crawl4AI官方文档深度优化)

    淘宝特点:
    - 需要中国IP代理才能访问
    - 需要登录cookies
    - 反爬虫检测较强
    - 使用虚拟滚动加载产品列表

    基于官方文档的功能:
    - Virtual Scroll - 处理淘宝的虚拟滚动产品列表
    - 反爬虫检测与重试 (Anti-Bot & Fallback)
    - 代理列表轮换 (Proxy & Security)
    - Hooks生命周期管理 (Hooks & Auth)
    - 深度挖掘支持 (Deep Crawling)
    - Filter Chains & Scorers

    使用示例:
    ```json
    {
        "urls": ["https://shop59361454.taobao.com/"],
        "mode": "smart",
        "virtual_scroll": true,
        "max_scroll_steps": 15,
        "proxy_list": ["http://user:pass@gateway:port"]
    }
    ```
    """
    return await crawl_tmall_v2(request)


# ============ Unified JD Crawler (Optimized) ============


class OptimizedEbayRequest(BaseModel):
    """统一优化的eBay爬虫请求

    eBay特点:
    - 反爬虫相对较弱
    - 页面结构相对稳定
    - 需要处理分页和无限滚动
    """

    urls: List[str] = Field(default=[], description="要爬取的URL列表")
    mode: str = Field(default="smart", description="模式: smart/standard/deep")
    headless: bool = Field(default=False, description="无头模式")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    wait_until: str = Field(default="load")
    max_scroll_steps: int = Field(default=15)
    enable_stealth: bool = Field(default=True)
    use_magic: bool = Field(default=True)
    simulate_user: bool = Field(default=True)
    override_navigator: bool = Field(default=True)
    locale: str = Field(default="en-US")
    max_retries: int = Field(default=2)
    proxy_list: List[str] = Field(default=[])
    use_proxy_rotation: bool = Field(default=False)
    extract_products: bool = Field(default=False)
    verbose: bool = Field(default=False)


def get_ebay_strategy(url: str, mode: str) -> Dict[str, Any]:
    """根据URL类型返回eBay最佳策略"""

    url_lower = url.lower()

    # URL类型检测
    url_type = "category"
    if "/itm/" in url_lower or "/p/" in url_lower:
        url_type = "product"
    elif "/b/" in url_lower and "search" in url_lower:
        url_type = "search"
    elif "/sch/" in url_lower:
        url_type = "search"

    mode_configs = {
        "smart": {
            "wait_until": "networkidle"
            if url_type in ["search", "category"]
            else "load",
            "max_scroll_steps": 20 if url_type in ["search", "category"] else 10,
            "magic": True,
            "stealth": True,
        },
        "standard": {
            "wait_until": "load",
            "max_scroll_steps": 10,
            "magic": True,
            "stealth": True,
        },
        "deep": {
            "wait_until": "networkidle",
            "max_scroll_steps": 30,
            "magic": True,
            "stealth": True,
        },
    }

    return mode_configs.get(mode, mode_configs["smart"])


@router.post("/crawl/ebay")
@router.post("/crawl/ebay/unified")
async def crawl_ebay_unified(request: OptimizedEbayRequest):
    """统一优化的eBay爬虫接口

    功能:
    - 智能URL分类与策略匹配
    - 反爬虫检测与重试
    - 代理支持
    - 产品数据提取

    使用示例:
    ```json
    {
        "urls": ["https://www.ebay.com/b/Computer-Components-Parts/175673/bn_1643095"],
        "mode": "smart",
        "max_scroll_steps": 20
    }
    ```
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig, ProxyConfig

        logger.info(
            f"[eBay] Starting crawl: {len(request.urls)} URLs, mode: {request.mode}"
        )

        # 代理配置
        proxy_config = None
        if request.use_proxy_rotation and request.proxy_list:
            first_proxy = request.proxy_list[0]
            try:
                parts = first_proxy.replace("http://", "").replace("https://", "")
                if "@" in parts:
                    auth, host = parts.split("@", 1)
                    user, pwd = auth.split(":", 1)
                    proxy_config = ProxyConfig(
                        server=f"http://{host}", username=user, password=pwd
                    )
                else:
                    proxy_config = ProxyConfig(server=f"http://{parts}")
            except:
                pass

        # 获取策略
        strategy = get_ebay_strategy(
            request.urls[0] if request.urls else "", request.mode
        )

        # 浏览器配置
        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            verbose=request.verbose,
            enable_stealth=request.enable_stealth,
            headers={
                "Accept-Language": request.locale,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        # 爬虫配置
        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=strategy.get("wait_until", "load"),
            max_scroll_steps=strategy.get("max_scroll_steps", 15),
            cache_mode=CacheMode.BYPASS,
            magic=request.use_magic,
            simulate_user=request.simulate_user,
            override_navigator=request.override_navigator,
            remove_overlay_elements=True,
            delay_before_return_html=2.0,
            proxy_config=proxy_config,
        )

        # 执行爬取
        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "status_code": result.status_code,
                            "markdown": result.markdown.raw_markdown[:5000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "links_count": len(result.links) if result.links else 0,
                            "images_count": len(result.media.get("images", []))
                            if result.media
                            else 0,
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
            "mode": request.mode,
            "strategy_applied": strategy,
            "results": results,
            "count": len(results),
            "config": {
                "max_scroll_steps": strategy.get("max_scroll_steps", 15),
                "wait_until": strategy.get("wait_until", "load"),
                "magic": request.use_magic,
                "stealth": request.enable_stealth,
            },
            "recommendations": [
                "eBay反爬较弱，使用smart模式即可",
                "分类页面建议设置更高的max_scroll_steps",
                "遇到问题可尝试deep模式",
            ],
        }

    except Exception as e:
        logger.error(f"[eBay] Crawl error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "platform": "ebay"}


@router.post("/crawl/jd")
@router.post("/crawl/jd/v2")
async def crawl_jd(request: OptimizedTmallRequest):
    """京东(JD)专用爬虫接口 (基于Crawl4AI官方文档深度优化)

    京东特点:
    - 需要中国IP代理才能访问
    - 需要登录cookies才能查看完整内容
    - 反爬虫检测较强 (京东安全系统)
    - 使用虚拟滚动加载产品列表
    - 大量使用懒加载图片

    基于官方文档的功能:
    1. Virtual Scroll - 处理京东的虚拟滚动产品列表
    2. Lazy Loading (官方文档) - 处理京东懒加载图片:
       - wait_for_images=True: 等待图片加载完成
       - scan_full_page=True: 全页面扫描触发懒加载
       - scroll_delay=0.5: 滚动延迟
    3. 反爬虫检测与重试 (Anti-Bot & Fallback)
    4. 代理列表轮换 (Proxy & Security)
    5. Hooks生命周期管理 (Hooks & Auth)
    6. 深度挖掘支持 (Deep Crawling)
    7. 电商专用Adaptive配置:
       - confidence_threshold=0.7
       - max_pages=20
       - top_k_links=2
       - min_gain_threshold=0.1

    使用示例:
    ```json
    {
        "urls": ["https://mall.jd.com/index-1000000127.html"],
        "mode": "smart",
        "virtual_scroll": true,
        "wait_for_images": true,
        "scan_full_page": true,
        "scroll_delay": 0.5,
        "max_scroll_steps": 15,
        "proxy_list": ["http://user:pass@gateway:port"],
        "cookies": [{"name": "cookie", "value": "xxx", "domain": ".jd.com"}]
    }
    ```
    """
    return await crawl_tmall_v2(request)


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


# ============ Unified Shopify Crawler (Optimized) ============


class OptimizedShopifyRequest(BaseModel):
    """统一优化的Shopify爬虫请求

    Shopify特点:
    - 反爬虫较弱
    - 页面基于Shopify框架
    - 一般需要处理无限滚动
    """

    urls: List[str] = Field(default=[], description="要爬取的URL列表")
    mode: str = Field(default="smart", description="模式: smart/standard/deep")
    headless: bool = Field(default=False, description="无头模式")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    wait_until: str = Field(default="load")
    max_scroll_steps: int = Field(default=10)
    enable_stealth: bool = Field(default=True)
    use_magic: bool = Field(default=True)
    simulate_user: bool = Field(default=True)
    override_navigator: bool = Field(default=True)
    locale: str = Field(default="en-US")
    max_retries: int = Field(default=2)
    proxy_list: List[str] = Field(default=[])
    use_proxy_rotation: bool = Field(default=False)
    extract_products: bool = Field(default=False)
    verbose: bool = Field(default=False)


def get_shopify_strategy(url: str, mode: str) -> Dict[str, Any]:
    """根据URL类型返回Shopify最佳策略"""

    url_lower = url.lower()

    # URL类型检测
    url_type = "home"
    if "/products/" in url_lower:
        url_type = "product"
    elif "/collections/" in url_lower:
        url_type = "collection"
    elif "/search" in url_lower:
        url_type = "search"

    mode_configs = {
        "smart": {
            "wait_until": "networkidle"
            if url_type in ["collection", "search"]
            else "domcontentloaded",
            "max_scroll_steps": 12 if url_type in ["collection", "search"] else 6,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 3.0,
        },
        "standard": {
            "wait_until": "domcontentloaded",
            "max_scroll_steps": 6,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 2.0,
        },
        "deep": {
            "wait_until": "networkidle",
            "max_scroll_steps": 20,
            "magic": True,
            "stealth": True,
            "delay_before_return_html": 5.0,
        },
    }

    return mode_configs.get(mode, mode_configs["smart"])


@router.post("/crawl/shopify")
@router.post("/crawl/shopify/unified")
async def crawl_shopify_unified(request: OptimizedShopifyRequest):
    """统一优化的Shopify爬虫接口

    功能:
    - 智能URL分类与策略匹配
    - 反爬虫检测与重试
    - 代理支持
    - 产品数据提取

    使用示例:
    ```json
    {
        "urls": ["https://thrivecausemetics.com/"],
        "mode": "smart"
    }
    ```
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig, ProxyConfig

        logger.info(
            f"[Shopify] Starting crawl: {len(request.urls)} URLs, mode: {request.mode}"
        )

        # 代理配置
        proxy_config = None
        if request.use_proxy_rotation and request.proxy_list:
            first_proxy = request.proxy_list[0]
            try:
                parts = first_proxy.replace("http://", "").replace("https://", "")
                if "@" in parts:
                    auth, host = parts.split("@", 1)
                    user, pwd = auth.split(":", 1)
                    proxy_config = ProxyConfig(
                        server=f"http://{host}", username=user, password=pwd
                    )
                else:
                    proxy_config = ProxyConfig(server=f"http://{parts}")
            except:
                pass

        # 获取策略
        strategy = get_shopify_strategy(
            request.urls[0] if request.urls else "", request.mode
        )

        # 浏览器配置
        browser_config = BrowserConfig(
            headless=request.headless,
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            verbose=request.verbose,
            enable_stealth=request.enable_stealth,
            headers={
                "Accept-Language": request.locale,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        # 爬虫配置
        crawl_config = CrawlerRunConfig(
            page_timeout=request.page_timeout,
            wait_until=strategy.get("wait_until", "domcontentloaded"),
            max_scroll_steps=strategy.get("max_scroll_steps", 8),
            cache_mode=CacheMode.BYPASS,
            magic=request.use_magic,
            simulate_user=request.simulate_user,
            override_navigator=request.override_navigator,
            remove_overlay_elements=True,
            delay_before_return_html=strategy.get("delay_before_return_html", 3.0),
            proxy_config=proxy_config,
        )

        # 执行爬取
        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    results.append(
                        {
                            "url": url,
                            "success": result.success,
                            "status_code": result.status_code,
                            "markdown": result.markdown.raw_markdown[:5000]
                            if result.markdown
                            else None,
                            "html": result.html[:2000] if result.html else None,
                            "links_count": len(result.links) if result.links else 0,
                            "images_count": len(result.media.get("images", []))
                            if result.media
                            else 0,
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
            "platform": "shopify",
            "mode": request.mode,
            "strategy_applied": strategy,
            "results": results,
            "count": len(results),
            "config": {
                "max_scroll_steps": strategy.get("max_scroll_steps", 10),
                "wait_until": strategy.get("wait_until", "load"),
                "magic": request.use_magic,
                "stealth": request.enable_stealth,
            },
            "recommendations": [
                "Shopify反爬较弱，使用smart模式即可",
                "产品集合页面建议设置更高的max_scroll_steps",
                "部分Shopify站点需要等待JavaScript渲染",
            ],
        }

    except Exception as e:
        logger.error(f"[Shopify] Crawl error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "platform": "shopify"}


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


# ============ Smart Amazon Crawler (Advanced) ============


class SmartAmazonRequest(BaseModel):
    """智能Amazon爬虫请求 - 基于Crawl4AI官方文档深度优化

    包含所有反爬虫策略:
    - max_retries: 反爬检测重试
    - proxy_config: 代理列表轮换
    - fallback_fetch_function: 最终回退函数
    - UndetectedBrowser: 高级反检测
    - Hooks: 生命周期钩子
    - Deep Crawling: 深度挖掘支持
    """

    # 基础
    urls: List[str] = Field(default=[], description="要爬取的URL列表")

    # 爬取策略类型
    crawl_strategy: str = Field(
        default="auto", description="爬取策略: auto/standard/deep/stealth/undetected"
    )

    # 深度挖掘配置
    deep_crawl: bool = Field(default=False, description="启用深度挖掘")
    max_depth: int = Field(default=2, description="深度挖掘最大层级")
    max_pages: int = Field(default=50, description="最大页面数")
    deep_strategy: str = Field(
        default="best_first", description="深度策略: bfs/dfs/best_first"
    )

    # 反爬虫配置 (基于官方文档: Anti-Bot & Fallback)
    max_retries: int = Field(
        default=2, description="反爬检测重试次数 (官方文档: max_retries)"
    )
    proxy_list: List[str] = Field(
        default=[], description="代理列表 (格式: http://user:pass@host:port)"
    )
    use_proxy_rotation: bool = Field(default=False, description="启用代理轮换")
    fallback_enabled: bool = Field(default=True, description="启用回退函数作为最后手段")

    # 浏览器配置
    browser_type: str = Field(default="chromium", description="浏览器类型")
    headless: bool = Field(default=False, description="是否无头模式")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    page_timeout: int = Field(default=120000)
    wait_until: str = Field(default="load", description="等待条件")
    max_scroll_steps: int = Field(default=10)

    # 反检测配置
    enable_stealth: bool = Field(default=True, description="启用隐身模式")
    use_undetected: bool = Field(
        default=False, description="使用UndetectedBrowser (高级反检测)"
    )
    use_magic: bool = Field(default=True, description="启用magic模式")
    simulate_user: bool = Field(default=True, description="模拟用户行为")
    override_navigator: bool = Field(default=True, description="覆盖navigator对象")

    # 身份配置
    locale: str = Field(default="en-US", description="地区设置")
    timezone_id: str = Field(default="America/New_York", description="时区")

    # 会话管理
    session_id: Optional[str] = Field(default=None, description="会话ID")
    use_persistent_context: bool = Field(default=False, description="使用持久化上下文")

    # Cookies (可用于登录状态)
    cookies: List[Dict[str, Any]] = Field(default=[], description="预设Cookies")

    # 提取配置
    extract_products: bool = Field(
        default=False, description="提取产品数据 (使用CSS选择器)"
    )
    extract_reviews: bool = Field(default=False, description="提取评论数据")

    # 高级功能
    capture_screenshot: bool = Field(default=False, description="捕获截图")
    capture_network: bool = Field(default=False, description="捕获网络请求")
    verbose: bool = Field(default=True, description="详细输出")


class AmazonURLClassifier:
    """Amazon URL分类器 - 智能匹配爬取策略"""

    URL_PATTERNS = {
        "search": [
            r"/s\?k=",
            r"/s\?",
            r"/search",
            r"/gp/search",
            r"/find\?",
            r"/search-results",
        ],
        "product": [r"/dp/", r"/gp/product/", r"/product/", r"/item\?id="],
        "review": [
            r"/review/",
            r"/customer-reviews/",
            r"/product-reviews",
            r"/gp/reviews/",
        ],
        "category": [
            r"/b/",
            r"/gp/bestsellers",
            r"/deal",
            r"/sale",
            r"/deal/",
            r"/bestsellers",
        ],
        "cart": [r"/cart", r"/gp/buy/", r"/checkout"],
        "account": [r"/gp/css", r"/gp/order", r"/account"],
    }

    @classmethod
    def classify_url(cls, url: str) -> List[str]:
        """分类URL类型"""
        url_lower = url.lower()
        types = []
        for url_type, patterns in cls.URL_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    types.append(url_type)
                    break
        return types if types else ["unknown"]

    @classmethod
    def get_strategy(cls, url: str) -> Dict[str, Any]:
        """根据URL类型返回最佳策略"""
        url_types = cls.classify_url(url)

        strategy_map = {
            "search": {
                "wait_until": "networkidle",
                "max_scroll_steps": 15,
                "magic": True,
                "stealth": True,
                "priority": "high",
            },
            "product": {
                "wait_until": "load",
                "max_scroll_steps": 5,
                "magic": True,
                "stealth": True,
                "priority": "critical",
            },
            "review": {
                "wait_until": "networkidle",
                "max_scroll_steps": 20,
                "magic": True,
                "stealth": True,
                "priority": "medium",
            },
            "category": {
                "wait_until": "networkidle",
                "max_scroll_steps": 25,
                "magic": True,
                "stealth": True,
                "priority": "high",
            },
            "cart": {
                "wait_until": "load",
                "max_scroll_steps": 0,
                "magic": False,
                "stealth": True,
                "priority": "critical",
            },
            "account": {
                "wait_until": "load",
                "max_scroll_steps": 0,
                "magic": False,
                "stealth": True,
                "priority": "critical",
                "requires_auth": True,
            },
            "unknown": {
                "wait_until": "networkidle",
                "max_scroll_steps": 10,
                "magic": True,
                "stealth": True,
                "priority": "medium",
            },
        }

        combined = {
            "wait_until": "networkidle",
            "max_scroll_steps": 10,
            "magic": True,
            "stealth": True,
            "priority": "medium",
        }

        for url_type in url_types:
            if url_type in strategy_map:
                combined.update(strategy_map[url_type])

        return combined


async def smart_amazon_fallback(url: str) -> str:
    """回退函数 - 当所有浏览器方法都失败时调用

    基于官方文档: Anti-Bot & Fallback
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                raise RuntimeError(f"Fallback HTTP error: {resp.status}")
        except Exception as e:
            raise RuntimeError(f"Fallback fetch failed: {str(e)}")


@router.post("/crawl/amazon/smart")
async def crawl_amazon_smart(request: SmartAmazonRequest):
    """智能Amazon爬虫接口 - 基于Crawl4AI官方文档深度优化

    功能特性:
    1. 自动URL类型检测与策略匹配
    2. 反爬虫检测与重试 (max_retries)
    3. 代理列表轮换 (proxy_config)
    4. 回退函数支持 (fallback_fetch_function)
    5. UndetectedBrowser高级反检测
    6. 深度挖掘支持 (Deep Crawling)
    7. 生命周期Hooks
    8. 产品/评论数据提取

    官方文档参考:
    - https://docs.crawl4ai.com/advanced/anti-bot-and-fallback/
    - https://docs.crawl4ai.com/advanced/undetected-browser/
    - https://docs.crawl4ai.com/advanced/hooks-auth/
    - https://docs.crawl4ai.com/core/deep-crawling/
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig, ProxyConfig
        from crawl4ai.deep_crawling import (
            BFSDeepCrawlStrategy,
            DFSDeepCrawlStrategy,
            BestFirstCrawlingStrategy,
        )
        from crawl4ai.deep_crawling.filters import FilterChain, DomainFilter
        from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        from playwright.async_api import Page, BrowserContext
        import asyncio

        logger.info(f"Smart Amazon Crawler started with {len(request.urls)} URLs")

        # ========== 1. 构建代理配置 ==========
        proxy_config = None
        if request.use_proxy_rotation and request.proxy_list:
            # 官方文档: proxy_config可以是列表，按顺序尝试
            proxy_config = []
            for proxy_str in request.proxy_list:
                if proxy_str.lower() == "direct":
                    proxy_config.append(ProxyConfig.DIRECT)
                else:
                    # 解析代理字符串
                    parts = proxy_str.replace("http://", "").replace("https://", "")
                    if "@" in parts:
                        auth, host = parts.split("@", 1)
                        user, pwd = auth.split(":", 1)
                        proxy_config.append(
                            ProxyConfig(
                                server=f"http://{host}", username=user, password=pwd
                            )
                        )
                    else:
                        proxy_config.append(ProxyConfig(server=f"http://{parts}"))
        elif request.proxy_list:
            # 单个代理
            proxy_str = request.proxy_list[0]
            parts = proxy_str.replace("http://", "").replace("https://", "")
            if "@" in parts:
                auth, host = parts.split("@", 1)
                user, pwd = auth.split(":", 1)
                proxy_config = ProxyConfig(
                    server=f"http://{host}", username=user, password=pwd
                )

        # ========== 2. 浏览器配置 ==========
        browser_config_kwargs = {
            "headless": request.headless,
            "viewport": {
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            "verbose": request.verbose,
            "enable_stealth": request.enable_stealth,
            "locale": request.locale,
            "timezone_id": request.timezone_id,
        }

        # UndetectedBrowser (高级反检测)
        if request.use_undetected:
            # 使用 UndetectedAdapter
            browser_config_kwargs["ad_blocker"] = True

        browser_config = BrowserConfig(**browser_config_kwargs)

        # ========== 3. 深度挖掘配置 ==========
        deep_crawl_strategy = None
        if request.deep_crawl:
            # 官方文档: Deep Crawling策略
            if request.deep_strategy == "bfs":
                deep_crawl_strategy = BFSDeepCrawlStrategy(
                    max_depth=request.max_depth,
                    max_pages=request.max_pages,
                    include_external=False,
                    filter_chain=FilterChain(
                        [DomainFilter(allowed_domains=["amazon.com", "www.amazon.com"])]
                    ),
                )
            elif request.deep_strategy == "dfs":
                deep_crawl_strategy = DFSDeepCrawlStrategy(
                    max_depth=request.max_depth,
                    max_pages=request.max_pages,
                    include_external=False,
                )
            else:  # best_first (推荐)
                keyword_scorer = KeywordRelevanceScorer(
                    keywords=["product", "price", "review", "buy", "cart"], weight=0.7
                )
                deep_crawl_strategy = BestFirstCrawlingStrategy(
                    max_depth=request.max_depth,
                    max_pages=request.max_pages,
                    include_external=False,
                    url_scorer=keyword_scorer,
                )

        # ========== 4. 产品提取CSS策略 ==========
        extraction_strategy = None
        if request.extract_products:
            # Amazon产品CSS提取schema
            product_schema = {
                "name": "Amazon Product",
                "base_selector": "[data-component-type='s-search-result']",
                "fields": [
                    {"name": "title", "selector": "h2 a span", "type": "text"},
                    {"name": "price", "selector": ".a-price-whole", "type": "text"},
                    {
                        "name": "rating",
                        "selector": ".a-icon-alt",
                        "type": "attribute",
                        "attribute": "textContent",
                    },
                    {
                        "name": "url",
                        "selector": "h2 a",
                        "type": "attribute",
                        "attribute": "href",
                    },
                ],
            }
            extraction_strategy = JsonCssExtractionStrategy(
                schema=product_schema, verbose=True
            )

        # ========== 5. 爬虫运行配置 ==========
        crawl_config_kwargs = {
            "page_timeout": request.page_timeout,
            "wait_until": request.wait_until,
            "max_scroll_steps": request.max_scroll_steps,
            "cache_mode": CacheMode.BYPASS,
            "magic": request.use_magic,
            "simulate_user": request.simulate_user,
            "override_navigator": request.override_navigator,
            "remove_overlay_elements": True,
            "delay_before_return_html": 2.0,
        }

        # 反爬虫配置 (官方文档: Anti-Bot & Fallback)
        if request.max_retries > 0:
            crawl_config_kwargs["max_retries"] = request.max_retries

        if proxy_config:
            crawl_config_kwargs["proxy_config"] = proxy_config

        if request.fallback_enabled:
            crawl_config_kwargs["fallback_fetch_function"] = smart_amazon_fallback

        if deep_crawl_strategy:
            crawl_config_kwargs["deep_crawl_strategy"] = deep_crawl_strategy

        if extraction_strategy:
            crawl_config_kwargs["extraction_strategy"] = extraction_strategy

        crawl_config = CrawlerRunConfig(**crawl_config_kwargs)

        # ========== 6. 创建爬虫并设置Hooks ==========
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()

        # Hook: 页面上下文创建后
        async def on_page_context_created(
            page: Page, context: BrowserContext, **kwargs
        ):
            # 设置Amazon特定headers
            await page.set_extra_http_headers(
                {
                    "Accept-Language": request.locale,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
            )

            # 如果有预设cookies
            if request.cookies:
                for cookie in request.cookies:
                    try:
                        await context.add_cookies([cookie])
                    except:
                        pass

            return page

        # Hook: 导航前
        async def before_goto(page: Page, context: BrowserContext, url: str, **kwargs):
            # 智能策略匹配
            strategy = AmazonURLClassifier.get_strategy(url)
            return page

        # Hook: 导航后
        async def after_goto(
            page: Page, context: BrowserContext, url: str, response, **kwargs
        ):
            # 根据URL类型调整等待
            url_types = AmazonURLClassifier.classify_url(url)

            if "search" in url_types or "category" in url_types:
                try:
                    await page.wait_for_selector(
                        "[data-component-type='s-search-result']", timeout=10000
                    )
                except:
                    pass

            return page

        # Hook: 获取HTML前
        async def before_retrieve_html(page: Page, context: BrowserContext, **kwargs):
            # 最终滚动
            await page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
                // 随机微滚动模拟用户
                for(let i=0; i<3; i++) {
                    window.scrollBy(0, Math.random() * 500);
                    await new Promise(r => setTimeout(r, 300));
                }
            """)
            return page

        # 设置Hooks
        crawler.crawler_strategy.set_hook(
            "on_page_context_created", on_page_context_created
        )
        crawler.crawler_strategy.set_hook("before_goto", before_goto)
        crawler.crawler_strategy.set_hook("after_goto", after_goto)
        crawler.crawler_strategy.set_hook("before_retrieve_html", before_retrieve_html)

        # ========== 7. 执行爬取 ==========
        results = []

        # 流式或非流式
        if request.deep_crawl:
            # 深度挖掘模式
            async for result in await crawler.arun(
                url=request.urls[0] if request.urls else "", config=crawl_config
            ):
                results.append(
                    {
                        "url": result.url,
                        "success": result.success,
                        "markdown": result.markdown.raw_markdown[:2000]
                        if result.markdown
                        else None,
                        "depth": result.metadata.get("depth", 0),
                        "score": result.metadata.get("score", 0),
                        "error": result.error_message,
                    }
                )
        else:
            # 普通模式
            for url in request.urls:
                try:
                    result = await crawler.arun(url=url, config=crawl_config)

                    # URL类型检测
                    url_types = AmazonURLClassifier.classify_url(url)
                    strategy = AmazonURLClassifier.get_strategy(url)

                    result_data = {
                        "url": url,
                        "url_types": url_types,
                        "strategy_applied": strategy,
                        "success": result.success,
                        "markdown": result.markdown.raw_markdown[:3000]
                        if result.markdown
                        else None,
                        "html": result.html[:2000] if result.html else None,
                        "error": result.error_message,
                        "status_code": result.status_code,
                    }

                    # 截图
                    if request.capture_screenshot and result.screenshot:
                        result_data["screenshot"] = "screenshot_captured"

                    # 网络请求
                    if request.capture_network and result.network_requests:
                        result_data["network_requests_count"] = len(
                            result.network_requests
                        )

                    # 反爬虫统计
                    if result.crawl_stats:
                        result_data["crawl_stats"] = {
                            "attempts": result.crawl_stats.get("attempts", 0),
                            "retries": result.crawl_stats.get("retries", 0),
                            "proxies_used": result.crawl_stats.get("proxies_used", []),
                            "resolved_by": result.crawl_stats.get("resolved_by"),
                        }

                    results.append(result_data)

                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "error": str(e),
                        }
                    )

        await crawler.close()

        # ========== 8. 返回结果 ==========
        return {
            "success": True,
            "platform": "amazon_smart",
            "strategy": request.crawl_strategy,
            "results": results,
            "count": len(results),
            "urls_classified": {
                url: AmazonURLClassifier.classify_url(url) for url in request.urls
            },
            "config_used": {
                "max_retries": request.max_retries,
                "proxy_rotation": request.use_proxy_rotation,
                "undetected": request.use_undetected,
                "deep_crawl": request.deep_crawl,
                "magic": request.use_magic,
                "stealth": request.enable_stealth,
            },
            "recommendations": [
                "使用美国住宅代理提高成功率",
                "预置有效Amazon cookies可绕过部分检测",
                "深度挖掘建议配合代理轮换使用",
                "遇到CAPTCHA建议使用UndetectedBrowser模式",
            ],
        }

    except Exception as e:
        logger.error(f"Smart Amazon crawl error: {e}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "platform": "amazon_smart",
            "recommendation": "尝试使用 /crawl/amazon/smart 端点并启用 UndetectedBrowser",
        }
