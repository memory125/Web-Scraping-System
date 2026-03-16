from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# ============ Request Models ============

class CrawlRequest(BaseModel):
    url: str
    word_count_threshold: int = 200
    wait_for: Optional[str] = None
    js_code: Optional[List[str]] = None
    screenshot: bool = False
    pdf: bool = False

class DeepCrawlRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"
    priority: int = 5

class ExtractRequest(BaseModel):
    url: str
    instruction: str
    schema: Optional[Dict[str, Any]] = None
    provider: str = "openai"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

class CSSExtractRequest(BaseModel):
    url: str
    selector: str
    attribute: Optional[str] = None

class XPathExtractRequest(BaseModel):
    url: str
    xpath: str

class EcommerceExtractRequest(BaseModel):
    url: str
    platform: str = "auto"

class BatchCrawlRequest(BaseModel):
    urls: List[str]
    concurrency: int = 3

class ProxyRequest(BaseModel):
    url: str
    proxy: str
    verify: bool = False

class SessionCrawlRequest(BaseModel):
    urls: List[str]
    session_id: str
    js_code: Optional[List[str]] = None
    wait_for: Optional[str] = None
    css_selector: Optional[str] = None

class PaginationCrawlRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    pages: int = 3
    next_button_selector: Optional[str] = None
    item_selector: str = "a"

class FitMarkdownRequest(BaseModel):
    url: str
    query: str

class CosineSimilarityRequest(BaseModel):
    url: str
    semantic_filter: str
    word_count_threshold: int = 200

class DOMExtractRequest(BaseModel):
    url: str
    selector: str

class TableExtractRequest(BaseModel):
    url: str
    table_index: int = 0
    as_dataframe: bool = True

class BrowserModeRequest(BaseModel):
    url: str
    mode: str = "dedicated"
    cdp_url: Optional[str] = None

class SmartCacheRequest(BaseModel):
    sitemap_url: str
    cache_ttl_hours: int = 24
    validate_lastmod: bool = True

class DeepCrawlResumeRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"
    resume_state: Optional[Dict[str, Any]] = None

class ProcessLocalFileRequest(BaseModel):
    file_path: str
    base_url: str
    process_in_browser: bool = True
    screenshot: bool = False

class DockerLLMConfigRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class InitScriptsRequest(BaseModel):
    url: str
    scripts: List[str]

class EnhancedVirtualScrollRequest(BaseModel):
    url: str
    container_selector: str
    scroll_count: int = 30
    scroll_by: str = "container_height"

class MultiURLMatcherRequest(BaseModel):
    urls: List[str]
    configs: List[Dict[str, Any]]

class LazyLoadingRequest(BaseModel):
    url: str
    wait_for_images: bool = True
    scroll_count: int = 5

class CleanPageRequest(BaseModel):
    url: str
    remove_overlay_elements: bool = True
    remove_consent_popups: bool = True

class VirtualScrollRequest(BaseModel):
    url: str
    container_selector: str
    scroll_count: int = 10
    scroll_by: str = "container_height"
    wait_after_scroll: int = 1000
    screenshot: bool = False

# ============ Response Models ============

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

class AdaptiveCrawlResult(BaseModel):
    success: bool
    url: str
    total_links: int
    relevant_links: List[str]
    extracted_data: Optional[Dict[str, Any]] = None

class ProfileResult(BaseModel):
    profiles: List[Dict[str, Any]]

class EcommerceResult(BaseModel):
    success: bool
    url: str
    products: List[Dict[str, Any]]
    total: int

class EcommerceSellerResult(BaseModel):
    success: bool
    seller_name: str
    products: List[Dict[str, Any]]
    total: int

class UrlSeedResult(BaseModel):
    success: bool
    urls_found: int
    urls: List[str]

class MultiUrlSeedResult(BaseModel):
    success: bool
    total_urls: int
    domains: Dict[str, int]

class SemanticSearchResult(BaseModel):
    success: bool
    query: str
    results: List[Dict[str, Any]]

class ChunkResult(BaseModel):
    success: bool
    chunks: List[str]
    count: int
