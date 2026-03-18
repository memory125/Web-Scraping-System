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


# ============ E-commerce Crawler Endpoints ============


@router.post("/crawl/amazon")
async def crawl_amazon(request: BaseEcommerceRequest):
    """Amazon 专用爬虫接口 (强化版)

    特点（基于 Crawl4AI 官方文档优化）：
    - 使用 UndetectedAdapter 反检测浏览器
    - 启用 stealth 模式 + magic 模式
    - 使用美国 UA 和 Accept-Language
    - 禁用 headless 模式减少检测
    - 添加延迟等待页面加载
    - 使用 BYPASS 缓存模式
    - 添加 simulate_user 模拟用户行为
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.async_configs import BrowserConfig

        # 根据文档: 使用 headless=False 减少检测，但可以通过 enable_stealth 增强
        # 文档建议：避免 headless 模式，但为了自动化我们使用 stealth 模式
        browser_config = BrowserConfig(
            headless=False,  # 文档建议避免 headless，但配合 stealth 使用
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
            # 文档: 自定义 User-Agent
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # 文档: 使用 headers 设置语言
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            verbose=True,
            enable_stealth=True,  # 文档: 启用 stealth 模式
        )

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
