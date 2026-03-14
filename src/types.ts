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
}

export interface Target {
  id: string;
  url: string;
  status: TargetStatus;
  result?: ScrapedResult;
  error?: string;
  parentUrl?: string;
  depth?: number;
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
}

export interface AppConfig {
  version: string;
  targets: Target[];
  settings: Settings;
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
}

export type CrawlState = 'idle' | 'running' | 'paused' | 'finished';
