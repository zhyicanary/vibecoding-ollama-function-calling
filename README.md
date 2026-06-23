# AI 数字人对话应用 — Supervisor + Team 多智能体系统 v3

基于 Ollama 本地大模型的 AI 数字人对话应用，采用 LangGraph Supervisor + 6 个专业 Agent 团队协作架构，集成 Function Calling、RAG 课程问答、简历筛选、语音交互等功能。

## 技术栈

- **前端**: React 18 + Vite + Web Speech API (STT/TTS)
- **后端**: Python FastAPI + Pydantic
- **AI**: Ollama 本地大模型
- **框架**: LangGraph (Supervisor 路由 + Agent 循环调度) + LangChain (工具函数、RAG 检索、LCEL Chain)

## 架构概览

```
                          ┌─────────────────────┐
                          │    Supervisor LLM    │
                          │   (Planner + Router) │
                          └──────────┬──────────┘
                                     │ 条件路由
         ┌─────────────┬─────────────┼─────────────┬──────────────┬──────────────┐
         ▼             ▼             ▼             ▼              ▼              ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌──────────┐
   │ utility  │ │  comm    │ │ finance  │ │ knowledge  │ │  resume   │ │  chat    │
   │ qwen0.6b │ │ qwen3.5  │ │ qwen3.5  │ │ qwen3.5    │ │ qwen3.5   │ │ qwen3.5  │
   │ 天气/时间│ │ 邮件/钉钉│ │ 股票查询 │ │ RAG 课程   │ │ 简历评估  │ │ 纯对话   │
   └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬─────┘ └─────┬─────┘ └────┬─────┘
        │            │            │               │             │            │
        └────────────┴────────────┴───────────────┴─────────────┴────────────┘
                                     │ LOOP: agent → supervisor
                                     ▼
                                 FINISH
```

**Supervisor 两阶段工作流：**
1. **Planning** — Supervisor LLM 分析用户输入，拆解为原子任务列表，分配给对应 Agent
2. **Dispatch** — 逐个执行任务，Agent 完成后返回 Supervisor 继续调度下一任务，全部完成后合成最终回复

## 项目结构

```
vibecoding-ollama-function-calling/
├── main.py                    # 入口点
├── pyproject.toml             # Python 项目配置 (uv)
├── backend/
│   ├── app.py                 # FastAPI 应用 + 状态图构建
│   ├── supervisor_agent.py    # Supervisor LLM (Planner + 合成)
│   ├── state.py               # TeamState 共享状态定义
│   ├── routing.py             # 基于规则的意图路由
│   ├── tools.py               # 工具/服务函数 + RAG 系统
│   ├── agents/                # 6 个专业 Agent 模块
│   │   ├── utility_agent.py   # 天气 + 时间
│   │   ├── comm_agent.py      # 邮件 + 钉钉
│   │   ├── finance_agent.py   # 股票查询
│   │   ├── knowledge_agent.py # RAG 课程问答
│   │   ├── resume_agent.py    # 简历筛选评估
│   │   └── chat_agent.py      # 纯对话
│   ├── test/                  # 单元测试
│   ├── .env                   # 环境变量
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # 主应用 (含 STT/TTS 语音交互)
│   │   ├── index.css          # 赛博朋克风格样式
│   │   └── main.jsx           # 入口
│   ├── index.html
│   ├── vite.config.js         # Vite 配置 (含 API 代理)
│   └── package.json
└── docs/                      # 课程文档 (RAG 知识库)
```

## 快速启动

### 前置条件

- Python ≥ 3.11 + [uv](https://docs.astral.sh/uv/) (推荐) 或 pip
- Node.js ≥ 18 + pnpm (或 npm)
- [Ollama](https://ollama.com/) 已安装并运行

### 1. 启动 Ollama 并拉取模型

```bash
ollama serve
ollama pull qwen3.5:4b         # Supervisor / 主力模型
ollama pull qwen3:0.6b         # utility_agent 轻量模型
ollama pull qwen3-embedding:4b # RAG 向量嵌入模型
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 填写必要配置
```

### 3. 启动后端

```bash
# 使用 uv (推荐)
uv sync
uv run python main.py

# 或使用 pip
cd backend && pip install -r requirements.txt && python app.py
```

后端运行在 `http://localhost:5000`
- Swagger 文档: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc

### 4. 启动前端

```bash
cd frontend
pnpm install   # 或 npm install
pnpm dev       # 或 npm run dev
```

前端默认运行在 `http://localhost:3000`，通过 Vite 代理连接后端。

## Agent 团队

| Agent | 模型 | 职责 | 工具/能力 |
|-------|------|------|-----------|
| **Supervisor** | qwen3.5:4b | 任务规划、路由调度、结果合成 | LLM Planning + JSON 解析 |
| **utility_agent** | qwen3:0.6b | 天气查询、时间查询 | Open-Meteo API + wttr.in 回退 |
| **comm_agent** | qwen3.5:4b | 邮件发送、钉钉消息 | SMTP + 钉钉 Webhook |
| **finance_agent** | qwen3.5:4b | A 股股票查询 | 新浪财经 API |
| **knowledge_agent** | qwen3.5:4b | 课程问答 (RAG) | ChromaDB + BM25 混合检索 + BGE Reranker |
| **resume_agent** | qwen3.5:4b | 简历解析、技能匹配、候选人评估 | LLM 解析 + 匹配分析 |
| **chat_agent** | qwen3.5:4b | 纯对话闲聊 | 对话 LLM |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送对话请求 (Supervisor 路由 → Agent 执行) |
| `/api/history/{session_id}` | GET | 获取会话历史 |
| `/api/history/{session_id}` | DELETE | 清除会话历史 |
| `/api/clear` | POST | 清空当前会话 |
| `/api/health` | GET | 健康检查 (含 Ollama 连接状态) |
| `/api/models` | GET | 获取可用模型列表 |

### Chat API 示例

**请求**

```json
POST /api/chat
{
  "message": "北京今天天气怎么样？顺便帮我查一下600519的股价",
  "session_id": "user123",
  "model": "qwen3.5:4b"
}
```

**响应**

```json
{
  "response": "北京今天多云，温度22°C，体感20°C... 贵州茅台(600519)当前价格1688.00元，涨幅2.35%...",
  "success": true
}
```

## 环境变量

### 后端 (`backend/.env`)

```env
# Ollama 连接
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=qwen3.5:4b

# 服务配置
PORT=5000
CORS_ORIGINS=http://localhost:3000

# Agent 模型 (按需覆盖默认值)
SUPERVISOR_AGENT_MODEL=qwen3.5:4b
CHAT_AGENT_MODEL=qwen3.5:4b
RESUME_AGENT_MODEL=qwen3.5:4b

# 邮件 (comm_agent)
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
FROM_EMAIL=your_email@example.com
SMTP_PASSWORD=your_password

# 钉钉 (comm_agent)
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# RAG (knowledge_agent)
CHROMA_DIR=backend/chroma_db
COURSE_DOC_PATH=../docs/《智能应用系统设计》课程介绍.md
RAG_EMBEDDING_MODEL=qwen3-embedding:4b
RAG_LLM_MODEL=qwen3.5:4b
```

## 功能特性

- ✅ Supervisor + Team 多智能体协作架构
- ✅ 两阶段工作流：任务规划 → 循环调度 → 结果合成
- ✅ 天气查询（Open-Meteo 地理编码 + wttr.in 回退，支持中文城市名）
- ✅ 时间查询（多时区支持）
- ✅ A 股实时股价查询
- ✅ 邮件发送（SMTP SSL/TLS）
- ✅ 钉钉群机器人消息推送
- ✅ RAG 课程问答（ChromaDB + BM25 混合检索 + BGE Reranker）
- ✅ 简历解析与候选人评估管道
- ✅ Web Speech API 语音输入（多语言）
- ✅ TTS 语音回答 + 口型动画
- ✅ 多模型动态切换
- ✅ 会话隔离与历史管理
- ✅ 赛博朋克风格 UI
- ✅ Swagger 自动 API 文档

## 开发

```bash
# 语法检查
python -m py_compile backend/app.py backend/supervisor_agent.py backend/tools.py

# 运行测试
python backend/test/test_routing.py
python backend/test/test_weather_tool.py
```

## 注意事项

1. 首次启动需确保 Ollama 服务正常运行且已拉取所需模型
2. 首次对话可能需要加载模型，等待时间较长（特别是 RAG 向量嵌入首次初始化）
3. 前端通过 Vite 代理连接后端，无需额外配置跨域
4. 邮件、钉钉功能需要配置对应的环境变量
5. 语音功能依赖浏览器 Web Speech API（推荐 Chrome/Edge）
6. RAG 系统首次初始化会下载 BGE Reranker 模型，耗时较长
