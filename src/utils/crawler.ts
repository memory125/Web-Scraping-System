const DEFAULT_PROXIES = [
  'https://api.allorigins.win/raw?url=',
  'https://corsproxy.io/?',
  'https://corsproxy.org/?',
  'https://api.codetabs.com/v1/proxy?quest=',
  'https://proxy.corshub.org/?',
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
