// Backend API configuration
// Set this to your Python backend URL, or leave empty to use local crawler

let backendConfig = {
  enabled: false,
  url: 'http://localhost:8001',
};

export const setBackendConfig = (config: { enabled: boolean; url: string }) => {
  backendConfig = config;
};

export const getBackendConfig = () => backendConfig;

export const API_CONFIG = {
  get backendUrl() { return backendConfig.url; },
  get useBackend() { return backendConfig.enabled; },
  timeout: 60000,
};

export interface BackendCrawlRequest {
  url: string;
  priority?: number;
  word_count_threshold?: number;
  wait_for?: string;
  js_code?: string[];
  screenshot?: boolean;
  pdf?: boolean;
}

export interface BackendDeepCrawlRequest {
  urls: string[];
  max_depth?: number;
  max_pages?: number;
  strategy?: 'bfs' | 'dfs' | 'best_first';
  priority?: number;
}

export interface BackendExtractRequest {
  url: string;
  instruction: string;
  schema?: Record<string, unknown>;
  provider?: string;
  api_key?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface BackendCrawlResult {
  success: boolean;
  url: string;
  markdown?: string;
  fit_markdown?: string;
  html?: string;
  links?: string[];
  images?: string[];
  videos?: string[];
  extracted_content?: string;
  screenshot?: string;
  error?: string;
}

export interface TestLLMRequest {
  provider: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  test_prompt?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface TestLLMResponse {
  success: boolean;
  message?: string;
  response?: string;
  error?: string;
  model?: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface AvailableModels {
  openai?: string[];
  anthropic?: string[];
  google?: string[];
  ollama?: string[];
  [key: string]: string[] | undefined;
}

export interface LLMProviderInfo {
  name: string;
  models: string[];
  requires_api_key: boolean;
  supports_base_url: boolean;
}

// Check if backend is available
export async function checkBackendHealth(): Promise<boolean> {
  if (!API_CONFIG.useBackend || !API_CONFIG.backendUrl) {
    return false;
  }
  
  try {
    const response = await fetch(`${API_CONFIG.backendUrl}/health`, {
      method: 'GET',
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Crawl using backend API
export async function crawlWithBackend(request: BackendCrawlRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Deep crawl using backend API
export async function deepCrawlWithBackend(request: BackendDeepCrawlRequest): Promise<BackendCrawlResult[]> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/deep`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// E-commerce extraction types
export interface EcommerceExtractRequest {
  url: string;
  platform?: 'auto' | 'amazon' | 'ebay' | 'taobao' | 'tmall' | 'jd' | 'shopify' | 'aliexpress' | '1688';
  extraction_type?: 'all' | 'listings' | 'prices';
  provider?: string;
  api_key?: string;
  max_items?: number;
  cookies?: { name: string; value: string }[];
}

export interface EcommerceProduct {
  product_name?: string;
  price?: string;
  original_price?: string;
  rating?: string;
  review_count?: number;
  sales?: string;
  shop_name?: string;
  availability?: string;
  image_url?: string;
  product_url?: string;
  [key: string]: any;
}

export interface EcommerceExtractResponse {
  success: boolean;
  url: string;
  platform: string;
  listings?: EcommerceProduct[];
  error?: string;
}

// E-commerce CSS extraction (fast, no LLM)
export interface EcommerceCSSRequest {
  url: string;
  platform?: 'auto' | 'amazon' | 'jd' | 'taobao' | 'tmall' | 'shopify';
  scroll_count?: number;
}

export interface EcommerceCSSResponse {
  success: boolean;
  url: string;
  platform: string;
  listings: any[];
  count: number;
  error?: string;
}

// Extract e-commerce data using CSS (fast, no LLM)
export async function extractEcommerceCSS(request: EcommerceCSSRequest): Promise<EcommerceCSSResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/ecommerce/css`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Extract e-commerce data (listings and prices)
export async function extractEcommerce(request: EcommerceExtractRequest): Promise<EcommerceExtractResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/ecommerce`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// E-commerce seller deep crawl types
export interface EcommerceSellerCrawlRequest {
  url: string;
  platform?: 'auto' | 'amazon' | 'ebay' | 'taobao' | 'tmall' | 'jd' | 'shopify' | 'aliexpress' | 'tiktok';
  max_pages?: number;
  max_items?: number;
  crawl_products?: boolean;
  crawl_reviews?: boolean;
  provider?: string;
  api_key?: string;
}

export interface EcommerceSellerResponse {
  success: boolean;
  url: string;
  platform: string;
  seller_info?: Record<string, any>;
  products?: EcommerceProduct[];
  reviews?: Record<string, any>[];
  total_products: number;
  error?: string;
}

// E-commerce seller deep crawl
export async function ecommerceSellerDeepCrawl(request: EcommerceSellerCrawlRequest): Promise<EcommerceSellerResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/ecommerce/seller`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Extract using LLM with backend API
export async function extractWithLLM(request: BackendExtractRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Batch crawl using backend API
export async function batchCrawlWithBackend(urls: string[]): Promise<BackendCrawlResult[]> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(urls),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Get available models from backend
export async function getAvailableModels(ollamaUrl?: string): Promise<AvailableModels> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  let url = `${API_CONFIG.backendUrl}/llm/models`;
  if (ollamaUrl) {
    url += `?ollama_url=${encodeURIComponent(ollamaUrl)}`;
  }
  
  const response = await fetch(url, {
    method: 'GET',
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Get available LLM providers
export async function getLLMProviders(): Promise<LLMProviderInfo[]> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/llm/providers`, {
    method: 'GET',
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.providers;
}

// Test LLM connection
export async function testLLMConnection(request: TestLLMRequest): Promise<TestLLMResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/llm/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Playwright crawl types
export interface PlaywrightCrawlRequest {
  url: string;
  wait_for?: string;
  wait_timeout?: number;
  scroll_count?: number;
  screenshot?: boolean;
  cookies?: { name: string; value: string }[];
}

// Playwright crawl using backend API
export async function playwrightCrawl(request: PlaywrightCrawlRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/playwright`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Adaptive Crawling API ============

export interface AdaptiveCrawlRequest {
  url: string;
  query: string;
  confidence_threshold?: number;
  max_pages?: number;
  top_k_links?: number;
  min_gain_threshold?: number;
  strategy?: 'statistical' | 'embedding';
  save_state?: boolean;
  state_path?: string;
  resume_from?: string;
}

export interface AdaptiveCrawlResult {
  success: boolean;
  url: string;
  query: string;
  confidence: number;
  pages_crawled: number;
  stopped_reason: string;
  results: any[];
  coverage_score: number;
  saturation_score: number;
  consistency_score: number;
}

export interface AdaptiveRelevantPage {
  url: string;
  content: string;
  score: number;
}

export interface AdaptiveRelevantResponse {
  success: boolean;
  confidence: number;
  pages_crawled: number;
  stopped_reason: string;
  relevant_pages: AdaptiveRelevantPage[];
}

// Adaptive crawl using backend API
export async function adaptiveCrawl(request: AdaptiveCrawlRequest): Promise<AdaptiveCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/adaptive`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Get adaptive crawl relevant content
export async function getAdaptiveRelevantContent(
  url: string,
  query: string,
  confidenceThreshold: number = 0.7,
  maxPages: number = 20,
  topKLinks: number = 3,
  strategy: 'statistical' | 'embedding' = 'statistical',
  topK: number = 5
): Promise<AdaptiveRelevantResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const params = new URLSearchParams({
    url,
    query,
    confidence_threshold: confidenceThreshold.toString(),
    max_pages: maxPages.toString(),
    top_k_links: topKLinks.toString(),
    strategy,
    top_k: topK.toString(),
  });
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/adaptive/relevant?${params}`, {
    method: 'GET',
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Virtual Scroll API ============

export interface VirtualScrollRequest {
  url: string;
  container_selector: string;
  scroll_count?: number;
  scroll_by?: 'container_height' | 'page_height' | string;
  wait_after_scroll?: number;
  screenshot?: boolean;
}

// Virtual scroll crawl using backend API
export async function virtualScrollCrawl(request: VirtualScrollRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/virtual-scroll`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Session-based Crawling API ============

export interface SessionCrawlRequest {
  urls: string[];
  session_id: string;
  js_code?: string[];
  wait_for?: string;
  css_selector?: string;
  capture_console?: boolean;
}

// Session-based crawl using backend API
export async function sessionCrawl(request: SessionCrawlRequest): Promise<BackendCrawlResult[]> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Chunking API ============

export interface ChunkTextRequest {
  text: string;
  method: 'regex' | 'sentence' | 'fixed' | 'sliding';
  chunk_size?: number;
  step?: number;
  patterns?: string[];
}

export interface ChunkResult {
  chunks: string[];
  count: number;
}

// Text chunking using backend API
export async function chunkText(request: ChunkTextRequest): Promise<ChunkResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/chunk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Semantic Search API ============

export interface SemanticSearchRequest {
  text: string;
  query: string;
  top_k?: number;
}

export interface SemanticSearchResultItem {
  text: string;
  score: number;
  index: number;
}

export interface SemanticSearchResult {
  query: string;
  results: SemanticSearchResultItem[];
}

// Semantic search using backend API
export async function semanticSearch(request: SemanticSearchRequest): Promise<SemanticSearchResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/search/semantic`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ URL Seeding API ============

export interface UrlSeedRequest {
  domain: string;
  source?: 'sitemap' | 'cc' | 'sitemap+cc';
  pattern?: string;
  extract_head?: boolean;
  max_urls?: number;
  query?: string;
  scoring_method?: string;
  score_threshold?: number;
  live_check?: boolean;
}

export interface UrlSeedResult {
  domain: string;
  count: number;
  urls: {
    url: string;
    status: string;
    head_data?: any;
    relevance_score?: number;
  }[];
}

// URL Seeding using backend API
export async function seedUrls(request: UrlSeedRequest): Promise<UrlSeedResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/seed/urls`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Multi-domain URL Seeding
export interface MultiUrlSeedRequest {
  domains: string[];
  source?: 'sitemap' | 'cc' | 'sitemap+cc';
  pattern?: string;
  extract_head?: boolean;
  max_urls?: number;
  query?: string;
  scoring_method?: string;
  score_threshold?: number;
}

export interface MultiUrlSeedResult {
  results: Record<string, any[]>;
  total_domains: number;
  total_urls: number;
}

// Multi-domain URL Seeding using backend API
export async function seedUrlsMany(request: MultiUrlSeedRequest): Promise<MultiUrlSeedResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/seed/urls/many`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Batch Crawl API ============

export interface BatchCrawlRequest {
  urls: string[];
  dispatcher_type?: 'memory_adaptive' | 'semaphore';
  memory_threshold?: number;
  max_concurrent?: number;
  use_rate_limiter?: boolean;
  rate_limit_delay?: [number, number];
  rate_limit_max_delay?: number;
  stream?: boolean;
}

export interface BatchCrawlResult {
  url: string;
  success: boolean;
  markdown_length: number;
  error?: string;
}

// Batch crawl using backend API
export async function batchCrawl(request: BatchCrawlRequest): Promise<BatchCrawlResult[]> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ C4A-Script API ============

export interface C4AScriptRequest {
  script: string;
  url?: string;
}

// Execute C4A-Script using backend API
export async function executeC4AScript(request: C4AScriptRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/c4a-script`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Advanced Extraction APIs ============

export interface CSSExtractionRequest {
  url: string;
  schema: Record<string, any>;
}

export interface XPathExtractionRequest {
  url: string;
  schema: Record<string, any>;
}

export interface RegexExtractionRequest {
  url: string;
  pattern?: string;
  custom_patterns?: Record<string, string>;
}

export interface SchemaGenerationRequest {
  url?: string;
  html?: string;
  query: string;
  schema_type?: 'css' | 'xpath';
  provider?: string;
  model?: string;
}

export interface AdvancedCrawlRequest {
  url: string;
  screenshot?: boolean;
  pdf?: boolean;
  headers?: Record<string, string>;
  enable_stealth?: boolean;
  use_undetected_browser?: boolean;
  check_robots_txt?: boolean;
  proxy?: string;
  proxy_username?: string;
  proxy_password?: string;
  fetch_ssl_certificate?: boolean;
  capture_network?: boolean;
  capture_console?: boolean;
  simulate_user?: boolean;
  magic?: boolean;
  override_navigator?: boolean;
  wait_time?: number;
  delay_before_return_html?: number;
  page_timeout?: number;
  session_id?: string;
  use_browser?: boolean;
  word_count_threshold?: number;
}

// CSS Extraction
export async function extractWithCSS(request: CSSExtractionRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/css`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// XPath Extraction
export async function extractWithXPath(request: XPathExtractionRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/xpath`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Regex Extraction
export async function extractWithRegex(request: RegexExtractionRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/regex`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Generate Schema with LLM
export async function generateSchema(request: SchemaGenerationRequest): Promise<{success: boolean; schema: any; schema_type: string}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/generate-schema`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Advanced Crawl with screenshot, PDF, stealth, etc.
export async function advancedCrawl(request: AdvancedCrawlRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/advanced`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Capture Screenshot
export async function captureScreenshot(url: string): Promise<{success: boolean; url: string; screenshot: string | null}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/screenshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, screenshot: true }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Capture PDF
export async function capturePDF(url: string): Promise<{success: boolean; url: string; pdf: string | null}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/page-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, pdf: true }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// Get extraction strategies status
export async function getExtractionStatus(): Promise<{extraction_strategies_available: boolean; strategies: Record<string, boolean>}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/llm/status`);
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Hooks API ============
export interface HooksCrawlRequest {
  url: string;
  on_browser_created?: string;
  on_page_context_created?: string;
  before_goto?: string;
  after_goto?: string;
  on_execution_started?: string;
  before_retrieve_html?: string;
  before_return_html?: string;
  screenshot?: boolean;
  pdf?: boolean;
  wait_for?: string;
}

export async function crawlWithHooks(request: HooksCrawlRequest): Promise<BackendCrawlResult> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/hooks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Session Management API ============
export interface SessionRequest {
  action: 'export' | 'import';
  session_id: string;
  storage_state?: Record<string, any>;
}

export interface SessionResponse {
  success: boolean;
  session_id: string;
  storage_state?: Record<string, any>;
  message?: string;
}

export async function manageSession(request: SessionRequest): Promise<SessionResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/session/manage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Multi-page Schema Generation API ============
export interface MultiPageSchemaRequest {
  html_samples: string[];
  query: string;
  schema_type?: 'css' | 'xpath';
  provider?: string;
  model?: string;
}

export async function generateMultiPageSchema(request: MultiPageSchemaRequest): Promise<{success: boolean; schema: any; schema_type: string; sample_count: number}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/schema/multi-page`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Token Usage API ============
export async function getTokenUsage(): Promise<{prompt_tokens: number; completion_tokens: number; total_tokens: number; message?: string}> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/llm/token-usage`);
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Anti-Bot Fallback API ============
export interface AntiBotRequest {
  url: string;
  max_retries?: number;
  proxies?: string[];
  enable_stealth?: boolean;
  magic?: boolean;
}

export interface AntiBotResponse {
  success: boolean;
  url: string;
  markdown?: string;
  html?: string;
  crawl_stats: {
    attempts: number;
    retries: number;
    proxies_used: any[];
    resolved_by: string;
    fallback_fetch_used: boolean;
  };
  error?: string;
}

export async function crawlWithAntiBot(request: AntiBotRequest): Promise<AntiBotResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/anti-bot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Filter Chain API ============
export interface FilterRequest {
  url: string;
  patterns?: string[];
  allowed_domains?: string[];
  blocked_domains?: string[];
  content_types?: string[];
  max_depth?: number;
  max_pages?: number;
  strategy?: 'bfs' | 'dfs' | 'best_first';
}

export interface FilterResponse {
  success: boolean;
  url: string;
  pages_crawled: number;
  results: Array<{url: string; depth: number; markdown_length: number}>;
}

export async function crawlWithFilter(request: FilterRequest): Promise<FilterResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/filter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Prefetch Mode API ============
export interface PrefetchRequest {
  url: string;
  max_pages?: number;
}

export interface PrefetchResponse {
  success: boolean;
  url: string;
  internal_links: string[];
  external_links: string[];
  total_internal: number;
  total_external: number;
}

export async function prefetchUrls(request: PrefetchRequest): Promise<PrefetchResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/prefetch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Deep Crawl State Management API ============
export interface DeepCrawlStateRequest {
  action: 'save' | 'resume' | 'cancel';
  state?: Record<string, any>;
  crawl_config?: Record<string, any>;
}

export interface DeepCrawlStateResponse {
  success: boolean;
  state_id?: string;
  message?: string;
  pages_crawled?: number;
  results?: Array<{url: string; depth: number}>;
}

export async function manageDeepCrawlState(request: DeepCrawlStateRequest): Promise<DeepCrawlStateResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Research Assistant API ============
export interface ResearchRequest {
  urls: string[];
  query: string;
  top_k?: number;
  provider?: string;
  model?: string;
}

export interface ResearchResponse {
  success: boolean;
  query: string;
  pages_analyzed: number;
  relevant_pages: Array<{url: string; content: string; content_length: number}>;
}

export async function researchAssistant(request: ResearchRequest): Promise<ResearchResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/research/assistant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Page Summarization API ============
export interface SummarizeRequest {
  url?: string;
  html?: string;
  provider?: string;
  model?: string;
  instruction?: string;
}

export interface SummarizeResponse {
  success: boolean;
  url?: string;
  summary?: string;
  full_content?: string;
}

export async function summarizePage(request: SummarizeRequest): Promise<SummarizeResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/content/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Knowledge Base API ============
export interface KnowledgeBaseRequest {
  action: 'collect' | 'export' | 'clear';
  urls?: string[];
  query?: string;
}

export interface KnowledgeBaseResponse {
  success: boolean;
  pages_collected?: number;
  query?: string;
  knowledge_base?: Array<{url: string; content: string; fit_content?: string}>;
  total_pages?: number;
  message?: string;
}

export async function manageKnowledgeBase(request: KnowledgeBaseRequest): Promise<KnowledgeBaseResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/knowledge/base`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Crawl Dispatcher API ============
export interface DispatchRequest {
  urls: string[];
  max_concurrent?: number;
  strategy?: 'parallel' | 'sequential';
}

export interface DispatchResponse {
  success: boolean;
  total_urls: number;
  strategy: string;
  results: Array<{url: string; success: boolean; markdown_length: number; error?: string}>;
}

export async function crawlDispatcher(request: DispatchRequest): Promise<DispatchResponse> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Advanced Browser Config API ============
export interface AdvancedBrowserRequest {
  url: string;
  browser_type?: 'chromium' | 'firefox' | 'webkit';
  browser_mode?: 'dedicated' | 'builtin' | 'custom' | 'docker';
  headless?: boolean;
  viewport_width?: number;
  viewport_height?: number;
  device_scale_factor?: number;
  text_mode?: boolean;
  light_mode?: boolean;
  user_agent?: string;
  user_agent_mode?: string;
  proxy?: string;
  enable_stealth?: boolean;
}

export async function crawlWithAdvancedBrowser(request: AdvancedBrowserRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/advanced-browser`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ MHTML Capture API ============
export async function captureMHTML(url: string): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/mhtml`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Geolocation API ============
export async function crawlWithGeolocation(url: string, lat: number, lng: number): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/geolocation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, latitude: lat, longitude: lng }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Shadow DOM API ============
export async function crawlWithShadowDOM(url: string, flatten: boolean = true): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/shadow-dom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, flatten_shadow_dom: flatten }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Multi-URL Config API ============
export interface MultiURLConfigRequest {
  urls: string[];
  word_count_threshold?: number;
  wait_for?: string;
  screenshot?: boolean;
  url_patterns?: string[];
  match_mode?: 'OR' | 'AND';
}

export async function crawlMultiURLConfig(request: MultiURLConfigRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/multi-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ LLM Provider Config API ============
export async function llmGenerateMarkdown(url: string, provider?: string, instruction?: string): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/llm/generate-markdown`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, provider, instruction }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ URL Seeding API ============
export interface URLSeedingRequest {
  domain: string;
  source?: 'cc' | 'sitemap' | 'sitemap+cc';
  pattern?: string;
  extract_head?: boolean;
  live_check?: boolean;
  max_urls?: number;
  query?: string;
  scoring_method?: string;
  score_threshold?: number;
}

export async function urlSeeding(request: URLSeedingRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/url/seeding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Multi-Domain URL Seeding API ============
export interface MultiDomainSeedingRequest {
  domains: string[];
  source?: string;
  pattern?: string;
  extract_head?: boolean;
  max_urls_per_domain?: number;
  query?: string;
  scoring_method?: string;
  score_threshold?: number;
}

export async function multiDomainSeeding(request: MultiDomainSeedingRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/url/seeding/multi-domain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Cache Management API ============
export async function getCacheStats(): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/cache/stats`);
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

export async function manageCache(action: string, cacheType: string = 'all'): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/cache/manage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, cache_type: cacheType }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Media Extraction API ============
export interface MediaExtractionRequest {
  url: string;
  extract_images?: boolean;
  extract_videos?: boolean;
  extract_audio?: boolean;
}

export async function extractMedia(request: MediaExtractionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/media`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Virtual Scroll API ============
export interface VirtualScrollRequest {
  url: string;
  container_selector?: string;
  scroll_count?: number;
  scroll_by?: string;
  scroll_pixel?: number;
  wait_after_scroll?: number;
}

export async function crawlWithVirtualScroll(request: VirtualScrollRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/virtual-scroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Form Interaction API ============
export interface FormInteractionRequest {
  url: string;
  form_selector?: string;
  form_data: Record<string, string>;
  submit_selector?: string;
  wait_for?: string;
}

export async function crawlWithFormInteraction(request: FormInteractionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/form`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ IFrame Processing API ============
export async function crawlWithIFrame(url: string, processIframes: boolean = true): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/iframe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, process_iframes: processIframes }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Multi-Step Session API ============
export interface MultiStepSessionRequest {
  url: string;
  steps: Array<{js_code?: string; wait_for?: string; action?: string}>;
  session_id?: string;
}

export async function crawlMultiStep(request: MultiStepSessionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/multi-step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Clean Page API ============
export interface CleanPageRequest {
  url: string;
  remove_overlay_elements?: boolean;
  remove_consent_popups?: boolean;
}

export async function crawlCleanPage(request: CleanPageRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/clean`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Lazy Loading API ============
export interface LazyLoadingRequest {
  url: string;
  wait_for_images?: boolean;
  scroll_count?: number;
}

export async function crawlWithLazyLoading(request: LazyLoadingRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/lazy-load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Local File Crawl API ============
export interface LocalFileRequest {
  file_path: string;
  word_count_threshold?: number;
}

export async function crawlLocalFile(request: LocalFileRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/local-file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Raw HTML Crawl API ============
export interface RawHTMLRequest {
  html_content: string;
  word_count_threshold?: number;
}

export async function crawlRawHTML(request: RawHTMLRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/raw-html`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Batch Crawl API ============
export interface BatchCrawlRequest {
  urls: string[];
  stream?: boolean;
  word_count_threshold?: number;
  max_concurrent?: number;
}

export async function crawlBatch(request: BatchCrawlRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Content Selection API ============
export interface ContentSelectionRequest {
  url: string;
  only_text?: boolean;
  only_main_content?: boolean;
  remove_overlay_elements?: boolean;
  remove_consent_popups?: boolean;
}

export async function crawlWithContentSelection(request: ContentSelectionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/content-select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Clustering Extraction API ============
export interface ClusteringExtractionRequest {
  url: string;
  n_clusters?: number;
  extraction_type?: 'css' | 'xpath';
}

export async function clusteringExtraction(request: ClusteringExtractionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/clustering`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Proxy Rotation API ============
export interface ProxyRotationRequest {
  urls: string[];
  proxies: string[];
  strategy?: 'round_robin' | 'random';
  fetch_ssl?: boolean;
}

export async function crawlWithProxyRotation(request: ProxyRotationRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/proxy-rotation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Proxy from Environment API ============
export interface ProxyFromEnvRequest {
  urls: string[];
  env_variable?: string;
  strategy?: 'round_robin' | 'random';
}

export async function crawlWithProxyFromEnv(request: ProxyFromEnvRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/proxy-env`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ SSL Certificate Export API ============
export interface SSLCertRequest {
  url: string;
  proxy?: string;
  export_json?: boolean;
}

export async function crawlWithSSLExport(request: SSLCertRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/ssl-export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Proxy Validation API ============
export async function validateProxies(proxies: string[]): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/proxy/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proxies }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ SOCKS5 Proxy API ============
export interface SOCKS5ProxyRequest {
  url: string;
  proxy_host: string;
  proxy_port: number;
  username?: string;
  password?: string;
}

export async function crawlWithSOCKS5(request: SOCKS5ProxyRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/socks5`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Rate Limiter API ============
export interface RateLimiterConfigRequest {
  urls: string[];
  base_delay_min?: number;
  base_delay_max?: number;
  max_delay?: number;
  max_retries?: number;
}

export async function crawlWithRateLimiter(request: RateLimiterConfigRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/rate-limited`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Memory Adaptive Dispatcher API ============
export interface MemoryAdaptiveDispatcherRequest {
  urls: string[];
  memory_threshold?: number;
  check_interval?: number;
  max_concurrent?: number;
  stream?: boolean;
}

export async function crawlWithMemoryAdaptive(request: MemoryAdaptiveDispatcherRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/memory-adaptive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Semaphore Dispatcher API ============
export interface SemaphoreDispatcherRequest {
  urls: string[];
  semaphore_count?: number;
  stream?: boolean;
}

export async function crawlWithSemaphore(request: SemaphoreDispatcherRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/semaphore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ URL Specific Config API ============
export interface URLSpecificConfigRequest {
  urls: string[];
  configs: Record<string, any>[];
}

export async function crawlWithURLSpecificConfig(request: URLSpecificConfigRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/url-specific`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Crawler Monitor Stats API ============
export async function getMonitorStats(): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/monitor/stats`);
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Storage State API ============
export interface StorageStateRequest {
  action: 'export' | 'import';
  session_id: string;
  storage_state?: Record<string, any>;
}

export async function manageStorageState(request: StorageStateRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/session/storage-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Cookie Management API ============
export interface CookieRequest {
  url: string;
  cookies: Array<{name: string; value: string; domain?: string}>;
}

export async function manageCookies(request: CookieRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/session/cookies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Pagination Crawl API ============
export interface PaginationRequest {
  url: string;
  session_id?: string;
  pages?: number;
  next_button_selector?: string;
  item_selector: string;
}

export async function crawlWithPagination(request: PaginationRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/pagination`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Fit Markdown API ============
export async function crawlFitMarkdown(url: string, query: string): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/fit-markdown`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, query }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Cosine Similarity API ============
export interface CosineSimilarityRequest {
  url: string;
  semantic_filter: string;
  word_count_threshold?: number;
}

export async function extractWithCosine(request: CosineSimilarityRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/cosine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ DOM Selector API ============
export async function extractWithDOM(url: string, selector: string): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/dom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, selector }),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Table Extraction API ============
export interface TableExtractRequest {
  url: string;
  table_index?: number;
  as_dataframe?: boolean;
}

export async function extractTables(request: TableExtractRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/extract/tables`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Browser Mode API ============
export interface BrowserModeRequest {
  url: string;
  mode: 'dedicated' | 'builtin' | 'custom' | 'docker';
  cdp_url?: string;
}

export async function crawlWithBrowserMode(request: BrowserModeRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/browser-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Smart TTL Cache API ============
export interface SmartCacheRequest {
  sitemap_url: string;
  cache_ttl_hours?: number;
  validate_lastmod?: boolean;
}

export async function seedWithSmartCache(request: SmartCacheRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/seed/smart-cache`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Deep Crawl with Resume API ============
export interface DeepCrawlResumeRequest {
  urls: string[];
  max_depth?: number;
  max_pages?: number;
  strategy?: 'bfs' | 'dfs' | 'best_first';
  resume_state?: Record<string, unknown>;
}

export async function deepCrawlWithResume(request: DeepCrawlResumeRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/deep/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Process Local File API ============
export interface ProcessLocalFileRequest {
  file_path: string;
  base_url: string;
  process_in_browser?: boolean;
  screenshot?: boolean;
}

export async function processLocalFile(request: ProcessLocalFileRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/process-local`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Docker LLM Config API ============
export interface DockerLLMConfigRequest {
  provider: string;
  api_key?: string;
  base_url?: string;
}

export async function configureDockerLLM(request: DockerLLMConfigRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/config/docker-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Init Scripts API ============
export interface InitScriptsRequest {
  url: string;
  scripts: string[];
}

export async function crawlWithInitScripts(request: InitScriptsRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/init-scripts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Enhanced Virtual Scroll API ============
export interface EnhancedVirtualScrollRequest {
  url: string;
  container_selector: string;
  scroll_count?: number;
  scroll_by?: 'container_height' | 'page_height' | number;
}

export async function crawlWithEnhancedVirtualScroll(request: EnhancedVirtualScrollRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/virtual-scroll/enhanced`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Multi-URL Matcher API ============
export interface MultiURLMatcherConfig {
  url_matchers: string[];
  word_count_threshold?: number;
  screenshot?: boolean;
  pdf?: boolean;
}

export interface MultiURLMatcherRequest {
  urls: string[];
  configs: MultiURLMatcherConfig[];
}

export async function crawlMultiURLMatcher(request: MultiURLMatcherRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/multi-url-matcher`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Enhanced Memory Stats API ============
export async function getEnhancedMemoryStats(): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/monitor/memory/enhanced`, {
    method: 'GET',
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Prefetch Mode API ============
export interface PrefetchCrawlRequest {
  url: string;
  max_depth?: number;
  max_pages?: number;
  strategy?: 'bfs' | 'dfs';
}

export async function crawlWithPrefetch(request: PrefetchCrawlRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/prefetch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Text-Only Mode API ============
export interface TextOnlyRequest {
  url: string;
  word_count_threshold?: number;
}

export async function crawlTextOnly(request: TextOnlyRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/text-only`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Dynamic Viewport API ============
export interface DynamicViewportRequest {
  url: string;
  viewport_width?: number;
  viewport_height?: number;
  adjust_to_content?: boolean;
}

export async function crawlWithDynamicViewport(request: DynamicViewportRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/dynamic-viewport`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ CDP Connection API ============
export interface CDPConnectionRequest {
  action: 'create' | 'list' | 'connect' | 'close';
  cdp_url?: string;
}

export async function manageCDPConnection(request: CDPConnectionRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/cdp/connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Crash Recovery API ============
export interface CrashRecoveryRequest {
  url: string;
  max_depth?: number;
  max_pages?: number;
  strategy?: 'bfs' | 'dfs' | 'best_first';
  resume_state?: Record<string, unknown>;
  save_state_interval?: number;
}

export async function crawlWithCrashRecovery(request: CrashRecoveryRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/crash-recovery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Sticky Proxy API ============
export interface StickyProxyRequest {
  url: string;
  proxy: string;
  sticky_session?: boolean;
}

export async function crawlWithStickyProxy(request: StickyProxyRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/sticky-proxy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ HTTP Proxy API ============
export interface HTTPProxyRequest {
  url: string;
  proxy: string;
}

export async function crawlWithHTTPProxy(request: HTTPProxyRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/http-proxy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Full Page Scan API ============
export interface FullPageScanRequest {
  url: string;
  scroll_pause?: number;
}

export async function crawlWithFullPageScan(request: FullPageScanRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/full-scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Smart Auto-Crawl API ============
export interface SmartCrawlRequest {
  url: string;
  max_depth?: number;
  max_pages?: number;
  proxy?: string;
}

export async function smartAutoCrawl(request: SmartCrawlRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/auto`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ Analyze URL API ============
export interface AnalyzeUrlRequest {
  url: string;
}

export async function analyzeUrl(request: AnalyzeUrlRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}

// ============ HTTP Only Crawl API ============
export interface HTTPCrawlRequest {
  url: string;
  headers?: Record<string, string>;
}

export async function httpOnlyCrawl(request: HTTPCrawlRequest): Promise<any> {
  if (!API_CONFIG.backendUrl) {
    throw new Error('Backend URL not configured');
  }
  
  const response = await fetch(`${API_CONFIG.backendUrl}/crawl/http-only`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }
  
  return response.json();
}
