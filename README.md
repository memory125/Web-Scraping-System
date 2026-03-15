# 网页爬虫系统 (Web Scraping System)

基于 React + TypeScript 前端 + Python FastAPI 后端的全功能网页爬虫工具。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [后端服务](#后端服务)
- [LLM 配置](#llm-配置)
- [前端功能](#前端功能)
- [常见问题](#常见问题)

---

## 功能特性

### 核心功能
- 多 URL 并发爬取
- 提取标题、描述、正文、图片、视频、链接
- 内容清洗与去重
- 代理支持，绕过 CORS
- 任务队列控制（暂停/恢复/停止）
- 批量导入（CSV/TXT）
- 进度跟踪

### 导出功能
- CSV 导出
- JSON 导出
- Excel 导出
- Markdown 导出

### 高级功能
- Cookie 同步
- AI 内容分析
- 存储配置管理
- 多账号管理
- 自定义代理

### AI 能力
- 关键词提取
- 内容摘要
- 分类标签
- 情感分析

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React + TS)                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ 任务管理 │ │ 下载队列 │ │ 设置面板 │ │ AI分析面板     │   │
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
    │ (cheerio+axios)   │     │ (Playwright浏览器)  │
    └───────────────────┘     └─────────────────────┘
```

### 组件说明

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| 前端 | React 19 + TypeScript + Tailwind CSS | 用户界面 |
| 默认爬虫 | Cheerio + Axios | 轻量级爬虫，适合简单页面 |
| 后端 | FastAPI + Crawl4AI | 强大爬虫，支持 JS 渲染 |
| LLM | LiteLLM | 统一接口支持多种大模型 |
| 存储 | IndexedDB | 浏览器本地存储 |

### 爬取流程

1. **URL 输入** → 用户添加 URL 或批量导入
2. **去重检查** → 过滤重复 URL
3. **爬取策略**:
   - 后端可用 → 使用 Crawl4AI (JS 渲染)
   - 后端不可用 → 使用默认爬虫
4. **内容提取** → 标题、正文、图片、视频、链接
5. **AI 分析** → 关键词、摘要、分类（可选）
6. **导出存储** → CSV/JSON/Excel/Markdown

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

# 安装 Playwright 浏览器 (后端)
crawl4ai-setup
# 或
python -m playwright install --with-deps chromium
```

### 启动

#### 方式一：分别启动

```bash
# 终端1: 启动后端
cd backend
python main.py
# 后端运行在 http://localhost:8000

# 终端2: 启动前端
npm run dev
# 前端运行在 http://localhost:5173
```

#### 方式二：一键启动

```bash
# Windows
start.bat

# 或手动
npm run dev & cd backend && python main.py
```

---

## 后端服务

### 环境配置

复制 `.env.example` 为 `.env` 并配置：

```env
# 默认 LLM 提供商 (openai, anthropic, google, ollama, deepseek, mistral, cohere)
LLM_PROVIDER=ollama

# 默认模型
LLM_MODEL=qwen3.5:9b

# OpenAI
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google
GOOGLE_API_KEY=your-google-api-key-here

# Ollama (本地)
OLLAMA_BASE_URL=http://localhost:11434

# LLM 参数
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务状态 |
| `/health` | GET | 健康检查 |
| `/llm/status` | GET | LLM 连接状态 |
| `/llm/config` | GET | LLM 配置信息 |
| `/llm/providers` | GET | 支持的 LLM 提供商 |
| `/llm/models` | GET | 可用模型列表 |
| `/llm/connect` | GET | 手动连接 LLM |
| `/crawl` | POST | 单 URL 爬取 |
| `/crawl/batch` | POST | 批量爬取 |
| `/crawl/deep` | POST | 深度爬取 |
| `/extract` | POST | LLM 结构化提取 |

### 使用示例

```bash
# 健康检查
curl http://localhost:8000/health

# LLM 状态
curl http://localhost:8000/llm/status

# 单 URL 爬取
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# 批量爬取
curl -X POST http://localhost:8000/crawl/batch \
  -H "Content-Type: application/json" \
  -d '["https://example.com", "https://example.org"]'
```

---

## LLM 配置

### 支持的提供商

| 提供商 | API Key | 说明 |
|--------|---------|------|
| OpenAI | 需要 | GPT-4, GPT-4o 等 |
| Anthropic | 需要 | Claude-3 系列 |
| Google | 需要 | Gemini 系列 |
| Ollama | 不需要 | 本地模型 |
| DeepSeek | 需要 | DeepSeek Chat |
| Mistral | 需要 | Mistral AI |
| Cohere | 需要 | Command R |

### Ollama 本地模型

推荐安装 Ollama 运行本地大模型：

```bash
# 安装 Ollama
# https://ollama.com/download

# 拉取模型
ollama pull qwen3.5:9b
ollama pull llama2
ollama pull mistral

# 查看可用模型
ollama list
```

### 配置步骤

1. 编辑 `backend/.env` 文件
2. 设置 `LLM_PROVIDER=ollama`
3. 设置 `LLM_MODEL=qwen3.5:9b`
4. 重启后端服务

---

## 前端功能

### 任务管理

1. **添加 URL** - 输入框添加单个或多个 URL
2. **批量导入** - 支持 CSV/TXT 文件导入
3. **优先级设置** - 数字越大越优先
4. **任务控制** - 开始/暂停/恢复/停止

### 设置面板

| 设置项 | 说明 |
|--------|------|
| 并发数 | 同时爬取的页面数 |
| 超时 | 请求超时时间(秒) |
| 自动去重 | 去除重复内容 |
| 清洗内容 | 清理 HTML 标签 |
| 提取媒体 | 提取图片/视频 |
| 使用代理 | 启用代理爬取 |
| JS 渲染 | 渲染动态内容 |

### 数据导出

支持格式：
- **CSV** - 通用表格格式
- **JSON** - 结构化数据
- **Excel** - 带格式表格
- **Markdown** - Markdown 文档

---

## 常见问题

### Q: 爬取失败显示"无权限"或"私密文章"？

**A:** 这是目标网站的访问限制，可能是：
- 文章需要登录才能查看
- 文章为付费/私密内容
- 网站反爬虫机制

**解决方案：**
1. 在设置中添加网站 Cookie
2. 使用代理 IP
3. 换其他公开文章测试

### Q: 后端启动失败？

**A:** 检查以下内容：
1. 端口 8000 是否被占用
2. Playwright 是否正确安装
3. Python 依赖是否完整

```bash
# 检查端口
netstat -ano | findstr :8000

# 重新安装依赖
pip install -r requirements.txt

# 重新安装 Playwright
python -m playwright install --with-deps chromium
```

### Q: Ollama 连接失败？

**A:** 
1. 确保 Ollama 已启动
2. 检查 `OLLAMA_BASE_URL` 配置
3. 确认模型已下载

```bash
# 检查 Ollama 状态
curl http://localhost:11434/api/tags
```

### Q: 如何使用 LLM 分析？

**A:**
1. 配置 `.env` 中的 LLM 提供商
2. 启用设置中的 AI 分析选项
3. 爬取时自动进行分析

### Q: 代理不工作？

**A:**
1. 确认代理格式正确 (`http://host:port`)
2. 检查代理是否可用
3. 尝试使用其他代理

---

## 技术栈

### 前端
- React 19
- TypeScript
- Tailwind CSS v4
- Vite
- idb (IndexedDB)
- xlsx (Excel 导出)

### 后端
- Python 3.10+
- FastAPI
- Crawl4AI
- LiteLLM
- Playwright

---

## 许可证

MIT License
