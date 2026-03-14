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
}

export interface LoginConfig {
  id: string;
  name: string;
  url: string;
  username: string;
  password: string;
  cookieName?: string;
  enabled: boolean;
}

export interface CrawlStrategy {
  id: string;
  name: string;
  settings: Partial<Settings>;
}

export interface AppConfig {
  version: string;
  targets: Target[];
  settings: Settings;
  proxyPools?: ProxyPool[];
  loginConfigs?: LoginConfig[];
  crawlStrategies?: CrawlStrategy[];
}

export interface LogEntry {
  id: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
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
