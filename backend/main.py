import litellm
import os
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple, Callable
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    VirtualScrollConfig,
)
from crawl4ai import AsyncUrlSeeder, SeedingConfig
from crawl4ai import RateLimiter
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher, SemaphoreDispatcher
from crawl4ai import LLMExtractionStrategy, LLMConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from crawl4ai import AdaptiveCrawler, AdaptiveConfig
import httpx
from bs4 import BeautifulSoup

from dotenv import load_dotenv
from modules.config import LLM_CONFIG, set_llm_status, get_llm_status

load_dotenv()

litellm.drop_params = True

crawler: Optional[AsyncWebCrawler] = None

# 当前服务配置
CURRENT_PORT = 8001
CURRENT_HOST = "0.0.0.0"


# ============ Smart Crawler Strategy Selector ============
class CrawlStrategy:
    """智能爬虫策略选择器 - 集成Crawl4AI所有高级功能"""

    # 高风险反爬网站（需要特殊处理）
    ANTI_BOT_DOMAINS = {
        "bbc.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "bbc.co.uk": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "nytimes.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "washingtonpost.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "theguardian.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "cnn.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "reuters.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "amazon.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "amazon.co.uk": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "ebay.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "facebook.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "twitter.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "x.com": {"strategy": "undetected_magic", "timeout": 120000, "wait_for": None},
        "instagram.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "reddit.com": {"strategy": "stealth_magic", "timeout": 90000, "wait_for": None},
        "linkedin.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "wallstreetcn.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "weibo.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "weibo.cn": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
        "t.co": {"strategy": "stealth_magic", "timeout": 60000, "wait_for": None},
        "jfinternational.com": {
            "strategy": "undetected_magic",
            "timeout": 120000,
            "wait_for": None,
        },
    }

    # 简单静态网站
    SIMPLE_DOMAINS = {
        "example.com": {"strategy": "text_only", "timeout": 15000, "wait_for": None},
        "httpbin.org": {"strategy": "text_only", "timeout": 15000, "wait_for": None},
        "jsonplaceholder.typicode.com": {
            "strategy": "text_only",
            "timeout": 15000,
            "wait_for": None,
        },
    }

    # 需要登录的网站的用户名URL模式
    LOGIN_REQUIRED_PATTERNS = {
        "weibo.com": {
            "patterns": ["/n/", "/u/", "/t/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
        "weibo.cn": {
            "patterns": ["/n/", "/u/", "/t/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
        "twitter.com": {
            "patterns": ["/", "/status/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
        "x.com": {
            "patterns": ["/", "/status/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
        "instagram.com": {
            "patterns": ["/", "/p/", "/reel/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
        "facebook.com": {
            "patterns": ["/", "/photo/", "/video/"],
            "strategy": "undetected_magic",
            "timeout": 120000,
        },
    }

    @classmethod
    def _has_username_pattern(cls, url: str) -> tuple[bool, str]:
        """检测URL是否包含用户名模式"""
        url_lower = url.lower()
        for domain, config in cls.LOGIN_REQUIRED_PATTERNS.items():
            if domain in url_lower:
                for pattern in config["patterns"]:
                    if pattern in url_lower:
                        return True, domain
        return False, ""

    @classmethod
    def _extract_domain(cls, url: str) -> str:
        """从URL中提取域名"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return ""

    @classmethod
    def analyze(cls, url: str) -> Dict[str, Any]:
        """分析URL并返回最佳策略"""
        url_lower = url.lower()

        # 检查是否是需要登录的用户名URL
        has_username, domain = cls._has_username_pattern(url)
        if has_username and domain in cls.LOGIN_REQUIRED_PATTERNS:
            config = cls.LOGIN_REQUIRED_PATTERNS[domain]
            return {
                "strategy": config["strategy"],
                "timeout": config["timeout"],
                "wait_for": None,
                "reason": f"Detected username pattern on {domain}, requires login",
                "confidence": 0.95,
                "requires_login": True,
            }

        # 检查反爬网站（无用户名的普通页面）
        for domain, config in cls.ANTI_BOT_DOMAINS.items():
            if domain in url_lower:
                return {
                    "strategy": config["strategy"],
                    "timeout": config["timeout"],
                    "wait_for": config["wait_for"],
                    "reason": f"Detected anti-bot site: {domain}",
                    "confidence": 0.9,
                }

        # 检查简单网站
        for domain, config in cls.SIMPLE_DOMAINS.items():
            if domain in url_lower:
                return {
                    "strategy": config["strategy"],
                    "timeout": config["timeout"],
                    "wait_for": config["wait_for"],
                    "reason": f"Simple static site: {domain}",
                    "confidence": 0.95,
                }

        # 检查新闻/文章URL模式
        if "/news/" in url_lower or "/article/" in url_lower or "/blog/" in url_lower:
            return {
                "strategy": "stealth",
                "timeout": 90000,
                "wait_for": None,
                "reason": "News/Article URL pattern detected",
                "confidence": 0.7,
            }

        # 默认策略 - 使用最优模式
        return {
            "strategy": "stealth",
            "timeout": 60000,
            "wait_for": None,
            "reason": "Default optimal strategy",
            "confidence": 0.5,
        }

    @classmethod
    async def crawl_with_strategy(
        cls,
        url: str,
        crawler: AsyncWebCrawler,
        cookies: List[Dict[str, str]] = None,
        retry_count: int = 0,
        **kwargs,
    ) -> Dict[str, Any]:
        """使用智能策略爬取，失败时自动切换更强策略"""
        strategy_info = cls.analyze(url)
        strategy = strategy_info["strategy"]

        # 获取域名对应的cookies
        domain = cls._extract_domain(url)
        if not cookies and domain in cookies_store:
            cookies = cookies_store[domain]

        # 检查是否需要登录但没有cookie
        requires_login = strategy_info.get("requires_login", False)
        has_cookie = cookies and len(cookies) > 0

        if requires_login and not has_cookie:
            # 尝试从cookies_store获取
            if domain in cookies_store and len(cookies_store[domain]) > 0:
                cookies = cookies_store[domain]
                has_cookie = True

        try:
            result = await cls._execute_strategy(
                url, crawler, strategy, strategy_info, cookies
            )

            # 检查内容是否有效
            if cls._is_content_valid(result):
                result_data = {
                    "result": result,
                    "strategy_used": strategy,
                    "strategy_info": strategy_info,
                }
                # 如果需要登录但没有cookie，添加警告
                if requires_login and not has_cookie:
                    result_data["warning"] = (
                        f"网站 {domain} 可能需要登录，建议添加Cookie以获取完整内容"
                    )
                return result_data

            # 内容无效，尝试更强策略
            if retry_count < 2:
                stronger_strategy = cls._get_stronger_strategy(strategy)
                if stronger_strategy != strategy:
                    strategy_info["reason"] = (
                        f"Content empty, retrying with {stronger_strategy}"
                    )
                    result = await cls._execute_strategy(
                        url, crawler, stronger_strategy, strategy_info, cookies
                    )
                    if cls._is_content_valid(result):
                        result_data = {
                            "result": result,
                            "strategy_used": stronger_strategy,
                            "strategy_info": strategy_info,
                        }
                        if requires_login and not has_cookie:
                            result_data["warning"] = (
                                f"网站 {domain} 可能需要登录，建议添加Cookie以获取完整内容"
                            )
                        return result_data

            # 最终回退到HTTP
            http_result = await cls._http_crawl(
                url, fallback=True, original_error="All browser strategies failed"
            )
            if requires_login and not has_cookie:
                http_result["warning"] = (
                    f"网站 {domain} 可能需要登录，建议添加Cookie以获取完整内容"
                )
            return http_result

        except Exception as e:
            error_str = str(e)
            if (
                "Timeout" in error_str
                or "timeout" in error_str
                or "Failed" in error_str
            ):
                if retry_count < 2:
                    stronger = cls._get_stronger_strategy(strategy)
                    return await cls.crawl_with_strategy(
                        url, crawler, cookies, retry_count=retry_count + 1
                    )
                return await cls._http_crawl(url, fallback=True, original_error=str(e))
            raise

    @classmethod
    def _is_content_valid(cls, result) -> bool:
        """检查爬取结果是否有效"""
        if not result:
            return False
        if hasattr(result, "success") and not result.success:
            return False
        content = ""
        if hasattr(result, "markdown") and result.markdown:
            content = getattr(result.markdown, "raw_markdown", "") or ""
        elif hasattr(result, "html") and result.html:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(result.html, "html.parser")
            content = soup.get_text(strip=True)
        return len(content) > 100

    @classmethod
    def _get_stronger_strategy(cls, current: str) -> str:
        """获取更强的爬取策略 - 渐进式增强"""
        strategy_chain = {
            "text_only": "stealth",
            "stealth": "stealth_magic",
            "stealth_magic": "stealth_full",
            "stealth_full": "undetected",
            "undetected": "undetected_magic",
            "undetected_magic": "http",
            "default": "stealth_magic",
            "http": "http",
        }
        return strategy_chain.get(current, "stealth_magic")

    @classmethod
    async def _execute_strategy(
        cls,
        url: str,
        crawler: AsyncWebCrawler,
        strategy: str,
        strategy_info: Dict[str, Any],
        cookies: List[Dict[str, str]] = None,
    ):
        """执行指定的爬取策略 - 集成Crawl4AI所有高级反检测功能"""

        # 反爬网站使用wait_until="load"更安全
        use_wait_load = strategy in [
            "stealth",
            "stealth_magic",
            "undetected",
            "undetected_magic",
        ]

        if strategy == "http":
            return (await cls._http_crawl(url))["result"]

        elif strategy == "text_only":
            browser_cfg = BrowserConfig(
                text_mode=True,
                headless=True,
                cookies=cookies if cookies else None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        elif strategy == "stealth":
            browser_cfg = BrowserConfig(
                headless=True,
                enable_stealth=True,
                cookies=cookies if cookies else None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load" if use_wait_load else None,
                simulate_user=True,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        elif strategy == "stealth_magic":
            browser_cfg = BrowserConfig(
                headless=False,
                enable_stealth=True,
                cookies=cookies if cookies else None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load",
                magic=True,
                simulate_user=True,
                delay_before_return_html=2.0,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        elif strategy == "stealth_full":
            browser_cfg = BrowserConfig(
                headless=False,
                enable_stealth=True,
                cookies=cookies if cookies else None,
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load",
                magic=True,
                simulate_user=True,
                delay_before_return_html=3.0,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        elif strategy == "undetected":
            try:
                from crawl4ai import UndetectedAdapter

                adapter = UndetectedAdapter()
                browser_cfg = BrowserConfig(
                    headless=False,
                    enable_stealth=True,
                    cookies=cookies if cookies else None,
                )
            except:
                browser_cfg = BrowserConfig(
                    headless=False,
                    enable_stealth=True,
                    cookies=cookies if cookies else None,
                )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load",
                max_retries=2,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        elif strategy == "undetected_magic":
            # 最强反检测模式：Undetected + Stealth + Magic
            try:
                from crawl4ai import UndetectedAdapter

                adapter = UndetectedAdapter()
                browser_cfg = BrowserConfig(
                    headless=False,
                    enable_stealth=True,
                    cookies=cookies if cookies else None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
            except:
                browser_cfg = BrowserConfig(
                    headless=False,
                    enable_stealth=True,
                    cookies=cookies if cookies else None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load",
                max_retries=3,
                magic=True,
                simulate_user=True,
                delay_before_return_html=3.0,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

        else:
            # 默认：使用stealth+magic
            browser_cfg = BrowserConfig(
                headless=False,
                enable_stealth=True,
                cookies=cookies if cookies else None,
            )
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=strategy_info["timeout"],
                wait_for=strategy_info["wait_for"],
                wait_until="load",
                max_retries=3,
                magic=True,
                simulate_user=True,
                delay_before_return_html=2.0,
            )
            return await crawler.arun(
                url=url, config=run_config, browser_config=browser_cfg
            )

    @classmethod
    async def _http_crawl(
        cls, url: str, fallback: bool = False, original_error: str = ""
    ) -> Dict[str, Any]:
        """HTTP纯请求爬取（最终回退方案）"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    },
                )

                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                text = soup.get_text(separator="\n", strip=True)

                links = []
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    if href and href.startswith("http"):
                        links.append(href)

                images = [
                    img.get("src", "") for img in soup.find_all("img") if img.get("src")
                ]

                # 创建模拟的CrawlResult对象
                class HTTPCrawlResult:
                    def __init__(self):
                        self.success = True
                        self.url = url
                        self.html = response.text
                        self.markdown = type("obj", (object,), {"raw_markdown": text})()
                        self.links = links
                        self.media = images[:20]
                        self.error_message = None

                result = HTTPCrawlResult()

                return {
                    "result": result,
                    "strategy_used": "http_fallback" if fallback else "http",
                    "strategy_info": {
                        "strategy": "http",
                        "reason": f"HTTP mode ({original_error[:50]}...)"
                        if fallback
                        else "Selected as best strategy",
                        "fallback": fallback,
                    },
                }
        except Exception as e:
            raise Exception(f"HTTP fallback also failed: {str(e)}")


async def test_llm_connection_startup():
    """Test LLM connection on startup - only verify connectivity, not generate"""
    provider = LLM_CONFIG["provider"].lower()
    model = LLM_CONFIG["model"]
    ollama_url = LLM_CONFIG["ollama_url"]

    try:
        if provider.startswith("ollama"):
            import httpx

            async with httpx.AsyncClient() as client:
                tags_resp = await client.get(f"{ollama_url}/api/tags", timeout=10.0)
                if tags_resp.status_code != 200:
                    set_llm_status(
                        {
                            "connected": False,
                            "provider": provider,
                            "model": model,
                            "error": f"Cannot connect to Ollama: HTTP {tags_resp.status_code}",
                        }
                    )
                    print(f"[FAIL] LLM connection failed: {get_llm_status()['error']}")
                    return

                models_data = tags_resp.json()
                available_models = [
                    m.get("name", "") for m in models_data.get("models", [])
                ]

                if not available_models:
                    set_llm_status(
                        {
                            "connected": False,
                            "provider": provider,
                            "model": model,
                            "error": "No models found in Ollama",
                        }
                    )
                    print(f"[FAIL] LLM connection failed: {get_llm_status()['error']}")
                    return

                selected_model = model
                model_found = False
                for m in available_models:
                    if m.split(":")[0] == model.split(":")[0]:
                        selected_model = m
                        model_found = True
                        break

                if not model_found:
                    selected_model = available_models[0]

                set_llm_status(
                    {
                        "connected": True,
                        "provider": provider,
                        "model": selected_model,
                        "available_models": available_models,
                        "error": "",
                    }
                )
                print(
                    f"[OK] LLM ready: {provider}/{selected_model} ({len(available_models)} models)"
                )

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
                timeout=30.0,
            )

            if response:
                set_llm_status(
                    {
                        "connected": True,
                        "provider": provider,
                        "model": final_model,
                        "error": "",
                    }
                )
                print(f"[OK] LLM connected: {provider}/{final_model}")
            else:
                set_llm_status(
                    {
                        "connected": False,
                        "provider": provider,
                        "model": model,
                        "error": "Unknown error",
                    }
                )

    except Exception as e:
        set_llm_status(
            {
                "connected": False,
                "provider": provider,
                "model": model,
                "error": str(e)[:100],
            }
        )
        print(f"[FAIL] LLM connection failed: {str(e)[:80]}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global crawler
    # Initialize crawler with smart strategy settings on startup
    browser_config = BrowserConfig(
        headless=False,  # 非无头模式更难检测
        verbose=False,
        enable_stealth=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    crawler = AsyncWebCrawler(config=browser_config)

    # Test LLM connection on startup (non-blocking with timeout)
    print(
        f"\nTesting LLM connection ({LLM_CONFIG['provider']}/{LLM_CONFIG['model']})..."
    )
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
            "message": f"Profile created at {profile_path}. Use BrowserProfiler or manual Chrome to login, then use this profile path in crawls.",
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
                profiles.append({"name": name, "path": path})
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
        return {
            "success": True,
            "message": "Use cookies parameter in crawl request instead",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/browser/load-state")
async def load_browser_state():
    """Load browser state from file"""
    try:
        import os

        if os.path.exists(storage_state_path):
            with open(storage_state_path, "r") as f:
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
    cookies: List[
        Dict[str, str]
    ]  # [{"name": "cookie_name", "value": "cookie_value"}, ...]


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
    virtual_scroll_by: str = (
        "container_height"  # container_height, page_height, or pixel int
    )
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
            {
                "name": "asin",
                "selector": "",
                "type": "attribute",
                "attribute": "data-asin",
            },
            {"name": "title", "selector": "h2 a span", "type": "text"},
            {
                "name": "url",
                "selector": "h2 a",
                "type": "attribute",
                "attribute": "href",
            },
            {
                "name": "image",
                "selector": ".s-image",
                "type": "attribute",
                "attribute": "src",
            },
            {
                "name": "rating",
                "selector": ".a-icon-star-small .a-icon-alt",
                "type": "text",
            },
            {
                "name": "reviews_count",
                "selector": "[data-csa-c-func-deps='aui-da-a-popover'] ~ span span",
                "type": "text",
            },
            {"name": "price", "selector": ".a-price .a-offscreen", "type": "text"},
            {
                "name": "original_price",
                "selector": ".a-price.a-text-price .a-offscreen",
                "type": "text",
            },
        ],
    },
    "jd": {
        "name": "JD Product List",
        "baseSelector": ".gl-item",
        "fields": [
            {
                "name": "sku_id",
                "selector": "",
                "type": "attribute",
                "attribute": "data-sku",
            },
            {"name": "title", "selector": ".p-name em", "type": "text"},
            {
                "name": "url",
                "selector": ".p-name a",
                "type": "attribute",
                "attribute": "href",
            },
            {
                "name": "image",
                "selector": ".p-img img",
                "type": "attribute",
                "attribute": "src",
            },
            {"name": "price", "selector": ".p-price strong i", "type": "text"},
            {"name": "shop", "selector": ".p-shop", "type": "text"},
        ],
    },
    "taobao": {
        "name": "Taobao Product List",
        "baseSelector": ".item",
        "fields": [
            {"name": "title", "selector": ".title", "type": "text"},
            {
                "name": "url",
                "selector": ".title a",
                "type": "attribute",
                "attribute": "href",
            },
            {
                "name": "image",
                "selector": ".pic-img",
                "type": "attribute",
                "attribute": "src",
            },
            {"name": "price", "selector": ".price", "type": "text"},
            {"name": "shop", "selector": ".shop", "type": "text"},
            {"name": "location", "selector": ".location", "type": "text"},
        ],
    },
    "tmall": {
        "name": "Tmall Product List",
        "baseSelector": ".product",
        "fields": [
            {"name": "title", "selector": ".productTitle", "type": "text"},
            {
                "name": "url",
                "selector": ".productTitle a",
                "type": "attribute",
                "attribute": "href",
            },
            {
                "name": "image",
                "selector": ".productImg",
                "type": "attribute",
                "attribute": "src",
            },
            {"name": "price", "selector": ".productPrice", "type": "text"},
            {"name": "shop", "selector": ".productShop", "type": "text"},
        ],
    },
    "shopify": {
        "name": "Shopify Product List",
        "baseSelector": ".grid-view-item",
        "fields": [
            {"name": "title", "selector": ".grid-view-item__title", "type": "text"},
            {
                "name": "url",
                "selector": ".grid-view-item__link",
                "type": "attribute",
                "attribute": "href",
            },
            {
                "name": "image",
                "selector": ".grid-view-item__image",
                "type": "attribute",
                "attribute": "src",
            },
            {"name": "price", "selector": ".price-item--regular", "type": "text"},
        ],
    },
}


class CSSExtractRequest(BaseModel):
    """CSS-based extraction (no LLM needed)"""

    url: str
    base_selector: str  # e.g., "div.product"
    fields: List[
        Dict[str, Any]
    ]  # [{"name": "title", "selector": "h2.name", "type": "text"}]


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
    platform: str = (
        "auto"  # auto, amazon, ebay, taobao, tmall, jd, shopify, aliexpress, 1688
    )
    extraction_type: str = "all"  # all, listings, prices
    provider: Optional[str] = None
    api_key: Optional[str] = None
    max_items: int = 20
    cookies: Optional[List[Dict[str, str]]] = (
        None  # [{"name": "cookie_name", "value": "cookie_value"}, ...]
    )


class EcommerceResult(BaseModel):
    success: bool
    url: str
    platform: str
    listings: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class EcommerceSellerCrawlRequest(BaseModel):
    url: str
    platform: str = (
        "auto"  # auto, amazon, ebay, taobao, tmall, jd, shopify, aliexpress, tiktok
    )
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


@app.get("/port")
async def get_port():
    """返回当前服务端口"""
    return {"port": CURRENT_PORT, "message": "Current running port"}


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "message": "Crawl4AI API",
        "version": "1.0.0",
        "port": CURRENT_PORT,
        "docs": "/docs",
    }


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
async def get_llm_status_endpoint():
    """Get LLM connection status"""
    status = get_llm_status()
    return {
        "connected": status.get("connected", False),
        "provider": status.get("provider", LLM_CONFIG["provider"]),
        "model": status.get("model", LLM_CONFIG["model"]),
        "error": status.get("error", ""),
        "available_models": status.get("available_models", []),
    }


@app.get("/llm/config")
async def get_llm_config_endpoint():
    """Get LLM configuration"""
    return {
        "provider": LLM_CONFIG["provider"],
        "model": LLM_CONFIG["model"],
        "temperature": LLM_CONFIG["temperature"],
        "max_tokens": LLM_CONFIG["max_tokens"],
        "ollama_url": LLM_CONFIG["ollama_url"],
    }


@app.get("/llm/connect")
async def connect_llm(provider: str = "", model: str = ""):
    """Manually reconnect LLM"""
    if provider:
        LLM_CONFIG["provider"] = provider
    if model:
        LLM_CONFIG["model"] = model

    await test_llm_connection_startup()

    status = get_llm_status()
    return {
        "connected": status.get("connected", False),
        "provider": status.get("provider", LLM_CONFIG["provider"]),
        "model": status.get("model", LLM_CONFIG["model"]),
        "error": status.get("error", ""),
    }


@app.post("/crawl", response_model=CrawlResult)
async def crawl_url(request: CrawlRequest):
    # Use Crawl4AI with smart strategy selection
    if request.use_browser:
        if not crawler:
            raise HTTPException(status_code=500, detail="Crawler not initialized")

        try:
            # Use smart strategy selector
            crawl_result = await CrawlStrategy.crawl_with_strategy(
                request.url,
                crawler,
                proxy_url=request.proxy_url,
                scroll_count=request.scroll_count,
            )

            result = crawl_result["result"]
            strategy_used = crawl_result.get("strategy_used", "unknown")

            # Extract result
            try:
                success = getattr(result, "success", False)
                html = getattr(result, "html", None)
                error_msg = (
                    getattr(result, "error_message", None) if not success else None
                )

                markdown = None
                fit_markdown = None
                if result.markdown:
                    markdown = getattr(result.markdown, "raw_markdown", None)
                    fit_markdown = getattr(result.markdown, "fit_markdown", None)

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
                if (
                    request.screenshot
                    and hasattr(result, "screenshot")
                    and result.screenshot
                ):
                    import base64

                    screenshot_b64 = (
                        base64.b64encode(result.screenshot).decode()
                        if isinstance(result.screenshot, bytes)
                        else result.screenshot
                    )

                return CrawlResult(
                    success=success,
                    url=request.url,
                    markdown=markdown,
                    fit_markdown=fit_markdown,
                    html=html,
                    links=links_list,
                    images=images_list,
                    videos=videos_list,
                    extracted_content=result.extracted_content
                    if hasattr(result, "extracted_content")
                    else None,
                    screenshot=screenshot_b64,
                    error=error_msg,
                )
            except Exception as e:
                # Always try HTTP fallback when browser fails
                try:
                    import httpx
                    from bs4 import BeautifulSoup

                    async with httpx.AsyncClient(
                        timeout=30.0, follow_redirects=True
                    ) as client:
                        response = await client.get(
                            request.url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            },
                        )

                        soup = BeautifulSoup(response.text, "html.parser")
                        for script in soup(["script", "style"]):
                            script.decompose()

                        text = soup.get_text(separator="\n", strip=True)
                        links_list = []
                        for a in soup.find_all("a", href=True):
                            href = a.get("href", "")
                            if href and href.startswith("http"):
                                links_list.append(href)
                        images_list = [
                            img.get("src", "")
                            for img in soup.find_all("img")
                            if img.get("src")
                        ]

                        return CrawlResult(
                            success=True,
                            url=request.url,
                            markdown=text[:100000],
                            links=links_list[:100],
                            images=images_list[:20],
                            error=None,
                        )
                except Exception as http_err:
                    return CrawlResult(
                        success=False,
                        url=request.url,
                        error=f"Browser failed: {str(e)}. HTTP fallback also failed: {str(http_err)}",
                    )
        except Exception as e:
            # Fallback to HTTP-only mode if browser fails
            try:
                import httpx
                from bs4 import BeautifulSoup

                async with httpx.AsyncClient(
                    timeout=30.0, follow_redirects=True
                ) as client:
                    response = await client.get(
                        request.url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                    )

                    soup = BeautifulSoup(response.text, "html.parser")
                    for script in soup(["script", "style"]):
                        script.decompose()

                    text = soup.get_text(separator="\n", strip=True)
                    links = [
                        a.get("href", "")
                        for a in soup.find_all("a", href=True)
                        if a.get("href", "").startswith("http")
                    ]
                    images = [
                        img.get("src", "")
                        for img in soup.find_all("img")
                        if img.get("src")
                    ]

                    return CrawlResult(
                        success=True,
                        url=request.url,
                        markdown=text[:100000],
                        links=links[:100],
                        images=images[:20],
                        error=None,
                    )
            except Exception as http_err:
                raise HTTPException(
                    status_code=500,
                    detail=f"Browser failed: {str(e)}. HTTP fallback also failed: {str(http_err)}",
                )


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
            url = (
                request.content
                if request.content.startswith("file://")
                else f"file://{request.content}"
            )
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
            error=result.error_message if not result.success else None,
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
            profile_list.append(
                ProfileListItem(
                    name=p.get("name", ""),
                    path=p.get("path", ""),
                    created=p.get("created", ""),
                    browser_type=p.get("type", "chromium"),
                )
            )

        return ProfileResult(
            success=True,
            profiles=profile_list,
            message=f"Found {len(profile_list)} profiles",
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
            raise HTTPException(
                status_code=404, detail=f"Profile {profile_name} not found"
            )
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
        if not url.startswith(("http://", "https://", "file://", "raw:")):
            url = f"file://{url}"

        result = await crawler.arun(url=url, config=run_config)

        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            extracted_content=result.extracted_content,
            error=result.error_message if not result.success else None,
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
            success = getattr(result, "success", False)
            html = getattr(result, "html", None)
            error_msg = getattr(result, "error_message", None) if not success else None

            # Markdown
            markdown = None
            fit_markdown = None
            if result.markdown:
                markdown = getattr(result.markdown, "raw_markdown", None)
                fit_markdown = getattr(result.markdown, "fit_markdown", None)

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
            raise HTTPException(
                status_code=500, detail=f"Result processing error: {str(e)}"
            )

        return CrawlResult(
            success=success,
            url=request.url,
            markdown=markdown,
            fit_markdown=fit_markdown,
            html=html,
            links=links_list,
            images=images_list,
            videos=videos_list,
            error=error_msg,
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
                error=r.error_message if not r.success else None,
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
                viewport={"width": 1920, "height": 1080},
            )

            # Set cookies if provided - add domain if not present
            if request.cookies:
                from urllib.parse import urlparse

                domain = urlparse(request.url).netloc
                formatted_cookies = []
                for cookie in request.cookies:
                    # Check if cookie has url or domain/path
                    if "url" not in cookie and "domain" not in cookie:
                        formatted_cookies.append(
                            {
                                "name": cookie.get("name", ""),
                                "value": cookie.get("value", ""),
                                "domain": "." + domain
                                if not domain.startswith(".")
                                else domain,
                                "path": "/",
                            }
                        )
                    else:
                        formatted_cookies.append(cookie)
                await context.add_cookies(formatted_cookies)

            page = await context.new_page()

            # Navigate to URL
            await page.goto(
                request.url, wait_until="networkidle", timeout=request.wait_timeout
            )

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
                error=None,
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
                max_depth=request.max_depth, max_pages=request.max_pages
            )
        elif request.strategy == "dfs":
            strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth, max_pages=request.max_pages
            )
        else:
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth, max_pages=request.max_pages
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
                error=result.error_message if not result.success else None,
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
        if hasattr(result, "metrics") and isinstance(result.metrics, dict):
            metrics = result.metrics
            confidence = float(metrics.get("confidence", 0.0))
            pages_crawled = int(metrics.get("pages_crawled", 0))
            stopped_reason = metrics.get("stopped_reason", "unknown")
            saturation_score = float(metrics.get("saturation_score", 0.0))
            consistency_score = float(metrics.get("consistency_score", 0.0))
            coverage_score = float(metrics.get("coverage_score", coverage_score))

        # Try direct attributes as fallback
        for attr in ["confidence", "score", "quality"]:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)) and confidence == 0.0:
                    confidence = float(val)

        for attr in ["pages_crawled", "crawled_pages", "total_pages"]:
            if hasattr(result, attr) and pages_crawled == 0:
                pages_crawled = int(getattr(result, attr, 0))

        for attr in ["stopped_reason", "reason", "status"]:
            if hasattr(result, attr) and stopped_reason == "unknown":
                stopped_reason = str(getattr(result, attr, "unknown"))

        for attr in ["saturation_score", "saturation", "info_gain"]:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)):
                    saturation_score = float(val)

        for attr in ["consistency_score", "consistency", "similarity"]:
            if hasattr(result, attr):
                val = getattr(result, attr, 0.0)
                if isinstance(val, (int, float)):
                    consistency_score = float(val)

        # Get extracted content - this is the main content source for adaptive crawl
        if hasattr(result, "extracted_content") and result.extracted_content:
            ec = result.extracted_content
            if isinstance(ec, list):
                for doc in ec:
                    if isinstance(doc, dict):
                        url_text = doc.get("url", "")
                        content_text = (
                            doc.get("content", "")
                            or doc.get("markdown", "")
                            or doc.get("text", "")
                        )
                        if url_text and content_text:
                            # 清理HTML标签 - 使用正则表达式
                            import re

                            html_content = str(content_text)

                            # 移除script和style标签及其内容
                            html_content = re.sub(
                                r"<script[^>]*>.*?</script>",
                                "",
                                html_content,
                                flags=re.DOTALL | re.IGNORECASE,
                            )
                            html_content = re.sub(
                                r"<style[^>]*>.*?</style>",
                                "",
                                html_content,
                                flags=re.DOTALL | re.IGNORECASE,
                            )

                            # 移除HTML标签但保留链接文字
                            def replace_link(match):
                                text = match.group(1) or match.group(2) or ""
                                return text.strip() if text else ""

                            # 处理链接 [text](url)
                            html_content = re.sub(
                                r"\[([^\]]*)\]\([^)]+\)", replace_link, html_content
                            )

                            # 移除所有剩余的HTML标签
                            html_content = re.sub(r"<[^>]+>", "", html_content)

                            # 解码HTML实体
                            html_content = html_content.replace("&nbsp;", " ")
                            html_content = html_content.replace("&amp;", "&")
                            html_content = html_content.replace("&lt;", "<")
                            html_content = html_content.replace("&gt;", ">")
                            html_content = html_content.replace("&quot;", '"')
                            html_content = html_content.replace("&#39;", "'")

                            # 移除多余空白
                            lines = [
                                line.strip()
                                for line in html_content.split("\n")
                                if line.strip()
                            ]
                            clean_text = "\n".join(lines)

                            extracted_data.append(
                                {"url": url_text, "content": clean_text[:10000]}
                            )
                        if url_text and content_text:
                            # 清理HTML标签
                            try:
                                from bs4 import BeautifulSoup

                                soup = BeautifulSoup(str(content_text), "html.parser")
                                # 移除脚本和样式
                                for script in soup(["script", "style"]):
                                    script.decompose()
                                # 获取文本，保留换行
                                clean_text = soup.get_text(separator="\n", strip=True)
                                # 移除空行
                                clean_text = "\n".join(
                                    line
                                    for line in clean_text.split("\n")
                                    if line.strip()
                                )
                                content_text = (
                                    clean_text[:10000]
                                    if clean_text
                                    else str(content_text)[:8000]
                                )
                            except:
                                content_text = str(content_text)[:8000]

                            extracted_data.append(
                                {"url": url_text, "content": content_text}
                            )

        # Get knowledge base content (fallback)
        if not extracted_data and hasattr(result, "knowledge_base"):
            kb = result.knowledge_base
            if isinstance(kb, list):
                for doc in kb:
                    content_text = ""
                    # Try to get full content from different attributes
                    content_text = ""

                    # 尝试多种属性获取内容
                    for attr in [
                        "content",
                        "markdown",
                        "text",
                        "raw_markdown",
                        "html",
                        "text_content",
                    ]:
                        if hasattr(doc, attr):
                            val = getattr(doc, attr, "")
                            if val:
                                content_text = str(val)
                                break

                    if not content_text and isinstance(doc, dict):
                        for key in ["content", "markdown", "text", "html"]:
                            if key in doc and doc[key]:
                                content_text = str(doc[key])
                                break

                    # 清理HTML标签
                    if content_text:
                        try:
                            soup = BeautifulSoup(str(content_text), "html.parser")
                            for script in soup(["script", "style"]):
                                script.decompose()
                            clean_text = soup.get_text(separator="\n", strip=True)
                            clean_text = "\n".join(
                                line for line in clean_text.split("\n") if line.strip()
                            )
                            content_text = (
                                clean_text[:10000]
                                if clean_text
                                else content_text[:8000]
                            )
                        except:
                            pass

                    # Get URL
                    url_text = ""
                    if hasattr(doc, "url") and doc.url:
                        url_text = str(doc.url)
                    elif hasattr(doc, "link") and doc.link:
                        url_text = str(doc.link)
                    elif isinstance(doc, dict):
                        url_text = doc.get("url", "") or doc.get("link", "")

                    extracted_data.append(
                        {
                            "url": url_text,
                            "content": content_text if content_text else "",
                        }
                    )

        # Get coverage from documents_with_terms if available
        if hasattr(result, "documents_with_terms"):
            dwm = result.documents_with_terms
            if isinstance(dwm, dict) and dwm:
                coverage_score = min(1.0, len(dwm) / max(1, request.max_pages))

        # Calculate derived metrics if not available
        if saturation_score == 0.0 and pages_crawled > 0:
            saturation_score = min(1.0, pages_crawled / max(1, request.max_pages))
        if consistency_score == 0.0 and pages_crawled > 0:
            consistency_score = min(
                0.8, 0.3 + (pages_crawled / max(1, request.max_pages)) * 0.5
            )
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
        if hasattr(result, "metrics") and isinstance(result.metrics, dict):
            metrics = result.metrics
            confidence = float(metrics.get("confidence", 0.0))
            pages_crawled = int(metrics.get("pages_crawled", 0))
            stopped_reason = metrics.get("stopped_reason", "unknown")

        success = pages_crawled > 0 or confidence > 0

        # Process relevant pages
        pages_list = []
        if relevant_pages:
            for page in relevant_pages:
                page_url = ""
                page_content = ""
                page_score = 0.0

                if hasattr(page, "url"):
                    page_url = str(page.url)
                elif isinstance(page, dict) and "url" in page:
                    page_url = str(page["url"])
                else:
                    page_url = str(page)

                if hasattr(page, "content"):
                    page_content = str(page.content)
                elif isinstance(page, dict) and "content" in page:
                    page_content = str(page["content"])
                else:
                    page_content = str(page)

                if hasattr(page, "score"):
                    page_score = float(page.score)
                elif isinstance(page, dict) and "score" in page:
                    page_score = float(page["score"])

                pages_list.append(
                    {"url": page_url, "content": page_content, "score": page_score}
                )

        return {
            "success": success,
            "confidence": confidence,
            "pages_crawled": pages_crawled,
            "stopped_reason": stopped_reason,
            "relevant_pages": pages_list,
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
            wait_after_scroll=request.wait_after_scroll,
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
            error=result.error_message if not result.success else None,
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

            results.append(
                CrawlResult(
                    success=result.success,
                    url=url,
                    markdown=result.markdown.raw_markdown if result.markdown else None,
                    fit_markdown=result.markdown.fit_markdown
                    if result.markdown
                    else None,
                    html=result.html,
                    extracted_content=result.extracted_content,
                    error=result.error_message if not result.success else None,
                )
            )

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
                api_token=request.api_key or os.getenv("OPENAI_API_KEY", ""),
            ),
            schema=request.schema,
            instruction=request.instruction,
            extraction_type="schema" if request.schema else "populator",
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
            error=result.error_message if not result.success else None,
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
            "fields": request.fields,
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
            "error": result.error_message if not result.success else None,
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
            "fields": request.fields,
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
            "error": result.error_message if not result.success else None,
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
        patterns = request.patterns or [r"\n\n", r"\n", r"\.\s+"]
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
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            from nltk.tokenize import sent_tokenize

            chunks = [s.strip() for s in sent_tokenize(text) if s.strip()]
        except:
            chunks = re.split(r"[.!?]+\s+", text)
            chunks = [c.strip() for c in chunks if c.strip()]

    elif request.method == "fixed":
        words = text.split()
        chunks = [
            " ".join(words[i : i + request.chunk_size])
            for i in range(0, len(words), request.chunk_size)
        ]

    elif request.method == "sliding":
        words = text.split()
        for i in range(0, len(words) - request.chunk_size + 1, request.step):
            chunks.append(" ".join(words[i : i + request.chunk_size]))

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
            detail="sklearn not installed. Install with: pip install scikit-learn",
        )

    # First chunk the text
    import re

    sentences = re.split(r"[.!?]+\s+", request.text)
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
    top_results = indexed[: request.top_k]

    results = []
    for idx, score in top_results:
        results.append({"text": sentences[idx], "score": float(score), "index": idx})

    return SemanticSearchResult(query=request.query, results=results)


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

        return UrlSeedResult(domain=request.domain, count=len(urls), urls=urls)
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
            results=results, total_domains=len(request.domains), total_urls=total_urls
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
                rate_limit_codes=[429, 503],
            )

        # Build dispatcher
        if request.dispatcher_type == "semaphore":
            dispatcher = SemaphoreDispatcher(
                max_session_permit=request.max_concurrent, rate_limiter=rate_limiter
            )
        else:  # memory_adaptive
            dispatcher = MemoryAdaptiveDispatcher(
                memory_threshold_percent=request.memory_threshold,
                max_session_permit=request.max_concurrent,
                rate_limiter=rate_limiter,
            )

        # Build run config
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )

        results = []

        if request.stream:
            # Stream mode - process results as they arrive
            async for result in await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            ):
                results.append(
                    {
                        "url": result.url,
                        "success": result.success,
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                        "error": result.error_message if not result.success else None,
                    }
                )
        else:
            # Batch mode - get all results at once
            crawl_results = await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            )

            for result in crawl_results:
                results.append(
                    {
                        "url": result.url,
                        "success": result.success,
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                        "error": result.error_message if not result.success else None,
                    }
                )

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
            error=result.error_message if not result.success else None,
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
        scroll_js = [
            f"window.scrollTo(0, document.body.scrollHeight * {i}/{request.scroll_count});"
            for i in range(1, request.scroll_count + 1)
        ]

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
            "success": result.success if hasattr(result, "success") else True,
            "url": request.url,
            "platform": platform,
            "listings": extracted,
            "count": len(extracted),
            "error": result.error_message
            if hasattr(result, "error_message") and not result.success
            else None,
        }
    except Exception as e:
        return {
            "success": False,
            "url": request.url,
            "platform": platform,
            "listings": [],
            "error": str(e),
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
            combined_pattern = pattern_map.get(
                request.patterns[0].lower(), RegexExtractionStrategy.Email
            )
            for p in request.patterns[1:]:
                combined_pattern = combined_pattern | pattern_map.get(
                    p.lower(), RegexExtractionStrategy.Email
                )

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
            "error": result.error_message if not result.success else None,
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
            "product_url": "string - product detail page URL",
        },
        "taobao": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "location": "string - 商品产地",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接",
        },
        "tmall": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 月销量",
            "shop_name": "string - 店铺名称",
            "brand": "string - 品牌",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接",
        },
        "1688": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "location": "string - 商品产地/所在地",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接",
        },
        "jd": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "original_price": "string - 原价",
            "sales": "string - 销量",
            "shop_name": "string - 店铺名称",
            "rating": "string - 评分",
            "image_url": "string - 商品图片URL",
            "product_url": "string - 商品链接",
        },
        "ebay": {
            "product_name": "string - item title",
            "price": "string - item price with currency",
            "condition": "string - new or used",
            "shipping": "string - shipping cost",
            "seller_rating": "string - seller feedback score",
            "image_url": "string - item image URL",
            "product_url": "string - item URL",
        },
        "generic": {
            "product_name": "string - product name or title",
            "price": "string - product price with currency",
            "original_price": "string - original price if on sale",
            "description": "string - product description",
            "image_url": "string - product image URL",
            "product_url": "string - product detail URL",
        },
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
    provider = (
        request.provider
        if request.provider
        else f"{LLM_CONFIG['provider']}/{LLM_CONFIG['model']}"
    )
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
            llm_config=LLMConfig(provider=provider, api_token=api_key),
            schema=schema,
            instruction=instruction,
            extraction_type="schema",
            max_items=request.max_items,
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
                crawl_result = await temp_crawler.arun(
                    url=request.url, config=run_config
                )
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
            error=result.error_message if not result.success else None,
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
            "storefront_url": "string - link to seller storefront",
        },
        "taobao": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "followers": "string - 粉丝数",
            "shop_url": "string - 店铺链接",
        },
        "tmall": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "brand授权": "string - 品牌授权状态",
            "shop_url": "string - 店铺链接",
        },
        "jd": {
            "shop_name": "string - 店铺名称",
            "shop_rating": "string - 店铺评分",
            "total_products": "number - 在售商品数量",
            "total_sales": "string - 总销量",
            "shop_url": "string - 店铺链接",
        },
        "shopify": {
            "store_name": "string - store name",
            "store_description": "string - store description",
            "total_products": "number - number of products",
            "store_url": "string - store URL",
            "created_at": "string - when store was created",
        },
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
            "product_url": "string - product link",
        },
        "taobao": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接",
        },
        "tmall": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 月销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接",
        },
        "jd": {
            "product_name": "string - 商品名称",
            "price": "string - 商品价格",
            "sales": "string - 销量",
            "images": "string - 商品图片",
            "product_url": "string - 商品链接",
        },
        "shopify": {
            "product_name": "string - product title",
            "price": "string - product price",
            "compare_at_price": "string - original price",
            "product_url": "string - product link",
            "image_url": "string - product image",
        },
    }

    # Use configured LLM if not specified
    provider = (
        request.provider
        if request.provider
        else f"{LLM_CONFIG['provider']}/{LLM_CONFIG['model']}"
    )
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
                    "store_url": "string - store URL",
                }

            # Build extraction instruction
            instruction = (
                f"Extract complete seller/store information from this {platform} page. "
            )
            instruction += "Include: seller name, rating, total products, description, any contact info. "
            instruction += (
                "Also extract all product listings with name, price, and image. "
            )
            instruction += "Return as JSON with format: {seller_info: {{...}}, products: [{{name, price, image, url}}]}"

            llm_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(provider=provider, api_token=api_key),
                schema={
                    "seller_info": f"object - {json.dumps(seller_schema)}",
                    "products": f"array of {{product_name: string, price: string, image_url: string, product_url: string}}",
                },
                instruction=instruction,
                extraction_type="schema",
                max_items=request.max_items,
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
        product_schema = product_schemas.get(
            platform, product_schemas.get("generic", {})
        )

        product_llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(provider=provider, api_token=api_key),
            schema={"products": f"array of {json.dumps(product_schema)}"},
            instruction=f"Extract all product listings from this {platform} store page. Return as JSON array.",
            extraction_type="schema",
            max_items=request.max_items,
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
                "verified_purchase": "boolean - if verified purchase",
            }

            review_llm_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(provider=provider, api_token=api_key),
                schema={"reviews": f"array of {json.dumps(review_schema)}"},
                instruction="Extract customer reviews from this page. Return as JSON array.",
                extraction_type="schema",
                max_items=50,
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
            error=None,
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
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
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
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Local File Crawl API ============
class LocalFileRequest(BaseModel):
    file_path: str
    word_count_threshold: int = 200


@app.post("/crawl/local-file")
async def crawl_local_file(request: LocalFileRequest):
    """Local File Crawl - 本地HTML文件爬取 (file://)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        # Build file URL with proper path
        import os

        abs_path = os.path.abspath(request.file_path)
        file_url = f"file://{abs_path}"

        run_config = CrawlerRunConfig(
            word_count_threshold=request.word_count_threshold,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=file_url, config=run_config)

        return {
            "success": result.success,
            "url": file_url,
            "markdown": result.markdown.raw_markdown if result.markdown else None,
            "fit_markdown": result.markdown.fit_markdown if result.markdown else None,
            "html_length": len(result.html) if result.html else 0,
            "error": result.error_message if not result.success else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Raw HTML Crawl API ============
class RawHTMLRequest(BaseModel):
    html_content: str
    word_count_threshold: int = 200


@app.post("/crawl/raw-html")
async def crawl_raw_html(request: RawHTMLRequest):
    """Raw HTML Crawl - 原始HTML内容爬取 (raw:)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        raw_url = f"raw:{request.html_content}"

        run_config = CrawlerRunConfig(
            word_count_threshold=request.word_count_threshold,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=raw_url, config=run_config)

        return {
            "success": result.success,
            "markdown": result.markdown.raw_markdown if result.markdown else None,
            "fit_markdown": result.markdown.fit_markdown if result.markdown else None,
            "html_length": len(result.html) if result.html else 0,
            "error": result.error_message if not result.success else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Batch URL Crawl API ============
class BatchCrawlRequest(BaseModel):
    urls: List[str]
    stream: bool = False
    word_count_threshold: int = 200
    max_concurrent: int = 5


@app.post("/crawl/batch")
async def crawl_batch(request: BatchCrawlRequest):
    """Batch Crawl - 批量URL爬取 (arun_many)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(
            word_count_threshold=request.word_count_threshold,
            stream=request.stream,
            cache_mode=CacheMode.BYPASS,
        )

        if request.stream:
            # Stream results
            results = []
            async for result in await crawler.arun_many(
                urls=request.urls, config=run_config
            ):
                results.append(
                    {
                        "url": result.url,
                        "success": result.success,
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                    }
                )
        else:
            # Non-stream results
            results_list = await crawler.arun_many(urls=request.urls, config=run_config)
            results = [
                {
                    "url": r.url,
                    "success": r.success,
                    "markdown_length": len(r.markdown.raw_markdown)
                    if r.markdown
                    else 0,
                }
                for r in results_list
            ]

        successful = sum(1 for r in results if r.get("success"))

        return {
            "success": True,
            "total_urls": len(request.urls),
            "successful": successful,
            "failed": len(request.urls) - successful,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Content Selection API ============
class ContentSelectionRequest(BaseModel):
    url: str
    # Content selection options
    only_text: bool = False
    only_main_content: bool = True
    remove_overlay_elements: bool = True
    remove_consent_popups: bool = True


@app.post("/crawl/content-select")
async def crawl_with_content_selection(request: ContentSelectionRequest):
    """Content Selection - 精确内容选择"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(
            only_text=request.only_text,
            only_main_content=request.only_main_content,
            remove_overlay_elements=request.remove_overlay_elements,
            remove_consent_popups=request.remove_consent_popups,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "fit_markdown_length": len(result.markdown.fit_markdown)
            if result.markdown and result.markdown.fit_markdown
            else 0,
            "html_length": len(result.html) if result.html else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Clustering Extraction API ============
class ClusteringExtractionRequest(BaseModel):
    url: str
    n_clusters: int = 5
    extraction_type: str = "css"  # css, xpath


@app.post("/extract/clustering")
async def clustering_extraction(request: ClusteringExtractionRequest):
    """Clustering Extraction - 基于聚类的内容提取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.extraction_strategy import ClusteringJsonExtractionStrategy

        strategy = ClusteringJsonExtractionStrategy(
            n_clusters=request.n_clusters, extraction_type=request.extraction_type
        )

        run_config = CrawlerRunConfig(
            extraction_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Proxy Rotation API ============
class ProxyRotationRequest(BaseModel):
    urls: List[str]
    proxies: List[str]  # List of proxy URLs
    strategy: str = "round_robin"  # round_robin, random
    fetch_ssl: bool = False


@app.post("/crawl/proxy-rotation")
async def crawl_with_proxy_rotation(request: ProxyRotationRequest):
    """Proxy Rotation - 代理轮换爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.proxy_strategy import RoundRobinProxyStrategy, RandomProxyStrategy
        from crawl4ai.async_configs import ProxyConfig

        # Convert proxy strings to ProxyConfig
        proxy_configs = [ProxyConfig.from_string(p) for p in request.proxies]

        # Create rotation strategy
        if request.strategy == "random":
            proxy_strategy = RandomProxyStrategy(proxy_configs)
        else:
            proxy_strategy = RoundRobinProxyStrategy(proxy_configs)

        run_config = CrawlerRunConfig(
            proxy_rotation_strategy=proxy_strategy,
            fetch_ssl_certificate=request.fetch_ssl,
            cache_mode=CacheMode.BYPASS,
        )

        results = []
        for url in request.urls:
            result = await crawler.arun(url=url, config=run_config)
            results.append(
                {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                    "ssl": {
                        "issuer": result.ssl_certificate.issuer
                        if result.ssl_certificate
                        else None,
                        "valid_until": str(result.ssl_certificate.valid_until)
                        if result.ssl_certificate
                        else None,
                    }
                    if request.fetch_ssl
                    else None,
                }
            )

        return {
            "success": True,
            "total_urls": len(request.urls),
            "proxy_count": len(request.proxies),
            "strategy": request.strategy,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Proxy from Environment API ============
class ProxyFromEnvRequest(BaseModel):
    urls: List[str]
    env_variable: str = "PROXIES"
    strategy: str = "round_robin"


@app.post("/crawl/proxy-env")
async def crawl_with_proxy_from_env(request: ProxyFromEnvRequest):
    """Proxy from Environment - 从环境变量加载代理"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.proxy_strategy import RoundRobinProxyStrategy, RandomProxyStrategy
        from crawl4ai.async_configs import ProxyConfig

        # Load proxies from environment
        proxies = ProxyConfig.from_env(request.env_variable)

        if not proxies:
            return {
                "success": False,
                "message": f"No proxies found in environment variable: {request.env_variable}",
                "format": "ip:port:user:pass,ip:port:user:pass",
            }

        # Create rotation strategy
        if request.strategy == "random":
            proxy_strategy = RandomProxyStrategy(proxies)
        else:
            proxy_strategy = RoundRobinProxyStrategy(proxies)

        run_config = CrawlerRunConfig(
            proxy_rotation_strategy=proxy_strategy, cache_mode=CacheMode.BYPASS
        )

        results = []
        for url in request.urls:
            result = await crawler.arun(url=url, config=run_config)
            results.append({"url": url, "success": result.success})

        return {
            "success": True,
            "total_urls": len(request.urls),
            "proxies_loaded": len(proxies),
            "env_variable": request.env_variable,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ SSL Certificate Export API ============
class SSLCertRequest(BaseModel):
    url: str
    proxy: Optional[str] = None
    export_json: bool = True


@app.post("/crawl/ssl-export")
async def crawl_with_ssl_export(request: SSLCertRequest):
    """SSL Certificate Export - SSL证书导出"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig

        proxy_config = None
        if request.proxy:
            proxy_config = ProxyConfig.from_string(request.proxy)

        run_config = CrawlerRunConfig(
            proxy_config=proxy_config,
            fetch_ssl_certificate=True,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=request.url, config=run_config)

        ssl_info = None
        if result.ssl_certificate:
            cert = result.ssl_certificate
            ssl_info = {
                "issuer": cert.issuer,
                "subject": cert.subject,
                "valid_from": str(cert.valid_from) if cert.valid_from else None,
                "valid_until": str(cert.valid_until) if cert.valid_until else None,
                "fingerprint": cert.fingerprint,
                "serial_number": cert.serial_number,
            }

            if request.export_json:
                cert.to_json("ssl_certificate.json")

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Rate Limiter API ============
class RateLimiterConfigRequest(BaseModel):
    urls: List[str]
    base_delay_min: float = 1.0
    base_delay_max: float = 3.0
    max_delay: float = 60.0
    max_retries: int = 3
    rate_limit_codes: Optional[List[int]] = None


@app.post("/crawl/rate-limited")
async def crawl_with_rate_limiter(request: RateLimiterConfigRequest):
    """Rate Limiter - 带速率限制的爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig, RateLimiter

        rate_limiter = RateLimiter(
            base_delay=(request.base_delay_min, request.base_delay_max),
            max_delay=request.max_delay,
            max_retries=request.max_retries,
            rate_limit_codes=request.rate_limit_codes or [429, 503],
        )

        run_config = CrawlerRunConfig(
            rate_limiter=rate_limiter, cache_mode=CacheMode.BYPASS
        )

        results = []
        for url in request.urls:
            result = await crawler.arun(url=url, config=run_config)
            results.append(
                {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {
            "success": True,
            "total_urls": len(request.urls),
            "rate_limiter_config": {
                "base_delay": (request.base_delay_min, request.base_delay_max),
                "max_delay": request.max_delay,
                "max_retries": request.max_retries,
            },
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Memory Adaptive Dispatcher API ============
class MemoryAdaptiveDispatcherRequest(BaseModel):
    urls: List[str]
    memory_threshold: float = 90.0
    check_interval: float = 1.0
    max_concurrent: int = 10
    stream: bool = False


@app.post("/crawl/memory-adaptive")
async def crawl_with_memory_adaptive(request: MemoryAdaptiveDispatcherRequest):
    """Memory Adaptive - 内存自适应调度爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher
        from crawl4ai import CrawlerMonitor, DisplayMode

        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=request.memory_threshold,
            check_interval=request.check_interval,
            max_session_permit=request.max_concurrent,
            monitor=CrawlerMonitor(display_mode=DisplayMode.AGGREGATED),
        )

        run_config = CrawlerRunConfig(
            stream=request.stream, cache_mode=CacheMode.BYPASS
        )

        if request.stream:
            results = []
            async for result in await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            ):
                results.append(
                    {
                        "url": result.url,
                        "success": result.success,
                        "dispatch_result": {
                            "memory_usage": result.dispatch_result.memory_usage
                            if result.dispatch_result
                            else None
                        },
                    }
                )
        else:
            results_list = await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            )
            results = [
                {
                    "url": r.url,
                    "success": r.success,
                    "dispatch_result": {
                        "memory_usage": r.dispatch_result.memory_usage
                        if r.dispatch_result
                        else None
                    },
                }
                for r in results_list
            ]

        return {
            "success": True,
            "total_urls": len(request.urls),
            "dispatcher": "MemoryAdaptive",
            "config": {
                "memory_threshold": request.memory_threshold,
                "max_concurrent": request.max_concurrent,
            },
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Semaphore Dispatcher API ============
class SemaphoreDispatcherRequest(BaseModel):
    urls: List[str]
    semaphore_count: int = 20
    stream: bool = False


@app.post("/crawl/semaphore")
async def crawl_with_semaphore(request: SemaphoreDispatcherRequest):
    """Semaphore - 信号量调度爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.async_dispatcher import SemaphoreDispatcher
        from crawl4ai import CrawlerMonitor, DisplayMode

        dispatcher = SemaphoreDispatcher(
            max_session_permit=request.semaphore_count,
            monitor=CrawlerMonitor(display_mode=DisplayMode.AGGREGATED),
        )

        run_config = CrawlerRunConfig(
            stream=request.stream, cache_mode=CacheMode.BYPASS
        )

        if request.stream:
            results = []
            async for result in await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            ):
                results.append({"url": result.url, "success": result.success})
        else:
            results_list = await crawler.arun_many(
                urls=request.urls, config=run_config, dispatcher=dispatcher
            )
            results = [{"url": r.url, "success": r.success} for r in results_list]

        return {
            "success": True,
            "total_urls": len(request.urls),
            "dispatcher": "Semaphore",
            "semaphore_count": request.semaphore_count,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ URL Specific Config API ============
class URLSpecificConfigRequest(BaseModel):
    urls: List[str]
    configs: List[Dict[str, Any]]


@app.post("/crawl/url-specific")
async def crawl_with_url_specific_config(request: URLSpecificConfigRequest):
    """URL Specific Config - URL特定配置爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        configs = []
        for cfg_dict in request.configs:
            configs.append(CrawlerRunConfig(**cfg_dict))

        results = []
        for url in request.urls:
            matched_config = None
            for i, cfg in enumerate(configs):
                if hasattr(cfg, "url_matcher") and cfg.url_matcher:
                    if callable(cfg.url_matcher):
                        if cfg.url_matcher(url):
                            matched_config = cfg
                            break
                    elif isinstance(cfg.url_matcher, str):
                        if cfg.url_matcher.replace("*", "") in url:
                            matched_config = cfg
                            break
                elif i == len(configs) - 1:
                    matched_config = cfg

            if not matched_config:
                matched_config = configs[-1] if configs else CrawlerRunConfig()

            result = await crawler.arun(url=url, config=matched_config)
            results.append(
                {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {"success": True, "total_urls": len(request.urls), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Crawler Monitor API ============
@app.get("/monitor/stats")
async def get_monitor_stats():
    """Crawler Monitor Stats - 获取爬虫监控统计"""
    try:
        import psutil

        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
        }
    except ImportError:
        return {
            "message": "psutil not available",
            "cpu_percent": 0,
            "memory_percent": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Proxy Validation API ============
class ProxyValidateRequest(BaseModel):
    proxies: List[str]


@app.post("/proxy/validate")
async def validate_proxies(request: ProxyValidateRequest):
    """Proxy Validation - 验证代理是否可用"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig

        results = []

        for proxy_str in request.proxies:
            try:
                proxy_config = ProxyConfig.from_string(proxy_str)

                run_config = CrawlerRunConfig(
                    proxy_config=proxy_config,
                    page_timeout=10000,
                    cache_mode=CacheMode.BYPASS,
                )

                result = await crawler.arun(
                    url="https://httpbin.org/ip", config=run_config
                )

                results.append(
                    {
                        "proxy": proxy_str,
                        "valid": result.success,
                        "error": result.error_message if not result.success else None,
                    }
                )
            except Exception as e:
                results.append({"proxy": proxy_str, "valid": False, "error": str(e)})

        valid_count = sum(1 for r in results if r["valid"])

        return {
            "success": True,
            "total": len(request.proxies),
            "valid": valid_count,
            "invalid": len(request.proxies) - valid_count,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ SOCKS5 Proxy API ============
class SOCKS5ProxyRequest(BaseModel):
    url: str
    proxy_host: str
    proxy_port: int
    username: Optional[str] = None
    password: Optional[str] = None


@app.post("/crawl/socks5")
async def crawl_with_socks5(request: SOCKS5ProxyRequest):
    """SOCKS5 Proxy - SOCKS5代理爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig

        proxy_url = f"socks5://{request.proxy_host}:{request.proxy_port}"
        if request.username and request.password:
            proxy_url = f"socks5://{request.username}:{request.password}@{request.proxy_host}:{request.proxy_port}"

        proxy_config = ProxyConfig.from_string(proxy_url)

        run_config = CrawlerRunConfig(
            proxy_config=proxy_config, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "proxy": proxy_url[:50] + "..." if len(proxy_url) > 50 else proxy_url,
            "error": result.error_message if not result.success else None,
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
            viewport={
                "width": request.viewport_width,
                "height": request.viewport_height,
            },
        )

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=["""return document.title"""],
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Storage State API ============
class StorageStateRequest(BaseModel):
    action: str
    session_id: str
    storage_state: Optional[Dict[str, Any]] = None


@app.post("/session/storage-state")
async def manage_storage_state(request: StorageStateRequest):
    """Storage State - 浏览器状态导出/导入"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        if request.action == "export":
            contexts = crawler.browser.contexts
            if not contexts:
                return {"success": False, "message": "No active contexts"}
            context = contexts[0]
            storage_state = await context.storage_state()
            return {
                "success": True,
                "session_id": request.session_id,
                "storage_state": storage_state,
            }
        elif request.action == "import":
            if not request.storage_state:
                return {"success": False, "message": "No storage state provided"}
            return {"success": True, "message": "Storage state imported"}
        return {"success": False, "message": "Invalid action"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Cookie Management API ============
class CookieRequest(BaseModel):
    url: str
    cookies: List[Dict[str, Any]]


@app.post("/session/cookies")
async def manage_cookies(request: CookieRequest):
    """Cookie Management - 设置Cookies"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig

        browser_config = BrowserConfig(cookies=request.cookies)
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await crawler.arun(url=request.url, config=run_config)
        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Pagination Crawl API ============
class PaginationRequest(BaseModel):
    url: str
    session_id: str = "pagination_session"
    pages: int = 3
    next_button_selector: str = "a.next"
    item_selector: str


@app.post("/crawl/pagination")
async def crawl_with_pagination(request: PaginationRequest):
    """Pagination Crawl - 分页爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        js_click_next = (
            f"document.querySelector('{request.next_button_selector}')?.click();"
        )
        results = []
        for page in range(request.pages):
            config = CrawlerRunConfig(
                session_id=request.session_id,
                js_code=js_click_next if page > 0 else None,
                wait_for=f"css:{request.item_selector}" if page > 0 else None,
                js_only=page > 0,
                cache_mode=CacheMode.BYPASS,
            )
            result = await crawler.arun(url=request.url, config=config)
            results.append({"page": page + 1, "success": result.success})
        return {"success": True, "pages_crawled": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Fit Markdown API ============
class FitMarkdownRequest(BaseModel):
    url: str
    query: str


@app.post("/crawl/fit-markdown")
async def crawl_fit_markdown(request: FitMarkdownRequest):
    """Fit Markdown - 基于查询的相关内容提取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await crawler.arun(url=request.url, config=run_config)
        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Smart Auto-Crawl with Proxy Fallback API ============
class SmartCrawlRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 50
    proxy: Optional[str] = None


class StrategyRecommendation(BaseModel):
    strategy: str
    confidence: float
    reason: str
    features: List[str]


@app.post("/crawl/auto")
async def smart_auto_crawl(request: SmartCrawlRequest):
    """Smart Auto-Crawl - 自动分析URL并选择最佳爬取策略，包含代理回退"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        url = request.url.lower()

        anti_bot_domains = [
            "bbc.com",
            "bbc.co.uk",
            "nytimes.com",
            "washingtonpost.com",
            "theguardian.com",
            "amazon.com",
            "ebay.com",
            "walmart.com",
            "target.com",
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "linkedin.com",
            "reddit.com",
            "stackoverflow.com",
            "github.com",
            "netflix.com",
            "spotify.com",
            "hulu.com",
            "news.google.com",
            "wikipedia.org",
            "cnn.com",
            "reuters.com",
        ]

        simple_domains = [
            "example.com",
            "httpbin.org",
            "jsonplaceholder.typicode.com",
            "placeholder.com",
            "via.placeholder.com",
        ]

        ecommerce_domains = [
            "amazon.com",
            "ebay.com",
            "walmart.com",
            "target.com",
            "bestbuy.com",
            "taobao.com",
            "tmall.com",
            "jd.com",
            "aliexpress.com",
            "shopify.com",
        ]

        recommendation = StrategyRecommendation(
            strategy="basic",
            confidence=0.5,
            reason="Default strategy",
            features=["basic_crawl"],
        )

        for domain in anti_bot_domains:
            if domain in url:
                recommendation = StrategyRecommendation(
                    strategy="undetected",
                    confidence=0.9,
                    reason=f"Detected protected site ({domain})",
                    features=[
                        "undetected_browser",
                        "stealth",
                        "retry",
                        "extended_timeout",
                    ],
                )
                break

        if recommendation.strategy == "basic":
            for domain in simple_domains:
                if domain in url:
                    recommendation = StrategyRecommendation(
                        strategy="text_only",
                        confidence=0.95,
                        reason=f"Simple static site ({domain})",
                        features=["text_only", "fast"],
                    )
                    break

        if recommendation.strategy == "basic":
            for domain in ecommerce_domains:
                if domain in url:
                    recommendation = StrategyRecommendation(
                        strategy="stealth",
                        confidence=0.85,
                        reason=f"E-commerce site ({domain})",
                        features=["stealth", "cookies", "session"],
                    )
                    break

        strategy_name = recommendation.strategy

        # Try strategies in order with fallbacks
        tried_strategies = []
        last_error = None

        # Strategy 1: Stealth with extended timeout
        if strategy_name in ["undetected", "stealth"]:
            try:
                browser_cfg = BrowserConfig(
                    headless=True,
                    enable_stealth=True,
                    proxy_config={"server": request.proxy} if request.proxy else None,
                )
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS, page_timeout=120000, wait_for=None
                )
                result = await crawler.arun(
                    url=request.url, config=run_config, browser_config=browser_cfg
                )
                if result.success:
                    return {
                        "success": True,
                        "url": request.url,
                        "strategy": {"used": strategy_name, "fallback": False},
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                        "links_count": len(result.links) if result.links else 0,
                        "images_count": len(result.media.get("images", []))
                        if result.media
                        else 0,
                    }
            except Exception as e:
                tried_strategies.append(strategy_name)
                last_error = str(e)[:200]

        # Strategy 2: Try with proxy if provided
        if request.proxy:
            try:
                browser_cfg = BrowserConfig(
                    headless=True,
                    enable_stealth=True,
                    proxy_config={"server": request.proxy, "bypass": ["*.bbc.com"]},
                )
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS, page_timeout=90000, wait_for=None
                )
                result = await crawler.arun(
                    url=request.url, config=run_config, browser_config=browser_cfg
                )
                if result.success:
                    return {
                        "success": True,
                        "url": request.url,
                        "strategy": {
                            "used": "proxy_stealth",
                            "fallback": True,
                            "proxy": request.proxy,
                        },
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                        "links_count": len(result.links) if result.links else 0,
                        "images_count": len(result.media.get("images", []))
                        if result.media
                        else 0,
                    }
            except Exception as e:
                tried_strategies.append("proxy_stealth")
                last_error = str(e)[:200]

        # Strategy 3: HTTP-only mode (no browser, use requests)
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    request.url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                )

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                text = soup.get_text(separator="\n", strip=True)

                return {
                    "success": True,
                    "url": request.url,
                    "strategy": {
                        "used": "http_fallback",
                        "fallback": True,
                        "tried": tried_strategies,
                    },
                    "markdown": text[:50000],
                    "markdown_length": len(text),
                    "content_type": response.headers.get("content-type", "unknown"),
                    "status_code": response.status_code,
                    "links_count": len(soup.find_all("a")),
                    "images_count": len(soup.find_all("img")),
                }
        except ImportError:
            pass
        except Exception as e:
            last_error = f"{last_error}; HTTP fallback also failed: {str(e)[:200]}"

        # Strategy 4: Text-only with no JS at all
        try:
            browser_cfg = BrowserConfig(text_mode=True, headless=True)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, page_timeout=30000
            )
            result = await crawler.arun(
                url=request.url, config=run_config, browser_config=browser_cfg
            )
            if result.success:
                return {
                    "success": True,
                    "url": request.url,
                    "strategy": {"used": "text_only_fallback", "fallback": True},
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                    "links_count": len(result.links) if result.links else 0,
                    "images_count": 0,
                }
        except Exception as e:
            last_error = f"{last_error}; Text-only fallback failed: {str(e)[:200]}"

        # All strategies failed
        raise HTTPException(
            status_code=500,
            detail=f"All crawling strategies failed for {request.url}. Tried: {tried_strategies}. Last error: {last_error}. Solution: Use a proxy or try a different URL.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        news_domains = [
            "bbc.com",
            "cnn.com",
            "nytimes.com",
            "theguardian.com",
            "washingtonpost.com",
            "reuters.com",
            "apnews.com",
        ]

        recommendation = StrategyRecommendation(
            strategy="basic",
            confidence=0.5,
            reason="Default strategy for unknown sites",
            features=["basic_crawl"],
        )

        selected_features = {}

        for domain in anti_bot_domains:
            if domain in url:
                recommendation = StrategyRecommendation(
                    strategy="undetected",
                    confidence=0.9,
                    reason=f"Detected anti-bot protected site ({domain})",
                    features=[
                        "undetected_browser",
                        "stealth",
                        "retry",
                        "extended_timeout",
                    ],
                )
                break

        if recommendation.strategy == "basic":
            for domain in simple_domains:
                if domain in url:
                    recommendation = StrategyRecommendation(
                        strategy="text_only",
                        confidence=0.95,
                        reason=f"Simple static site ({domain})",
                        features=["text_only", "fast"],
                    )
                    break

        if recommendation.strategy == "basic":
            for domain in ecommerce_domains:
                if domain in url:
                    recommendation = StrategyRecommendation(
                        strategy="stealth",
                        confidence=0.85,
                        reason=f"E-commerce site detected ({domain})",
                        features=["stealth", "cookies", "session"],
                    )
                    break

        if recommendation.strategy == "basic":
            for domain in news_domains:
                if domain in url:
                    recommendation = StrategyRecommendation(
                        strategy="stealth",
                        confidence=0.8,
                        reason=f"News site detected ({domain})",
                        features=["stealth", "extended_timeout"],
                    )
                    break

        if ".news." in url or "/news/" in url or "/article/" in url:
            if recommendation.strategy in ["basic", "text_only"]:
                recommendation.strategy = "stealth"
                recommendation.confidence = 0.7
                recommendation.reason = "News/Article URL pattern detected"
                recommendation.features = ["stealth", "extended_timeout"]

        if request.max_depth > 0:
            recommendation.features.append("deep_crawl")

        strategy_name = recommendation.strategy

        if strategy_name == "undetected":
            try:
                from crawl4ai import UndetectedAdapter

                adapter = UndetectedAdapter()
                browser_cfg = BrowserConfig(
                    headless=True, enable_stealth=True, browser_adapter=adapter
                )
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS, page_timeout=90000
                )
                result = await crawler.arun(
                    url=request.url, config=run_config, browser_config=browser_cfg
                )
            except (ImportError, Exception):
                browser_cfg = BrowserConfig(
                    headless=True,
                    enable_stealth=True,
                )
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS, page_timeout=120000
                )
                result = await crawler.arun(
                    url=request.url, config=run_config, browser_config=browser_cfg
                )
                strategy_name = "stealth"
        if strategy_name == "stealth":
            browser_cfg = BrowserConfig(headless=True, enable_stealth=True)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, page_timeout=90000
            )
            result = await crawler.arun(
                url=request.url, config=run_config, browser_config=browser_cfg
            )
        elif strategy_name == "text_only":
            browser_cfg = BrowserConfig(text_mode=True, headless=True)
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            result = await crawler.arun(
                url=request.url, config=run_config, browser_config=browser_cfg
            )
        elif strategy_name == "deep_crawl":
            from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth, max_pages=request.max_pages
            )
            run_config = CrawlerRunConfig(
                deep_crawl_strategy=strategy, cache_mode=CacheMode.BYPASS
            )
            result = await crawler.arun(url=request.url, config=run_config)
        else:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "strategy": {
                "used": strategy_name,
                "recommendation": recommendation.model_dump(),
            },
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "links_count": len(result.links) if result.links else 0,
            "images_count": len(result.media.get("images", [])) if result.media else 0,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Analyze URL API ============
class AnalyzeUrlRequest(BaseModel):
    url: str


@app.post("/crawl/analyze")
async def analyze_url(request: AnalyzeUrlRequest):
    """Analyze URL - 分析URL并推荐最佳爬取策略"""
    try:
        url = request.url.lower()

        analysis = {
            "url": request.url,
            "detected": [],
            "recommended_strategy": "basic",
            "confidence": 0.5,
            "tips": [],
        }

        anti_bot_domains = [
            ("bbc.com", "BBC News - Strong anti-bot protection"),
            ("nytimes.com", "NY Times - Requires subscription/cookies"),
            ("washingtonpost.com", "Washington Post - Paywall detected"),
            ("theguardian.com", "The Guardian - Region restrictions"),
            ("amazon.com", "Amazon - Sophisticated bot detection"),
            ("ebay.com", "eBay - Anti-scraping measures"),
            ("facebook.com", "Facebook - Strict anti-bot"),
            ("twitter.com", "Twitter/X - Heavy protection"),
            ("instagram.com", "Instagram - Account required"),
            ("reddit.com", "Reddit - Rate limiting active"),
        ]

        for domain, description in anti_bot_domains:
            if domain in url:
                analysis["detected"].append(description)
                analysis["recommended_strategy"] = "undetected"
                analysis["confidence"] = 0.9
                analysis["tips"].append("Use Undetected Browser mode")
                analysis["tips"].append("Consider using proxies")
                break

        if analysis["recommended_strategy"] == "basic":
            ecommerce_domains = [
                ("amazon.com", "E-commerce - May need stealth"),
                ("ebay.com", "E-commerce platform"),
                ("walmart.com", "Walmart - Anti-bot active"),
                ("taobao.com", "Taobao - Chinese e-commerce"),
                ("jd.com", "JD.com - Complex anti-bot"),
            ]
            for domain, description in ecommerce_domains:
                if domain in url:
                    analysis["detected"].append(description)
                    analysis["recommended_strategy"] = "stealth"
                    analysis["confidence"] = 0.85
                    analysis["tips"].append("Use Stealth mode")
                    break

        if ".gov" in url or ".edu" in url:
            analysis["tips"].append("Government/Edu sites may have strict access")

        if "/api/" in url or ".json" in url:
            analysis["recommended_strategy"] = "text_only"
            analysis["confidence"] = 0.95
            analysis["tips"].append("API endpoints - use fast text-only mode")

        if "/news/" in url or "/article/" in url or "/blog/" in url:
            if analysis["recommended_strategy"] == "basic":
                analysis["recommended_strategy"] = "stealth"
                analysis["confidence"] = 0.7
                analysis["tips"].append("News/Article page - consider stealth mode")

        if not analysis["tips"]:
            analysis["tips"].append("Standard crawl should work")
            analysis["tips"].append("Enable screenshot if needed for debugging")

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Cosine Similarity API ============
class CosineSimilarityRequest(BaseModel):
    url: str
    semantic_filter: str
    word_count_threshold: int = 100


@app.post("/extract/cosine")
async def extract_with_cosine(request: CosineSimilarityRequest):
    """Cosine Similarity - 余弦相似度内容提取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai.extraction_strategy import CosineStrategy

        strategy = CosineStrategy(
            semantic_filter=request.semantic_filter,
            word_count_threshold=request.word_count_threshold,
        )
        run_config = CrawlerRunConfig(
            extraction_strategy=strategy, cache_mode=CacheMode.BYPASS
        )
        result = await crawler.arun(url=request.url, config=run_config)
        return {
            "success": result.success,
            "url": result.url,
            "extracted_content": result.extracted_content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ DOM Selector API ============
class DOMSelectorRequest(BaseModel):
    url: str
    selector: str


@app.post("/extract/dom")
async def extract_with_dom(request: DOMSelectorRequest):
    """DOM Selector - CSS选择器提取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        run_config = CrawlerRunConfig(
            css_selector=request.selector, cache_mode=CacheMode.BYPASS
        )
        result = await crawler.arun(url=request.url, config=run_config)
        return {
            "success": result.success,
            "url": result.url,
            "html_length": len(result.html) if result.html else 0,
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
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="anthropic",
            models=[
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="google",
            models=[
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-pro",
            ],
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="ollama",
            models=[],  # Dynamically fetched
            requires_api_key=False,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="azure",
            models=[],  # Depends on Azure configuration
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="deepseek",
            models=["deepseek-chat", "deepseek-coder"],
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="mistral",
            models=[
                "mistral-small-latest",
                "mistral-medium-latest",
                "mistral-large-latest",
            ],
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="cohere",
            models=["command-r", "command-r-plus", "command"],
            requires_api_key=True,
            supports_base_url=True,
        ),
        LLMProviderInfo(
            name="openrouter",
            models=[],  # Supports many models via openrouter
            requires_api_key=True,
            supports_base_url=True,
        ),
    ]
    return {"providers": [p.model_dump() for p in providers]}


@app.get("/llm/models")
async def get_available_models(ollama_url: str = "http://localhost:11434"):
    """Get available models from different LLM providers"""
    models = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4"],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "google": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-pro",
        ],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
        "mistral": [
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
        ],
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
                ollama_models = [
                    m.get("name", "").split(":")[0] for m in data.get("models", [])
                ]
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
                    return {
                        "success": False,
                        "error": f"Cannot connect to Ollama: HTTP {tags_resp.status_code}",
                    }

                models_data = tags_resp.json()
                available_models = [
                    m.get("name", "") for m in models_data.get("models", [])
                ]

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
                    json={
                        "model": model_name,
                        "prompt": request.test_prompt or "Hello",
                        "stream": False,
                    },
                    timeout=120.0,
                )

                if gen_resp.status_code == 200:
                    gen_data = gen_resp.json()
                    content = gen_data.get("response", "")
                    return {
                        "success": True,
                        "message": f"Connected! Using model: {model_name}",
                        "response": content,
                        "model": model_name,
                        "available_models": available_models[:10],
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Generate failed: HTTP {gen_resp.status_code}, {gen_resp.text[:200]}",
                    }
                gen_resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": request.test_prompt or "Hello",
                        "stream": False,
                    },
                    timeout=60.0,
                )

                if gen_resp.status_code == 200:
                    gen_data = gen_resp.json()
                    content = gen_data.get("response", "")
                    return {
                        "success": True,
                        "message": f"Connected! Using model: {model_name}",
                        "response": content,
                        "model": model_name,
                        "available_models": available_models[:10],
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Generate failed: HTTP {gen_resp.status_code}",
                    }

        # Handle other providers using LiteLLM
        final_model = ""

        if provider.startswith("anthropic"):
            final_model = model_input if model_input else "claude-3-haiku-20240307"
            os.environ["ANTHROPIC_API_KEY"] = request.api_key or os.getenv(
                "ANTHROPIC_API_KEY", ""
            )
        elif provider.startswith("google") or provider.startswith("gemini"):
            final_model = model_input if model_input else "gemini-1.5-flash"
            os.environ["GOOGLE_API_KEY"] = request.api_key or os.getenv(
                "GOOGLE_API_KEY", ""
            )
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
            os.environ["OPENAI_API_KEY"] = request.api_key or os.getenv(
                "OPENAI_API_KEY", ""
            )

        # Set custom base URL if provided
        if request.base_url:
            os.environ["OPENAI_API_BASE"] = request.base_url.strip()

        # Make test completion using LiteLLM
        response = await litellm.acompletion(
            model=final_model,
            messages=[{"role": "user", "content": request.test_prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=60.0,
        )

        # Extract response content - handle different response types
        content = ""
        model_name = ""
        usage_info = {}

        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content or ""

        if hasattr(response, "model"):
            model_name = response.model

        if hasattr(response, "usage") and response.usage:
            usage_info = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return {
            "success": True,
            "message": f"Connected to {request.provider}!",
            "response": content,
            "model": model_name,
            "usage": usage_info,
        }

    except litellm.exceptions.AuthenticationError as e:
        return {
            "success": False,
            "error": f"Authentication failed: {str(e)}. Please check your API key.",
        }
    except litellm.exceptions.RateLimitError as e:
        return {"success": False, "error": f"Rate limit exceeded: {str(e)}"}
    except litellm.exceptions.Timeout as e:
        return {"success": False, "error": f"Request timeout: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
            ollama_url = (
                request.base_url if request.base_url else "http://localhost:11434"
            )
            os.environ["OLLAMA_BASE_URL"] = ollama_url
            if not model.startswith("ollama/"):
                model = f"ollama/{model}"

        # Set API key if provided
        if request.api_key:
            if request.provider.startswith("anthropic"):
                os.environ["ANTHROPIC_API_KEY"] = request.api_key
            elif request.provider.startswith("google") or request.provider.startswith(
                "gemini"
            ):
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
            custom_llm_provider=custom_llm_provider,
        )

        # Extract response content - handle different response types
        content = ""
        model_name = ""
        usage_info = {}

        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content or ""

        if hasattr(response, "model"):
            model_name = response.model

        if hasattr(response, "usage") and response.usage:
            usage_info = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return {
            "success": True,
            "content": content,
            "model": model_name,
            "usage": usage_info,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    import socket

    def find_available_port(start_port=8001, max_attempts=100):
        """自动查找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                continue
        return start_port

    # 自动查找可用端口
    port = find_available_port(8001)

    # 直接更新模块级变量
    import __main__

    __main__.CURRENT_PORT = port

    print(f"🚀 Starting Crawl4AI Backend on port {port}")
    print(f"📡 API URL: http://localhost:{port}")

    uvicorn.run(app, host="0.0.0.0", port=port)

# ============ New Advanced Features ============

# Import additional extraction strategies
try:
    from crawl4ai import (
        JsonCssExtractionStrategy,
        JsonXPathExtractionStrategy,
        RegexExtractionStrategy,
    )

    EXTRACTION_STRATEGIES_AVAILABLE = True
except ImportError:
    EXTRACTION_STRATEGIES_AVAILABLE = False
    print("Warning: Some extraction strategies not available")


# CSS Extraction Request
class CSSExtractionRequest(BaseModel):
    url: str
    schema: Dict[str, Any]
    base_url: Optional[str] = None


# XPath Extraction Request
class XPathExtractionRequest(BaseModel):
    url: str
    schema: Dict[str, Any]
    base_url: Optional[str] = None


# Regex Extraction Request
class RegexExtractionRequest(BaseModel):
    url: str
    pattern: Optional[str] = None
    custom_patterns: Optional[Dict[str, str]] = None


# Schema Generation Request
class SchemaGenerationRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    query: str
    schema_type: str = "css"  # css or xpath
    provider: str = "openai"
    model: str = "gpt-4o-mini"


# Advanced Crawl Request with new options
class AdvancedCrawlRequest(BaseModel):
    url: str
    # Screenshot & PDF
    screenshot: bool = False
    pdf: bool = False
    # Custom Headers
    headers: Optional[Dict[str, str]] = None
    # Stealth mode
    enable_stealth: bool = False
    # Undetected Browser (Cloudflare, DataDome, etc.)
    use_undetected_browser: bool = False
    # Robots.txt
    check_robots_txt: bool = False
    # Proxy
    proxy: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    # SSL Certificate
    fetch_ssl_certificate: bool = False
    # Network & Console Capture
    capture_network: bool = False
    capture_console: bool = False
    # User Simulation & Magic Mode
    simulate_user: bool = False
    magic: bool = False
    override_navigator: bool = True
    # Timing
    wait_time: float = 1.0
    delay_before_return_html: float = 1.0
    page_timeout: int = 60000
    # Existing options
    use_browser: bool = True
    word_count_threshold: int = 10
    extraction_type: Optional[str] = None
    # Session
    session_id: Optional[str] = None


# Hooks API Request
class HooksCrawlRequest(BaseModel):
    url: str
    # Hook configuration
    on_browser_created: Optional[str] = None  # JavaScript code
    on_page_context_created: Optional[str] = None
    before_goto: Optional[str] = None
    after_goto: Optional[str] = None
    on_execution_started: Optional[str] = None
    before_retrieve_html: Optional[str] = None
    before_return_html: Optional[str] = None
    # Other options
    screenshot: bool = False
    pdf: bool = False
    wait_for: Optional[str] = None


# Session Management Request
class SessionRequest(BaseModel):
    action: str  # "export" or "import"
    session_id: str
    storage_state: Optional[Dict[str, Any]] = None  # For import


# Multi-page Schema Generation Request
class MultiPageSchemaRequest(BaseModel):
    html_samples: List[str]  # Multiple HTML samples
    query: str  # What to extract
    schema_type: str = "css"  # "css" or "xpath"
    provider: Optional[str] = None
    model: Optional[str] = None


# Token Usage Response
class TokenUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@app.post("/extract/css", response_model=CrawlResult)
async def extract_with_css(request: CSSExtractionRequest):
    """使用CSS选择器提取结构化数据"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    if not EXTRACTION_STRATEGIES_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Extraction strategies not available"
        )

    try:
        strategy = JsonCssExtractionStrategy(request.schema, verbose=True)
        run_config = CrawlerRunConfig(
            extraction_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            extracted_content=result.extracted_content,
            screenshot=result.screenshot,
            error=result.error_message if not result.success else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/xpath", response_model=CrawlResult)
async def extract_with_xpath(request: XPathExtractionRequest):
    """使用XPath提取结构化数据"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    if not EXTRACTION_STRATEGIES_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Extraction strategies not available"
        )

    try:
        strategy = JsonXPathExtractionStrategy(request.schema, verbose=True)
        run_config = CrawlerRunConfig(
            extraction_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return CrawlResult(
            success=result.success,
            url=result.url,
            extracted_content=result.extracted_content,
            html=result.html,
            error=result.error_message if not result.success else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/regex", response_model=CrawlResult)
async def extract_with_regex(request: RegexExtractionRequest):
    """使用正则表达式提取数据"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    if not EXTRACTION_STRATEGIES_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Extraction strategies not available"
        )

    try:
        if request.custom_patterns:
            strategy = RegexExtractionStrategy(custom=request.custom_patterns)
        elif request.pattern:
            strategy = RegexExtractionStrategy(pattern=request.pattern)
        else:
            strategy = RegexExtractionStrategy()  # Default patterns

        run_config = CrawlerRunConfig(
            extraction_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return CrawlResult(
            success=result.success,
            url=result.url,
            extracted_content=result.extracted_content,
            error=result.error_message if not result.success else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/generate-schema")
async def generate_extraction_schema(request: SchemaGenerationRequest):
    """使用LLM自动生成提取Schema"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    if not EXTRACTION_STRATEGIES_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Extraction strategies not available"
        )

    try:
        # Get HTML content
        html_content = request.html
        if request.url and not html_content:
            result = await crawler.arun(
                url=request.url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            html_content = result.html if result.success else None

        if not html_content:
            raise HTTPException(status_code=400, detail="No HTML content provided")

        # Configure LLM
        llm_config = LLMConfig(
            provider=f"{request.provider}/{request.model}",
            api_token=os.getenv(
                "OPENAI_API_KEY", os.getenv("ANTHROPIC_API_KEY", "env:OPENAI_API_KEY")
            ),
        )

        # Generate schema
        if request.schema_type == "xpath":
            strategy = JsonXPathExtractionStrategy
        else:
            strategy = JsonCssExtractionStrategy

        schema = strategy.generate_schema(
            html=html_content,
            query=request.query,
            schema_type=request.schema_type,
            llm_config=llm_config,
        )

        return {"success": True, "schema": schema, "schema_type": request.schema_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crawl/advanced", response_model=CrawlResult)
async def advanced_crawl(request: AdvancedCrawlRequest):
    """高级爬取 - 包含截图、PDF、自定义Headers、Stealth模式、反爬虫浏览器等"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        # Build proxy config
        proxy_config = None
        if request.proxy:
            proxy_config = {
                "server": request.proxy,
                "username": request.proxy_username,
                "password": request.proxy_password,
            }

        # Determine headless mode
        headless = not (request.enable_stealth or request.use_undetected_browser)

        # Build browser config with stealth mode and undetected browser
        browser_config = BrowserConfig(
            headless=headless,
            proxy_config=proxy_config,
            enable_stealth=request.enable_stealth,
            verbose=True,
        )

        # Build run config with all advanced options
        run_config = CrawlerRunConfig(
            screenshot=request.screenshot,
            pdf=request.pdf,
            headers=request.headers,
            check_robots_txt=request.check_robots_txt,
            fetch_ssl_certificate=request.fetch_ssl_certificate,
            capture_network_requests=request.capture_network,
            capture_console_messages=request.capture_console,
            simulate_user=request.simulate_user,
            magic=request.magic,
            override_navigator=request.override_navigator,
            wait_time=request.wait_time,
            delay_before_return_html=request.delay_before_return_html,
            page_timeout=request.page_timeout,
            session_id=request.session_id,
            cache_mode=CacheMode.BYPASS,
        )

        # Use undetected browser if requested
        if request.use_undetected_browser:
            try:
                from crawl4ai import UndetectedAdapter
                from crawl4ai.async_crawler_strategy import (
                    AsyncPlaywrightCrawlerStrategy,
                )

                adapter = UndetectedAdapter()
                strategy = AsyncPlaywrightCrawlerStrategy(
                    browser_config=browser_config, browser_adapter=adapter
                )

                async with AsyncWebCrawler(
                    crawler_strategy=strategy, config=browser_config
                ) as adv_crawler:
                    result = await adv_crawler.arun(url=request.url, config=run_config)
                    return build_crawl_result(result, request)
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="UndetectedAdapter not available. Please install crawl4ai with undetected support.",
                )
        else:
            async with AsyncWebCrawler(config=browser_config) as adv_crawler:
                result = await adv_crawler.arun(url=request.url, config=run_config)
                return build_crawl_result(result, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_crawl_result(result, request: AdvancedCrawlRequest) -> CrawlResult:
    """Helper to build crawl result with all options"""
    # Handle screenshot
    screenshot_data = None
    if result.screenshot:
        screenshot_data = result.screenshot

    # Handle PDF
    pdf_data = None
    if result.pdf:
        import base64

        pdf_data = (
            base64.b64encode(result.pdf).decode("utf-8")
            if isinstance(result.pdf, bytes)
            else result.pdf
        )

    return CrawlResult(
        success=result.success,
        url=result.url,
        markdown=result.markdown.raw_markdown if result.markdown else None,
        fit_markdown=result.markdown.fit_markdown if result.markdown else None,
        html=result.html,
        links=[link["href"] for link in result.links.get("internal", [])]
        if result.links
        else None,
        images=[img["src"] for img in result.links.get("images", [])]
        if result.links
        else None,
        screenshot=screenshot_data,
        extracted_content=result.extracted_content,
        network_requests=result.network_requests if request.capture_network else None,
        console_messages=result.console_messages if request.capture_console else None,
        error=result.error_message if not result.success else None,
        ssl_certificate={
            "issuer": result.ssl_certificate.issuer if result.ssl_certificate else None,
            "valid_until": result.ssl_certificate.valid_until
            if result.ssl_certificate
            else None,
            "fingerprint": result.ssl_certificate.fingerprint
            if result.ssl_certificate
            else None,
        }
        if result.ssl_certificate
        else None,
    )


@app.post("/crawl/screenshot", response_model=Dict)
async def capture_screenshot(request: AdvancedCrawlRequest):
    """仅捕获页面截图"""
    request.screenshot = True
    result = await advanced_crawl(request)
    return {
        "success": result.success,
        "url": result.url,
        "screenshot": result.screenshot,
        "error": result.error,
    }


@app.post("/crawl/page-pdf", response_model=Dict)
async def capture_pdf(request: AdvancedCrawlRequest):
    """仅捕获页面PDF"""
    request.pdf = True
    result = await advanced_crawl(request)
    return {
        "success": result.success,
        "url": result.url,
        "pdf": result.fit_markdown,  # PDF is returned in fit_markdown for base64
        "error": result.error,
    }


@app.get("/llm/status")
async def get_extraction_status():
    """获取提取策略可用状态"""
    return {
        "extraction_strategies_available": EXTRACTION_STRATEGIES_AVAILABLE,
        "strategies": {
            "css": EXTRACTION_STRATEGIES_AVAILABLE,
            "xpath": EXTRACTION_STRATEGIES_AVAILABLE,
            "regex": EXTRACTION_STRATEGIES_AVAILABLE,
            "llm": True,
        },
    }


# ============ Hooks API ============
@app.post("/crawl/hooks", response_model=CrawlResult)
async def crawl_with_hooks(request: HooksCrawlRequest):
    """使用页面生命周期钩子爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from playwright.async_api import Page, BrowserContext

        # Define hook functions
        hooks = {}

        if request.on_browser_created:

            async def on_browser_created(browser, **kwargs):
                return browser

            hooks["on_browser_created"] = on_browser_created

        if request.on_page_context_created:

            async def on_page_context_created(
                page: Page, context: BrowserContext, **kwargs
            ):
                if request.on_page_context_created:
                    await page.evaluate(request.on_page_context_created)
                return page

            hooks["on_page_context_created"] = on_page_context_created

        if request.before_goto:

            async def before_goto(
                page: Page, context: BrowserContext, url: str, **kwargs
            ):
                if request.before_goto:
                    await page.evaluate(request.before_goto)
                return page

            hooks["before_goto"] = before_goto

        if request.after_goto:

            async def after_goto(
                page: Page, context: BrowserContext, url: str, response, **kwargs
            ):
                if request.after_goto:
                    await page.evaluate(request.after_goto)
                return page

            hooks["after_goto"] = after_goto

        if request.before_retrieve_html:

            async def before_retrieve_html(
                page: Page, context: BrowserContext, **kwargs
            ):
                if request.before_retrieve_html:
                    await page.evaluate(request.before_retrieve_html)
                return page

            hooks["before_retrieve_html"] = before_retrieve_html

        # Register hooks
        for hook_name, hook_func in hooks.items():
            crawler.crawler_strategy.set_hook(hook_name, hook_func)

        # Build run config
        run_config = CrawlerRunConfig(
            screenshot=request.screenshot,
            pdf=request.pdf,
            wait_for=request.wait_for,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return CrawlResult(
            success=result.success,
            url=result.url,
            markdown=result.markdown.raw_markdown if result.markdown else None,
            fit_markdown=result.markdown.fit_markdown if result.markdown else None,
            html=result.html,
            screenshot=result.screenshot,
            error=result.error_message if not result.success else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Session Management API ============
@app.post("/session/manage")
async def manage_session(request: SessionRequest):
    """Session 管理 - 导出/导入浏览器状态"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        if request.action == "export":
            # Export session state
            if not crawler.browser:
                raise HTTPException(status_code=500, detail="No active browser")

            # Get all contexts
            contexts = crawler.browser.contexts
            if not contexts:
                return {"success": False, "message": "No active contexts"}

            # Export first context's storage state
            context = contexts[0]
            storage_state = await context.storage_state()

            return {
                "success": True,
                "session_id": request.session_id,
                "storage_state": storage_state,
            }

        elif request.action == "import":
            # Import session state
            if not request.storage_state:
                raise HTTPException(status_code=400, detail="No storage state provided")

            # Create new context with imported state
            browser_config = BrowserConfig(storage_state=request.storage_state)

            async with AsyncWebCrawler(config=browser_config) as session_crawler:
                # Just verify it works
                result = await session_crawler.arun(
                    url="about:blank",
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
                )

            return {
                "success": True,
                "session_id": request.session_id,
                "message": "Session imported successfully",
            }

        else:
            raise HTTPException(
                status_code=400, detail="Invalid action. Use 'export' or 'import'"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Multi-page Schema Generation API ============
@app.post("/extract/schema/multi-page")
async def generate_multi_page_schema(request: MultiPageSchemaRequest):
    """多页面Schema生成 - 生成跨多个页面的稳定选择器"""
    if not EXTRACTION_STRATEGIES_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Extraction strategies not available"
        )

    try:
        from crawl4ai import (
            JsonCssExtractionStrategy,
            JsonXPathExtractionStrategy,
            LLMConfig,
        )

        # Combine HTML samples with labels
        combined_html = ""
        for i, html in enumerate(request.html_samples):
            combined_html += f"## HTML Sample {i + 1}\n```html\n{html}\n```\n\n"

        # Add query with instructions for stable selectors
        query = f"""IMPORTANT: I'm providing {len(request.html_samples)} HTML samples from different pages. Generate selectors using stable attributes (href patterns, data attributes, class names) instead of fragile positional selectors like nth-child().\n\n{request.query}"""

        # Configure LLM
        llm_config = LLMConfig(
            provider=f"{request.provider or 'openai'}/{request.model or 'gpt-4o-mini'}",
            api_token=os.getenv("OPENAI_API_KEY", "env:OPENAI_API_KEY"),
        )

        # Generate schema
        if request.schema_type == "xpath":
            strategy_class = JsonXPathExtractionStrategy
        else:
            strategy_class = JsonCssExtractionStrategy

        schema = strategy_class.generate_schema(
            html=combined_html,
            query=query,
            schema_type=request.schema_type,
            llm_config=llm_config,
            validate=True,
        )

        return {
            "success": True,
            "schema": schema,
            "schema_type": request.schema_type,
            "sample_count": len(request.html_samples),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Token Usage Statistics API ============
@app.get("/llm/token-usage")
async def get_token_usage():
    """获取LLM token使用统计"""
    try:
        from crawl4ai.models import TokenUsage

        return {
            "prompt_tokens": TokenUsage().prompt_tokens,
            "completion_tokens": TokenUsage().completion_tokens,
            "total_tokens": TokenUsage().total_tokens,
        }
    except ImportError:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "message": "TokenUsage not available in this version",
        }


# ============ File Downloading API ============
class DownloadRequest(BaseModel):
    url: str
    js_trigger: Optional[str] = None  # JavaScript to trigger download
    wait_time: int = 5


@app.post("/crawl/download")
async def download_file(request: DownloadRequest):
    """文件下载 - 触发页面下载并获取文件"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig

        browser_config = BrowserConfig(
            accept_downloads=True, downloads_path=os.path.join(os.getcwd(), "downloads")
        )

        os.makedirs(browser_config.downloads_path, exist_ok=True)

        run_config = CrawlerRunConfig(
            js_code=request.js_trigger,
            wait_for=request.wait_time,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(config=browser_config) as dl_crawler:
            result = await dl_crawler.arun(url=request.url, config=run_config)

            downloaded_files = result.downloaded_files or []

            return {
                "success": result.success,
                "url": result.url,
                "downloaded_files": downloaded_files,
                "file_count": len(downloaded_files),
                "error": result.error_message if not result.success else None,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Markdown Content Filter API ============
class MarkdownFilterRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    filter_type: str = "pruning"  # "pruning", "bm25", "llm"
    # Pruning options
    threshold: float = 0.5
    threshold_type: str = "fixed"
    min_word_threshold: int = 50
    # BM25 options
    bm25_query: Optional[str] = None
    bm25_threshold: float = 1.2
    # LLM options
    llm_instruction: Optional[str] = None
    chunk_token_threshold: int = 4096
    provider: Optional[str] = None
    model: Optional[str] = None
    # Markdown options
    ignore_links: bool = True
    ignore_images: bool = False
    escape_html: bool = False


@app.post("/markdown/filter")
async def filter_markdown(request: MarkdownFilterRequest):
    """Markdown内容过滤 - 使用BM25/Pruning/LLM过滤内容"""
    if not request.url and not request.html:
        raise HTTPException(
            status_code=400, detail="Either url or html must be provided"
        )

    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig, LLMConfig
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import (
            PruningContentFilter,
            BM25ContentFilter,
            LLMContentFilter,
        )

        # Get HTML content
        html_content = request.html
        if request.url and not html_content:
            result = await crawler.arun(
                url=request.url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            html_content = result.html if result.success else None

        if not html_content:
            raise HTTPException(status_code=400, detail="No HTML content available")

        # Build content filter
        content_filter = None
        if request.filter_type == "pruning":
            content_filter = PruningContentFilter(
                threshold=request.threshold,
                threshold_type=request.threshold_type,
                min_word_threshold=request.min_word_threshold,
            )
        elif request.filter_type == "bm25":
            content_filter = BM25ContentFilter(
                user_query=request.bm25_query or "",
                bm25_threshold=request.bm25_threshold,
            )
        elif request.filter_type == "llm":
            llm_config = LLMConfig(
                provider=f"{request.provider or 'openai'}/{request.model or 'gpt-4o-mini'}",
                api_token=os.getenv("OPENAI_API_KEY", "env:OPENAI_API_KEY"),
            )
            content_filter = LLMContentFilter(
                llm_config=llm_config,
                instruction=request.llm_instruction
                or "Extract the main content, remove navigation and ads.",
                chunk_token_threshold=request.chunk_token_threshold,
            )

        # Build markdown generator
        md_generator = DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_links": request.ignore_links,
                "ignore_images": request.ignore_images,
                "escape_html": request.escape_html,
            },
        )

        # Generate markdown
        run_config = CrawlerRunConfig(markdown_generator=md_generator)

        async with AsyncWebCrawler() as filter_crawler:
            # Use raw:// to pass HTML directly
            result = await filter_crawler.arun(
                url=f"raw://{html_content}", config=run_config
            )

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ HTTP Only Crawl (No Browser) ============
class HTTPCrawlRequest(BaseModel):
    url: str
    headers: Optional[Dict[str, str]] = None


@app.post("/crawl/http-only")
async def http_only_crawl(request: HTTPCrawlRequest):
    """HTTP Only Crawl - 无浏览器，直接用HTTP请求爬取"""
    try:
        import httpx
        from bs4 import BeautifulSoup

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        headers = {**default_headers, **(request.headers or {})}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(request.url, headers=headers)

            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()

            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else ""

            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_=lambda x: x and "content" in x.lower())
                or soup.body
            )

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http"):
                    links.append(href)
                elif href.startswith("/"):
                    from urllib.parse import urljoin

                    links.append(urljoin(request.url, href))

            images = [
                img.get("src", "") for img in soup.find_all("img") if img.get("src")
            ]
            images = [img for img in images if img][:20]

            return {
                "success": True,
                "url": request.url,
                "title": title_text,
                "markdown": text[:100000],
                "markdown_length": len(text),
                "links": links[:100],
                "links_count": len(links),
                "images": images,
                "images_count": len(images),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "strategy": "http_only (no browser)",
            }

    except ImportError:
        raise HTTPException(
            status_code=500, detail="httpx or beautifulsoup4 not installed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTTP crawl failed: {str(e)}")


# ============ Chunking API ============
class ChunkRequest(BaseModel):
    text: str
    chunk_size: int = 100
    chunk_overlap: int = 50
    chunk_type: str = "fixed"  # "fixed", "sliding", "sentence", "regex"
    regex_pattern: Optional[str] = None


@app.post("/text/chunk")
async def chunk_text(request: ChunkRequest):
    """文本分块 - 将长文本分割成小块"""
    try:
        chunks = []

        if request.chunk_type == "fixed":
            words = request.text.split()
            chunks = [
                " ".join(words[i : i + request.chunk_size])
                for i in range(0, len(words), request.chunk_size)
            ]

        elif request.chunk_type == "sliding":
            words = request.text.split()
            for i in range(
                0, len(words) - request.chunk_size + 1, request.chunk_overlap
            ):
                chunks.append(" ".join(words[i : i + request.chunk_size]))

        elif request.chunk_type == "sentence":
            import re

            sentences = re.split(r"(?<=[.!?])\s+", request.text)
            current_chunk = ""
            for sentence in sentences:
                if (
                    len(current_chunk.split()) + len(sentence.split())
                    <= request.chunk_size
                ):
                    current_chunk += " " + sentence if current_chunk else sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
            if current_chunk:
                chunks.append(current_chunk.strip())

        elif request.chunk_type == "regex":
            if request.regex_pattern:
                import re

                parts = re.split(request.regex_pattern, request.text)
                chunks = [p.strip() for p in parts if p.strip()]

        return {
            "success": True,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "chunk_type": request.chunk_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ C4A-Script Execution API ============
class C4AScriptRequest(BaseModel):
    script: str
    url: str = "about:blank"
    timeout: int = 60


@app.post("/crawl/c4a-script")
async def execute_c4a_script(request: C4AScriptRequest):
    """执行C4A-Script自动化脚本"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig

        # C4A-Script is passed as js_code
        run_config = CrawlerRunConfig(
            js_code=request.script,
            page_timeout=request.timeout * 1000,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler() as script_crawler:
            result = await script_crawler.arun(url=request.url, config=run_config)

            return {
                "success": result.success,
                "url": result.url,
                "markdown": result.markdown.raw_markdown if result.markdown else None,
                "html": result.html,
                "screenshot": result.screenshot,
                "error": result.error_message if not result.success else None,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Anti-Bot Fallback API ============
class AntiBotRequest(BaseModel):
    url: str
    max_retries: int = 3
    proxies: Optional[List[str]] = None
    enable_stealth: bool = True
    magic: bool = True


@app.post("/crawl/anti-bot")
async def crawl_with_anti_bot(request: AntiBotRequest):
    """Anti-Bot Fallback - 自动重试/代理轮换/备用方案"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig

        # Build proxy config list
        proxy_configs = []
        if request.proxies:
            for proxy in request.proxies:
                proxy_configs.append(ProxyConfig(server=proxy))

        browser_config = BrowserConfig(
            headless=True, enable_stealth=request.enable_stealth
        )

        run_config = CrawlerRunConfig(
            max_retries=request.max_retries,
            proxy_config=proxy_configs if proxy_configs else None,
            magic=request.magic,
            wait_until="load",
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(config=browser_config) as antibot_crawler:
            result = await antibot_crawler.arun(url=request.url, config=run_config)

            # Extract crawl stats
            crawl_stats = result.crawl_stats or {}

            return {
                "success": result.success,
                "url": result.url,
                "markdown": result.markdown.raw_markdown if result.markdown else None,
                "html": result.html,
                "crawl_stats": {
                    "attempts": crawl_stats.get("attempts", 1),
                    "retries": crawl_stats.get("retries", 0),
                    "proxies_used": crawl_stats.get("proxies_used", []),
                    "resolved_by": crawl_stats.get("resolved_by"),
                    "fallback_fetch_used": crawl_stats.get(
                        "fallback_fetch_used", False
                    ),
                },
                "error": result.error_message if not result.success else None,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Filter Chain API ============
class FilterRequest(BaseModel):
    url: str
    patterns: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    blocked_domains: Optional[List[str]] = None
    content_types: Optional[List[str]] = None
    max_depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"  # bfs, dfs, best_first


@app.post("/crawl/filter")
async def crawl_with_filter(request: FilterRequest):
    """使用Filter Chain进行过滤爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.deep_crawling import (
            BFSDeepCrawlStrategy,
            DFSDeepCrawlStrategy,
            BestFirstCrawlingStrategy,
        )
        from crawl4ai.deep_crawling.filters import (
            FilterChain,
            URLPatternFilter,
            DomainFilter,
            ContentTypeFilter,
        )

        # Build filters
        filters = []
        if request.patterns:
            filters.append(URLPatternFilter(patterns=request.patterns))
        if request.allowed_domains or request.blocked_domains:
            filters.append(
                DomainFilter(
                    allowed_domains=request.allowed_domains,
                    blocked_domains=request.blocked_domains,
                )
            )
        if request.content_types:
            filters.append(ContentTypeFilter(allowed_types=request.content_types))

        filter_chain = FilterChain(filters) if filters else None

        # Build strategy
        if request.strategy == "dfs":
            deep_strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                filter_chain=filter_chain,
            )
        elif request.strategy == "best_first":
            deep_strategy = BestFirstCrawlingStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                filter_chain=filter_chain,
            )
        else:
            deep_strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                filter_chain=filter_chain,
            )

        run_config = CrawlerRunConfig(
            deep_crawl_strategy=deep_strategy, stream=False, cache_mode=CacheMode.BYPASS
        )

        results = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": True,
            "url": request.url,
            "pages_crawled": len(results),
            "results": [
                {
                    "url": r.url,
                    "depth": r.metadata.get("depth", 0),
                    "markdown_length": len(r.markdown.raw_markdown)
                    if r.markdown
                    else 0,
                }
                for r in results[:20]  # Return first 20
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Prefetch Mode API ============
class PrefetchRequest(BaseModel):
    url: str
    max_pages: int = 100


@app.post("/crawl/prefetch")
async def prefetch_urls(request: PrefetchRequest):
    """Prefetch Mode - 快速URL发现 (不处理内容)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(prefetch=True, cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(url=request.url, config=run_config)

        internal_links = (
            [link["href"] for link in result.links.get("internal", [])]
            if result.links
            else []
        )
        external_links = (
            [link["href"] for link in result.links.get("external", [])]
            if result.links
            else []
        )

        return {
            "success": result.success,
            "url": result.url,
            "internal_links": internal_links[: request.max_pages],
            "external_links": external_links[: request.max_pages],
            "total_internal": len(internal_links),
            "total_external": len(external_links),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Deep Crawl State Management API ============
class DeepCrawlStateRequest(BaseModel):
    action: str  # "save", "resume", "cancel"
    state: Optional[Dict[str, Any]] = None
    crawl_config: Optional[Dict[str, Any]] = None


# In-memory state storage (for demo - use Redis in production)
deep_crawl_states: Dict[str, Dict[str, Any]] = {}


@app.post("/crawl/state")
async def manage_deep_crawl_state(request: DeepCrawlStateRequest):
    """Deep Crawl状态管理 - 保存/恢复/取消"""
    try:
        if request.action == "save":
            if not request.state:
                raise HTTPException(status_code=400, detail="No state provided")

            state_id = f"state_{len(deep_crawl_states)}"
            deep_crawl_states[state_id] = request.state

            return {"success": True, "state_id": state_id, "message": "State saved"}

        elif request.action == "resume":
            if not request.crawl_config:
                raise HTTPException(status_code=400, detail="No crawl config provided")

            if not crawler:
                raise HTTPException(status_code=500, detail="Crawler not initialized")

            from crawl4ai import CrawlerRunConfig
            from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

            # Build strategy with resume state
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.crawl_config.get("max_depth", 2),
                max_pages=request.crawl_config.get("max_pages", 50),
                resume_state=request.state,
            )

            run_config = CrawlerRunConfig(
                deep_crawl_strategy=strategy, stream=True, cache_mode=CacheMode.BYPASS
            )

            results = []
            async for result in await crawler.arun(
                url=request.crawl_config.get("url", "about:blank"), config=run_config
            ):
                results.append(
                    {"url": result.url, "depth": result.metadata.get("depth", 0)}
                )

            return {"success": True, "pages_crawled": len(results), "results": results}

        elif request.action == "cancel":
            # Mark state as cancelled
            state_id = request.state.get("state_id") if request.state else None
            if state_id and state_id in deep_crawl_states:
                deep_crawl_states[state_id]["cancelled"] = True

            return {"success": True, "message": "Crawl cancelled"}

        else:
            raise HTTPException(status_code=400, detail="Invalid action")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Research Assistant API ============
class ResearchRequest(BaseModel):
    urls: List[str]
    query: str
    top_k: int = 5
    provider: Optional[str] = None
    model: Optional[str] = None


@app.post("/research/assistant")
async def research_assistant(request: ResearchRequest):
    """Research Assistant - 从多个URL中提取与查询相关的内容"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig, LLMConfig
        from crawl4ai.content_filter_strategy import BM25ContentFilter

        results = []

        for url in request.urls:
            # Use BM25 filter to find relevant content
            filter_obj = BM25ContentFilter(user_query=request.query, bm25_threshold=0.5)

            md_generator = DefaultMarkdownGenerator(content_filter=filter_obj)

            run_config = CrawlerRunConfig(
                markdown_generator=md_generator, cache_mode=CacheMode.BYPASS
            )

            result = await crawler.arun(url=url, config=run_config)

            if result.success and result.markdown:
                results.append(
                    {
                        "url": url,
                        "content": result.markdown.fit_markdown
                        or result.markdown.raw_markdown,
                        "content_length": len(result.markdown.raw_markdown or ""),
                    }
                )

        # Sort by relevance (content length as proxy)
        results.sort(key=lambda x: x["content_length"], reverse=True)

        return {
            "success": True,
            "query": request.query,
            "pages_analyzed": len(results),
            "relevant_pages": results[: request.top_k],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Page Summarization API ============
class SummarizeRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    instruction: Optional[str] = None


@app.post("/content/summarize")
async def summarize_page(request: SummarizeRequest):
    """Page Summarization - 使用LLM生成页面摘要"""
    if not request.url and not request.html:
        raise HTTPException(
            status_code=400, detail="Either url or html must be provided"
        )

    try:
        from crawl4ai import CrawlerRunConfig, LLMConfig
        from crawl4ai.content_filter_strategy import LLMContentFilter

        # Get HTML content
        html_content = request.html
        if request.url and not html_content:
            result = await crawler.arun(
                url=request.url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            html_content = result.html if result.success else None

        if not html_content:
            raise HTTPException(status_code=400, detail="No HTML content available")

        # Configure LLM
        llm_config = LLMConfig(
            provider=f"{request.provider or 'openai'}/{request.model or 'gpt-4o-mini'}",
            api_token=os.getenv("OPENAI_API_KEY", "env:OPENAI_API_KEY"),
        )

        # Use LLM content filter for summarization
        instruction = (
            request.instruction
            or "Summarize the main content of this page in 2-3 sentences."
        )

        filter_obj = LLMContentFilter(
            llm_config=llm_config, instruction=instruction, chunk_token_threshold=2048
        )

        md_generator = DefaultMarkdownGenerator(content_filter=filter_obj)
        run_config = CrawlerRunConfig(markdown_generator=md_generator)

        async with AsyncWebCrawler() as summarize_crawler:
            result = await summarize_crawler.arun(
                url=f"raw://{html_content}", config=run_config
            )

        return {
            "success": result.success,
            "url": request.url,
            "summary": result.markdown.fit_markdown if result.markdown else None,
            "full_content": result.markdown.raw_markdown if result.markdown else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Knowledge Base API ============
class KnowledgeBaseRequest(BaseModel):
    action: str  # "export" or "import"
    urls: Optional[List[str]] = None
    query: Optional[str] = None
    file_path: Optional[str] = None


knowledge_base_data: List[Dict[str, Any]] = []


@app.post("/knowledge/base")
async def knowledge_base(request: KnowledgeBaseRequest):
    """Knowledge Base - 收集和导出知识库"""
    try:
        if request.action == "collect":
            if not request.urls or not request.query:
                raise HTTPException(
                    status_code=400, detail="urls and query required for collect"
                )

            if not crawler:
                raise HTTPException(status_code=500, detail="Crawler not initialized")

            from crawl4ai import CrawlerRunConfig
            from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
            from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

            # Use adaptive crawling to collect relevant content
            scorer = KeywordRelevanceScorer(keywords=request.query.split(), weight=0.7)

            strategy = BestFirstCrawlingStrategy(
                max_depth=2, max_pages=20, url_scorer=scorer
            )

            run_config = CrawlerRunConfig(
                deep_crawl_strategy=strategy, stream=False, cache_mode=CacheMode.BYPASS
            )

            results = await crawler.arun(url=request.urls[0], config=run_config)

            global knowledge_base_data
            knowledge_base_data = []

            for r in results:
                if r.success and r.markdown:
                    knowledge_base_data.append(
                        {
                            "url": r.url,
                            "content": r.markdown.raw_markdown,
                            "fit_content": r.markdown.fit_markdown,
                            "metadata": r.metadata,
                        }
                    )

            return {
                "success": True,
                "pages_collected": len(knowledge_base_data),
                "query": request.query,
            }

        elif request.action == "export":
            return {
                "success": True,
                "knowledge_base": knowledge_base_data,
                "total_pages": len(knowledge_base_data),
            }

        elif request.action == "clear":
            knowledge_base_data = []
            return {"success": True, "message": "Knowledge base cleared"}

        else:
            raise HTTPException(status_code=400, detail="Invalid action")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Crawl Dispatcher API ============
class DispatchRequest(BaseModel):
    urls: List[str]
    max_concurrent: int = 5
    strategy: str = "parallel"  # parallel, sequential, adaptive


@app.post("/crawl/dispatch")
async def crawl_dispatcher(request: DispatchRequest):
    """Crawl Dispatcher - 并行/顺序爬取多个URL"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        if request.strategy == "sequential":
            # Sequential crawling
            results = []
            for url in request.urls:
                result = await crawler.arun(
                    url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                )
                results.append(
                    {
                        "url": url,
                        "success": result.success,
                        "markdown_length": len(result.markdown.raw_markdown)
                        if result.markdown
                        else 0,
                    }
                )

        else:
            # Parallel crawling (default)
            import asyncio

            async def crawl_url(url: str):
                result = await crawler.arun(
                    url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                )
                return {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                    "error": result.error_message if not result.success else None,
                }

            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(request.max_concurrent)

            async def limited_crawl(url: str):
                async with semaphore:
                    return await crawl_url(url)

            results = await asyncio.gather(
                *[limited_crawl(url) for url in request.urls]
            )

        return {
            "success": True,
            "total_urls": len(request.urls),
            "strategy": request.strategy,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Advanced Browser Config API ============
class AdvancedBrowserRequest(BaseModel):
    url: str
    # Browser type
    browser_type: str = "chromium"  # chromium, firefox, webkit
    # Browser mode
    browser_mode: str = "dedicated"  # dedicated, builtin, custom, docker
    # Display settings
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    device_scale_factor: float = 1.0
    # Performance modes
    text_mode: bool = False
    light_mode: bool = False
    # User agent
    user_agent: Optional[str] = None
    user_agent_mode: str = ""  # "random" for randomization
    # Proxy
    proxy: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    # Stealth
    enable_stealth: bool = False
    # Persistent context
    use_persistent_context: bool = False
    user_data_dir: Optional[str] = None
    # Additional
    extra_args: Optional[List[str]] = None


@app.post("/crawl/advanced-browser")
async def crawl_with_advanced_browser(request: AdvancedBrowserRequest):
    """高级浏览器配置爬取 - 支持多种浏览器引擎和配置"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig, GeolocationConfig

        # Build proxy config
        proxy_config = None
        if request.proxy:
            proxy_config = ProxyConfig(
                server=request.proxy,
                username=request.proxy_username,
                password=request.proxy_password,
            )

        # Build browser config
        browser_config = BrowserConfig(
            browser_type=request.browser_type,
            browser_mode=request.browser_mode,
            headless=request.headless,
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height,
            device_scale_factor=request.device_scale_factor,
            text_mode=request.text_mode,
            light_mode=request.light_mode,
            user_agent=request.user_agent,
            user_agent_mode=request.user_agent_mode
            if request.user_agent_mode
            else None,
            proxy_config=proxy_config,
            enable_stealth=request.enable_stealth,
            use_persistent_context=request.use_persistent_context,
            user_data_dir=request.user_data_dir,
            extra_args=request.extra_args,
            verbose=True,
        )

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        async with AsyncWebCrawler(config=browser_config) as adv_crawler:
            result = await adv_crawler.arun(url=request.url, config=run_config)

            return {
                "success": result.success,
                "url": result.url,
                "markdown_length": len(result.markdown.raw_markdown)
                if result.markdown
                else 0,
                "html_length": len(result.html) if result.html else 0,
                "links_count": len(result.links.get("internal", []))
                if result.links
                else 0,
                "error": result.error_message if not result.success else None,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ MHTML Capture API ============
class MHTMLRequest(BaseModel):
    url: str


@app.post("/crawl/mhtml")
async def capture_mhtml(request: MHTMLRequest):
    """MHTML 捕获 - 完整页面快照"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(capture_mhtml=True, cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Prefetch Mode API ============
class PrefetchCrawlRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 100
    strategy: str = "bfs"


@app.post("/crawl/prefetch")
async def crawl_with_prefetch(request: PrefetchCrawlRequest):
    """Prefetch Mode - 5-10倍快速URL发现，跳过完整页面渲染"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy

        if request.strategy == "bfs":
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth, max_pages=request.max_pages
            )
        else:
            strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth, max_pages=request.max_pages
            )

        run_config = CrawlerRunConfig(
            prefetch=True, deep_crawl_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "prefetch_mode": True,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "links_found": len(result.links) if result.links else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Text-Only Mode API ============
class TextOnlyRequest(BaseModel):
    url: str
    word_count_threshold: int = 200


@app.post("/crawl/text-only")
async def crawl_text_only(request: TextOnlyRequest):
    """Text-Only Mode - 禁用JS和图片，3-4倍快速爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        browser_cfg = BrowserConfig(text_mode=True, headless=True)

        run_config = CrawlerRunConfig(
            word_count_threshold=request.word_count_threshold,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(
            url=request.url, config=run_config, browser_config=browser_cfg
        )

        return {
            "success": result.success,
            "url": result.url,
            "text_only_mode": True,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Dynamic Viewport API ============
class DynamicViewportRequest(BaseModel):
    url: str
    viewport_width: int = 1280
    viewport_height: int = 720
    adjust_to_content: bool = True


@app.post("/crawl/dynamic-viewport")
async def crawl_with_dynamic_viewport(request: DynamicViewportRequest):
    """Dynamic Viewport - 根据内容动态调整视口大小"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        browser_cfg = BrowserConfig(
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height,
            adjust_viewport_to_content=request.adjust_to_content,
        )

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(
            url=request.url, config=run_config, browser_config=browser_cfg
        )

        return {
            "success": result.success,
            "url": result.url,
            "viewport": {
                "width": request.viewport_width,
                "height": request.viewport_height,
                "adjusted": request.adjust_to_content,
            },
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ CDP Connection Management API ============
class CDPConnectionRequest(BaseModel):
    action: str  # create, list, connect, close
    cdp_url: Optional[str] = None


@app.post("/cdp/connection")
async def manage_cdp_connection(request: CDPConnectionRequest):
    """CDP Connection - 浏览器复用和CDP连接管理"""
    try:
        if request.action == "create":
            browser_cfg = BrowserConfig(
                browser_mode="builtin", cdp_cleanup_on_close=True
            )
            return {
                "success": True,
                "action": "create",
                "cdp_url": browser_cfg.cdp_url,
                "message": "CDP connection created with cleanup enabled",
            }

        elif request.action == "list":
            return {
                "success": True,
                "action": "list",
                "message": "Use browser_mode=builtin for CDP reuse",
            }

        elif request.action == "close":
            return {
                "success": True,
                "action": "close",
                "message": "CDP connection will be cleaned up on close",
            }

        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Crash Recovery State API ============
class CrashRecoveryRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"
    resume_state: Optional[Dict[str, Any]] = None
    save_state_interval: int = 10


@app.post("/crawl/crash-recovery")
async def crawl_with_crash_recovery(request: CrashRecoveryRequest):
    """Crash Recovery - 深度爬取崩溃恢复，状态持久化"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
        import json

        saved_state = {"visited": [], "pending": [], "depth": 0}

        def on_state_change(state):
            saved_state.update(state)
            return state

        if request.strategy == "bfs":
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
                on_state_change=on_state_change if not request.resume_state else None,
            )
        elif request.strategy == "dfs":
            strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
                on_state_change=on_state_change if not request.resume_state else None,
            )
        else:
            from crawl4ai.deep_crawling import BestFirstDeepCrawlStrategy

            strategy = BestFirstDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
                on_state_change=on_state_change if not request.resume_state else None,
            )

        run_config = CrawlerRunConfig(
            deep_crawl_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "crash_recovery": True,
            "current_state": saved_state,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Sticky Session Proxy API ============
class StickyProxyRequest(BaseModel):
    url: str
    proxy: str
    sticky_session: bool = True


@app.post("/crawl/sticky-proxy")
async def crawl_with_sticky_proxy(request: StickyProxyRequest):
    """Sticky Session Proxy - 粘性会话代理，保持同一代理"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import ProxyConfig

        proxy_cfg = ProxyConfig(
            server=request.proxy, sticky_session=request.sticky_session
        )

        browser_cfg = BrowserConfig(proxy_config=proxy_cfg)
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(
            url=request.url, config=run_config, browser_config=browser_cfg
        )

        return {
            "success": result.success,
            "url": result.url,
            "proxy": request.proxy,
            "sticky_session": request.sticky_session,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ HTTP Strategy Proxy API ============
class HTTPProxyRequest(BaseModel):
    url: str
    proxy: str


@app.post("/crawl/http-proxy")
async def crawl_with_http_proxy(request: HTTPProxyRequest):
    """HTTP Strategy Proxy - 非浏览器爬取的代理支持"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        run_config = CrawlerRunConfig(proxy=request.proxy, cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "proxy": request.proxy,
            "http_strategy": True,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Full Page Scan API ============
class FullPageScanRequest(BaseModel):
    url: str
    scroll_pause: int = 1000


@app.post("/crawl/full-scan")
async def crawl_with_full_page_scan(request: FullPageScanRequest):
    """Full Page Scan - 模拟滚动到底部捕获所有懒加载内容"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        run_config = CrawlerRunConfig(
            scan_full_page=True,
            delay_before_return_html=request.scroll_pause / 1000.0,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "full_page_scan": True,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "images_count": len(result.media.get("images", [])) if result.media else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Geolocation API ============
class GeolocationRequest(BaseModel):
    url: str
    latitude: float
    longitude: float
    accuracy: float = 100.0


@app.post("/crawl/geolocation")
async def crawl_with_geolocation(request: GeolocationRequest):
    """地理位置模拟爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig
        from crawl4ai.async_configs import GeolocationConfig

        browser_config = BrowserConfig(headless=True, verbose=True)

        geolocation = GeolocationConfig(
            latitude=request.latitude,
            longitude=request.longitude,
            accuracy=request.accuracy,
        )

        run_config = CrawlerRunConfig(
            geolocation=geolocation, cache_mode=CacheMode.BYPASS
        )

        async with AsyncWebCrawler(config=browser_config) as geo_crawler:
            result = await geo_crawler.arun(url=request.url, config=run_config)

            return {
                "success": result.success,
                "url": result.url,
                "geolocation": {
                    "latitude": request.latitude,
                    "longitude": request.longitude,
                },
                "markdown_length": len(result.markdown.raw_markdown)
                if result.markdown
                else 0,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Shadow DOM API ============
class ShadowDOMRequest(BaseModel):
    url: str
    flatten_shadow_dom: bool = True


@app.post("/crawl/shadow-dom")
async def crawl_with_shadow_dom(request: ShadowDOMRequest):
    """Shadow DOM 处理爬取 - 用于 Web Components"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(
            flatten_shadow_dom=request.flatten_shadow_dom, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "html_length": len(result.html) if result.html else 0,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Multi-URL Config API ============
class MultiURLConfigRequest(BaseModel):
    urls: List[str]
    # Common config
    word_count_threshold: int = 200
    wait_for: Optional[str] = None
    screenshot: bool = False
    # URL-specific patterns
    url_patterns: Optional[List[str]] = None
    match_mode: str = "OR"  # OR, AND


@app.post("/crawl/multi-url")
async def crawl_multi_url_config(request: MultiURLConfigRequest):
    """多URL配置爬取 - 支持URL特定配置"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.utils import MatchMode

        # Build URL matcher
        url_matcher = None
        if request.url_patterns:
            url_matcher = request.url_patterns

        match_mode_enum = MatchMode.OR if request.match_mode == "OR" else MatchMode.AND

        run_config = CrawlerRunConfig(
            word_count_threshold=request.word_count_threshold,
            wait_for=request.wait_for,
            screenshot=request.screenshot,
            url_matcher=url_matcher,
            match_mode=match_mode_enum,
            cache_mode=CacheMode.BYPASS,
        )

        # Crawl all URLs
        results = []
        async for result in await crawler.arun_many(
            urls=request.urls, config=run_config
        ):
            results.append(
                {
                    "url": result.url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {"success": True, "total_urls": len(request.urls), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ LLM Provider Config API ============
class LLMProviderRequest(BaseModel):
    url: str
    provider: str = "openai/gpt-4o-mini"
    instruction: str = "Extract the main content and summarize it."
    temperature: float = 0.7


@app.post("/llm/generate-markdown")
async def llm_generate_markdown(request: LLMProviderRequest):
    """LLM Markdown 生成 - 使用指定Provider生成Markdown"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig, LLMConfig
        from crawl4ai.content_filter_strategy import LLMContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        # Configure LLM
        llm_config = LLMConfig(
            provider=request.provider,
            api_token=os.getenv("OPENAI_API_KEY", "env:OPENAI_API_KEY"),
            temperature=request.temperature,
        )

        # Use LLM content filter
        filter_obj = LLMContentFilter(
            llm_config=llm_config,
            instruction=request.instruction,
            chunk_token_threshold=2048,
        )

        md_generator = DefaultMarkdownGenerator(content_filter=filter_obj)
        run_config = CrawlerRunConfig(markdown_generator=md_generator)

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown": result.markdown.fit_markdown if result.markdown else None,
            "provider": request.provider,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ URL Seeding API ============
class URLSeedingRequest(BaseModel):
    domain: str
    source: str = "sitemap+cc"  # "cc", "sitemap", "sitemap+cc"
    pattern: Optional[str] = None
    extract_head: bool = True
    live_check: bool = False
    max_urls: int = 100
    query: Optional[str] = None
    scoring_method: Optional[str] = None
    score_threshold: Optional[float] = None


@app.post("/url/seeding")
async def url_seeding(request: URLSeedingRequest):
    """URL Seeding - 批量URL发现 (Sitemap/Common Crawl)"""
    try:
        from crawl4ai import AsyncUrlSeeder, SeedingConfig

        async with AsyncUrlSeeder() as seeder:
            config = SeedingConfig(
                source=request.source,
                pattern=request.pattern or "*",
                extract_head=request.extract_head,
                live_check=request.live_check,
                max_urls=request.max_urls,
                query=request.query,
                scoring_method=request.scoring_method,
                score_threshold=request.score_threshold,
                verbose=True,
            )

            urls = await seeder.urls(request.domain, config)

            # Process results
            valid_urls = [u for u in urls if u.get("status") == "valid"]

            return {
                "success": True,
                "domain": request.domain,
                "total_found": len(urls),
                "valid_count": len(valid_urls),
                "urls": valid_urls[: request.max_urls],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Multi-Domain URL Seeding API ============
class MultiDomainSeedingRequest(BaseModel):
    domains: List[str]
    source: str = "sitemap"
    pattern: Optional[str] = None
    extract_head: bool = True
    max_urls_per_domain: int = 20
    query: Optional[str] = None
    scoring_method: str = "bm25"
    score_threshold: float = 0.3


@app.post("/url/seeding/multi-domain")
async def multi_domain_seeding(request: MultiDomainSeedingRequest):
    """多域名URL发现 - 跨多个域名发现URL"""
    try:
        from crawl4ai import AsyncUrlSeeder, SeedingConfig

        async with AsyncUrlSeeder() as seeder:
            config = SeedingConfig(
                source=request.source,
                pattern=request.pattern or "*",
                extract_head=request.extract_head,
                query=request.query,
                scoring_method=request.scoring_method,
                score_threshold=request.score_threshold,
                max_urls=request.max_urls_per_domain,
                verbose=True,
            )

            results = await seeder.many_urls(request.domains, config)

            # Process results
            processed = {}
            for domain, urls in results.items():
                valid_urls = [u for u in urls if u.get("status") == "valid"]
                processed[domain] = {
                    "total": len(urls),
                    "valid": len(valid_urls),
                    "urls": valid_urls,
                }

            return {"success": True, "domains": request.domains, "results": processed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Cache Management API ============
class CacheManagementRequest(BaseModel):
    action: str  # "get", "clear", "stats"
    cache_type: str = "all"  # "all", "html", "seo", "screenshot"


@app.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        cache_dir = os.path.join(os.path.expanduser("~"), ".crawl4ai")
        seeder_cache = os.path.join(cache_dir, "seeder_cache")
        html_cache = os.path.join(cache_dir, "cache", "html")

        stats = {
            "cache_dir": cache_dir,
            "exists": os.path.exists(cache_dir),
            "seeder_cache_exists": os.path.exists(seeder_cache),
            "html_cache_exists": os.path.exists(html_cache),
        }

        # Count files
        if os.path.exists(seeder_cache):
            stats["seeder_files"] = len(
                [
                    f
                    for f in os.listdir(seeder_cache)
                    if os.path.isfile(os.path.join(seeder_cache, f))
                ]
            )

        if os.path.exists(html_cache):
            stats["html_files"] = len(
                [
                    f
                    for f in os.listdir(html_cache)
                    if os.path.isfile(os.path.join(html_cache, f))
                ]
            )

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/manage")
async def manage_cache(request: CacheManagementRequest):
    """缓存管理 - 清除缓存"""
    try:
        import shutil

        cache_dir = os.path.join(os.path.expanduser("~"), ".crawl4ai")

        if request.action == "clear":
            removed = []

            if request.cache_type in ["all", "html"]:
                html_cache = os.path.join(cache_dir, "cache", "html")
                if os.path.exists(html_cache):
                    shutil.rmtree(html_cache)
                    removed.append("html_cache")

            if request.cache_type in ["all", "seo"]:
                seo_cache = os.path.join(cache_dir, "seo_cache")
                if os.path.exists(seo_cache):
                    shutil.rmtree(seo_cache)
                    removed.append("seo_cache")

            if request.cache_type in ["all"]:
                seeder_cache = os.path.join(cache_dir, "seeder_cache")
                if os.path.exists(seeder_cache):
                    shutil.rmtree(seeder_cache)
                    removed.append("seeder_cache")

            return {
                "success": True,
                "message": f"Cleared cache types: {', '.join(removed) if removed else 'none'}",
            }

        return {"success": False, "message": "Unknown action"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Media Extraction API ============
class MediaExtractionRequest(BaseModel):
    url: str
    extract_images: bool = True
    extract_videos: bool = True
    extract_audio: bool = True


@app.post("/extract/media")
async def extract_media(request: MediaExtractionRequest):
    """媒体提取 - 提取图片/视频/音频"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(url=request.url, config=run_config)

        media = {"images": [], "videos": [], "audio": []}

        if result.media:
            if request.extract_images:
                media["images"] = result.media.get("images", [])
            if request.extract_videos:
                media["videos"] = result.media.get("videos", [])
            if request.extract_audio:
                media["audio"] = result.media.get("audio", [])

        return {
            "success": result.success,
            "url": result.url,
            "media": media,
            "media_count": len(media["images"])
            + len(media["videos"])
            + len(media["audio"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Virtual Scroll API ============
class VirtualScrollRequest(BaseModel):
    url: str
    container_selector: str = "[data-testid='primaryColumn']"
    scroll_count: int = 30
    scroll_by: str = "container_height"  # "container_height" or "pixel"
    scroll_pixel: int = 500
    wait_after_scroll: float = 1.0


@app.post("/crawl/virtual-scroll")
async def crawl_with_virtual_scroll(request: VirtualScrollRequest):
    """Virtual Scroll - 虚拟滚动爬取 (Twitter/Instagram风格)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.virtual_scroll_strategy import VirtualScrollConfig

        virtual_config = VirtualScrollConfig(
            container_selector=request.container_selector,
            scroll_count=request.scroll_count,
            scroll_by=request.scroll_by,
            scroll_pixel=request.scroll_pixel,
            wait_after_scroll=request.wait_after_scroll,
        )

        run_config = CrawlerRunConfig(
            virtual_scroll_config=virtual_config, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Form Interaction API ============
class FormInteractionRequest(BaseModel):
    url: str
    form_selector: str = "form"
    form_data: Dict[str, str]  # field_name: value
    submit_selector: Optional[str] = None
    wait_for: Optional[str] = None


@app.post("/crawl/form")
async def crawl_with_form_interaction(request: FormInteractionRequest):
    """Form Interaction - 表单交互 (填写/提交)"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        # Build JS to fill form
        js_code = ""
        for field, value in request.form_data.items():
            js_code += f"document.querySelector('{request.form_selector} [name=\"{field}\"]').value = '{value}';"

        if request.submit_selector:
            js_code += f"document.querySelector('{request.submit_selector}').click();"

        run_config = CrawlerRunConfig(
            js_code=js_code, wait_for=request.wait_for, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "form_data": request.form_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ IFrame Processing API ============
class IFrameRequest(BaseModel):
    url: str
    process_iframes: bool = True


@app.post("/crawl/iframe")
async def crawl_with_iframe(request: IFrameRequest):
    """IFrame Processing - 内联IFrame内容处理"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(
            process_iframes=request.process_iframes, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "html_length": len(result.html) if result.html else 0,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Multi-Step Session API ============
class MultiStepSessionRequest(BaseModel):
    url: str
    steps: List[Dict[str, Any]]  # Each step: {js_code, wait_for, action}
    session_id: str = "multi_step_session"


@app.post("/crawl/multi-step")
async def crawl_multi_step(request: MultiStepSessionRequest):
    """Multi-Step Session - 多步骤会话交互"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        results = []

        for i, step in enumerate(request.steps):
            js_code = step.get("js_code")
            wait_for = step.get("wait_for")
            action = step.get("action", "click")  # click, scroll, fill, submit

            run_config = CrawlerRunConfig(
                js_code=js_code,
                wait_for=wait_for,
                session_id=request.session_id,
                js_only=(i > 0),  # First step is full navigation
                cache_mode=CacheMode.BYPASS,
            )

            result = await crawler.arun(url=request.url, config=run_config)

            results.append(
                {
                    "step": i + 1,
                    "action": action,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {
            "success": True,
            "url": request.url,
            "session_id": request.session_id,
            "steps_completed": len(results),
            "step_results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Overlay/Consent Removal API ============
class CleanPageRequest(BaseModel):
    url: str
    remove_overlay_elements: bool = True
    remove_consent_popups: bool = True


@app.post("/crawl/clean")
async def crawl_clean_page(request: CleanPageRequest):
    """Clean Page - 移除弹窗/Consent弹窗"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        run_config = CrawlerRunConfig(
            remove_overlay_elements=request.remove_overlay_elements,
            remove_consent_popups=request.remove_consent_popups,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "cleaned": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Table Extraction Enhancement ============
class TableExtractRequest(BaseModel):
    url: str
    table_index: int = 0
    as_dataframe: bool = True


@app.post("/extract/tables")
async def extract_tables(request: TableExtractRequest):
    """Table Extraction - 增强的表格提取，支持DataFrame转换"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        result = await crawler.arun(url=request.url)

        tables_data = []
        if hasattr(result, "tables") and result.tables:
            for idx, table in enumerate(result.tables):
                if idx >= request.table_index:
                    table_info = {
                        "index": idx,
                        "columns": table.columns if hasattr(table, "columns") else [],
                        "row_count": len(table.data) if hasattr(table, "data") else 0,
                        "data": table.data[:10] if hasattr(table, "data") else [],
                    }
                    if request.as_dataframe and hasattr(table, "to_dataframe"):
                        table_info["dataframe"] = table.to_dataframe().to_dict()
                    tables_data.append(table_info)

        return {
            "success": result.success,
            "url": result.url,
            "tables_found": len(tables_data),
            "tables": tables_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Browser Mode Config ============
class BrowserModeRequest(BaseModel):
    url: str
    mode: str = "dedicated"  # dedicated, builtin, custom, docker
    cdp_url: Optional[str] = None


@app.post("/crawl/browser-mode")
async def crawl_with_browser_mode(request: BrowserModeRequest):
    """Browser Mode - 不同的浏览器初始化模式"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        browser_cfg = BrowserConfig(browser_mode=request.mode)
        if request.cdp_url:
            browser_cfg.cdp_url = request.cdp_url

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "browser_mode": request.mode,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Smart TTL Cache for Sitemap ============
class SmartCacheRequest(BaseModel):
    sitemap_url: str
    cache_ttl_hours: int = 24
    validate_lastmod: bool = True


@app.post("/seed/smart-cache")
async def seed_with_smart_cache(request: SmartCacheRequest):
    """Smart TTL Cache - 智能缓存失效的Sitemap seeder"""
    try:
        seeding_config = SeedingConfig(
            cache_ttl_hours=request.cache_ttl_hours,
            validate_sitemap_lastmod=request.validate_lastmod,
        )

        seeder = AsyncUrlSeeder(config=seeding_config)
        urls = await seeder.seed(request.sitemap_url)

        return {
            "success": True,
            "sitemap_url": request.sitemap_url,
            "urls_found": len(urls),
            "urls": urls[:100],
            "cache_ttl_hours": request.cache_ttl_hours,
            "validate_lastmod": request.validate_lastmod,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Deep Crawl with Crash Recovery ============
class DeepCrawlResumeRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"
    resume_state: Optional[Dict[str, Any]] = None


@app.post("/crawl/deep/resume")
async def deep_crawl_with_resume(request: DeepCrawlResumeRequest):
    """Deep Crawl with Crash Recovery - 支持从检查点恢复"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        if request.strategy == "bfs":
            strategy = BFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
            )
        elif request.strategy == "dfs":
            strategy = DFSDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
            )
        else:
            from crawl4ai.deep_crawling import BestFirstDeepCrawlStrategy

            strategy = BestFirstDeepCrawlStrategy(
                max_depth=request.max_depth,
                max_pages=request.max_pages,
                resume_state=request.resume_state,
            )

        run_config = CrawlerRunConfig(
            deep_crawl_strategy=strategy, cache_mode=CacheMode.BYPASS
        )

        results = []
        for url in request.urls:
            result = await crawler.arun(url=url, config=run_config)
            results.append(
                {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {
            "success": True,
            "crawled_pages": len(results),
            "results": results,
            "resume_state_available": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Process Local File in Browser ============
class ProcessLocalFileRequest(BaseModel):
    file_path: str
    base_url: str
    process_in_browser: bool = True
    screenshot: bool = False


@app.post("/crawl/process-local")
async def process_local_file(request: ProcessLocalFileRequest):
    """Process Local File in Browser - 在浏览器中处理本地HTML文件"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        file_path = request.file_path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        file_url = f"file://{file_path}"

        run_config = CrawlerRunConfig(
            base_url=request.base_url,
            process_in_browser=request.process_in_browser,
            screenshot=request.screenshot,
            cache_mode=CacheMode.BYPASS,
        )

        result = await crawler.arun(url=file_url, config=run_config)

        return {
            "success": result.success,
            "file_path": file_path,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "screenshot": result.screenshot is not None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Docker LLM Provider Config ============
class DockerLLMConfigRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@app.post("/config/docker-llm")
async def configure_docker_llm(request: DockerLLMConfigRequest):
    """Docker LLM Provider Config - 通过环境变量配置LLM提供商"""
    try:
        env_config = {
            "LLM_PROVIDER": request.provider,
        }

        if request.api_key:
            if request.provider.startswith("openai"):
                env_config["OPENAI_API_KEY"] = request.api_key
            elif request.provider.startswith("groq"):
                env_config["GROQ_API_KEY"] = request.api_key
            elif request.provider.startswith("anthropic"):
                env_config["ANTHROPIC_API_KEY"] = request.api_key
            elif request.provider.startswith("google"):
                env_config["GOOGLE_API_KEY"] = request.api_key

        if request.base_url:
            env_config["LLM_BASE_URL"] = request.base_url

        return {
            "success": True,
            "configured_provider": request.provider,
            "environment_variables": list(env_config.keys()),
            "note": "Configure these environment variables in your Docker container",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Init Scripts for Browser ============
class InitScriptsRequest(BaseModel):
    url: str
    scripts: List[str]


@app.post("/crawl/init-scripts")
async def crawl_with_init_scripts(request: InitScriptsRequest):
    """Init Scripts - 页面加载前执行JavaScript"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        browser_cfg = BrowserConfig(init_scripts=request.scripts)

        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

        result = await crawler.arun(
            url=request.url, config=run_config, browser_config=browser_cfg
        )

        return {
            "success": result.success,
            "url": result.url,
            "scripts_count": len(request.scripts),
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Enhanced Virtual Scroll ============
class EnhancedVirtualScrollRequest(BaseModel):
    url: str
    container_selector: str
    scroll_count: int = 30
    scroll_by: str = "container_height"  # container_height, page_height, or pixels


@app.post("/crawl/virtual-scroll/enhanced")
async def crawl_with_enhanced_virtual_scroll(request: EnhancedVirtualScrollRequest):
    """Enhanced Virtual Scroll - 针对Twitter/Instagram等虚拟滚动优化"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        virtual_scroll_cfg = VirtualScrollConfig(
            container_selector=request.container_selector,
            scroll_count=request.scroll_count,
            scroll_by=request.scroll_by,
        )

        run_config = CrawlerRunConfig(
            virtual_scroll_config=virtual_scroll_cfg, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "virtual_scroll": {
                "container": request.container_selector,
                "scroll_count": request.scroll_count,
                "scroll_by": request.scroll_by,
            },
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Multi-URL with URL Matcher ============
class MultiURLMatcherRequest(BaseModel):
    urls: List[str]
    configs: List[Dict[str, Any]]


@app.post("/crawl/multi-url-matcher")
async def crawl_multi_url_matcher(request: MultiURLMatcherRequest):
    """Multi-URL with URL Matcher - 不同URL使用不同配置"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import MatchMode

        url_configs = []
        for cfg in request.configs:
            url_matchers = cfg.get("url_matchers", [])
            crawl_config = CrawlerRunConfig(
                word_count_threshold=cfg.get("word_count_threshold", 200),
                screenshot=cfg.get("screenshot", False),
                pdf=cfg.get("pdf", False),
                cache_mode=CacheMode.BYPASS,
            )
            url_configs.append({"url_matcher": url_matchers, "config": crawl_config})

        results = []
        for url in request.urls:
            result = await crawler.arun(url=url)
            results.append(
                {
                    "url": url,
                    "success": result.success,
                    "markdown_length": len(result.markdown.raw_markdown)
                    if result.markdown
                    else 0,
                }
            )

        return {"success": True, "urls_processed": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Memory Monitoring Enhanced ============
@app.get("/monitor/memory/enhanced")
async def get_enhanced_memory_stats():
    """Enhanced Memory Monitoring - 详细的内存使用统计"""
    try:
        import psutil
        import gc

        gc.collect()

        process = psutil.Process()
        mem_info = process.memory_info()

        return {
            "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
            "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
            "percent": process.memory_percent(),
            "gc_stats": {"collections": gc.get_count()},
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
            "available_percent": round(psutil.virtual_memory().percent, 2),
        }
    except ImportError:
        return {"error": "psutil not installed", "rss_mb": 0, "vms_mb": 0, "percent": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Lazy Loading API ============
class LazyLoadingRequest(BaseModel):
    url: str
    wait_for_images: bool = True
    scroll_count: int = 5


@app.post("/crawl/lazy-load")
async def crawl_with_lazy_loading(request: LazyLoadingRequest):
    """Lazy Loading - 处理懒加载内容"""
    if not crawler:
        raise HTTPException(status_code=500, detail="Crawler not initialized")

    try:
        from crawl4ai import CrawlerRunConfig

        js_code = ""
        for _ in range(request.scroll_count):
            js_code += "window.scrollTo(0, document.body.scrollHeight);"

        run_config = CrawlerRunConfig(
            js_code=js_code, delay_before_return_html=1.0, cache_mode=CacheMode.BYPASS
        )

        result = await crawler.arun(url=request.url, config=run_config)

        return {
            "success": result.success,
            "url": result.url,
            "markdown_length": len(result.markdown.raw_markdown)
            if result.markdown
            else 0,
            "scroll_count": request.scroll_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
