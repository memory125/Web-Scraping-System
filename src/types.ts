export type TargetStatus = 'pending' | 'scraping' | 'completed' | 'failed' | 'paused' | 'cancelled';

export interface ScrapedResult {
  title: string;
  wordCount: number;
  content: string;
  cleanedContent?: string;
  scrapedAt: string;
  description?: string;
  keywords?: string;
  links?: string[];
  images?: string[];
  videos?: string[];
  encoding?: string;
  extractedKeywords?: string[];
  summary?: string;
  category?: string;
  tags?: string[];
  sentiment?: 'positive' | 'negative' | 'neutral';
}

export interface Target {
  id: string;
  url: string;
  status: TargetStatus;
  result?: ScrapedResult;
  error?: string;
  parentUrl?: string;
  depth?: number;
  priority?: number;
  retryCount?: number;
  lastAttempt?: string;
}

export interface ResumeToken {
  targets: Target[];
  settings: Settings;
  completedIds: string[];
  failedIds: string[];
  timestamp: string;
}

export interface Settings {
  concurrency: number;
  timeout: number;
  proxy?: string;
  customProxies?: string[];
  useCustomProxiesOnly?: boolean;
  useProxy?: boolean;
  userAgent?: string;
  crawlDepth: number;
  autoDedup: boolean;
  cleanContent: boolean;
  deduplicateContent: boolean;
  extractMedia: boolean;
  randomDelay: boolean;
  minDelay: number;
  maxDelay: number;
  customCookies?: string;
  customReferer?: string;
  useJsRendering?: boolean;
  autoDetectEncoding?: boolean;
  maxConcurrentRequests?: number;
  followRobotsTxt?: boolean;
  respectNoFollow?: boolean;
  autoResume?: boolean;
  maxRetries?: number;
}

export interface ProxyPool {
  id: string;
  name: string;
  proxies: ProxyItem[];
  enabled: boolean;
}

export interface ProxyItem {
  url: string;
  enabled: boolean;
  lastUsed?: string;
  successCount: number;
  failCount: number;
  avgResponseTime?: number;
  lastCheck?: string;
  status?: 'active' | 'failed' | 'checking';
}

export interface Account {
  id: string;
  name: string;
  platform: string;
  username: string;
  cookie?: string;
  userAgent?: string;
  enabled: boolean;
  lastUsed?: string;
  successCount: number;
  failCount: number;
  createdAt: string;
}

export interface CrawlStrategy {
  id: string;
  name: string;
  settings: Partial<Settings>;
}

export interface DownloadTask {
  id: string;
  url: string;
  type: 'image' | 'video';
  filename?: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  progress?: number;
  error?: string;
}

export interface AppConfig {
  version: string;
  targets: Target[];
  settings: Settings;
  proxyPools?: ProxyPool[];
  accounts?: Account[];
  crawlStrategies?: CrawlStrategy[];
  downloadTasks?: DownloadTask[];
  resumeToken?: ResumeToken;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'debug' | 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export interface HistoryRecord {
  id: string;
  name: string;
  timestamp: string;
  targets: Target[];
  totalUrls: number;
  successCount: number;
  failedCount: number;
}

export interface ScheduledTask {
  id: string;
  name: string;
  urls: string[];
  schedule: string;
  enabled: boolean;
  lastRun?: string;
  nextRun?: string;
  strategyId?: string;
  priority?: number;
}

export type CrawlState = 'idle' | 'running' | 'paused' | 'finished';

export interface CookieSync {
  id: string;
  name: string;
  domain: string;
  cookie: string;
  enabled: boolean;
  lastSynced?: string;
  platform: string;
}

export interface AIAnalysis {
  id: string;
  targetId: string;
  viralElements?: string[];
  inspiration?: string;
  createdAt: string;
}

export interface StorageConfig {
  id: string;
  type: 'excel' | 'mysql' | 'json' | 'csv';
  name: string;
  enabled: boolean;
  config: {
    host?: string;
    port?: number;
    database?: string;
    username?: string;
    password?: string;
    tableName?: string;
    filePath?: string;
  };
}

export interface AIModelConfig {
  id: string;
  provider: 'openai' | 'anthropic' | 'google' | 'local' | 'custom';
  name: string;
  apiKey?: string;
  endpoint?: string;
  model: string;
  enabled: boolean;
  config: {
    temperature?: number;
    maxTokens?: number;
    topP?: number;
  };
}

export interface BackendConfig {
  enabled: boolean;
  url: string;
  authToken?: string;
}
