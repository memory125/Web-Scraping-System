# Crawl4AI Backend

基于 [Crawl4AI](https://github.com/unclecode/crawl4ai) 的Python后端服务，为爬虫系统提供强大的AI驱动爬取能力。

## 功能特性

- **基础爬取**: 快速获取网页Markdown/HTML
- **深度爬取**: 支持BFS/DFS/Best-First策略
- **LLM提取**: 使用AI从网页中提取结构化数据
- **浏览器控制**: 截图、PDF、执行JavaScript
- **会话管理**: 保持登录状态、Cookie管理
- **代理支持**: 配置代理进行爬取

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt

# 安装Playwright浏览器
crawl4ai-setup
# 或
python -m playwright install --with-deps chromium
```

### 2. 启动服务

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式3: Docker部署
docker pull unclecode/crawl4ai:latest
docker run -d -p 11235:11235 --name crawl4ai unclecode/crawl4ai:latest
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入API密钥:

```bash
cp .env.example .env
# 编辑 .env 文件
```

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务状态 |
| `/health` | GET | 健康检查 |
| `/crawl` | POST | 单URL爬取 |
| `/crawl/batch` | POST | 批量爬取 |
| `/crawl/deep` | POST | 深度爬取 |
| `/extract` | POST | LLM结构化提取 |
| `/browser/screenshot` | POST | 页面截图 |
| `/browser/execute` | POST | 执行JavaScript |

### 使用示例

#### 单URL爬取
```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

#### 批量爬取
```bash
curl -X POST http://localhost:8000/crawl/batch \
  -H "Content-Type: application/json" \
  -d '["https://example.com", "https://example.org"]'
```

#### 深度爬取
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

#### LLM提取
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://openai.com/pricing",
    "instruction": "提取所有AI模型的定价信息",
    "provider": "openai/gpt-4o-mini",
    "api_key": "your-api-key"
  }'
```

## 前端配置

在前端设置中启用后端服务:

1. 打开设置面板
2. 启用"后端服务(Crawl4AI)"
3. 输入后端URL (默认: `http://localhost:8000`)
4. 点击"测试连接"验证

## 支持的LLM提供商

- OpenAI (gpt-4, gpt-3.5-turbo, etc.)
- Anthropic (claude-3-opus, claude-3-sonnet, etc.)
- Google (gemini-pro, gemini-1.5-flash, etc.)
- Ollama (本地模型: llama2, mistral, etc.)
- 自定义API

## Docker部署

```bash
# 启动Crawl4AI Docker服务
docker run -d -p 11235:11235 --shm-size=1g unclecode/crawl4ai:latest

# 访问监控面板
# http://localhost:11235/dashboard
```

注意: Docker版本使用端口 11235，与Python版本(8000)不同。

## 许可证

Apache 2.0 - 与Crawl4AI相同
