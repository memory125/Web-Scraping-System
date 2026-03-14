export type Language = 'en' | 'zh';

export interface Translations {
  title: string;
  subtitle: string;
  queue: string;
  history: string;
  schedule: string;
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
}

export const translations: Record<Language, Translations> = {
  en: {
    title: 'Crawler Controller',
    subtitle: 'Manage and execute distributed web scraping tasks',
    queue: 'Queue',
    history: 'History',
    schedule: 'Schedule',
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
  },
  zh: {
    title: '爬虫控制器',
    subtitle: '管理并执行分布式网页爬取任务',
    queue: '队列',
    history: '历史',
    schedule: '定时',
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
  },
};

export function getTranslation(lang: Language): Translations {
  return translations[lang];
}
