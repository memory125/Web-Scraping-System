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
