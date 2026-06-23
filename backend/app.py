"""
AI 数字人 — Supervisor + Team 多智能体系统 v3.0 (LOOP)
======================================================
架构: Supervisor (8B LLM) 路由 → 6 个专业 Agent 团队 (循环调度)

核心改进: Supervisor 可规划多步任务，Agent 执行完后回到 Supervisor
继续判断下一步，直到 Supervisor 输出 FINISH 为止。

Agent 团队:
  utility_agent   (qwen3:0.6b) — 天气 + 时间
  comm_agent      (qwen3.5:4b)   — 邮件 + 钉钉
  finance_agent   (qwen3.5:4b)   — 股票查询
  knowledge_agent (qwen3.5:4b)   — RAG 课程问答
  resume_agent    (qwen3.5:4b)   — 简历筛选评估管道
  chat_agent      (qwen3.5:4b)   — 纯对话

运行: cd backend && python app.py
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from agents.chat_agent import chat_agent_node
from agents.comm_agent import comm_agent_node
from agents.finance_agent import finance_agent_node
from agents.knowledge_agent import knowledge_agent_node
from agents.resume_agent import resume_agent_node
from agents.utility_agent import utility_agent_node
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from state import TeamState
from supervisor_agent import supervisor_node

# ========================================
# 日志
# ========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# 环境配置
# ========================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "llama3.2")
PORT = int(os.environ.get("PORT", 5000))

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:3000"]
ALLOW_CREDENTIALS = "*" not in ALLOWED_ORIGINS

# ========================================
# 会话历史存储
# ========================================
session_history_store: dict = {}


# ========================================
# FastAPI 应用
# ========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Supervisor + Team 多智能体系统 v3.0.0")
    logger.info(f"  Ollama: {OLLAMA_HOST}")
    logger.info("  Agents: supervisor→[utility|comm|finance|knowledge|resume|chat]")
    logger.info("=" * 60)
    yield
    logger.info("系统关闭")


app = FastAPI(
    title="AI数字人 — Supervisor+Team 多智能体",
    description="基于LangGraph + Ollama的Supervisor路由 + 专业Agent团队架构 (LOOP: supervisor→agent→supervisor→...→FINISH)",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# Pydantic 模型
# ========================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "北京今天天气怎么样？",
                "session_id": "user123",
                "model": "llama3.2",
            }
        }


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    history: List[HistoryMessage]


class HealthResponse(BaseModel):
    status: str
    ollama: str
    model: str
    ollama_host: str


class ModelsResponse(BaseModel):
    models: List[str]


class ClearRequest(BaseModel):
    session_id: str = "default"


class ClearResponse(BaseModel):
    message: str
    session_id: str


# ========================================
# 会话管理
# ========================================
def get_session_history(session_id: str) -> list:
    if session_id not in session_history_store:
        session_history_store[session_id] = []
    return session_history_store[session_id]


# ========================================
# Supervisor + Team 状态图构建
# ========================================


def build_team_graph():
    """构建 Supervisor + 6 Agent 团队协作图。"""

    workflow = StateGraph(TeamState)

    # --- 添加所有节点 ---
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("utility_agent", utility_agent_node)
    workflow.add_node("comm_agent", comm_agent_node)
    workflow.add_node("finance_agent", finance_agent_node)
    workflow.add_node("knowledge_agent", knowledge_agent_node)
    workflow.add_node("resume_agent", resume_agent_node)
    workflow.add_node("chat_agent", chat_agent_node)

    workflow.set_entry_point("supervisor")

    # --- Supervisor 路由到对应 Agent（条件边）---
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "chat"),
        {
            "utility": "utility_agent",
            "comm": "comm_agent",
            "finance": "finance_agent",
            "knowledge": "knowledge_agent",
            "resume": "resume_agent",
            "chat": "chat_agent",
            "FINISH": END,  # 大写 FINISH → 结束
        },
    )

    # --- 所有 Agent 执行完毕 → 回到 Supervisor (LOOP!) ---
    agent_names = [
        "utility_agent",
        "comm_agent",
        "finance_agent",
        "knowledge_agent",
        "resume_agent",
        "chat_agent",
    ]
    for name in agent_names:
        workflow.add_edge(name, "supervisor")  # LOOP: agent → supervisor

    return workflow.compile()


# 全局编译好的图
team_graph = build_team_graph()


# ========================================
# API 端点
# ========================================


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求 — Supervisor 路由 → Agent 执行 → 返回结果。"""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        logger.info("📩 收到消息: %s", request.message[:60])

        # 获取历史 + 构建初始状态（支持多轮循环）
        history = get_session_history(request.session_id)
        initial_state: TeamState = {
            "messages": history + [HumanMessage(content=request.message)],
            "session_id": request.session_id,
            "model": request.model,
            "next": "chat",  # 默认值，supervisor 会覆盖
            "pending_tasks": [],
            "completed_tasks": [],
            "iteration_count": 0,
        }

        # 运行 Supervisor + Team 图
        result = team_graph.invoke(initial_state)

        # 提取最后一条 AI 回复
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if not ai_messages:
            response_text = "抱歉，没有生成回复。"
        else:
            response_text = ai_messages[-1].content

        # 持久化会话历史
        session_history_store[request.session_id] = result["messages"]

        logger.info("✅ 回复: %s", response_text[:60])
        return ChatResponse(response=response_text, success=True)

    except Exception as e:
        logger.error("聊天处理错误: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/clear", response_model=ClearResponse)
async def clear_conversation(request: ClearRequest = None):
    session_id = request.session_id if request else "default"
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return ClearResponse(message="对话已清空", session_id=session_id)


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    history = get_session_history(session_id)
    messages = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            messages.append(HistoryMessage(role="user", content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(HistoryMessage(role="assistant", content=msg.content))
    return HistoryResponse(session_id=session_id, history=messages)


@app.delete("/api/history/{session_id}", response_model=ClearResponse)
async def clear_history(session_id: str):
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return ClearResponse(message=f"会话 {session_id} 已清除", session_id=session_id)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    ollama_status = "disconnected"
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        if r.status_code == 200:
            ollama_status = "connected"
    except Exception:
        pass

    return HealthResponse(
        status="ok" if ollama_status == "connected" else "degraded",
        ollama=ollama_status,
        model=DEFAULT_MODEL,
        ollama_host=OLLAMA_HOST,
    )


@app.get("/api/models", response_model=ModelsResponse)
async def get_models():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return ModelsResponse(models=models)
        raise HTTPException(status_code=500, detail="获取模型列表失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@app.get("/")
async def root():
    return {
        "name": "AI数字人 — Supervisor+Team 多智能体",
        "version": "3.0.0",
        "agents": [
            "supervisor",
            "utility",
            "comm",
            "finance",
            "knowledge",
            "resume",
            "chat",
        ],
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ========================================
# 主入口
# ========================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
