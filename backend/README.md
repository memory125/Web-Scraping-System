# Crawl4AI Backend

基于 [Crawl4AI](https://github.com/unclecode/crawl4ai) 的 Python 后端服务，为爬虫系统提供强大的 AI 驱动爬取能力。

## 功能特性

- **基础爬取**: 快速获取网页 Markdown/HTML
- **深度爬取**: 支持 BFS/DFS/Best-First 策略
- **LLM 提取**: 使用 AI 从网页中提取结构化数据
- **浏览器控制**: 截图、PDF、执行 JavaScript
- **会话管理**: 保持登录状态、Cookie 管理
- **代理支持**: 配置代理进行爬取

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt

# 安装 Playwright 浏览器
crawl4ai-setup
# 或
python -m playwright install --with-deps chromium
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 3. 启动服务

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `ollama` |
| `LLM_MODEL` | 默认模型 | `qwen3.5:9b` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `GOOGLE_API_KEY` | Google API Key | - |
| `OLLAMA_BASE_URL` | Ollama 地址 | `http://localhost:11434` |
| `LLM_TEMPERATURE` | 温度参数 | `0.7` |
| `LLM_MAX_TOKENS` | 最大令牌数 | `2000` |

## API 接口

| 接口 | 方法 | 说明 |
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

## 使用示例

### 单 URL 爬取

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### 批量爬取

```bash
curl -X POST "http://localhost:8000/crawl/batch?urls=["https://example.com","https://example.org"]" \
  -H "Content-Type: application/json"
```

### 深度爬取

```bash
curl -X POST http://localhost:8000/crawl/deep \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://docs.example.com"],
    "max_depth": 2,
    "max_pages": 10,
    "strategy": "bfs"
  }'
```

### LLM 提取

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://openai.com/pricing",
    "instruction": "提取所有AI模型的定价信息",
    "provider": "openai/gpt-4o-mini"
  }'
```

## 支持的 LLM 提供商

| 提供商 | 需要 API Key | 默认模型 |
|--------|-------------|----------|
| OpenAI | 是 | gpt-4o-mini |
| Anthropic | 是 | claude-3-haiku |
| Google | 是 | gemini-1.5-flash |
| Ollama | 否 | qwen3.5:9b |
| DeepSeek | 是 | deepseek-chat |
| Mistral | 是 | mistral-small-latest |
| Cohere | 是 | command-r |

## 响应格式

### /crawl 响应

```json
{
  "success": true,
  "url": "https://example.com",
  "markdown": "# Page Title\n\nContent...",
  "fit_markdown": "Content...",
  "html": "<html>...</html>",
  "links": ["https://example.com/link1", "https://example.com/link2"],
  "images": ["https://example.com/img1.jpg"],
  "videos": [],
  "error": null
}
```

## 错误排查

### 常见错误

1. **端口被占用**
   ```bash
   netstat -ano | findstr :8000
   ```

2. **Playwright 未安装**
   ```bash
   python -m playwright install --with-deps chromium
   ```

3. **LLM 连接失败**
   - 检查 Ollama 是否启动
   - 检查 API Key 是否正确
   - 查看 `/llm/status` 端点

## Docker 部署

```bash
# 启动 Crawl4AI Docker 服务
docker run -d -p 11235:11235 --shm-size=1g unclecode/crawl4ai:latest

# 访问监控面板
# http://localhost:11235/dashboard
```

注意: Docker 版本使用端口 11235，与 Python 版本(8000)不同。

## 许可证

Apache 2.0 - 与 Crawl4AI 相同
