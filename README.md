# RAG Blog — AI 个人技术博客

一个基于 **FastAPI + LangChain + ChromaDB** 的 AI 问答博客系统。
文章自带"AI 大脑"：访客可以直接向博客提问，AI 会基于知识库内容回答。

## ✨ 功能

- 📝 文章管理（增删改查，MySQL 存储）
- 🤖 **AI 问答**（RAG：检索增强生成）
- 🔄 一键更新知识库（新文章自动向量化）
- 🛡️ **防幻觉设计**（资料里没有的答案会如实说明）

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI |
| 数据库 | MySQL |
| 向量库 | ChromaDB |
| AI | LangChain · Ollama（nomic-embed-text 嵌入 + deepseek-r1:8b 生成） |
| 前端 | 原生 HTML/CSS/JS |

## 🏗️ 工作原理（RAG 流程）
访客提问
│
▼
/rag ──→ 向量检索（ChromaDB 找最相关的资料）
│                       │
▼                       ▼
deepseek-r1:8b ←── 资料 + 防幻觉提示词
│
▼
AI 回答


## 🚀 快速开始

1. **准备环境**：Python 3.10+、MySQL、Ollama

2. **拉取模型**：
   ```bash
   ollama pull nomic-embed-text
   ollama pull deepseek-r1:8b

3. **安装依赖**：
    pip install fastapi uvicorn pymysql python-dotenv \
                langchain chromadb langchain-chroma \
                langchain-ollama langchain-text-splitters

4. **配置 .env**（本地创建，不进仓库）：
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=wen_blog

5. **初始化数据库**（MySQL执行）：
CREATE DATABASE wen_blog;
USE wen_blog;
CREATE TABLE cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    date VARCHAR(50),
    `desc` TEXT
);

6. **启动服务**：
cd backend
uvicorn main:app --reload

7. **初始化向量库**：调用 POST /ai-init（把文章向量化）

## 📂 项目结构
├── backend/
│   ├── main.py          # FastAPI 主程序（CRUD + RAG）
│   └── ai_service.py    # 向量库操作
├── reindex.html         # 前端页面
├── style-practice.css   # 样式
└── .env                 # 本地配置（不进仓库）

## 📌 API 一览
方法	路径	说明
GET	/cards	文章列表
POST	/cards	新增文章
DELETE	/cards/{index}	删除文章
PUT	/cards/{index}	更新文章
POST	/ai-init	向量化文章（更新知识库）
POST	/rag	AI 问答