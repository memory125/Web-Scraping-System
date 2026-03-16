# 网页爬虫系统 (Web Scraping System)

基于 React + TypeScript 前端 + Python FastAPI 后端的全功能网页爬虫工具，集成 Crawl4AI v0.8.x 最先进功能。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [后端服务](#后端服务)
- [LLM 配置](#llm-配置)
- [高级特性](#高级特性)
- [Docker部署](#docker部署)
- [常见问题](#常见问题)

---

## 功能特性

### 核心爬取
- 单/批量 URL 爬取
- 深度爬取 (BFS/DFS/Best-First)
- 自适应爬取 (智能停止)
- 电商平台爬取 (Amazon/eBay/Taobao/JD等)
- 卖家深爬

### 内容提取
- Markdown 清洗 (Clean/Fit)
- CSS 选择器提取
- XPath 提取
- 正则表达式提取
- LLM 结构化提取 (Pydantic Schema)
- 表格提取 (DataFrame)
- 聚类提取
- 余弦相似度过滤
- BM25 内容过滤

### 浏览器控制
- 截图/PDF/MHTML 导出
- 反爬虫模式 (Stealth/Undetected)
- 代理轮换 (HTTP/SOCKS5)
- 会话管理 (Cookies/Storage State)
- 虚拟滚动 (Twitter/Instagram)
- 懒加载处理
- 分页爬取

### 性能优化
- Rate Limiter 调度器
- Memory Adaptive 调度器
- Semaphore 调度器
- 代理粘性会话
- Prefetch 模式 (5-10x加速)
- Text-Only 模式 (3-4x加速)
- 崩溃恢复 (Crash Recovery)

### AI 能力 (Crawl4AI v0.8.x)
- LLM 结构化提取
- 内容摘要
- 知识库构建
- URL 智能发现
- 语义搜索

### v0.8.x 新特性
- ✅ Prefetch 模式 - 快速 URL 发现
- ✅ Crash Recovery - 深度爬取崩溃恢复
- ✅ Text-Only 模式 - 禁用 JS/图片加速
- ✅ Dynamic Viewport - 动态视口调整
- ✅ CDP 连接管理 - 浏览器复用
- ✅ Sticky Proxy - 粘性会话代理
- ✅ Full Page Scan - 全页面扫描

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React + TS)                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ 任务管理 │ │ 下载队列 │ │ 高级面板 │ │ AI分析面板     │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘   │
│       │           │           │               │             │
│       └───────────┴───────────┴───────────────┘             │
│                           │                                   │
│                    ┌──────┴──────┐                          │
│                    │  API 层     │                          │
│                    └──────┬──────┘                          │
└───────────────────────────┼─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
    ┌─────────▼─────────┐     ┌──────────▼──────────┐
    │   默认爬虫引擎     │     │   Crawl4AI 后端    │
    │ (cheerio+axios)  │     │ (125+ API 端点)    │
    └───────────────────┘     └─────────────────────┘
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 前端 | React 19 + TS + Tailwind | 现代 UI 界面 |
| 后端 | FastAPI + Crawl4AI | 125+ API 端点 |
| LLM | LiteLLM | 统一多模型接口 |
| 浏览器 | Playwright | JS 渲染支持 |
| 存储 | IndexedDB | 本地数据持久化 |

---

## 快速开始

### 前置要求
- Node.js 18+
- Python 3.10+
- (可选) Ollama 本地大模型

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd web-scraping-system

# 安装前端依赖
npm install

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装 Playwright 浏览器
crawl4ai-setup
# 或
python -m playwright install --with-deps chromium
```

### 启动

```bash
# 终端1: 后端 (端口 8001)
cd backend
python main.py

# 终端2: 前端 (端口 5173)
npm run dev
```

或使用 Windows 一键启动:
```bash
start.bat
```

---

## 后端服务

### 环境配置

```env
# LLM 提供商 (openai/anthropic/google/ollama/deepseek/mistral/cohere)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# API Keys
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
GOOGLE_API_KEY=your-key

# Ollama (本地)
OLLAMA_BASE_URL=http://localhost:11434
```

### API 端点 (125+)

#### 基础爬取
| 端点 | 方法 | 说明 |
|------|------|------|
| `/crawl` | POST | 单 URL 爬取 |
| `/crawl/batch` | POST | 批量爬取 |
| `/crawl/deep` | POST | 深度爬取 |
| `/crawl/adaptive` | POST | 自适应爬取 |

#### 高级爬取
| 端点 | 方法 | 说明 |
|------|------|------|
| `/crawl/prefetch` | POST | Prefetch 快速发现 |
| `/crawl/text-only` | POST | Text-Only 加速 |
| `/crawl/dynamic-viewport` | POST | 动态视口 |
| `/crawl/full-scan` | POST | 全页面扫描 |
| `/crawl/crash-recovery` | POST | 崩溃恢复 |
| `/crawl/virtual-scroll` | POST | 虚拟滚动 |
| `/crawl/pagination` | POST | 分页爬取 |

#### 提取策略
| 端点 | 方法 | 说明 |
|------|------|------|
| `/extract` | POST | LLM 提取 |
| `/extract/css` | POST | CSS 提取 |
| `/extract/xpath` | POST | XPath 提取 |
| `/extract/regex` | POST | 正则提取 |
| `/extract/cosine` | POST | 余弦相似度 |
| `/extract/clustering` | POST | 聚类提取 |
| `/extract/tables` | POST | 表格提取 |

#### 电商爬取
| 端点 | 方法 | 说明 |
|------|------|------|
| `/extract/ecommerce` | POST | 电商平台爬取 |
| `/extract/ecommerce/seller` | POST | 卖家深爬 |

#### 浏览器控制
| 端点 | 方法 | 说明 |
|------|------|------|
| `/browser/screenshot` | POST | 截图 |
| `/crawl/page-pdf` | POST | PDF 导出 |
| `/crawl/mhtml` | POST | MHTML 导出 |
| `/browser/execute` | POST | JS 执行 |

#### 反爬虫
| 端点 | 方法 | 说明 |
|------|------|------|
| `/crawl/anti-bot` | POST | 反爬虫模式 |
| `/crawl/stealth` | POST | Stealth 模式 |

#### 代理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/crawl/proxy-rotation` | POST | 代理轮换 |
| `/crawl/socks5` | POST | SOCKS5 代理 |
| `/crawl/sticky-proxy` | POST | 粘性代理 |
| `/crawl/http-proxy` | POST | HTTP 代理 |

#### 调度器
| 端点 | 方法 | 说明 |
|------|------|------|
| `/crawl/rate-limited` | POST | 限速调度 |
| `/crawl/memory-adaptive` | POST | 内存自适应 |
| `/crawl/semaphore` | POST | 信号量调度 |

#### LLM
| 端点 | 方法 | 说明 |
|------|------|------|
| `/llm/status` | GET | LLM 状态 |
| `/llm/providers` | GET | 提供商列表 |
| `/llm/models` | GET | 模型列表 |
| `/llm/completions` | POST | LLM 调用 |
| `/llm/test` | POST | 测试连接 |

---

## LLM 配置

### 支持的提供商

| 提供商 | 需要 API Key | 模型示例 |
|--------|-------------|---------|
| OpenAI | ✅ | gpt-4o, gpt-4o-mini |
| Anthropic | ✅ | claude-3.5-sonnet |
| Google | ✅ | gemini-1.5-flash |
| Ollama | ❌ | qwen2.5, llama3 |
| DeepSeek | ✅ | deepseek-chat |
| Mistral | ✅ | mistral-large |
| Groq | ✅ | llama-3.2-90b |

### Ollama 本地模型

```bash
# 安装 Ollama
# https://ollama.com

# 拉取模型
ollama pull qwen2.5:7b
ollama pull llama3:8b

# 查看模型
ollama list
```

---

## 高级特性

### 崩溃恢复
```python
# 使用 resume_state 从检查点恢复
config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=3,
        resume_state=saved_state  # 上次保存的状态
    )
)
```

### Prefetch 模式
```python
# 5-10x 快速 URL 发现，跳过完整渲染
config = CrawlerRunConfig(prefetch=True)
```

### Text-Only 模式
```python
# 禁用 JS/图片，3-4x 加速
browser_cfg = BrowserConfig(text_mode=True)
```

### 智能知识库
```python
# 自动发现相关 URL 并构建知识库
result = await crawler.arun(
    url="https://docs.example.com",
    query="installation guide"
)
```

---

## Docker 部署

### 构建并运行

```bash
# 构建镜像
docker build -t crawl4ai-web .

# 或使用 docker-compose
docker-compose up -d
```

### Docker 环境变量

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your-key
```

---

## 常见问题

### Q: 爬取失败显示"无权限"？
**A:** 
1. 添加网站 Cookie
2. 使用代理 IP
3. 启用 Stealth 模式

### Q: 后端启动失败？
**A:**
```bash
# 检查端口
netstat -ano | findstr :8001

# 重新安装 Playwright
python -m playwright install --with-deps chromium
```

### Q: Ollama 连接失败？
**A:**
```bash
# 检查状态
curl http://localhost:11434/api/tags

# 配置正确 URL
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 许可证

MIT License
