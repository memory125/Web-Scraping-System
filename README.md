# 网页爬虫系统

基于 React + TypeScript 的全功能网页爬虫工具。

## 功能特性

- 多 URL 并发爬取
- 提取标题、描述、正文、图片、视频、链接
- 内容清洗与去重
- 导出为 CSV/JSON/Excel/Markdown
- 代理支持，绕过 CORS
- IndexedDB 本地存储
- 暗色模式 UI
- 任务队列控制（暂停/恢复/停止）
- 批量导入（CSV/TXT）
- 进度跟踪

## 快速开始

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

## 技术栈

- React 19
- TypeScript
- Tailwind CSS v4
- Vite
- idb (IndexedDB)
- xlsx (Excel 导出)
