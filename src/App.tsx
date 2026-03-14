import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Target, AppConfig, LogEntry, HistoryRecord, ScheduledTask, CrawlState } from './types';
import { Play, Square, Upload, Download, Plus, Trash2, FileJson, FileSpreadsheet, Settings, Pause, X, Clock, FileText, RefreshCw, Moon, Sun, Check, ChevronDown, ChevronUp, BarChart3, Activity, Globe, Layers, Languages } from 'lucide-react';
import { crawlUrl, parseSitemap } from './utils/crawler';
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
  }
};

export default function App() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [settings, setSettings] = useState<AppConfig['settings']>(DEFAULT_CONFIG.settings);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [crawlState, setCrawlState] = useState<CrawlState>('idle');
  const [newUrl, setNewUrl] = useState('');
  const [activeTab, setActiveTab] = useState<'queue' | 'history' | 'schedule'>('queue');
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [themeColor, setThemeColor] = useState(() => localStorage.getItem('themeColor') || 'indigo');
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
    
    try {
      const result = await crawlUrl(target.url, { 
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
  }, [settings]);

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

  const stats = {
    total: targets.length,
    pending: targets.filter(t => t.status === 'pending').length,
    scraping: targets.filter(t => t.status === 'scraping').length,
    completed: targets.filter(t => t.status === 'completed').length,
    failed: targets.filter(t => t.status === 'failed').length,
    progress: targets.length > 0 ? Math.round(((targets.filter(t => t.status === 'completed').length + targets.filter(t => t.status === 'failed').length) / targets.length) * 100) : 0,
  };

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
              value={themeColor}
              onChange={(e) => setThemeColor(e.target.value)}
              className="px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700"
            >
              <option value="indigo">Indigo</option>
              <option value="blue">Blue</option>
              <option value="emerald">Emerald</option>
              <option value="amber">Amber</option>
              <option value="rose">Rose</option>
              <option value="purple">Purple</option>
            </select>
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
                className="inline-flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-bold text-white transition-colors shadow-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4 fill-current" /> {t.startCrawler}
              </button>
            )}
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-3 space-y-6">
            {stats.total > 0 && (
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-600 dark:text-slate-300">Progress ({crawlState})</span>
                  <span className="font-medium text-indigo-600 dark:text-indigo-400">{stats.progress}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
                  <div className="bg-indigo-600 dark:bg-indigo-500 h-2.5 rounded-full transition-all duration-500" style={{ width: `${stats.progress}%` }}></div>
                </div>
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-2">
                  <span>{stats.completed} completed</span>
                  <span>{stats.pending} pending</span>
                  <span>{stats.scraping} scraping</span>
                  <span>{stats.failed} failed</span>
                </div>
              </div>
            )}

            {showVisualizer && (
              <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
                <h3 className="font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" /> Data Visualization
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">Total URLs</div>
                    <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{stats.total}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">Avg Words</div>
                    <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{avgWordCount}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">Total Words</div>
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{totalWords.toLocaleString()}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <div className="text-xs text-slate-500 dark:text-slate-400">Success Rate</div>
                    <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}%</div>
                  </div>
                </div>
                {Object.keys(categoryStats).length > 0 && (
                  <div className="mb-4">
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1"><Layers className="w-3 h-3" /> Category Distribution</div>
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
                    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1"><Activity className="w-3 h-3" /> Sentiment Analysis</div>
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
                </div>
                <div className="flex gap-2 items-center">
                  {activeTab === 'queue' && (
                    <>
                      <button onClick={() => setShowImportOptions(!showImportOptions)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-medium transition-colors">
                        <FileText className="w-3.5 h-3.5" /> Import {showImportOptions ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                      <button onClick={() => setShowExportOptions(!showExportOptions)} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-medium transition-colors">
                        <Download className="w-3.5 h-3.5" /> {t.export} {showExportOptions ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {activeTab === 'queue' && showImportOptions && (
                <div className="p-4 bg-slate-100 dark:bg-slate-750 border-b border-slate-200 dark:border-slate-700 space-y-3">
                  <p className="text-xs text-slate-600 dark:text-slate-400">Import URLs from CSV or TXT file</p>
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

                  <div className="h-[400px] overflow-auto">
                {activeTab === 'queue' && filteredTargets.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 p-8 text-center">
                    <Settings className="w-12 h-12 mb-3 text-slate-300 dark:text-slate-600" />
                    <p>{searchQuery ? (language === 'zh' ? '无匹配结果' : 'No matching results') : (language === 'zh' ? '尚未添加目标' : 'No targets added yet')}</p>
                    <p className="text-sm mt-1">{searchQuery ? (language === 'zh' ? '尝试其他搜索词' : 'Try a different search term') : (language === 'zh' ? '在上方添加 URL 或从文件导入' : 'Add a URL above or import from file')}</p>
                  </div>
                )}

                {activeTab === 'queue' && filteredTargets.length > 0 && (
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
                              <button onClick={() => { setSelectedPreview(target); setShowPreview(true); }} className="text-indigo-400 hover:text-indigo-600 dark:text-indigo-500 dark:hover:text-indigo-300 transition-colors p-1 mr-2" title="Preview">
                                <FileText className="w-4 h-4" />
                              </button>
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
              </div>
            </div>
          </div>

          <div className="space-y-6">
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
                <div className="space-y-2">
                  {['autoDedup', 'cleanContent', 'deduplicateContent', 'extractMedia', 'useProxy', 'randomDelay', 'useJsRendering', 'autoDetectEncoding'].map(key => (
                    <div key={key} className="flex items-center gap-2">
                      <input type="checkbox" id={key} checked={settings[key as keyof typeof settings] as boolean || false} onChange={(e) => setSettings(s => ({ ...s, [key]: e.target.checked }))} className="rounded" />
                      <label htmlFor={key} className="text-xs text-slate-600 dark:text-slate-400">
                        {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                      </label>
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Advanced Options</label>
                  <div className="space-y-2">
                    {[
                      { key: 'extractKeywords', label: 'Extract Keywords' },
                      { key: 'generateSummary', label: 'Auto Summary' },
                      { key: 'classifyContent', label: 'Content Classification' },
                      { key: 'analyzeSentiment', label: 'Sentiment Analysis' },
                    ].map(({ key }) => (
                      <div key={key} className="flex items-center gap-2">
                        <input type="checkbox" id={key} checked={settings[key as keyof typeof settings] as boolean || false} onChange={(e) => setSettings(s => ({ ...s, [key]: e.target.checked }))} className="rounded" />
                        <label htmlFor={key} className="text-xs text-slate-600 dark:text-slate-400">{key.replace(/([A-Z])/g, ' ')}</label>
                      </div>
                    ))}
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
      </div>

      {showPreview && selectedPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-750">
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">Content Preview</h3>
              <button onClick={() => setShowPreview(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <div className="flex-1 overflow-auto p-4 space-y-4">
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">URL</h4><a href={selectedPreview.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 dark:text-indigo-400 hover:underline text-sm">{selectedPreview.url}</a></div>
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">Title</h4><p className="text-slate-800 dark:text-slate-200 font-medium">{selectedPreview.result?.title}</p></div>
              {selectedPreview.result?.description && <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">Description</h4><p className="text-slate-600 dark:text-slate-300 text-sm">{selectedPreview.result.description}</p></div>}
              <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">Word Count</h4><p className="text-slate-600 dark:text-slate-300 text-sm">{selectedPreview.result?.wordCount} words</p></div>
              {selectedPreview.result?.content && <div><h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">Content</h4><div className="bg-slate-50 dark:bg-slate-750 p-3 rounded-lg text-sm text-slate-700 dark:text-slate-300 max-h-[300px] overflow-auto whitespace-pre-wrap">{selectedPreview.result.content.substring(0, 5000)}{selectedPreview.result.content.length > 5000 && '...'}</div></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
