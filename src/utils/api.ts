// Backend API configuration
// Set this to your Python backend URL, or leave empty to use local crawler

let backendConfig = {
  enabled: false,
  url: 'http://localhost:8000',
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
