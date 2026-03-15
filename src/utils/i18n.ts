export type Language = 'en' | 'zh';

export interface Translations {
  title: string;
  subtitle: string;
  queue: string;
  history: string;
  schedule: string;
  deepCrawl: string;
  addUrl: string;
  enterUrl: string;
  priority: string;
  low: string;
  mediumLow: string;
  normal: string;
  mediumHigh: string;
  high: string;
  search: string;
  status: string;
  title_col: string;
  words: string;
  description: string;
  actions: string;
  pending: string;
  scraping: string;
  completed: string;
  failed: string;
  view: string;
  retry: string;
  delete: string;
  loadConfig: string;
  exportConfig: string;
  startCrawler: string;
  pause: string;
  stop: string;
  resume: string;
  settings: string;
  concurrency: string;
  timeout: string;
  crawlDepth: string;
  customProxies: string;
  addProxy: string;
  logs: string;
  content: string;
  url: string;
  noResults: string;
  export: string;
  import: string;
  csv: string;
  json: string;
  excel: string;
  markdown: string;
  parseSitemap: string;
  deepCrawlSettings: string;
  maxDepth: string;
  maxPages: string;
  crawlStrategy: string;
  startDeepCrawl: string;
  deepCrawling: string;
  parsing: string;
  noUrlsFound: string;
  progress: string;
  visualizer: string;
  totalUrls: string;
  avgWords: string;
  totalWords: string;
  successRate: string;
  category: string;
  sentiment: string;
  positive: string;
  neutral: string;
  negative: string;
  scheduledTasks: string;
  noScheduledTasks: string;
  taskName: string;
  addTask: string;
  enable: string;
  disable: string;
  save: string;
  cancel: string;
  language: string;
  selectProxy: string;
  accounts: string;
  addAccount: string;
  platform: string;
  cookies: string;
  download: string;
  downloadAll: string;
  downloadImages: string;
  downloadVideos: string;
  saveResume: string;
  loadResume: string;
  autoResume: string;
  maxRetries: string;
  proxyPool: string;
  addProxy: string;
  addCustomProxy: string;
  cookieSync: string;
  addCookie: string;
  syncCookies: string;
  aiAnalysis: string;
  viralElements: string;
  inspiration: string;
  analyzeContent: string;
  storage: string;
  addStorage: string;
  excelStorage: string;
  mysqlStorage: string;
  testConnection: string;
  aiModel: string;
  addModel: string;
  apiKey: string;
  endpoint: string;
  model: string;
  provider: string;
  temperature: string;
  maxTokens: string;
  openai: string;
  anthropic: string;
  google: string;
  local: string;
  custom: string;
  backend: string;
  backendUrl: string;
  enableBackend: string;
}

export const translations: Record<Language, Translations> = {
  en: {
    title: 'Crawler Controller',
    subtitle: 'Manage and execute distributed web scraping tasks',
    queue: 'Queue',
    history: 'History',
    schedule: 'Schedule',
    deepCrawl: 'Deep Crawl',
    addUrl: 'Add',
    enterUrl: 'Enter URL (auto-normalized)',
    priority: 'Priority',
    low: 'Low',
    mediumLow: 'Medium-Low',
    normal: 'Normal',
    mediumHigh: 'Medium-High',
    high: 'High',
    search: 'Search URLs, titles, content...',
    status: 'Status',
    title_col: 'Title',
    words: 'Words',
    description: 'Description',
    actions: 'Actions',
    pending: 'Pending',
    scraping: 'Scraping',
    completed: 'Completed',
    failed: 'Failed',
    view: 'View',
    retry: 'Retry',
    delete: 'Delete',
    loadConfig: 'Load Config',
    exportConfig: 'Export Config',
    startCrawler: 'Start Crawler',
    pause: 'Pause',
    stop: 'Stop',
    resume: 'Resume',
    settings: 'Settings',
    concurrency: 'Concurrency',
    timeout: 'Timeout (ms)',
    crawlDepth: 'Crawl Depth',
    customProxies: 'Custom Proxies',
    addProxy: 'Add proxy...',
    logs: 'System Logs',
    content: 'Content',
    url: 'URL',
    noResults: 'No results',
    export: 'Export',
    import: 'Import',
    csv: 'CSV',
    json: 'JSON',
    excel: 'Excel',
    markdown: 'Markdown',
    parseSitemap: 'Parse Sitemap',
    deepCrawlSettings: 'Deep Crawl Settings',
    maxDepth: 'Max Depth',
    maxPages: 'Max Pages',
    crawlStrategy: 'Crawl Strategy',
    startDeepCrawl: 'Start Deep Crawl',
    deepCrawling: 'Deep Crawling...',
    parsing: 'Parsing...',
    noUrlsFound: 'No URLs found',
    progress: 'Progress',
    visualizer: 'Data Visualization',
    totalUrls: 'Total URLs',
    avgWords: 'Avg Words',
    totalWords: 'Total Words',
    successRate: 'Success Rate',
    category: 'Category',
    sentiment: 'Sentiment',
    positive: 'Positive',
    neutral: 'Neutral',
    negative: 'Negative',
    scheduledTasks: 'Scheduled Tasks',
    noScheduledTasks: 'No scheduled tasks',
    taskName: 'Task Name',
    addTask: 'Add Task',
    enable: 'Enabled',
    disable: 'Disabled',
    save: 'Save',
    cancel: 'Cancel',
    language: 'Language',
    selectProxy: 'Select Proxy',
    accounts: 'Accounts',
    addAccount: 'Add Account',
    platform: 'Platform',
    cookies: 'Cookies',
    download: 'Download',
    downloadAll: 'Download All',
    downloadImages: 'Download Images',
    downloadVideos: 'Download Videos',
    saveResume: 'Save Resume Point',
    loadResume: 'Load Resume Point',
    autoResume: 'Auto Resume',
    maxRetries: 'Max Retries',
    proxyPool: 'Proxy Pool',
    addCustomProxy: 'Add Proxy',
    cookieSync: 'Cookie Sync',
    addCookie: 'Add Cookie',
    syncCookies: 'Sync from Chrome',
    aiAnalysis: 'AI Analysis',
    viralElements: 'Viral Elements',
    inspiration: 'Inspiration',
    analyzeContent: 'Analyze Content',
    storage: 'Storage',
    addStorage: 'Add Storage',
    excelStorage: 'Excel',
    mysqlStorage: 'MySQL',
    testConnection: 'Test Connection',
    aiModel: 'AI Model',
    addModel: 'Add Model',
    apiKey: 'API Key',
    endpoint: 'Endpoint',
    model: 'Model',
    provider: 'Provider',
    temperature: 'Temperature',
    maxTokens: 'Max Tokens',
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    local: 'Local',
    custom: 'Custom',
    backend: 'Backend',
    backendUrl: 'Backend URL',
    enableBackend: 'Enable Backend',
  },
  zh: {
    title: '爬虫控制器',
    subtitle: '管理并执行分布式网页爬取任务',
    queue: '队列',
    history: '历史',
    schedule: '定时',
    deepCrawl: '深度爬取',
    addUrl: '添加',
    enterUrl: '输入 URL (自动标准化)',
    priority: '优先级',
    low: '低',
    mediumLow: '中低',
    normal: '普通',
    mediumHigh: '中高',
    high: '高',
    search: '搜索 URL、标题、内容...',
    status: '状态',
    title_col: '标题',
    words: '字数',
    description: '描述',
    actions: '操作',
    pending: '等待中',
    scraping: '爬取中',
    completed: '已完成',
    failed: '失败',
    view: '查看',
    retry: '重试',
    delete: '删除',
    loadConfig: '加载配置',
    exportConfig: '导出配置',
    startCrawler: '启动爬虫',
    pause: '暂停',
    stop: '停止',
    resume: '恢复',
    settings: '设置',
    concurrency: '并发数',
    timeout: '超时时间 (毫秒)',
    crawlDepth: '爬取深度',
    customProxies: '自定义代理',
    addProxy: '添加代理...',
    logs: '系统日志',
    content: '内容',
    url: '网址',
    noResults: '无结果',
    export: '导出',
    import: '导入',
    csv: 'CSV',
    json: 'JSON',
    excel: 'Excel',
    markdown: 'Markdown',
    parseSitemap: '解析网站地图',
    deepCrawlSettings: '深度爬取设置',
    maxDepth: '最大深度',
    maxPages: '最大页面数',
    crawlStrategy: '爬取策略',
    startDeepCrawl: '开始深度爬取',
    deepCrawling: '深度爬取中...',
    parsing: '解析中...',
    noUrlsFound: '未找到网址',
    progress: '进度',
    visualizer: '数据可视化',
    totalUrls: '总 URL',
    avgWords: '平均字数',
    totalWords: '总字数',
    successRate: '成功率',
    category: '分类',
    sentiment: '情感',
    positive: '正面',
    neutral: '中性',
    negative: '负面',
    scheduledTasks: '定时任务',
    noScheduledTasks: '无定时任务',
    taskName: '任务名称',
    addTask: '添加任务',
    enable: '启用',
    disable: '禁用',
    save: '保存',
    cancel: '取消',
    language: '语言',
    selectProxy: '选择代理',
    accounts: '账号管理',
    addAccount: '添加账号',
    platform: '平台',
    cookies: 'Cookies',
    download: '下载',
    downloadAll: '批量下载',
    downloadImages: '下载图片',
    downloadVideos: '下载视频',
    saveResume: '保存断点',
    loadResume: '加载断点',
    autoResume: '自动恢复',
    maxRetries: '最大重试',
    proxyPool: '代理池',
    addCustomProxy: '添加代理',
    cookieSync: 'Cookie同步',
    addCookie: '添加Cookie',
    syncCookies: '从Chrome同步',
    aiAnalysis: 'AI内容分析',
    viralElements: '爆款元素',
    inspiration: '创作灵感',
    analyzeContent: '分析内容',
    storage: '数据存储',
    addStorage: '添加存储',
    excelStorage: 'Excel',
    mysqlStorage: 'MySQL',
    testConnection: '测试连接',
    aiModel: 'AI模型',
    addModel: '添加模型',
    apiKey: 'API密钥',
    endpoint: '接口地址',
    model: '模型',
    provider: '提供商',
    temperature: '温度',
    maxTokens: '最大令牌',
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    local: '本地',
    custom: '自定义',
    backend: '后端服务',
    backendUrl: '后端地址',
    enableBackend: '启用后端',
  },
};

export function getTranslation(lang: Language): Translations {
  return translations[lang];
}
