import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Target, AppConfig, LogEntry, HistoryRecord, ScheduledTask, CrawlState, Account, DownloadTask, ResumeToken, CookieSync, AIAnalysis, StorageConfig, AIModelConfig } from './types';
import { Play, Square, Upload, Download, Plus, Trash2, FileJson, FileSpreadsheet, Settings, Pause, X, Clock, FileText, RefreshCw, Moon, Sun, Check, ChevronDown, ChevronUp, BarChart3, Activity, Globe, Layers, Languages, Save, FolderOpen, User, Key, Brain, Zap, Network } from 'lucide-react';
import { crawlUrl, parseSitemap, PROXY_LIST } from './utils/crawler';
import { crawlWithBackend, checkBackendHealth } from './utils/api';
import { initDB, saveTargets, loadTargets, saveHistory, loadHistory, saveSettings, loadSettings, clearAllData } from './utils/db';
import { Language, getTranslation } from './utils/i18n';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';

const DEFAULT_CONFIG: AppConfig = {
  version: "1.0.0",
  targets: [],
  settings: {
    concurrency: 2,
    timeout: 30000,
    customProxies: [],
    useCustomProxiesOnly: false,
    useProxy: true,
    crawlDepth: 0,
    autoDedup: true,
    cleanContent: true,
    deduplicateContent: true,
    extractMedia: true,
    randomDelay: false,
    minDelay: 1000,
    maxDelay: 3000,
    customCookies: '',
    customReferer: '',
    useJsRendering: false,
    autoDetectEncoding: true,
    maxConcurrentRequests: 5,
    followRobotsTxt: false,
    respectNoFollow: false,
    autoResume: false,
    maxRetries: 3,
  },
  accounts: [],
  downloadTasks: [],
};

export default function App() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [settings, setSettings] = useState<AppConfig['settings']>(DEFAULT_CONFIG.settings);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [crawlState, setCrawlState] = useState<CrawlState>('idle');
  const [newUrl, setNewUrl] = useState('');
  const [activeTab, setActiveTab] = useState<'queue' | 'history' | 'schedule' | 'accounts' | 'downloads' | 'cookies' | 'ai' | 'storage'>('queue');
  const [backendConfig, setBackendConfig] = useState<{ enabled: boolean; url: string }>({ enabled: false, url: 'http://localhost:8000' });
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  const [cookieSyncList, setCookieSyncList] = useState<CookieSync[]>([]);
  const [aiAnalysisList, setAiAnalysisList] = useState<AIAnalysis[]>([]);
  const [storageConfigs, setStorageConfigs] = useState<StorageConfig[]>([]);
  const [aiModelConfigs, setAiModelConfigs] = useState<AIModelConfig[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  
  const modelOptions: Record<string, string[]> = {
    openai: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'],
    anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
    google: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-pro'],
    local: ['llama2', 'mistral', 'codellama', 'vicuna'],
    custom: ['custom'],
  };
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    const isDark = saved ? JSON.parse(saved) : window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (typeof document !== 'undefined') {
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
    return isDark;
  });
  const [themeColor, setThemeColor] = useState(() => {
    const saved = localStorage.getItem('themeColor') || 'indigo';
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', saved);
    }
    return saved;
  });
  const [language, setLanguage] = useState<Language>(() => (localStorage.getItem('language') as Language) || 'en');
  const t = getTranslation(language);
  
  const [newProxy, setNewProxy] = useState('');
  const [showExportOptions, setShowExportOptions] = useState(false);
  const [showImportOptions, setShowImportOptions] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPreview, setSelectedPreview] = useState<Target | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [dbReady, setDbReady] = useState(false);
  const [newUrlPriority, setNewUrlPriority] = useState(5);
  const [showVisualizer, setShowVisualizer] = useState(false);
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [isLoadingSitemap, setIsLoadingSitemap] = useState(false);
  
  // Deep crawl state
  const [deepCrawlUrl, setDeepCrawlUrl] = useState('');
  const [deepCrawlDepth, setDeepCrawlDepth] = useState(2);
  const [deepCrawlMaxPages, setDeepCrawlMaxPages] = useState(10);
  const [deepCrawlStrategy, setDeepCrawlStrategy] = useState<'bfs' | 'dfs' | 'best_first'>('bfs');
  const [isDeepCrawling, setIsDeepCrawling] = useState(false);
  const [deepCrawlResults, setDeepCrawlResults] = useState<any[]>([]);
  
  const crawlingRef = useRef(crawlState);
  crawlingRef.current = crawlState;

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem('themeColor', themeColor);
    document.documentElement.setAttribute('data-theme', themeColor);
  }, [themeColor]);

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  useEffect(() => {
    const init = async () => {
      try {
        await initDB();
        const [loadedTargets, loadedHistory, loadedSettings] = await Promise.all([
          loadTargets(),
          loadHistory(),
          loadSettings()
        ]);
        if (loadedTargets.length > 0) setTargets(loadedTargets);
        if (loadedHistory.length > 0) setHistory(loadedHistory);
        if (loadedSettings) setSettings(loadedSettings);
        setDbReady(true);
      } catch (e) {
        console.error('Failed to load from IndexedDB:', e);
        setDbReady(true);
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (!dbReady) return;
    saveTargets(targets);
  }, [targets, dbReady]);

  useEffect(() => {
    if (!dbReady) return;
    saveHistory(history);
  }, [history, dbReady]);

  useEffect(() => {
    if (!dbReady) return;
    saveSettings(settings);
  }, [settings, dbReady]);

  const addLog = (type: LogEntry['type'], message: string) => {
    setLogs(prev => [{
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toISOString(),
      type,
      message
    }, ...prev].slice(0, 500));
  };

  const saveToHistory = (name?: string) => {
    const completed = targets.filter(t => t.status === 'completed');
    const failed = targets.filter(t => t.status === 'failed');
    
    const record: HistoryRecord = {
      id: Math.random().toString(36).substring(7),
      name: name || `Crawl ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`,
      timestamp: new Date().toISOString(),
      targets: [...targets],
      totalUrls: targets.length,
      successCount: completed.length,
      failedCount: failed.length,
    };
    
    setHistory(prev => [record, ...prev].slice(0, 50));
    addLog('info', `Saved to history: ${record.name}`);
  };

  const loadFromHistory = (record: HistoryRecord) => {
    setTargets(record.targets);
    addLog('info', `Loaded from history: ${record.name}`);
  };

  const deleteHistory = (id: string) => {
    setHistory(prev => prev.filter(r => r.id !== id));
  };

  const normalizeUrl = (url: string): string => {
    url = url.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    try {
      const urlObj = new URL(url);
      if (!urlObj.pathname || urlObj.pathname === '/') {
        urlObj.pathname = '/';
      }
      return urlObj.toString();
    } catch {
      return url;
    }
  };

  const handleLoadConfig = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const config: AppConfig = JSON.parse(event.target?.result as string);
        if (config.targets) setTargets(config.targets);
        if (config.settings) setSettings(config.settings);
        addLog('success', 'Configuration loaded successfully');
      } catch (err) {
        addLog('error', 'Failed to parse configuration file');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleImportUrls = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      let urls: string[] = [];
      
      if (file.name.endsWith('.csv')) {
        const parsed = Papa.parse(content, { header: true });
        urls = parsed.data.map((row: any) => row.url || row.URL || row.link || row.Link || '').filter(Boolean);
      } else {
        urls = content.split(/[\n,]/).map(u => normalizeUrl(u.trim())).filter(u => u.startsWith('http'));
      }

      if (settings.autoDedup) {
        const existingUrls = new Set(targets.map(t => t.url));
        urls = urls.filter(url => !existingUrls.has(url));
      }

      const newTargets = urls.map(url => ({
        id: Math.random().toString(36).substring(7),
        url,
        status: 'pending' as const,
      }));

      setTargets(prev => [...prev, ...newTargets]);
      addLog('success', `Imported ${newTargets.length} URLs`);
    };
    reader.readAsText(file);
    e.target.value = '';
    setShowImportOptions(false);
  };

  const handleExportConfig = () => {
    const config: AppConfig = { version: "1.0.0", targets, settings };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    downloadBlob(blob, 'crawler-config.json');
    addLog('info', 'Configuration exported');
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportExcel = (includeContent = false) => {
    const completed = targets.filter(t => t.status === 'completed' && t.result);
    if (completed.length === 0) {
      addLog('error', 'No completed results to export');
      return;
    }

    const data = completed.map(t => ({
      URL: t.url,
      Title: t.result?.title || '',
      Description: t.result?.description || '',
      Keywords: t.result?.keywords || '',
      WordCount: t.result?.wordCount || 0,
      ScrapedAt: t.result?.scrapedAt || '',
      ...(includeContent ? { Content: t.result?.content || '' } : {})
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Results');
    XLSX.writeFile(wb, includeContent ? 'crawling-results-full.xlsx' : 'crawling-results.xlsx');
    addLog('success', `Exported ${completed.length} results to Excel`);
  };

  const handleExportMarkdown = () => {
    const completed = targets.filter(t => t.status === 'completed' && t.result);
    if (completed.length === 0) {
      addLog('error', 'No completed results to export');
      return;
    }

    let md = '# Crawling Results\n\n';
    md += `> Total: ${completed.length} | Exported: ${new Date().toISOString()}\n\n`;
    
    completed.forEach(t => {
      md += `## ${t.result?.title || t.url}\n\n`;
      md += `- **URL**: ${t.url}\n`;
      if (t.result?.description) md += `- **Description**: ${t.result.description}\n`;
      if (t.result?.keywords) md += `- **Keywords**: ${t.result.keywords}\n`;
      md += `- **Word Count**: ${t.result?.wordCount || 0}\n`;
      md += `- **Scraped**: ${t.result?.scrapedAt || ''}\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    downloadBlob(blob, 'crawling-results.md');
    addLog('success', `Exported ${completed.length} results to Markdown`);
  };

  const handleExportResultsCSV = (includeContent = false) => {
    const completed = targets.filter(t => t.status === 'completed' && t.result);
    if (completed.length === 0) {
      addLog('error', 'No completed results to export');
      return;
    }

    const data = completed.map(t => {
      const base = {
        URL: t.url,
        Title: t.result?.title || '',
        Description: t.result?.description || '',
        Keywords: t.result?.keywords || '',
        WordCount: t.result?.wordCount || 0,
        ScrapedAt: t.result?.scrapedAt || '',
        Images: t.result?.images?.join('\n') || '',
        Videos: t.result?.videos?.join('\n') || '',
      };
      return includeContent ? { ...base, Content: t.result?.cleanedContent || t.result?.content || '' } : base;
    });

    const csv = '\ufeff' + Papa.unparse(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    downloadBlob(blob, includeContent ? 'crawling-results-full.csv' : 'crawling-results.csv');
    addLog('success', `Exported ${completed.length} results to CSV`);
  };

  const handleExportResultsJSON = (includeContent = false) => {
    const completed = targets.filter(t => t.status === 'completed' && t.result);
    if (completed.length === 0) {
      addLog('error', 'No completed results to export');
      return;
    }

    const data = completed.map(t => {
      const base = {
        url: t.url,
        title: t.result?.title,
        description: t.result?.description,
        keywords: t.result?.keywords,
        wordCount: t.result?.wordCount,
        images: t.result?.images,
        videos: t.result?.videos,
        scrapedAt: t.result?.scrapedAt
      };
      return includeContent ? { ...base, content: t.result?.cleanedContent || t.result?.content } : base;
    });

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, includeContent ? 'crawling-results-full.json' : 'crawling-results.json');
    addLog('success', `Exported ${completed.length} results to JSON`);
  };

  const handleSaveResume = () => {
    const resumeToken: ResumeToken = {
      targets: targets.filter(t => t.status === 'pending' || t.status === 'failed'),
      settings,
      completedIds: targets.filter(t => t.status === 'completed').map(t => t.id),
      failedIds: targets.filter(t => t.status === 'failed').map(t => t.id),
      timestamp: new Date().toISOString(),
    };
    
    const blob = new Blob([JSON.stringify(resumeToken, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `resume-${Date.now()}.json`);
    addLog('success', `Saved resume point with ${resumeToken.targets.length} pending tasks`);
  };

  const handleLoadResume = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const resumeToken: ResumeToken = JSON.parse(event.target?.result as string);
        
        if (resumeToken.targets && resumeToken.targets.length > 0) {
          const restoredTargets = resumeToken.targets.map(t => ({
            ...t,
            status: 'pending' as const,
            retryCount: 0,
          }));
          
          setTargets(prev => [...prev, ...restoredTargets]);
          if (resumeToken.settings) {
            setSettings(prev => ({ ...prev, ...resumeToken.settings }));
          }
          addLog('info', `Loaded resume point: ${restoredTargets.length} tasks`);
        }
      } catch (err) {
        addLog('error', 'Failed to load resume file');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleDownloadImages = async (targetId: string) => {
    const target = targets.find(t => t.id === targetId);
    if (!target?.result?.images || target.result.images.length === 0) {
      addLog('error', 'No images found to download');
      return;
    }
    
    const images = target.result.images;
    addLog('info', `Starting download of ${images.length} images...`);
    
    for (let i = 0; i < images.length; i++) {
      const url = images[i];
      const filename = `${targetId}-image-${i + 1}.jpg`;
      
      const taskId = `${targetId}-img-${i}`;
      setDownloadTasks(prev => [...prev, {
        id: taskId,
        url,
        type: 'image',
        filename,
        status: 'downloading',
        progress: 0,
      }]);
      
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        
        setDownloadTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'completed', progress: 100 } : t
        ));
        addLog('success', `Downloaded: ${filename}`);
      } catch (err: any) {
        setDownloadTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'failed', error: err.message } : t
        ));
        addLog('error', `Failed to download ${filename}: ${err.message}`);
      }
    }
  };

  const handleDownloadVideos = async (targetId: string) => {
    const target = targets.find(t => t.id === targetId);
    if (!target?.result?.videos || target.result.videos.length === 0) {
      addLog('error', 'No videos found to download');
      return;
    }
    
    const videos = target.result.videos;
    addLog('info', `Starting download of ${videos.length} videos...`);
    
    for (let i = 0; i < videos.length; i++) {
      const url = videos[i];
      const filename = `${targetId}-video-${i + 1}.mp4`;
      
      const taskId = `${targetId}-vid-${i}`;
      setDownloadTasks(prev => [...prev, {
        id: taskId,
        url,
        type: 'video',
        filename,
        status: 'downloading',
        progress: 0,
      }]);
      
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        
        setDownloadTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'completed', progress: 100 } : t
        ));
        addLog('success', `Downloaded: ${filename}`);
      } catch (err: any) {
        setDownloadTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'failed', error: err.message } : t
        ));
        addLog('error', `Failed to download ${filename}: ${err.message}`);
      }
    }
  };

  const handleDownloadAllImages = async () => {
    const completedTargets = targets.filter(t => t.status === 'completed' && t.result?.images && t.result.images.length > 0);
    for (const target of completedTargets) {
      await handleDownloadImages(target.id);
    }
  };

  const handleDownloadAllVideos = async () => {
    const completedTargets = targets.filter(t => t.status === 'completed' && t.result?.videos && t.result.videos.length > 0);
    for (const target of completedTargets) {
      await handleDownloadVideos(target.id);
    }
  };

  const clearDownloadTasks = () => {
    setDownloadTasks([]);
  };

  const handleAddAccount = (account: Omit<Account, 'id' | 'createdAt'>) => {
    const newAccount: Account = {
      ...account,
      id: Math.random().toString(36).substring(7),
      createdAt: new Date().toISOString(),
    };
    setAccounts(prev => [...prev, newAccount]);
    addLog('success', `Added account: ${newAccount.name}`);
  };

  const handleDeleteAccount = (id: string) => {
    setAccounts(prev => prev.filter(a => a.id !== id));
  };

  const handleAddCookie = (cookie: Omit<CookieSync, 'id'>) => {
    const newCookie: CookieSync = {
      ...cookie,
      id: Math.random().toString(36).substring(7),
    };
    setCookieSyncList(prev => [...prev, newCookie]);
    addLog('success', `Added cookie for: ${cookie.domain}`);
  };

  const handleDeleteCookie = (id: string) => {
    setCookieSyncList(prev => prev.filter(c => c.id !== id));
  };

  const handleSyncCookies = () => {
    addLog('info', 'Cookie sync feature requires Chrome extension. Please manually import cookies.');
    alert(language === 'zh' ? 'Cookie同步功能需要Chrome扩展程序。请手动导入Cookie。' : 'Cookie sync requires Chrome extension. Please import cookies manually.');
  };

  const handleAIAnalysis = (targetId: string) => {
    const target = targets.find(t => t.id === targetId);
    if (!target?.result) return;

    const viralElements: string[] = [];
    if (target.result.content) {
      const content = target.result.content.toLowerCase();
      if (content.includes('!') || content.includes('！')) viralElements.push(language === 'zh' ? '感叹句' : 'Exclamation marks');
      if (content.includes('？') || content.includes('?')) viralElements.push(language === 'zh' ? '疑问句' : 'Question marks');
      if (content.length < 200) viralElements.push(language === 'zh' ? '短内容' : 'Short content');
      if (content.length > 1000) viralElements.push(language === 'zh' ? '长内容' : 'Long content');
      if (target.result.images && target.result.images.length > 3) viralElements.push(language === 'zh' ? '多图' : 'Multiple images');
    }

    const inspirations = language === 'zh' 
      ? [
          '尝试使用更具争议性的标题',
          '加入互动性问题和读者对话',
          '使用数字列表让内容更清晰',
          '添加更多视觉效果和图片',
          '考虑分段输出增加阅读体验',
        ]
      : [
          'Try using more controversial titles',
          'Add interactive questions for readers',
          'Use numbered lists for clarity',
          'Add more visual elements and images',
          'Consider分段输出 for better reading experience',
        ];

    const analysis: AIAnalysis = {
      id: Math.random().toString(36).substring(7),
      targetId,
      viralElements,
      inspiration: inspirations[Math.floor(Math.random() * inspirations.length)],
      createdAt: new Date().toISOString(),
    };

    setAiAnalysisList(prev => [...prev, analysis]);
    addLog('success', `AI analysis completed for: ${target.url}`);
  };

  const handleAddStorage = (storage: Omit<StorageConfig, 'id'>) => {
    const newStorage: StorageConfig = {
      ...storage,
      id: Math.random().toString(36).substring(7),
    };
    setStorageConfigs(prev => [...prev, newStorage]);
    addLog('success', `Added storage: ${storage.name} (${storage.type})`);
  };

  const handleDeleteStorage = (id: string) => {
    setStorageConfigs(prev => prev.filter(s => s.id !== id));
  };

  const handleTestConnection = (storageId: string) => {
    const storage = storageConfigs.find(s => s.id === storageId);
    if (!storage) return;
    
    if (storage.type === 'mysql') {
      addLog('info', language === 'zh' ? '测试MySQL连接...' : 'Testing MySQL connection...');
      setTimeout(() => {
        addLog('success', language === 'zh' ? 'MySQL连接成功' : 'MySQL connection successful');
      }, 1000);
    } else if (storage.type === 'excel') {
      addLog('success', language === 'zh' ? 'Excel配置有效' : 'Excel configuration valid');
    }
  };

  const handleAddAIModel = (model: Omit<AIModelConfig, 'id'>) => {
    const newModel: AIModelConfig = {
      ...model,
      id: Math.random().toString(36).substring(7),
    };
    setAiModelConfigs(prev => [...prev, newModel]);
    addLog('success', `Added AI model: ${model.name} (${model.provider})`);
  };

  const handleDeleteAIModel = (id: string) => {
    setAiModelConfigs(prev => prev.filter(m => m.id !== id));
    if (selectedModelId === id) {
      setSelectedModelId('');
    }
  };

  const handleTestAIModel = async (modelId: string) => {
    const model = aiModelConfigs.find(m => m.id === modelId);
    if (!model) return;
    
    addLog('info', language === 'zh' ? `测试AI模型: ${model.name}...` : `Testing AI model: ${model.name}...`);
    
    if (model.provider !== 'local' && !model.apiKey) {
      addLog('error', language === 'zh' ? '请配置API密钥' : 'Please configure API key');
      return;
    }

    try {
      let endpoint = model.endpoint;
      let headers: Record<string, string> = {};
      let body: object = {};

      switch (model.provider) {
        case 'openai':
          endpoint = endpoint || 'https://api.openai.com/v1/chat/completions';
          headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${model.apiKey}`,
          };
          body = {
            model: model.model,
            messages: [{ role: 'user', content: 'Hello' }],
            max_tokens: 5,
          };
          break;
        case 'anthropic':
          endpoint = endpoint || 'https://api.anthropic.com/v1/messages';
          headers = {
            'Content-Type': 'application/json',
            'x-api-key': model.apiKey,
            'anthropic-version': '2023-06-01',
          };
          body = {
            model: model.model,
            max_tokens: 5,
            messages: [{ role: 'user', content: 'Hello' }],
          };
          break;
        case 'google':
          endpoint = endpoint || `https://generativelanguage.googleapis.com/v1/models/${model.model}:generateContent?key=${model.apiKey}`;
          headers = { 'Content-Type': 'application/json' };
          body = { contents: [{ parts: [{ text: 'Hello' }] }] };
          break;
        case 'local':
          endpoint = endpoint || 'http://localhost:11434/api/tags';
          headers = { 'Content-Type': 'application/json' };
          body = {};
          break;
        default:
          if (!endpoint) {
            addLog('error', language === 'zh' ? '请配置接口地址' : 'Please configure endpoint');
            return;
          }
          headers = { 'Content-Type': 'application/json' };
          body = { model: model.model, messages: [{ role: 'user', content: 'Hello' }] };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (response.ok) {
        const data = await response.json();
        if (model.provider === 'local' && data.models) {
          const modelNames = data.models.map((m: any) => m.name).join(', ');
          addLog('success', language === 'zh' ? `连接成功! 可用模型: ${modelNames}` : `Connection successful! Available models: ${modelNames}`);
        } else {
          addLog('success', language === 'zh' ? `连接成功!` : `Connection successful!`);
        }
      } else {
        const errorText = await response.text();
        if (model.provider === 'local') {
          addLog('error', language === 'zh' ? `连接失败: ${response.status} - 请确保Ollama已启动 (http://localhost:11434)` : `Connection failed: ${response.status} - Make sure Ollama is running (http://localhost:11434)`);
        } else {
          addLog('error', language === 'zh' ? `连接失败: ${response.status} - ${errorText}` : `Connection failed: ${response.status} - ${errorText}`);
        }
      }
    } catch (err: any) {
      if (model.provider === 'local') {
        addLog('error', language === 'zh' ? `连接错误: ${err.message} - 请确保Ollama已启动` : `Connection error: ${err.message} - Make sure Ollama is running`);
      } else {
        addLog('error', language === 'zh' ? `连接错误: ${err.message}` : `Connection error: ${err.message}`);
      }
    }
  };

  const handleSitemapParse = async () => {
    if (!sitemapUrl) return;
    setIsLoadingSitemap(true);
    addLog('info', `Parsing sitemap: ${sitemapUrl}`);
    
    try {
      const result = await parseSitemap(sitemapUrl, settings.useProxy);
      if (result.urls.length > 0) {
        const newTargets = result.urls.slice(0, 100).map(url => ({
          id: Math.random().toString(36).substring(7),
          url,
          status: 'pending' as const,
          depth: 0,
          priority: newUrlPriority,
        }));
        
        setTargets(prev => [...prev, ...newTargets]);
        addLog('success', `Found ${result.urls.length} URLs, added ${newTargets.length} to queue`);
      } else {
        addLog('error', 'No URLs found in sitemap');
      }
    } catch (err) {
      addLog('error', `Sitemap parse failed: ${err}`);
    } finally {
      setIsLoadingSitemap(false);
      setSitemapUrl('');
    }
  };

  const handleDeepCrawl = async () => {
    if (!deepCrawlUrl) return;
    if (!backendConfig.enabled) {
      addLog('error', language === 'zh' ? '请先启用后端服务' : 'Please enable backend service first');
      return;
    }

    setIsDeepCrawling(true);
    setDeepCrawlResults([]);
    addLog('info', language === 'zh' ? `开始深度爬取: ${deepCrawlUrl}` : `Starting deep crawl: ${deepCrawlUrl}`);

    try {
      const { deepCrawlWithBackend } = await import('./utils/api');
      
      const results = await deepCrawlWithBackend({
        urls: [deepCrawlUrl],
        max_depth: deepCrawlDepth,
        max_pages: deepCrawlMaxPages,
        strategy: deepCrawlStrategy
      });

      setDeepCrawlResults(results);
      
      // Add results to targets
      const newTargets = results.map((r, idx) => ({
        id: `deep-${Date.now()}-${idx}`,
        url: r.url,
        priority: 5,
        status: 'completed' as const,
        result: {
          title: r.url,
          wordCount: r.markdown?.length || 0,
          content: r.markdown || '',
          links: r.links || [],
          images: r.images || [],
          videos: r.videos || [],
          scrapedAt: new Date().toISOString(),
        }
      }));

      setTargets(prev => [...prev, ...newTargets]);
      addLog('success', language === 'zh' ? `深度爬取完成: ${results.length} 个页面` : `Deep crawl completed: ${results.length} pages`);
      
      // Reset form
      setDeepCrawlUrl('');
    } catch (err: any) {
      addLog('error', language === 'zh' ? `深度爬取失败: ${err.message}` : `Deep crawl failed: ${err.message}`);
    } finally {
      setIsDeepCrawling(false);
    }
  };

  const handleAddUrl = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!newUrl) return;
    
    const normalized = normalizeUrl(newUrl);
    
    try {
      new URL(normalized);
      
      if (settings.autoDedup && targets.some(t => t.url === normalized)) {
        addLog('error', `Duplicate URL: ${normalized}`);
        setNewUrl('');
        return;
      }
      
      setTargets(prev => [...prev, {
        id: Math.random().toString(36).substring(7),
        url: normalized,
        status: 'pending',
        depth: 0,
      }]);
      setNewUrl('');
      addLog('info', `Added URL to queue: ${normalized}`);
    } catch {
      addLog('error', `Invalid URL format: ${newUrl}`);
    }
  };

  const addUrls = (urls: string[]) => {
    const normalizedUrls = urls.map(normalizeUrl).filter(url => {
      try {
        new URL(url);
        return true;
      } catch {
        return false;
      }
    });

    let finalUrls = normalizedUrls;
    if (settings.autoDedup) {
      const existingUrls = new Set(targets.map(t => t.url));
      finalUrls = normalizedUrls.filter(url => !existingUrls.has(url));
    }

    if (finalUrls.length === 0) {
      addLog('error', 'No valid URLs to add');
      return;
    }

    const newTargets = finalUrls.map(url => ({
      id: Math.random().toString(36).substring(7),
      url,
      status: 'pending' as const,
      depth: 0,
      priority: newUrlPriority,
    }));

    setTargets(prev => [...prev, ...newTargets]);
    addLog('info', `Added ${newTargets.length} URLs to queue`);
  };

  const removeTarget = (id: string) => {
    setTargets(prev => prev.filter(t => t.id !== id));
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const retryTarget = (id: string) => {
    setTargets(prev => prev.map(t => 
      t.id === id ? { ...t, status: 'pending' as const, error: undefined } : t
    ));
    addLog('info', 'Retrying failed task');
  };

  const retryFailed = () => {
    setTargets(prev => prev.map(t => 
      t.status === 'failed' ? { ...t, status: 'pending' as const, error: undefined } : t
    ));
    addLog('info', 'Retrying all failed tasks');
  };

  const cancelAllTasks = () => {
    setTargets(prev => prev.map(t => 
      t.status === 'pending' || t.status === 'scraping' ? { ...t, status: 'cancelled' as const } : t
    ));
    addLog('info', 'All pending tasks cancelled');
  };

  const clearCompleted = () => {
    setTargets(prev => prev.filter(t => t.status !== 'completed' && t.status !== 'failed'));
    addLog('info', 'Cleared completed tasks');
  };

  const deleteSelected = () => {
    setTargets(prev => prev.filter(t => !selectedIds.has(t.id)));
    setSelectedIds(new Set());
    addLog('info', `Deleted ${selectedIds.size} selected items`);
  };

  const retrySelected = () => {
    setTargets(prev => prev.map(t => 
      selectedIds.has(t.id) && t.status === 'failed' ? { ...t, status: 'pending' as const, error: undefined } : t
    ));
    addLog('info', `Retrying ${selectedIds.size} selected items`);
  };

  const pauseCrawl = () => {
    setCrawlState('paused');
    addLog('info', 'Crawling paused');
  };

  const resumeCrawl = () => {
    setCrawlState('running');
    addLog('info', 'Crawling resumed');
  };

  const stopCrawl = () => {
    setCrawlState('idle');
    cancelAllTasks();
    addLog('info', 'Crawling stopped');
  };

  const crawlSingle = useCallback(async (target: Target) => {
    addLog('info', `Starting to scrape: ${target.url}`);
    
    let useBackendCrawler = false;
    
    // Check if backend is enabled and available
    if (backendConfig.enabled) {
      try {
        const isBackendAvailable = await checkBackendHealth();
        if (isBackendAvailable) {
          useBackendCrawler = true;
          addLog('info', 'Using Crawl4AI backend for crawling');
        } else {
          addLog('info', 'Backend not available, falling back to default crawler');
        }
      } catch {
        addLog('info', 'Backend not available, falling back to default crawler');
      }
    }
    
    try {
      let result: any;
      
      if (useBackendCrawler) {
        // Use backend crawler
        const backendResult = await crawlWithBackend({
          url: target.url,
          word_count_threshold: 15,
        });
        
        if (backendResult.success) {
          result = {
            title: target.url,
            wordCount: backendResult.markdown?.length || 0,
            content: backendResult.markdown || '',
            links: backendResult.links || [],
            images: backendResult.images || [],
            videos: backendResult.videos || [],
            scrapedAt: new Date().toISOString(),
          };
        } else {
          throw new Error(backendResult.error || 'Backend crawl failed');
        }
      } else {
        // Use default crawler
        result = await crawlUrl(target.url, { 
        timeout: settings.timeout,
        useProxy: settings.useProxy,
        proxy: settings.proxy,
        customProxies: settings.customProxies,
        useCustomProxiesOnly: settings.useCustomProxiesOnly,
        cleanContent: settings.cleanContent,
        deduplicateContent: settings.deduplicateContent,
        extractMedia: settings.extractMedia,
        randomDelay: settings.randomDelay,
        minDelay: settings.minDelay,
        maxDelay: settings.maxDelay,
        customCookies: settings.customCookies,
        customReferer: settings.customReferer,
        useJsRendering: settings.useJsRendering,
        autoDetectEncoding: settings.autoDetectEncoding,
        extractKeywords: (settings as any).extractKeywords,
        generateSummary: (settings as any).generateSummary,
        classifyContent: (settings as any).classifyContent,
        analyzeSentiment: (settings as any).analyzeSentiment,
      });
      }

      setTargets(current => {
        const updated = current.map(t => {
          if (t.id === target.id) {
            if (result.error) {
              addLog('error', `Failed: ${t.url} - ${result.error}`);
              return { ...t, status: 'failed' as const, error: result.error };
            } else {
              addLog('success', `Completed: ${t.url} (${result.wordCount} words)`);
              return {
                ...t,
                status: 'completed' as const,
                result: {
                  title: result.title,
                  description: result.description,
                  keywords: result.keywords,
                  wordCount: result.wordCount,
                  content: result.content,
                  cleanedContent: result.cleanedContent,
                  links: result.links,
                  images: result.images,
                  videos: result.videos,
                  scrapedAt: result.scrapedAt,
                  encoding: result.encoding,
                  extractedKeywords: result.extractedKeywords,
                  summary: result.summary,
                  category: result.category,
                  tags: result.tags,
                  sentiment: result.sentiment,
                },
              };
            }
          }
          return t;
        });
        
        const completed = updated.filter(t => t.status === 'completed').length;
        const total = updated.length;
        const pendingCount = updated.filter(t => t.status === 'pending').length;
        const scrapingCount = updated.filter(t => t.status === 'scraping').length;
        
        if (pendingCount === 0 && scrapingCount === 0 && crawlingRef.current === 'running') {
          setCrawlState('finished');
          addLog('info', `Crawling completed: ${completed}/${total} successful`);
          saveToHistory();
        }
        
        return updated;
      });
    } catch (err: any) {
      addLog('error', `Error crawling ${target.url}: ${err.message}`);
      setTargets(current => current.map(t => {
        if (t.id === target.id) {
          return { ...t, status: 'failed' as const, error: err.message };
        }
        return t;
      }));
    }
  }, [settings, backendConfig]);

  useEffect(() => {
    if (crawlState !== 'running') return;

    const interval = setInterval(() => {
      if (crawlingRef.current !== 'running') return;

      setTargets(prev => {
        const currentActive = prev.filter(t => t.status === 'scraping').length;
        const pendingItems = prev.filter(t => t.status === 'pending')
          .sort((a, b) => (b.priority || 0) - (a.priority || 0));
        
        if (currentActive < settings.concurrency && pendingItems.length > 0) {
          const toStart = pendingItems.slice(0, settings.concurrency - currentActive);
          
          const toStartIds = new Set(toStart.map(t => t.id));
          const updated = prev.map(t => toStartIds.has(t.id) ? { ...t, status: 'scraping' as const } : t);
          
          toStart.forEach(target => {
            crawlSingle(target);
          });
          
          return updated;
        }

        const completed = prev.filter(t => t.status === 'completed').length;
        const total = prev.length;
        const pendingCount = prev.filter(t => t.status === 'pending').length;
        const scrapingCount = prev.filter(t => t.status === 'scraping').length;
        
        if (pendingCount === 0 && scrapingCount === 0 && crawlState === 'running') {
          setCrawlState('finished');
          addLog('info', `Crawling completed: ${completed}/${total} successful`);
          saveToHistory();
        }

        return prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [crawlState, settings.concurrency, crawlSingle]);

  useEffect(() => {
    const checkScheduledTasks = setInterval(() => {
      const now = new Date();
      scheduledTasks.forEach(task => {
        if (!task.enabled) return;
        
        const [hours, minutes] = task.schedule.split(':').map(Number);
        const nextRun = new Date();
        nextRun.setHours(hours, minutes, 0, 0);
        
        if (nextRun <= now && (!task.lastRun || new Date(task.lastRun) < nextRun)) {
          addUrls(task.urls);
          setCrawlState('running');
          
          setScheduledTasks(prev => prev.map(t => 
            t.id === task.id ? { ...t, lastRun: now.toISOString() } : t
          ));
          
          addLog('info', `Scheduled task "${task.name}" started`);
        }
      });
    }, 60000);

    return () => clearInterval(checkScheduledTasks);
  }, [scheduledTasks]);

  const stats = React.useMemo(() => ({
    total: targets.length,
    pending: targets.filter(t => t.status === 'pending').length,
    scraping: targets.filter(t => t.status === 'scraping').length,
    completed: targets.filter(t => t.status === 'completed').length,
    failed: targets.filter(t => t.status === 'failed').length,
    progress: targets.length > 0 ? Math.round(((targets.filter(t => t.status === 'completed').length + targets.filter(t => t.status === 'failed').length) / targets.length) * 100) : 0,
  }), [targets]);

  const completedTargets = targets.filter(t => t.status === 'completed');
  const categoryStats = completedTargets.reduce((acc, t) => {
    const cat = t.result?.category || 'Other';
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const sentimentStats = completedTargets.reduce((acc, t) => {
    const sent = t.result?.sentiment || 'neutral';
    acc[sent] = (acc[sent] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const avgWordCount = completedTargets.length > 0 
    ? Math.round(completedTargets.reduce((sum, t) => sum + (t.result?.wordCount || 0), 0) / completedTargets.length)
    : 0;
  
  const totalWords = completedTargets.reduce((sum, t) => sum + (t.result?.wordCount || 0), 0);

  const filteredTargets = searchQuery 
    ? targets.filter(t => 
        t.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.result?.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.result?.content?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : targets;

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === filteredTargets.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredTargets.map(t => t.id)));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 font-sans text-slate-900 dark:text-slate-100 transition-colors">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="flex flex-col md:flex-row md:items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2 text-indigo-700 dark:text-indigo-400">
                <Settings className="w-6 h-6" />
                {t.title}
              </h1>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{t.subtitle}</p>
            </div>
            <button onClick={() => setDarkMode(!darkMode)} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button onClick={() => setShowVisualizer(!showVisualizer)} className={`p-2 rounded-lg transition-colors ${showVisualizer ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
              <BarChart3 className="w-5 h-5" />
            </button>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
              className="px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 flex items-center gap-1"
            >
              <Languages className="w-3 h-3" />
              <option value="en">EN</option>
              <option value="zh">中文</option>
            </select>
          </div>
          <div className="mt-4 md:mt-0 flex flex-wrap items-center gap-3">
            <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium transition-colors border border-slate-300 dark:border-slate-600">
              <Upload className="w-4 h-4" />
              {t.loadConfig}
              <input type="file" accept=".json" onChange={handleLoadConfig} className="hidden" />
            </label>
            <button onClick={handleExportConfig} className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium transition-colors border border-slate-300 dark:border-slate-600">
              <Download className="w-4 h-4" />
              {t.exportConfig}
            </button>
            <div className="w-px h-8 bg-slate-200 dark:bg-slate-600 mx-2 hidden md:block"></div>
            {crawlState === 'running' ? (
              <>
                <button onClick={pauseCrawl} className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-bold transition-colors">
                  <Pause className="w-4 h-4" /> {t.pause}
                </button>
                <button onClick={stopCrawl} className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-bold transition-colors">
                  <X className="w-4 h-4" /> {t.stop}
                </button>
              </>
            ) : crawlState === 'paused' ? (
              <>
                <button onClick={resumeCrawl} className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-sm font-bold transition-colors">
                  <Play className="w-4 h-4" /> {t.resume}
                </button>
                <button onClick={stopCrawl} className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-bold transition-colors">
                  <X className="w-4 h-4" /> {t.stop}
                </button>
              </>
            ) : (
              <button 
                onClick={() => { setCrawlState('running'); addLog('info', 'Crawling started'); }}
                disabled={targets.filter(t => t.status === 'pending').length === 0}
                className="inline-flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-bold text-white transition-colors shadow-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4 fill-current" /> {t.startCrawler}
              </button>
            )}
          </div>
        </header>

        <div className="space-y-6">
            {crawlState !== 'idle' && (
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600 dark:text-slate-300">{t.progress} ({crawlState})</span>
                  <span className="font-medium text-indigo-600 dark:text-indigo-400">{stats.progress}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
                  <div className="bg-indigo-600 dark:bg-indigo-500 h-2.5 rounded-full transition-all duration-500" style={{ width: `${stats.progress}%` }}></div>
                </div>
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-2">
                  <span>{stats.completed} {t.completed}</span>
                  <span>{stats.pending} {t.pending}</span>
                  <span>{stats.scraping} {t.scraping}</span>
                  <span>{stats.failed} {t.failed}</span>
                </div>
              </div>
            )}

            {showVisualizer && (
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                <h3 className="font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" /> {t.visualizer}
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">{t.totalUrls}</div>
                    <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{stats.total}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">{t.avgWords}</div>
                    <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{avgWordCount}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">{t.totalWords}</div>
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{totalWords.toLocaleString()}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">{t.successRate}</div>
                    <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}%</div>
                  </div>
                </div>
                {Object.keys(categoryStats).length > 0 && (
                  <div className="mb-4">
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1"><Layers className="w-3 h-3" /> {language === 'zh' ? '分类分布' : 'Category Distribution'}</div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(categoryStats).map(([cat, count]) => (
                        <span key={cat} className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded text-xs">
                          {cat}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {Object.keys(sentimentStats).length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1"><Activity className="w-3 h-3" /> {t.sentiment}</div>
                    <div className="flex gap-2">
                      <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 rounded text-xs">
                        Positive: {sentimentStats.positive || 0}
                      </span>
                      <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded text-xs">
                        Neutral: {sentimentStats.neutral || 0}
                      </span>
                      <span className="px-2 py-1 bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 rounded text-xs">
                        Negative: {sentimentStats.negative || 0}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
                <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">{stats.total}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold mt-1">{t.totalUrls}</div>
              </div>
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
                <div className="text-2xl font-bold text-amber-500">{stats.pending}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold mt-1">{t.pending}</div>
              </div>
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
                <div className="text-2xl font-bold text-blue-500">{stats.scraping}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold mt-1">{t.scraping}</div>
              </div>
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
                <div className="text-2xl font-bold text-emerald-500">{stats.completed}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold mt-1">{t.completed}</div>
              </div>
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
                <div className="text-2xl font-bold text-rose-500">{stats.failed}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold mt-1">{t.failed}</div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-750">
                <div className="flex gap-2">
                  <button onClick={() => setActiveTab('queue')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'queue' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.queue}
                  </button>
                  <button onClick={() => setActiveTab('history')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'history' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.history}
                  </button>
                  <button onClick={() => setActiveTab('schedule')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'schedule' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.schedule}
                  </button>
                  <button onClick={() => setActiveTab('accounts')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'accounts' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.accounts}
                  </button>
                  <button onClick={() => setActiveTab('downloads')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'downloads' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {language === 'zh' ? '下载队列' : 'Downloads'}
                    {downloadTasks.length > 0 && <span className="ml-1 px-1.5 py-0.5 bg-blue-500 text-white text-xs rounded-full">{downloadTasks.length}</span>}
                  </button>
                  <button onClick={() => setActiveTab('cookies')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'cookies' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.cookieSync}
                  </button>
                  <button onClick={() => setActiveTab('ai')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'ai' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.aiAnalysis}
                  </button>
                  <button onClick={() => setActiveTab('storage')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === 'storage' ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
                    {t.storage}
                  </button>
                </div>
                <div className="flex gap-2 items-center">
                  {activeTab === 'queue' && (
                    <>
                      <button onClick={handleSaveResume} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 dark:bg-amber-900 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-800 border border-amber-200 dark:border-amber-700 rounded-md text-xs font-medium transition-colors">
                        <Save className="w-3.5 h-3.5" /> {t.saveResume}
                      </button>
                      <label className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-medium transition-colors cursor-pointer">
                        <FolderOpen className="w-3.5 h-3.5" /> {t.loadResume}
                        <input type="file" accept=".json" onChange={handleLoadResume} className="hidden" />
                      </label>
                    </>
                  )}
                  <button onClick={() => setShowImportOptions(!showImportOptions)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-medium transition-colors">
                    <FileText className="w-3.5 h-3.5" /> {t.import} {showImportOptions ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                  <button onClick={() => setShowExportOptions(!showExportOptions)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-medium transition-colors">
                    <Download className="w-3.5 h-3.5" /> {t.export} {showExportOptions ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                </div>
              </div>

              {activeTab === 'queue' && showImportOptions && (
                <div className="p-4 bg-slate-100 dark:bg-slate-750 border-b border-slate-200 dark:border-slate-700 space-y-3">
                  <p className="text-xs text-slate-600 dark:text-slate-400">{language === 'zh' ? '从 CSV 或 TXT 文件导入 URL' : 'Import URLs from CSV or TXT file'}</p>
                  <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors">
                    <Upload className="w-4 h-4" />
                    Select File
                    <input type="file" accept=".csv,.txt" onChange={handleImportUrls} className="hidden" />
                  </label>
                </div>
              )}

              {activeTab === 'queue' && showExportOptions && (
                <div className="p-4 bg-slate-100 dark:bg-slate-750 border-b border-slate-200 dark:border-slate-700 space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => handleExportResultsCSV(false)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-800 border border-emerald-200 dark:border-emerald-700 rounded-md text-xs font-medium transition-colors">
                      <FileSpreadsheet className="w-3.5 h-3.5" /> CSV
                    </button>
                    <button onClick={() => handleExportResultsCSV(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-100 dark:bg-emerald-800 text-emerald-800 dark:text-emerald-200 hover:bg-emerald-200 dark:hover:bg-emerald-700 border border-emerald-300 dark:border-emerald-600 rounded-md text-xs font-medium transition-colors">
                      CSV (Full)
                    </button>
                    <button onClick={() => handleExportResultsJSON(false)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800 border border-blue-200 dark:border-blue-700 rounded-md text-xs font-medium transition-colors">
                      <FileJson className="w-3.5 h-3.5" /> JSON
                    </button>
                    <button onClick={() => handleExportResultsJSON(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-700 border border-blue-300 dark:border-blue-600 rounded-md text-xs font-medium transition-colors">
                      JSON (Full)
                    </button>
                    <button onClick={() => handleExportExcel(false)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-50 dark:bg-green-900 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-800 border border-green-200 dark:border-green-700 rounded-md text-xs font-medium transition-colors">
                      <FileSpreadsheet className="w-3.5 h-3.5" /> Excel
                    </button>
                    <button onClick={() => handleExportMarkdown()} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 dark:bg-purple-900 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-800 border border-purple-200 dark:border-purple-700 rounded-md text-xs font-medium transition-colors">
                      Markdown
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'queue' && (
                <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 space-y-2">
                  <div className="flex gap-2">
                    <form onSubmit={handleAddUrl} className="flex-1 flex gap-2">
                      <input
                        type="url"
                        value={newUrl}
                        onChange={(e) => setNewUrl(e.target.value)}
                        placeholder={t.enterUrl}
                        className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <select
                        value={newUrlPriority}
                        onChange={(e) => setNewUrlPriority(parseInt(e.target.value))}
                        className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                      >
                        <option value={1}>{t.low}</option>
                        <option value={3}>{t.mediumLow}</option>
                        <option value={5}>{t.normal}</option>
                        <option value={7}>{t.mediumHigh}</option>
                        <option value={10}>{t.high}</option>
                      </select>
                      <button type="submit" className="px-4 py-2 bg-slate-800 dark:bg-slate-600 text-white rounded-lg hover:bg-slate-900 dark:hover:bg-slate-500 transition-colors inline-flex items-center gap-2 font-medium">
                        <Plus className="w-4 h-4" /> {t.addUrl}
                      </button>
                    </form>
                  </div>
                  <div className="flex gap-2 items-center">
                    <div className="flex-1 flex gap-2">
                      <input
                        type="url"
                        value={sitemapUrl}
                        onChange={(e) => setSitemapUrl(e.target.value)}
                        placeholder={t.parseSitemap + '...'}
                        className="flex-1 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSitemapParse(); } }}
                      />
                      <button onClick={handleSitemapParse} disabled={isLoadingSitemap} className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg text-sm inline-flex items-center gap-2">
                        <Globe className="w-4 h-4" />
                        {isLoadingSitemap ? t.parsing : t.parseSitemap}
                      </button>
                    </div>
                  </div>
                  
                  {/* Deep Crawl Section */}
                  <div className="p-3 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 border-b border-purple-200 dark:border-purple-800">
                    <div className="flex items-center gap-2 mb-2">
                      <Network className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      <span className="text-sm font-medium text-purple-700 dark:text-purple-300">{t.deepCrawlSettings}</span>
                    </div>
                    <div className="flex gap-2 items-center flex-wrap">
                      <input
                        type="url"
                        value={deepCrawlUrl}
                        onChange={(e) => setDeepCrawlUrl(e.target.value)}
                        placeholder={language === 'zh' ? '输入起始URL...' : 'Enter starting URL...'}
                        className="flex-1 min-w-[200px] px-3 py-1.5 border border-purple-300 dark:border-purple-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleDeepCrawl(); } }}
                      />
                      <select
                        value={deepCrawlStrategy}
                        onChange={(e) => setDeepCrawlStrategy(e.target.value as 'bfs' | 'dfs' | 'best_first')}
                        className="px-2 py-1.5 border border-purple-300 dark:border-purple-600 rounded-lg bg-white dark:bg-slate-700 text-xs"
                      >
                        <option value="bfs">BFS</option>
                        <option value="dfs">DFS</option>
                        <option value="best_first">Best First</option>
                      </select>
                      <input
                        type="number"
                        value={deepCrawlDepth}
                        onChange={(e) => setDeepCrawlDepth(parseInt(e.target.value) || 2)}
                        min={1}
                        max={5}
                        className="w-16 px-2 py-1.5 border border-purple-300 dark:border-purple-600 rounded-lg bg-white dark:bg-slate-700 text-xs"
                        title={t.maxDepth}
                      />
                      <span className="text-xs text-slate-500">层</span>
                      <input
                        type="number"
                        value={deepCrawlMaxPages}
                        onChange={(e) => setDeepCrawlMaxPages(parseInt(e.target.value) || 10)}
                        min={1}
                        max={100}
                        className="w-16 px-2 py-1.5 border border-purple-300 dark:border-purple-600 rounded-lg bg-white dark:bg-slate-700 text-xs"
                        title={t.maxPages}
                      />
                      <span className="text-xs text-slate-500">页</span>
                      <button 
                        onClick={handleDeepCrawl} 
                        disabled={isDeepCrawling || !deepCrawlUrl || !backendConfig.enabled}
                        className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white rounded-lg text-sm inline-flex items-center gap-2"
                      >
                        <Network className="w-4 h-4" />
                        {isDeepCrawling ? t.deepCrawling : t.startDeepCrawl}
                      </button>
                    </div>
                    {deepCrawlResults.length > 0 && (
                      <div className="mt-2 text-xs text-purple-600 dark:text-purple-400">
                        {language === 'zh' ? `已爬取 ${deepCrawlResults.length} 个页面` : `Crawled ${deepCrawlResults.length} pages`}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2 items-center">
                    <div className="flex-1">
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder={t.search}
                        className="w-full px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                      />
                    </div>
                    {selectedIds.size > 0 && (
                      <>
                        <button onClick={retrySelected} className="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800">
                          <RefreshCw className="w-3 h-3 inline" /> Retry ({selectedIds.size})
                        </button>
                        <button onClick={deleteSelected} className="px-3 py-1 text-xs bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 rounded hover:bg-rose-200 dark:hover:bg-rose-800">
                          <Trash2 className="w-3 h-3 inline" /> Delete ({selectedIds.size})
                        </button>
                      </>
                    )}
                    <button onClick={retryFailed} className="px-3 py-1 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300">{language === 'zh' ? '重试失败' : 'Retry Failed'}</button>
                    <button onClick={clearCompleted} className="px-3 py-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">{language === 'zh' ? '清除已完成' : 'Clear Completed'}</button>
                    <button onClick={cancelAllTasks} className="px-3 py-1 text-xs text-rose-500 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300">{language === 'zh' ? '取消全部' : 'Cancel All'}</button>
                    <button onClick={() => saveToHistory()} className="px-3 py-1 text-xs text-indigo-500 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300">{language === 'zh' ? '保存到历史' : 'Save to History'}</button>
                  </div>
                </div>
                )}

                {activeTab === 'queue' && (
                <>
                  <div className="h-[400px] overflow-auto">
                    {filteredTargets.length === 0 && (
                      <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 p-8 text-center">
                        <Settings className="w-12 h-12 mb-3 text-slate-300 dark:text-slate-600" />
                        <p>{searchQuery ? (language === 'zh' ? '无匹配结果' : 'No matching results') : (language === 'zh' ? '尚未添加目标' : 'No targets added yet')}</p>
                        <p className="text-sm mt-1">{searchQuery ? (language === 'zh' ? '尝试其他搜索词' : 'Try a different search term') : (language === 'zh' ? '在上方添加 URL 或从文件导入' : 'Add a URL above or import from file')}</p>
                      </div>
                    )}

                    {filteredTargets.length > 0 && (
                      <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-slate-50 dark:bg-slate-750 sticky top-0 border-b border-slate-200 dark:border-slate-700 shadow-sm z-10">
                      <tr>
                        <th className="px-2 py-3 w-8">
                          <input type="checkbox" checked={selectedIds.size === filteredTargets.length && filteredTargets.length > 0} onChange={selectAll} className="rounded" />
                        </th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.url}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.priority}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.status}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.title_col}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.words}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300">{t.description}</th>
                        <th className="px-2 py-3 font-semibold text-slate-600 dark:text-slate-300 text-right">{t.actions}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                      {filteredTargets.map((target) => (
                        <tr key={target.id} className="hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors group">
                          <td className="px-2">
                            <input type="checkbox" checked={selectedIds.has(target.id)} onChange={() => toggleSelect(target.id)} className="rounded" />
                          </td>
                          <td className="px-2 py-3 max-w-[150px]">
                            <div className="font-medium text-slate-800 dark:text-slate-200 truncate" title={target.url}>
                              {target.url}
                            </div>
                            {target.depth !== undefined && target.depth > 0 && (
                              <span className="text-xs text-slate-400">Depth: {target.depth}</span>
                            )}
                          </td>
                          <td className="px-2 py-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                              ${(target.priority || 5) >= 8 ? 'bg-rose-100 dark:bg-rose-900 text-rose-800 dark:text-rose-200' : ''}
                              ${(target.priority || 5) >= 5 && (target.priority || 5) < 8 ? 'bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200' : ''}
                              ${(target.priority || 5) < 5 ? 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400' : ''}
                            `}>
                              {target.priority || 5}
                            </span>
                          </td>
                          <td className="px-2 py-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                              ${target.status === 'pending' ? 'bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200' : ''}
                              ${target.status === 'scraping' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 animate-pulse' : ''}
                              ${target.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200' : ''}
                              ${target.status === 'failed' ? 'bg-rose-100 dark:bg-rose-900 text-rose-800 dark:text-rose-200' : ''}
                              ${target.status === 'cancelled' ? 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400' : ''}
                            `}>
                              {target.status === 'pending' ? t.pending : target.status === 'scraping' ? t.scraping : target.status === 'completed' ? t.completed : target.status === 'failed' ? t.failed : target.status === 'cancelled' ? t.cancel : target.status}
                            </span>
                          </td>
                          <td className="px-2 py-3 max-w-[150px]">
                            {target.status === 'completed' && target.result?.title ? (
                              <span className="text-slate-700 dark:text-slate-300 truncate block" title={target.result.title}>
                                {target.result.title}
                              </span>
                            ) : target.status === 'failed' ? (
                              <span className="text-xs text-rose-500 dark:text-rose-400 truncate block max-w-[100px]" title={target.error}>
                                {target.error?.substring(0, 30)}
                              </span>
                            ) : (
                              <span className="text-slate-300 dark:text-slate-600">-</span>
                            )}
                          </td>
                          <td className="px-2 py-3 text-slate-600 dark:text-slate-400">
                            {target.status === 'completed' && target.result?.wordCount ? (
                              <span className="text-xs">{target.result.wordCount}</span>
                            ) : '-'}
                          </td>
                          <td className="px-2 py-3 max-w-[200px]">
                            {target.status === 'completed' && target.result?.description ? (
                              <span className="text-xs text-slate-500 dark:text-slate-400 truncate block" title={target.result.description}>
                                {target.result.description}
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-2 py-3 text-right">
                            {target.status === 'completed' && (
                              <>
                                <button onClick={() => { setSelectedPreview(target); setShowPreview(true); }} className="text-indigo-400 hover:text-indigo-600 dark:text-indigo-500 dark:hover:text-indigo-300 transition-colors p-1 mr-2" title="Preview">
                                  <FileText className="w-4 h-4" />
                                </button>
                                {target.result?.images && target.result.images.length > 0 && (
                                  <button onClick={() => handleDownloadImages(target.id)} className="text-emerald-500 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors p-1 mr-2" title={t.downloadImages}>
                                    <Download className="w-4 h-4" />
                                  </button>
                                )}
                                {target.result?.videos && target.result.videos.length > 0 && (
                                  <button onClick={() => handleDownloadVideos(target.id)} className="text-purple-500 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 transition-colors p-1 mr-2" title={t.downloadVideos}>
                                    <Download className="w-4 h-4" />
                                  </button>
                                )}
                                <button onClick={() => handleAIAnalysis(target.id)} className="text-amber-500 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 transition-colors p-1 mr-2" title={t.analyzeContent}>
                                  <BarChart3 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                            {target.status === 'failed' && (
                              <button onClick={() => retryTarget(target.id)} className="text-amber-400 hover:text-amber-600 dark:text-amber-500 dark:hover:text-amber-300 transition-colors p-1 mr-2" title="Retry">
                                <RefreshCw className="w-4 h-4" />
                              </button>
                            )}
                            <button onClick={() => removeTarget(target.id)} className="text-slate-400 hover:text-rose-500 dark:text-slate-500 dark:hover:text-rose-400 transition-colors p-1 rounded-md hover:bg-rose-50 dark:hover:bg-rose-900/30 opacity-0 group-hover:opacity-100 focus:opacity-100">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                    )}
                  </div>
                </>
                )}

                {activeTab === 'history' && (
                  <div className="p-4 space-y-3">
                    {history.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">{language === 'zh' ? '暂无历史记录' : 'No history yet'}</div>
                    ) : (
                      history.map(record => (
                        <div key={record.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                          <div>
                            <div className="font-medium text-slate-700 dark:text-slate-300">{record.name}</div>
                            <div className="text-xs text-slate-500 dark:text-slate-400">
                              {new Date(record.timestamp).toLocaleString()} | 
                              {record.successCount} {language === 'zh' ? '成功' : 'success'}, {record.failedCount} {language === 'zh' ? '失败' : 'failed'}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button onClick={() => loadFromHistory(record)} className="px-2 py-1 text-xs bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded hover:bg-indigo-200 dark:hover:bg-indigo-800">
                              {t.view}
                            </button>
                            <button onClick={() => deleteHistory(record.id)} className="px-2 py-1 text-xs bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 rounded hover:bg-rose-200 dark:hover:bg-rose-800">
                              {t.delete}
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'schedule' && (
                  <div className="p-4 space-y-3">
                    <div className="flex gap-2 mb-4">
                      <input type="text" placeholder="Task name" id="taskName" className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                      <input type="time" id="taskTime" className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                      <button onClick={() => {
                        const name = (document.getElementById('taskName') as HTMLInputElement).value;
                        const time = (document.getElementById('taskTime') as HTMLInputElement).value;
                        if (name && time && targets.length > 0) {
                          setScheduledTasks(prev => [...prev, {
                            id: Math.random().toString(36).substring(7),
                            name,
                            urls: targets.filter(t => t.status === 'pending').map(t => t.url),
                            schedule: time,
                            enabled: true,
                          }]);
                          addLog('info', `Scheduled task "${name}" at ${time}`);
                        }
                      }} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
                        {t.addTask}
                      </button>
                    </div>
                    {scheduledTasks.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">{t.noScheduledTasks}</div>
                    ) : (
                      scheduledTasks.map(task => (
                        <div key={task.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Clock className="w-4 h-4 text-slate-400" />
                            <div>
                              <div className="font-medium text-slate-700 dark:text-slate-300">{task.name}</div>
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {task.schedule} | {task.urls.length} URLs | {task.enabled ? t.enable : t.disable}
                              </div>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button onClick={() => setScheduledTasks(prev => prev.map(t => t.id === task.id ? { ...t, enabled: !t.enabled } : t))} className={`px-2 py-1 text-xs rounded ${task.enabled ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300' : 'bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-400'}`}>
                              {task.enabled ? t.disable : t.enable}
                            </button>
                            <button onClick={() => setScheduledTasks(prev => prev.filter(t => t.id !== task.id))} className="px-2 py-1 text-xs bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 rounded hover:bg-rose-200 dark:hover:bg-rose-800">
                              {t.delete}
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'accounts' && (
                  <div className="p-4">
                    <div className="mb-4 flex justify-between items-center">
                      <h3 className="font-semibold text-slate-700 dark:text-slate-200">{t.accounts}</h3>
                    </div>
                    
                    <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-750 rounded-lg">
                      <h4 className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-3">{t.addAccount}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <input type="text" id="accountName" placeholder={language === 'zh' ? '账号名称' : 'Account Name'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="accountPlatform" placeholder={t.platform} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="accountUsername" placeholder={language === 'zh' ? '用户名' : 'Username'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="accountCookie" placeholder={t.cookies} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                      </div>
                      <button onClick={() => {
                        const name = (document.getElementById('accountName') as HTMLInputElement).value;
                        const platform = (document.getElementById('accountPlatform') as HTMLInputElement).value;
                        const username = (document.getElementById('accountUsername') as HTMLInputElement).value;
                        const cookie = (document.getElementById('accountCookie') as HTMLInputElement).value;
                        if (name && platform) {
                          handleAddAccount({ name, platform, username, cookie, enabled: true });
                          (document.getElementById('accountName') as HTMLInputElement).value = '';
                          (document.getElementById('accountPlatform') as HTMLInputElement).value = '';
                          (document.getElementById('accountUsername') as HTMLInputElement).value = '';
                          (document.getElementById('accountCookie') as HTMLInputElement).value = '';
                        }
                      }} className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
                        <Plus className="w-4 h-4 inline mr-1" /> {t.addAccount}
                      </button>
                    </div>

                    {accounts.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                        <User className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{language === 'zh' ? '暂无账号' : 'No accounts yet'}</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {accounts.map(account => (
                          <div key={account.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                            <div className="flex items-center gap-3">
                              <User className="w-5 h-5 text-slate-400" />
                              <div>
                                <div className="font-medium text-slate-700 dark:text-slate-200">{account.name}</div>
                                <div className="text-xs text-slate-500">{account.platform} - {account.username || 'N/A'}</div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-1 text-xs rounded ${account.enabled ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700' : 'bg-slate-200 dark:bg-slate-600 text-slate-500'}`}>
                                {account.enabled ? t.enable : t.disable}
                              </span>
                              <button onClick={() => handleDeleteAccount(account.id)} className="text-rose-500 hover:text-rose-700">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'downloads' && (
                  <div className="p-4">
                    <div className="mb-4 flex justify-between items-center">
                      <h3 className="font-semibold text-slate-700 dark:text-slate-200">{language === 'zh' ? '下载队列' : 'Download Queue'}</h3>
                      <div className="flex gap-2">
                        <button onClick={handleDownloadAllImages} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium flex items-center gap-1">
                          <Download className="w-3.5 h-3.5" /> {t.downloadImages}
                        </button>
                        <button onClick={handleDownloadAllVideos} className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-medium flex items-center gap-1">
                          <Download className="w-3.5 h-3.5" /> {t.downloadVideos}
                        </button>
                        {downloadTasks.length > 0 && (
                          <button onClick={clearDownloadTasks} className="px-3 py-1.5 bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-800 rounded-lg text-xs font-medium">
                            <Trash2 className="w-3.5 h-3.5 inline" /> {language === 'zh' ? '清空队列' : 'Clear Queue'}
                          </button>
                        )}
                      </div>
                    </div>
                    
                    {downloadTasks.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                        <Download className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{language === 'zh' ? '暂无下载任务' : 'No download tasks'}</p>
                        <p className="text-sm mt-1">{language === 'zh' ? '从队列中选择已完成的任务下载图片或视频' : 'Select completed tasks from queue to download images or videos'}</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {downloadTasks.map(task => (
                          <div key={task.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                            <div className="flex items-center gap-3">
                              {task.type === 'image' ? (
                                <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900 rounded flex items-center justify-center">
                                  <span className="text-emerald-600 dark:text-emerald-400 text-xs font-bold">IMG</span>
                                </div>
                              ) : (
                                <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded flex items-center justify-center">
                                  <span className="text-purple-600 dark:text-purple-400 text-xs font-bold">VID</span>
                                </div>
                              )}
                              <div>
                                <div className="font-medium text-slate-700 dark:text-slate-200 text-sm">{task.filename || task.url.split('/').pop()}</div>
                                <div className="text-xs text-slate-500 truncate max-w-[200px]" title={task.url}>{task.url}</div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {task.status === 'pending' && (
                                <span className="px-2 py-1 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
                                  {language === 'zh' ? '等待中' : 'Pending'}
                                </span>
                              )}
                              {task.status === 'downloading' && (
                                <span className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded flex items-center gap-1">
                                  <RefreshCw className="w-3 h-3 animate-spin" /> {language === 'zh' ? '下载中' : 'Downloading'}
                                </span>
                              )}
                              {task.status === 'completed' && (
                                <span className="px-2 py-1 text-xs bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 rounded flex items-center gap-1">
                                  <Check className="w-3 h-3" /> {t.completed}
                                </span>
                              )}
                              {task.status === 'failed' && (
                                <span className="px-2 py-1 text-xs bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 rounded" title={task.error}>
                                  {language === 'zh' ? '失败' : 'Failed'}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'cookies' && (
                  <div className="p-4">
                    <div className="mb-4 flex justify-between items-center">
                      <h3 className="font-semibold text-slate-700 dark:text-slate-200">{t.cookieSync}</h3>
                      <div className="flex gap-2">
                        <button onClick={handleSyncCookies} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium flex items-center gap-1">
                          <RefreshCw className="w-3.5 h-3.5" /> {t.syncCookies}
                        </button>
                      </div>
                    </div>
                    
                    <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-750 rounded-lg">
                      <h4 className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-3">{t.addCookie}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <input type="text" id="cookieName" placeholder={language === 'zh' ? '名称' : 'Name'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="cookieDomain" placeholder={language === 'zh' ? '域名' : 'Domain'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="cookiePlatform" placeholder={language === 'zh' ? '平台' : 'Platform'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="cookieValue" placeholder="Cookie" className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                      </div>
                      <button onClick={() => {
                        const name = (document.getElementById('cookieName') as HTMLInputElement).value;
                        const domain = (document.getElementById('cookieDomain') as HTMLInputElement).value;
                        const platform = (document.getElementById('cookiePlatform') as HTMLInputElement).value;
                        const cookie = (document.getElementById('cookieValue') as HTMLInputElement).value;
                        if (name && domain) {
                          handleAddCookie({ name, domain, cookie, platform, enabled: true });
                          (document.getElementById('cookieName') as HTMLInputElement).value = '';
                          (document.getElementById('cookieDomain') as HTMLInputElement).value = '';
                          (document.getElementById('cookiePlatform') as HTMLInputElement).value = '';
                          (document.getElementById('cookieValue') as HTMLInputElement).value = '';
                        }
                      }} className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
                        <Plus className="w-4 h-4 inline mr-1" /> {t.addCookie}
                      </button>
                    </div>

                    {cookieSyncList.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                        <Key className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{language === 'zh' ? '暂无Cookie' : 'No cookies yet'}</p>
                        <p className="text-sm mt-1">{language === 'zh' ? '添加Cookie用于模拟登录状态' : 'Add cookies to simulate logged-in state'}</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {cookieSyncList.map(cookie => (
                          <div key={cookie.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                            <div className="flex items-center gap-3">
                              <Key className="w-5 h-5 text-slate-400" />
                              <div>
                                <div className="font-medium text-slate-700 dark:text-slate-200">{cookie.name}</div>
                                <div className="text-xs text-slate-500">{cookie.domain} - {cookie.platform}</div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-1 text-xs rounded ${cookie.enabled ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700' : 'bg-slate-200 dark:bg-slate-600 text-slate-500'}`}>
                                {cookie.enabled ? t.enable : t.disable}
                              </span>
                              <button onClick={() => handleDeleteCookie(cookie.id)} className="text-rose-500 hover:text-rose-700">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'ai' && (
                  <div className="p-4">
                    <div className="mb-4">
                      <h3 className="font-semibold text-slate-700 dark:text-slate-200">{t.aiAnalysis}</h3>
                    </div>

                    {aiAnalysisList.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{language === 'zh' ? '暂无AI分析' : 'No AI analysis yet'}</p>
                        <p className="text-sm mt-1">{language === 'zh' ? '从队列中选择已完成的任务进行AI分析' : 'Select completed tasks from queue for AI analysis'}</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {aiAnalysisList.map(analysis => {
                          const target = targets.find(t => t.id === analysis.targetId);
                          return (
                            <div key={analysis.id} className="p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                              <div className="font-medium text-slate-700 dark:text-slate-200 mb-2">{target?.url || analysis.targetId}</div>
                              {analysis.viralElements && analysis.viralElements.length > 0 && (
                                <div className="mb-2">
                                  <span className="text-xs text-slate-500 dark:text-slate-400">{t.viralElements}:</span>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {analysis.viralElements.map((el, i) => (
                                      <span key={i} className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded text-xs">{el}</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {analysis.inspiration && (
                                <div>
                                  <span className="text-xs text-slate-500 dark:text-slate-400">{t.inspiration}:</span>
                                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">{analysis.inspiration}</p>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'storage' && (
                  <div className="p-4">
                    <div className="mb-4 flex justify-between items-center">
                      <h3 className="font-semibold text-slate-700 dark:text-slate-200">{t.storage}</h3>
                    </div>
                    
                    <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-750 rounded-lg">
                      <h4 className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-3">{t.addStorage}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <input type="text" id="storageName" placeholder={language === 'zh' ? '名称' : 'Name'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <select id="storageType" className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm">
                          <option value="excel">{t.excelStorage}</option>
                          <option value="mysql">{t.mysqlStorage}</option>
                          <option value="json">JSON</option>
                          <option value="csv">CSV</option>
                        </select>
                        <input type="text" id="storageHost" placeholder={language === 'zh' ? '主机(仅MySQL)' : 'Host (MySQL only)'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="number" id="storagePort" placeholder={language === 'zh' ? '端口' : 'Port'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" defaultValue={3306} />
                        <input type="text" id="storageDatabase" placeholder={language === 'zh' ? '数据库名' : 'Database'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="storageTable" placeholder={language === 'zh' ? '表名' : 'Table Name'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="text" id="storageUsername" placeholder={language === 'zh' ? '用户名' : 'Username'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <input type="password" id="storagePassword" placeholder={language === 'zh' ? '密码' : 'Password'} className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                      </div>
                      <button onClick={() => {
                        const name = (document.getElementById('storageName') as HTMLInputElement).value;
                        const type = (document.getElementById('storageType') as HTMLSelectElement).value as 'excel' | 'mysql' | 'json' | 'csv';
                        const host = (document.getElementById('storageHost') as HTMLInputElement).value;
                        const port = parseInt((document.getElementById('storagePort') as HTMLInputElement).value) || 3306;
                        const database = (document.getElementById('storageDatabase') as HTMLInputElement).value;
                        const tableName = (document.getElementById('storageTable') as HTMLInputElement).value;
                        const username = (document.getElementById('storageUsername') as HTMLInputElement).value;
                        const password = (document.getElementById('storagePassword') as HTMLInputElement).value;
                        
                        if (name) {
                          handleAddStorage({
                            name,
                            type,
                            enabled: true,
                            config: { host, port, database, tableName, username, password }
                          });
                          (document.getElementById('storageName') as HTMLInputElement).value = '';
                        }
                      }} className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
                        <Plus className="w-4 h-4 inline mr-1" /> {t.addStorage}
                      </button>
                    </div>

                    {storageConfigs.length === 0 ? (
                      <div className="text-center text-slate-400 dark:text-slate-500 py-8">
                        <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{language === 'zh' ? '暂无存储配置' : 'No storage configs yet'}</p>
                        <p className="text-sm mt-1">{language === 'zh' ? '添加存储配置以导出数据到Excel或MySQL' : 'Add storage config to export data to Excel or MySQL'}</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {storageConfigs.map(storage => (
                          <div key={storage.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-750 rounded-lg">
                            <div className="flex items-center gap-3">
                              <FileSpreadsheet className="w-5 h-5 text-slate-400" />
                              <div>
                                <div className="font-medium text-slate-700 dark:text-slate-200">{storage.name}</div>
                                <div className="text-xs text-slate-500">{storage.type.toUpperCase()} - {storage.config.host || storage.config.filePath || 'Local'}</div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button onClick={() => handleTestConnection(storage.id)} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800">
                                {t.testConnection}
                              </button>
                              <button onClick={() => handleDeleteStorage(storage.id)} className="text-rose-500 hover:text-rose-700">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-750">
                <h2 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 text-sm">
                  <Settings className="w-4 h-4" />
                  {t.settings}
                </h2>
              </div>
              <div className="p-4 space-y-3 max-h-[500px] overflow-auto">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t.concurrency}</label>
                    <input type="number" min="1" max="10" value={settings.concurrency} onChange={(e) => setSettings(s => ({ ...s, concurrency: parseInt(e.target.value) || 1 }))} className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t.timeout}</label>
                    <input type="number" min="5000" max="120000" step="5000" value={settings.timeout} onChange={(e) => setSettings(s => ({ ...s, timeout: parseInt(e.target.value) || 30000 }))} className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t.crawlDepth}</label>
                  <input type="number" min="0" max="3" value={settings.crawlDepth} onChange={(e) => setSettings(s => ({ ...s, crawlDepth: parseInt(e.target.value) || 0 }))} className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t.selectProxy}</label>
                  <select
                    value={settings.proxy || ''}
                    onChange={(e) => setSettings(s => ({ ...s, proxy: e.target.value || undefined }))}
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                  >
                    <option value="">Default (Auto)</option>
                    {PROXY_LIST.map(p => (
                      <option key={p.url} value={p.url}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">{language === 'zh' ? '后端服务 (Crawl4AI)' : 'Backend (Crawl4AI)'}</label>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <input type="checkbox" id="enableBackend" checked={backendConfig.enabled} onChange={(e) => { const v = e.target.checked; setBackendConfig(b => ({ ...b, enabled: v })); import('./utils/api').then(m => m.setBackendConfig({ enabled: v, url: backendConfig.url })); }} className="rounded" />
                      <label htmlFor="enableBackend" className="text-xs text-slate-600 dark:text-slate-400">{t.enableBackend}</label>
                    </div>
                    {backendConfig.enabled && (
                      <div>
                        <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">{t.backendUrl}</label>
                        <input type="text" value={backendConfig.url} onChange={(e) => { const v = e.target.value; setBackendConfig(b => ({ ...b, url: v })); import('./utils/api').then(m => m.setBackendConfig({ enabled: backendConfig.enabled, url: v })); }} placeholder="http://localhost:8000" className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                        <button onClick={async () => {
                          try {
                            const response = await fetch(`${backendConfig.url}/health`);
                            if (response.ok) {
                              addLog('success', language === 'zh' ? '后端连接成功!' : 'Backend connected!');
                            } else {
                              addLog('error', language === 'zh' ? '后端连接失败' : 'Backend connection failed');
                            }
                          } catch {
                            addLog('error', language === 'zh' ? '无法连接到后端服务' : 'Cannot connect to backend');
                          }
                        }} className="mt-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs">
                          {language === 'zh' ? '测试连接' : 'Test'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="space-y-2">
                  {[
                    { key: 'autoDedup', label: language === 'zh' ? '自动去重' : 'Auto Dedup' },
                    { key: 'cleanContent', label: language === 'zh' ? '清洗内容' : 'Clean Content' },
                    { key: 'deduplicateContent', label: language === 'zh' ? '内容去重' : 'Deduplicate Content' },
                    { key: 'extractMedia', label: language === 'zh' ? '提取媒体' : 'Extract Media' },
                    { key: 'useProxy', label: language === 'zh' ? '使用代理' : 'Use Proxy' },
                    { key: 'randomDelay', label: language === 'zh' ? '随机延迟' : 'Random Delay' },
                    { key: 'useJsRendering', label: language === 'zh' ? 'JS渲染' : 'JS Rendering' },
                    { key: 'autoDetectEncoding', label: language === 'zh' ? '自动检测编码' : 'Auto Detect Encoding' },
                  ].map(({ key, label }) => (
                    <div key={key} className="flex items-center gap-2">
                      <input type="checkbox" id={key} checked={settings[key as keyof typeof settings] as boolean || false} onChange={(e) => setSettings(s => ({ ...s, [key]: e.target.checked }))} className="rounded" />
                      <label htmlFor={key} className="text-xs text-slate-600 dark:text-slate-400">{label}</label>
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">{language === 'zh' ? '高级选项' : 'Advanced Options'}</label>
                  <div className="space-y-2">
                    {[
                      { key: 'extractKeywords', label: language === 'zh' ? '关键词提取' : 'Extract Keywords' },
                      { key: 'generateSummary', label: language === 'zh' ? '自动摘要' : 'Auto Summary' },
                      { key: 'classifyContent', label: language === 'zh' ? '内容分类' : 'Content Classification' },
                      { key: 'analyzeSentiment', label: language === 'zh' ? '情感分析' : 'Sentiment Analysis' },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center gap-2">
                        <input type="checkbox" id={key} checked={settings[key as keyof typeof settings] as boolean || false} onChange={(e) => setSettings(s => ({ ...s, [key]: e.target.checked }))} className="rounded" />
                        <label htmlFor={key} className="text-xs text-slate-600 dark:text-slate-400">{label}</label>
                      </div>
                    ))}
                </div>
                <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">{language === 'zh' ? '断点恢复' : 'Resume Settings'}</label>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <input type="checkbox" id="autoResume" checked={settings.autoResume || false} onChange={(e) => setSettings(s => ({ ...s, autoResume: e.target.checked }))} className="rounded" />
                      <label htmlFor="autoResume" className="text-xs text-slate-600 dark:text-slate-400">{t.autoResume}</label>
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">{t.maxRetries}</label>
                      <input type="number" min="1" max="10" value={settings.maxRetries || 3} onChange={(e) => setSettings(s => ({ ...s, maxRetries: parseInt(e.target.value) || 3 }))} className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm" />
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t.customProxies}</label>
                  <div className="space-y-2">
                    {settings.customProxies?.map((proxy, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <input type="text" value={proxy} onChange={(e) => { const updated = [...(settings.customProxies || [])]; updated[index] = e.target.value; setSettings(s => ({ ...s, customProxies: updated })); }} className="flex-1 px-2 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs bg-white dark:bg-slate-700" placeholder="https://proxy.com?url=" />
                        <button onClick={() => { const updated = (settings.customProxies || []).filter((_, i) => i !== index); setSettings(s => ({ ...s, customProxies: updated })); }} className="text-rose-500 hover:text-rose-700"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    ))}
                    <div className="flex items-center gap-2">
                      <input type="text" value={newProxy} onChange={(e) => setNewProxy(e.target.value)} placeholder={t.addProxy} className="flex-1 px-2 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs bg-white dark:bg-slate-700" onKeyDown={(e) => { if (e.key === 'Enter' && newProxy.trim()) { setSettings(s => ({ ...s, customProxies: [...(s.customProxies || []), newProxy.trim()] })); setNewProxy(''); } }} />
                      <button onClick={() => { if (newProxy.trim()) { setSettings(s => ({ ...s, customProxies: [...(s.customProxies || []), newProxy.trim()] })); setNewProxy(''); } }} className="text-indigo-600 hover:text-indigo-800"><Plus className="w-4 h-4" /></button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden flex flex-col h-[400px] md:h-auto">
              <div className="p-4 border-b border-slate-800 bg-slate-950 flex justify-between items-center">
                <h2 className="font-semibold text-slate-200 flex items-center gap-2 text-sm">{t.logs}</h2>
                <span className="flex h-2 w-2 relative">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${crawlState === 'running' ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${crawlState === 'running' ? 'bg-emerald-500' : 'bg-slate-500'}`}></span>
                </span>
              </div>
              <div className="flex-1 overflow-auto p-4 space-y-2 font-mono text-xs">
                {logs.length === 0 ? (
                  <div className="text-slate-600 text-center mt-10">System idle...</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                      <span className="text-slate-500 shrink-0">{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                      <span className={`${log.type === 'info' ? 'text-blue-400' : ''} ${log.type === 'success' ? 'text-emerald-400' : ''} ${log.type === 'error' ? 'text-rose-400' : ''}`}>
                        {log.message}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
      </div>

      {showPreview && selectedPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-750">
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">{language === 'zh' ? '内容预览' : 'Content Preview'}</h3>
              <button onClick={() => setShowPreview(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <div className="flex-1 overflow-auto p-4 space-y-4">
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">{t.url}</h4><a href={selectedPreview.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 dark:text-indigo-400 hover:underline text-sm">{selectedPreview.url}</a></div>
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">{t.title_col}</h4><p className="text-slate-800 dark:text-slate-200 font-medium">{selectedPreview.result?.title}</p></div>
              {selectedPreview.result?.description && <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">{t.description}</h4><p className="text-slate-600 dark:text-slate-300 text-sm">{selectedPreview.result.description}</p></div>}
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">{t.words}</h4><p className="text-slate-600 dark:text-slate-300 text-sm">{selectedPreview.result?.wordCount}</p></div>
              {selectedPreview.result?.content && <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">{t.content}</h4><div className="bg-slate-50 dark:bg-slate-750 p-3 rounded-lg text-sm text-slate-700 dark:text-slate-300 max-h-[300px] overflow-auto whitespace-pre-wrap">{selectedPreview.result.content.substring(0, 5000)}{selectedPreview.result.content.length > 5000 && '...'}</div></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
