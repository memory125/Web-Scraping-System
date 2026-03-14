const DEFAULT_PROXIES = [
  'https://api.allorigins.win/raw?url=',
  'https://corsproxy.io/?',
  'https://corsproxy.org/?',
  'https://api.codetabs.com/v1/proxy?quest=',
  'https://proxy.corshub.org/?',
  'https://corsproxy.net/?',
  'https://allorigins.win/raw?url=',
  'https://api.allorigins.workers.dev/raw?url=',
];

export const PROXY_LIST = [
  { name: 'AllOrigins', url: 'https://api.allorigins.win/raw?url=' },
  { name: 'AllOrigins (Alt)', url: 'https://api.allorigins.workers.dev/raw?url=' },
  { name: 'CorsProxy.io', url: 'https://corsproxy.io/?' },
  { name: 'CorsProxy.org', url: 'https://corsproxy.org/?' },
  { name: 'CodeTabs', url: 'https://api.codetabs.com/v1/proxy?quest=' },
  { name: 'CorsHub', url: 'https://proxy.corshub.org/?' },
  { name: 'CorsProxy.net', url: 'https://corsproxy.net/?' },
  { name: 'GProxy', url: 'https://gproxy.io/?' },
  { name: 'Scrape-It', url: 'https://scrape-it.cloudflare-docs.workers.dev/?url=' },
];

const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
];

export interface CrawlOptions {
  timeout?: number;
  proxy?: string;
  customProxies?: string[];
  useCustomProxiesOnly?: boolean;
  useProxy?: boolean;
  retries?: number;
  userAgent?: string;
  cleanContent?: boolean;
  deduplicateContent?: boolean;
  extractMedia?: boolean;
  randomDelay?: boolean;
  minDelay?: number;
  maxDelay?: number;
  customCookies?: string;
  customReferer?: string;
  useJsRendering?: boolean;
  autoDetectEncoding?: boolean;
  extractKeywords?: boolean;
  generateSummary?: boolean;
  classifyContent?: boolean;
  analyzeSentiment?: boolean;
}

export interface CrawlResult {
  title: string;
  description?: string;
  keywords?: string;
  wordCount: number;
  content: string;
  cleanedContent?: string;
  links?: string[];
  images?: string[];
  videos?: string[];
  scrapedAt: string;
  error?: string;
  encoding?: string;
  extractedKeywords?: string[];
  summary?: string;
  category?: string;
  tags?: string[];
  sentiment?: 'positive' | 'negative' | 'neutral';
}

export interface SitemapResult {
  urls: string[];
  error?: string;
}

export interface FrequencyConfig {
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
  retryAfter429: number;
}

const DEFAULT_FREQUENCY_CONFIG: FrequencyConfig = {
  baseDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 1.5,
  retryAfter429: 5000,
};

let requestHistory: Record<string, { count: number; lastRequest: number; backoffUntil: number }> = {};

function getAdaptiveDelay(url: string, config: FrequencyConfig = DEFAULT_FREQUENCY_CONFIG): number {
  const now = Date.now();
  const domain = new URL(url).hostname;
  
  if (!requestHistory[domain]) {
    requestHistory[domain] = { count: 0, lastRequest: 0, backoffUntil: 0 };
  }
  
  const history = requestHistory[domain];
  
  if (now < history.backoffUntil) {
    return history.backoffUntil - now + Math.random() * 1000;
  }
  
  const timeSinceLastRequest = now - history.lastRequest;
  let delay = config.baseDelay;
  
  if (history.count > 10) {
    delay = Math.min(delay * config.backoffFactor, config.maxDelay);
  }
  
  if (timeSinceLastRequest < 1000) {
    delay = Math.max(delay, 1000 - timeSinceLastRequest);
  }
  
  history.count++;
  history.lastRequest = now;
  
  return delay + Math.random() * 500;
}

export function handleRateLimitResponse(url: string, status: number, config: FrequencyConfig = DEFAULT_FREQUENCY_CONFIG): void {
  const domain = new URL(url).hostname;
  
  if (status === 429 || status === 503) {
    if (requestHistory[domain]) {
      requestHistory[domain].backoffUntil = Date.now() + config.retryAfter429;
      requestHistory[domain].count = Math.max(requestHistory[domain].count, 5);
    }
  } else if (status >= 200 && status < 300) {
    if (requestHistory[domain]) {
      requestHistory[domain].count = Math.max(0, requestHistory[domain].count - 1);
    }
  }
}

export async function parseSitemap(url: string, useProxy: boolean = true): Promise<SitemapResult> {
  const sitemapUrls = [
    url.replace(/\/$/, '') + '/sitemap.xml',
    url.replace(/\/$/, '') + '/sitemap_index.xml',
    url.replace(/\/$/, '') + '/sitemap-news.xml',
    url + '/robots.txt',
  ];
  
  const urls: string[] = [];
  
  for (const sitemapUrl of sitemapUrls) {
    try {
      let fetchUrl = sitemapUrl;
      if (useProxy) {
        fetchUrl = DEFAULT_PROXIES[0] + encodeURIComponent(sitemapUrl);
      }
      
      const response = await fetch(fetchUrl, {
        headers: { 'User-Agent': getRandomUserAgent() },
      });
      
      if (!response.ok) continue;
      
      const text = await response.text();
      
      if (sitemapUrl.endsWith('robots.txt')) {
        const sitemapMatches = text.match(/Sitemap:\s*(\S+)/gi);
        if (sitemapMatches) {
          for (const match of sitemapMatches) {
            const sitemapLink = match.replace(/Sitemap:\s*/i, '');
            const subResult = await parseSitemap(sitemapLink, useProxy);
            urls.push(...subResult.urls);
          }
        }
        continue;
      }
      
      if (text.includes('<sitemapindex')) {
        const sitemapMatches = text.match(/<loc>([^<]+)<\/loc>/g);
        if (sitemapMatches) {
          for (const match of sitemapMatches) {
            const sitemapLink = match.replace(/<\/?loc>/g, '');
            const subResult = await parseSitemap(sitemapLink, useProxy);
            urls.push(...subResult.urls);
          }
        }
      } else if (text.includes('<urlset')) {
        const urlMatches = text.match(/<loc>([^<]+)<\/loc>/g);
        if (urlMatches) {
          for (const match of urlMatches) {
            const pageUrl = match.replace(/<\/?loc>/g, '');
            if (pageUrl.startsWith('http')) {
              urls.push(pageUrl);
            }
          }
        }
      }
    } catch {
      continue;
    }
  }
  
  return { urls: [...new Set(urls)] };
}

function getRandomUserAgent(): string {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

function cleanContent(text: string): string {
  if (!text) return '';
  
  let cleaned = text
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&hellip;/g, '...')
    .replace(/&copy;/g, '©')
    .replace(/&reg;/g, '®')
    .replace(/&trade;/g, '™')
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, '')
    .replace(/\u3000+/g, ' ')
    .replace(/[\r\n]+/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  
  return cleaned;
}

function filterNoiseLines(text: string): string {
  const lines = text.split('\n');
  const cleanedLines: string[] = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    if (trimmed.length < 3) continue;
    
    const skipPatterns = [
      /^[\d\.\,\;\:\-]+$/,
      /^[\u4e00-\u9fa5]{1,3}$/,
      /^https?:\/\//,
      /^Copyright/i,
      /^All rights reserved/i,
      /^热门推荐/i,
      /^相关文章/i,
      /^相关阅读/i,
      /^上一条/i,
      /^下一条/i,
      /^返回首页/i,
      /^了解更多/i,
      /^点击查看/i,
      /^查看详情/i,
      /^更多详情/i,
      /更多+/,
      /热门+/,
      /推荐+/,
      /热门+/,
      /推荐+/,
      /^IT之家/i,
      /^软媒产品/i,
      /^Win11/i,
      /^Win10/i,
      /^iOS/i,
      /^游戏喜加一/i,
      /^日榜/i,
      /^周榜/i,
      /^月榜/i,
      /立即下载/,
      /返回顶部/,
      /Copyright\s*\d{4}/i,
      /全栈工程师/,
      /前端开发/,
      /后端开发/,
      /技术博客/,
      /个人主页/,
      /RSS订阅/,
      /收藏本站/,
      /网站地图/,
      /联系我们/,
      /广告合作/,
      /友链交换/,
      /^var\s+/,
      /^let\s+/,
      /^const\s+/,
      /=>\s*\{/,
      /\{\s*$/,
      /^\s*\}/,
      /^\s*\{$/,
    ];
    
    let shouldSkip = false;
    for (const pattern of skipPatterns) {
      if (pattern.test(trimmed)) {
        shouldSkip = true;
        break;
      }
    }
    
    if (!shouldSkip) {
      cleanedLines.push(trimmed);
    }
  }
  
  return cleanedLines.join('\n\n');
}

const NOISE_SELECTORS = [
  'script', 'style', 'noscript',
];

function removeNoiseElements(doc: Document): void {
  NOISE_SELECTORS.forEach(selector => {
    try {
      doc.querySelectorAll(selector).forEach(el => el.remove());
    } catch {
    }
  });
}

function deduplicateContent(text: string): string {
  const paragraphs = text.split(/\n\s*\n/);
  const seenParagraphs = new Set<string>();
  const cleanParagraphs: string[] = [];
  
  for (const para of paragraphs) {
    const normalized = para.trim().toLowerCase();
    if (!seenParagraphs.has(normalized) && normalized.length > 20) {
      seenParagraphs.add(normalized);
      cleanParagraphs.push(para.trim());
    }
  }
  
  return cleanParagraphs.join('\n\n');
}

function extractMedia(doc: Document, baseUrl: string): { images: string[], videos: string[] } {
  const images: string[] = [];
  const videos: string[] = [];
  
  const base = new URL(baseUrl);
  
  doc.querySelectorAll('img[src]').forEach(img => {
    const src = img.getAttribute('src');
    if (src && !src.startsWith('data:')) {
      try {
        const resolved = new URL(src, baseUrl).href;
        if (!images.includes(resolved)) {
          images.push(resolved);
        }
      } catch {
      }
    }
  });
  
  doc.querySelectorAll('video source[src]').forEach(source => {
    const src = source.getAttribute('src');
    if (src) {
      try {
        const resolved = new URL(src, baseUrl).href;
        if (!videos.includes(resolved)) {
          videos.push(resolved);
        }
      } catch {
      }
    }
  });
  
  return { images, videos };
}

async function fetchWithProxy(url: string, options: CrawlOptions, proxyList: string[]): Promise<CrawlResult> {
  const { 
    timeout = 30000, 
    userAgent = getRandomUserAgent(),
    randomDelay = false,
    minDelay = 1000,
    maxDelay = 3000,
    customCookies,
    customReferer,
  } = options;
  
  if (randomDelay) {
    const delay = Math.floor(Math.random() * (maxDelay - minDelay + 1)) + minDelay;
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  for (let i = 0; i < proxyList.length; i++) {
    const proxy = proxyList[i];
    const proxyUrl = proxy + encodeURIComponent(url);
    
    const headers: Record<string, string> = {
      'User-Agent': userAgent,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
    };
    
    if (customCookies) {
      headers['Cookie'] = customCookies;
    }
    
    if (customReferer) {
      headers['Referer'] = customReferer;
    } else {
      headers['Referer'] = new URL(url).origin + '/';
    }
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(proxyUrl, {
        signal: controller.signal,
        headers,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();
      
      if (!html || html.trim().length === 0) {
        throw new Error('Empty response');
      }
      
      return parseHtml(html, url, options);
      
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      console.warn(`Proxy ${proxy} failed for ${url}:`, message);
      
      if (i === proxyList.length - 1) {
        return {
          title: '',
          wordCount: 0,
          content: '',
          scrapedAt: new Date().toISOString(),
          error: `All proxies failed. Last error: ${message}`,
        };
      }
    }
  }
  
  return {
    title: '',
    wordCount: 0,
    content: '',
    scrapedAt: new Date().toISOString(),
    error: 'All proxies failed',
  };
}

function decodeHtml(html: string): string {
  if (!html) return '';
  
  const utf8Match = html.match(/<meta[^>]*charset=["']?([^"'>\s]+)["']?/i);
  const charset = utf8Match ? utf8Match[1].toLowerCase() : '';
  
  if (charset && charset !== 'utf-8' && charset !== 'utf8') {
    try {
      const decoder = new TextDecoder(charset);
      const encoder = new TextEncoder();
      const bytes = encoder.encode(html);
      const decoded = decoder.decode(bytes);
      return decoded;
    } catch {
      return html;
    }
  }
  
  return html;
}

function cleanDescription(text: string): string {
  if (!text) return '';
  
  let cleaned = text
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&hellip;/g, '...')
    .replace(/\s+/g, ' ')
    .trim();
  
  const adPatterns = [
    /【.*?】/g,
    /\[.*?\]/g,
    /「.*?」/g,
    /『.*?』/g,
    /关注[^\s]{0,10}/g,
    /了解更多[^\s]{0,10}/g,
    /点击查看[^\s]{0,10}/g,
    /扫描二维码[^\s]*/g,
    /广告[^\s]*/gi,
    /推广[^\s]*/gi,
    /赞助[^\s]*/gi,
    /Sponsored/gi,
    /Advertisement/gi,
  ];
  
  adPatterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '');
  });
  
  cleaned = cleaned.replace(/^\s*[\d\-\.\,\。\、]+[\s\-\.\,\。\、]*/g, '')
    .replace(/\s*[\d\-\.\,\。\、]+[\s\-\.\,\。\、]*$/g, '')
    .replace(/^[\s\,\.\-\—]+|[\s\,\.\-\—]+$/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  
  return cleaned.length > 500 ? cleaned.substring(0, 500) + '...' : cleaned;
}

function parseHtml(html: string, url: string, options: CrawlOptions): CrawlResult {
  const decodedHtml = decodeHtml(html);
  const parser = new DOMParser();
  const doc = parser.parseFromString(decodedHtml, 'text/html');

  const title = doc.querySelector('title')?.textContent?.trim() 
    || doc.querySelector('h1')?.textContent?.trim() 
    || doc.querySelector('meta[property="og:title"]')?.getAttribute('content')
    || new URL(url).hostname;

  const rawDescription = doc.querySelector('meta[name="description"]')?.getAttribute('content')
    || doc.querySelector('meta[property="og:description"]')?.getAttribute('content')
    || '';
    
  const description = options.cleanContent !== false ? cleanDescription(rawDescription) : rawDescription;

  const keywords = doc.querySelector('meta[name="keywords"]')?.getAttribute('content') || '';

  const links = Array.from(doc.querySelectorAll('a[href]'))
    .map(a => a.getAttribute('href'))
    .filter(href => href && (href.startsWith('http://') || href.startsWith('https://')))
    .filter((value, index, self) => self.indexOf(value) === index);

  let body = doc.body?.textContent || '';
  if (!body || body.trim().length === 0) {
    body = doc.documentElement?.textContent || '';
  }
  
  const originalBody = body;
  let finalContent = originalBody;
  
  if (options.cleanContent !== false) {
    removeNoiseElements(doc);
    const cleanedBody = doc.body?.textContent || doc.documentElement?.textContent || '';
    finalContent = cleanContent(cleanedBody);
    if (options.deduplicateContent !== false && finalContent) {
      finalContent = deduplicateContent(finalContent);
    }
  }

  const wordCount = finalContent.trim().split(/\s+/).filter(word => word.length > 0).length;

  let images: string[] = [];
  let videos: string[] = [];
  
  if (options.extractMedia !== false) {
    const media = extractMedia(doc, url);
    images = media.images;
    videos = media.videos;
  }
  
  let encoding: string | undefined;
  let extractedKeywords: string[] | undefined;
  let summary: string | undefined;
  let category: string | undefined;
  let tags: string[] | undefined;
  let sentiment: 'positive' | 'negative' | 'neutral' | undefined;
  
  if (options.autoDetectEncoding !== false) {
    encoding = detectEncoding(html);
  }
  
  if (options.extractKeywords !== false && finalContent) {
    extractedKeywords = extractKeywords(finalContent);
  }
  
  if (options.generateSummary !== false && finalContent) {
    summary = generateSummary(finalContent);
  }
  
  if (options.classifyContent !== false && finalContent) {
    const classification = classifyContent(finalContent);
    category = classification.category;
    tags = classification.tags;
  }
  
  if (options.analyzeSentiment !== false && finalContent) {
    sentiment = analyzeSentiment(finalContent);
  }
  
  return {
    title,
    description,
    keywords,
    wordCount,
    content: finalContent,
    links,
    images: images.length > 0 ? images : undefined,
    videos: videos.length > 0 ? videos : undefined,
    scrapedAt: new Date().toISOString(),
    encoding,
    extractedKeywords,
    summary,
    category,
    tags,
    sentiment,
  };
}

export async function crawlUrl(url: string, options: CrawlOptions = {}): Promise<CrawlResult> {
  const { retries = 3, customProxies = [], useCustomProxiesOnly = false, useProxy = true } = options;
  
  if (!useProxy) {
    return crawlDirect(url, options);
  }
  
  const proxyList = useCustomProxiesOnly && customProxies.length > 0
    ? customProxies
    : [...customProxies, ...(options.proxy ? [options.proxy] : DEFAULT_PROXIES)];
  
  let lastError: string = '';
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    const result = await fetchWithProxy(url, {
      ...options,
      userAgent: options.userAgent || getRandomUserAgent(),
    }, proxyList);
    
    if (!result.error) {
      return result;
    }
    
    lastError = result.error;
    
    if (attempt < retries) {
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
  
  try {
    const directResult = await crawlDirect(url, options);
    if (!directResult.error) {
      return directResult;
    }
  } catch {}
  
  return {
    title: '',
    wordCount: 0,
    content: '',
    scrapedAt: new Date().toISOString(),
    error: `Failed after ${retries} attempts: ${lastError}`,
  };
}

async function crawlDirect(url: string, options: CrawlOptions): Promise<CrawlResult> {
  const { 
    timeout = 30000, 
    userAgent = getRandomUserAgent(),
    customCookies,
    customReferer,
  } = options;
  
  const headers: Record<string, string> = {
    'User-Agent': userAgent,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
  };
  
  if (customCookies) {
    headers['Cookie'] = customCookies;
  }
  
  if (customReferer) {
    headers['Referer'] = customReferer;
  }
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(url, { signal: controller.signal, headers });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const html = await response.text();
    
    if (!html || html.trim().length === 0) {
      throw new Error('Empty response');
    }
    
    return parseHtml(html, url, options);
    
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return {
      title: '',
      wordCount: 0,
      content: '',
      scrapedAt: new Date().toISOString(),
      error: message,
    };
  }
}

export function extractMetaTags(doc: Document): Record<string, string> {
  const meta: Record<string, string> = {};
  
  doc.querySelectorAll('meta').forEach(el => {
    const name = el.getAttribute('name') || el.getAttribute('property') || '';
    const content = el.getAttribute('content') || '';
    if (name && content) {
      meta[name] = content;
    }
  });
  
  return meta;
}

export function detectEncoding(html: string): string {
  const charsetMatch = html.match(/charset=["']?([^"'>\s]+)/i);
  if (charsetMatch) {
    return charsetMatch[1].toLowerCase();
  }
  
  const metaCharset = html.match(/<meta[^>]*charset=["']?([^"'>\s]+)/i);
  if (metaCharset) {
    return metaCharset[1].toLowerCase();
  }
  
  return 'utf-8';
}

const CHINESE_STOPWORDS = new Set([
  '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '里', '为', '什么', '可以', '这个', '那个', '他', '她', '它', '们', '这些', '那些', '与', '及', '或', '等', '但', '而', '如', '因', '所', '从', '以', '于', '对', '把', '被', '让', '使', '由', '向', '往', '在', '至', '自', '比', '更', '最', '已', '曾', '将', '正在', '曾', '还', '再', '又', '亦', '即', '若', '则', '如此', '怎么', '怎样', '如何', '为什么', '哪', '哪个', '哪些', '哪里', '谁', '多少', '几', '什么样', '其', '其中', '其它', '别的', '其他', '另外', '此外', '总之', '因此', '所以', '因为', '虽然', '但是', '然而', '不过', '只是', '只有', '除非', '无论', '不管', '尽管', '即使', '哪怕', '即使', '只要', '一旦', '万一'
]);

const ENGLISH_STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then', 'once', 'if', 'else', 'while', 'although', 'because', 'since', 'unless', 'until', 'after', 'before', 'above', 'below', 'between', 'under', 'over', 'through', 'during', 'about', 'into', 'out', 'off', 'up', 'down'
]);

export function extractKeywords(text: string, maxKeywords: number = 10): string[] {
  if (!text || text.length < 10) return [];
  
  const words = text.toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 1);
  
  const wordCount: Record<string, number> = {};
  
  for (const word of words) {
    const isChinese = /[\u4e00-\u9fa5]/.test(word);
    const stopwords = isChinese ? CHINESE_STOPWORDS : ENGLISH_STOPWORDS;
    
    if (!stopwords.has(word) && word.length > 1) {
      wordCount[word] = (wordCount[word] || 0) + 1;
    }
  }
  
  return Object.entries(wordCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxKeywords)
    .map(([word]) => word);
}

export function generateSummary(text: string, maxLength: number = 200): string {
  if (!text || text.length <= maxLength) return text;
  
  const sentences = text.split(/[。！？.!?]+/).filter(s => s.trim().length > 10);
  
  if (sentences.length === 0) {
    return text.substring(0, maxLength) + '...';
  }
  
  const scored = sentences.map((sentence, index) => {
    let score = sentence.length / 10;
    if (index === 0) score += 2;
    if (sentence.includes('主要') || sentence.includes('首先') || sentence.includes('总结')) score += 1;
    if (sentence.includes('本文') || sentence.includes('本文') || sentence.includes('介绍')) score += 1;
    return { sentence: sentence.trim(), score };
  });
  
  scored.sort((a, b) => b.score - a.score);
  
  let summary = '';
  for (const { sentence } of scored) {
    if (summary.length + sentence.length > maxLength) break;
    summary += sentence + '。';
  }
  
  if (!summary) {
    summary = text.substring(0, maxLength) + '...';
  }
  
  return summary;
}

const CATEGORY_KEYWORDS: Record<string, string[]> = {
  '科技': ['技术', '软件', '电脑', '手机', '互联网', 'AI', '人工智能', '编程', '代码', '开发', '程序', 'app', 'application', 'software', 'technology', 'tech', 'computer', 'phone', 'mobile', 'ai', 'artificial intelligence'],
  '财经': ['股票', '金融', '投资', '银行', '经济', '财富', '基金', '证券', '理财', '美元', '人民币', 'finance', 'stock', 'investment', 'bank', 'economy', 'money', 'market'],
  '娱乐': ['电影', '音乐', '游戏', '明星', '综艺', '电视剧', '演员', '歌手', '票房', 'movie', 'music', 'game', 'entertainment', 'star', 'actor', 'celebrity'],
  '体育': ['足球', '篮球', '跑步', '比赛', '运动员', '冠军', '奥运', 'sport', 'football', 'basketball', 'game', 'player', 'match', 'champion', 'olympics'],
  '新闻': ['新闻', '报道', '事件', '政府', '社会', '国际', '国内', 'news', 'report', 'event', 'government', 'society'],
  '教育': ['学校', '学生', '老师', '学习', '考试', '大学', '教育', '课程', 'school', 'student', 'teacher', 'education', 'learn', 'university', 'college'],
  '健康': ['医生', '医院', '健康', '疾病', '治疗', '药品', '身体', '医疗', 'health', 'medical', 'doctor', 'hospital', 'disease', 'medicine'],
  '汽车': ['汽车', '车', '驾驶', '车型', '新能源', '电动车', 'car', 'automobile', 'drive', 'vehicle', 'electric'],
  '房产': ['房子', '房价', '房地产', '购房', '装修', 'house', 'real estate', 'property', 'apartment', 'mortgage'],
  '美食': ['美食', '餐厅', '菜', '烹饪', '食材', 'food', 'restaurant', 'cook', 'recipe', 'cuisine'],
  '旅游': ['旅游', '旅行', '景点', '酒店', '机票', '攻略', 'travel', 'tourism', 'hotel', 'flight', 'trip', 'destination'],
  '时尚': ['时尚', '服装', '搭配', '美容', '化妆', '品牌', 'fashion', 'clothing', 'beauty', 'makeup', 'brand'],
};

export function classifyContent(text: string): { category: string; tags: string[] } {
  const textLower = text.toLowerCase();
  
  const scores: Record<string, number> = {};
  
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    scores[category] = 0;
    for (const keyword of keywords) {
      const regex = new RegExp(keyword, 'gi');
      const matches = textLower.match(regex);
      if (matches) {
        scores[category] += matches.length;
      }
    }
  }
  
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const category = sorted[0]?.[1] > 0 ? sorted[0][0] : '其他';
  
  const allKeywords = CATEGORY_KEYWORDS[category] || [];
  const tags = allKeywords
    .filter(kw => textLower.includes(kw.toLowerCase()))
    .slice(0, 5);
  
  return { category, tags };
}

const POSITIVE_WORDS = new Set([
  '好', '棒', '优秀', '精彩', '喜欢', '满意', '高兴', '快乐', '幸福', '成功', '伟大', '美丽', '漂亮', '完美', '赞', '支持', '感谢', '希望', '相信', '期待',
  'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'happy', 'joy', 'beautiful', 'perfect', 'awesome', 'best', 'better', 'success', 'thank', 'thanks', 'hope', 'believe', 'expect', 'support', 'agree', 'yes', 'correct', 'right'
]);

const NEGATIVE_WORDS = new Set([
  '差', '坏', '糟糕', '失望', '讨厌', '不满', '愤怒', '悲伤', '失败', '难过', '问题', '错误', 'bug', '崩溃', '失败', '垃圾', '烂',
  'bad', 'terrible', 'awful', 'hate', 'dislike', 'sad', 'angry', 'fail', 'wrong', 'error', 'bug', 'crash', 'problem', 'issue', 'worst', 'worse', 'fail', 'broken', 'stupid', 'ugly'
]);

export function analyzeSentiment(text: string): 'positive' | 'negative' | 'neutral' {
  const words = text.toLowerCase().split(/[\s,.\-:;!?，。、；：！？]+/);
  
  let positiveCount = 0;
  let negativeCount = 0;
  
  for (const word of words) {
    if (POSITIVE_WORDS.has(word)) positiveCount++;
    if (NEGATIVE_WORDS.has(word)) negativeCount++;
  }
  
  if (positiveCount > negativeCount + 2) return 'positive';
  if (negativeCount > positiveCount + 2) return 'negative';
  return 'neutral';
}
