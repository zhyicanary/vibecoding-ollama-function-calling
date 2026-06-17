from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
import requests
from typing import Optional, List, TypedDict, Literal, Any, Dict
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from routing import route_request

from tools import (
    get_current_time as _get_current_time,
    get_weather as _get_weather,
    get_stock_price_cn as _get_stock_price_cn,
    send_email as _send_email,
    send_dingtalk as _send_dingtalk,
    query_course
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# FastAPI 应用初始化
# ========================================
app = FastAPI(
    title="AI数字人对话应用",
    description="基于Ollama本地大模型的AI数字人对话应用",
    version="2.0.0"
)

# ========================================
# 配置参数
# ========================================
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')
LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.7'))

CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(',') if origin.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:3000"]
ALLOW_CREDENTIALS = "*" not in ALLOWED_ORIGINS

SMTP_CONFIG = {
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.qq.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
    'from_email': os.environ.get('FROM_EMAIL', ''),
    'from_password': os.environ.get('SMTP_PASSWORD', '')
}

DINGTALK_CONFIG = {
    'webhook_url': os.environ.get('DINGTALK_WEBHOOK_URL', '')
}

session_history_store = {}

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# Pydantic 模型定义
# ========================================
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: str = "default"
    model: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "北京今天天气怎么样？",
                "session_id": "user123",
                "model": "llama3.2"
            }
        }


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    success: bool
    error: Optional[str] = None


class HistoryMessage(BaseModel):
    """历史消息模型"""
    role: str  # "user" 或 "assistant"
    content: str


class HistoryResponse(BaseModel):
    """历史记录响应模型"""
    session_id: str
    history: List[HistoryMessage]


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    ollama: str
    model: str
    ollama_host: str


class ModelsResponse(BaseModel):
    """模型列表响应模型"""
    models: List[str]


class ClearRequest(BaseModel):
    """清空请求模型"""
    session_id: str = "default"


class ClearResponse(BaseModel):
    """清空响应模型"""
    message: str
    session_id: str


# ========================================
# 会话管理函数
# ========================================
def get_session_history(session_id: str):
    """获取指定会话ID的历史记录"""
    if session_id not in session_history_store:
        session_history_store[session_id] = []
    return session_history_store[session_id]


# ========================================
# LangChain 工具定义
# ========================================
@tool
def get_time(timezone: str = "Asia/Shanghai", format: str = "full") -> str:
    """
    获取当前时间信息，支持查询指定时区的当前日期和时间。

    参数:
        timezone: 时区名称，支持 'Asia/Shanghai', 'America/New_York', 'UTC' 等，默认为 'Asia/Shanghai'
        format: 返回格式，可选 'full'(完整日期时间), 'date'(仅日期), 'time'(仅时间)，默认为 'full'

    返回:
        格式化的日期时间字符串
    """
    return _get_current_time(timezone=timezone, format=format)


@tool
def get_weather(city: str) -> str:
    """
    获取指定城市的天气信息，支持全球城市查询。

    参数:
        city: 城市名称，支持中英文，如 '上海', '北京', 'Tokyo', 'New York' 等

    返回:
        格式化的天气信息字符串，包含温度、体感温度、天气状况、湿度和风速
    """
    if not city:
        return "错误: 请提供城市名称"
    return _get_weather(city=city)


@tool
def get_stock_price(ticker: str) -> str:
    """
    获取A股股票价格信息，支持查询A股实时行情。

    参数:
        ticker: 6位股票代码，如 '600519' (贵州茅台), '000001' (平安银行), '000858' (五粮液)

    返回:
        JSON格式的股价信息，包含股票名称、当前价格、涨跌幅、开盘价、昨收价、最高价、最低价
    """
    if not ticker:
        return json.dumps({"status": "error", "message": "请提供股票代码"})
    json_result = _get_stock_price_cn(ticker=ticker)
    try:
        data = json.loads(json_result)
        if data.get('status') == 'success':
            return json.dumps({
                "status": "success",
                "股票名称": data['name'],
                "股票代码": data['ticker'],
                "当前价格": f"{data['current_price']}元",
                "涨跌幅": f"{data['change_percent']}%",
                "开盘价": f"{data['open']}元",
                "昨收价": f"{data['last_close']}元",
                "最高价": f"{data['high']}元",
                "最低价": f"{data['low']}元"
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"status": "error", "message": data.get('message', '查询失败')}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"解析股票数据失败: {e}")
        return json.dumps({"status": "error", "message": f"查询失败: {str(e)}"}, ensure_ascii=False)


@tool
def send_email_tool(to_email: str, subject: str, content: str) -> str:
    """
    通过SMTP协议发送邮件，可用于向指定收件人发送邮件。

    参数:
        to_email: 收件人邮箱地址，格式需正确，如 'example@example.com'
        subject: 邮件主题，不能为空
        content: 邮件正文内容，支持纯文本

    返回:
        JSON格式的发送结果，包含发送状态、消息、收件人、主题和发送时间
    """
    if not to_email or not subject or not content:
        return json.dumps({"status": "error", "message": "请提供收件人邮箱、主题和内容"}, ensure_ascii=False)
    return _send_email(
        to_email=to_email,
        subject=subject,
        content=content,
        from_email=SMTP_CONFIG['from_email'],
        from_password=SMTP_CONFIG['from_password'],
        smtp_server=SMTP_CONFIG['smtp_server'],
        smtp_port=SMTP_CONFIG['smtp_port']
    )


@tool
def send_dingtalk(message: str) -> str:
    """
    发送钉钉群消息，可以将消息实时推送到钉钉群。

    参数:
        message: 要发送的消息内容，支持任意文本

    返回:
        JSON格式的发送结果，包含发送状态、消息内容、发送时间和可能的错误信息
    """
    if not message:
        return json.dumps({"status": "error", "message": "消息内容不能为空"}, ensure_ascii=False)
    return _send_dingtalk(
        message=message,
        webhook_url=DINGTALK_CONFIG['webhook_url']
    )


@tool
def query_course_info(question: str) -> str:
    """
    查询《智能应用系统设计》课程相关信息，包括课程介绍、教学大纲、考核方式等。

    参数:
        question: 关于课程的问题，例如"课程考核方式是什么？"、"这门课学什么？"等

    返回:
        课程相关的问答结果，如果无法从资料中找到答案会返回相应提示
    """
    if not question:
        return "请提供问题内容"
    return query_course(question)


# ========================================
# LangChain 配置
# ========================================
TOOLS = [get_time, get_weather, get_stock_price, send_email_tool, send_dingtalk, query_course_info]
tool_map = {tool.name: tool for tool in TOOLS}

_llm_cache: Dict[str, ChatOllama] = {}


def get_llm(model_name: Optional[str]) -> ChatOllama:
    selected_model = model_name or DEFAULT_MODEL
    cached = _llm_cache.get(selected_model)
    if cached is None:
        cached = ChatOllama(
            model=selected_model,
            base_url=OLLAMA_HOST,
            temperature=LLM_TEMPERATURE
        )
        _llm_cache[selected_model] = cached
    return cached

system_message = SystemMessage(content="""你是一个智能助手，可以帮助用户查询时间、天气、股票信息，发送邮件和钉钉消息，还可以回答《智能应用系统设计》课程相关问题。

当用户请求执行工具操作时，请调用相应的工具。工具返回的结果会直接展示给用户。

回答问题时请简洁明了，对于工具返回的信息，适当整理后告知用户。""")


class ChatState(TypedDict, total=False):
    input: str
    session_id: str
    model: Optional[str]
    route: Literal["tool", "chat"]
    tool_name: str
    tool_args: Dict[str, Any]
    response: str


def run_selected_tool(state: ChatState) -> ChatState:
    tool_name = state.get("tool_name")
    tool_args = state.get("tool_args", {})

    if not tool_name or tool_name not in tool_map:
        return {"response": "抱歉，当前没有可用的工具。"}

    try:
        result = tool_map[tool_name].invoke(tool_args)
        return {"response": str(result)}
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        return {"response": f"工具执行失败: {str(e)}"}


def chat_with_llm(state: ChatState) -> ChatState:
    session_id = state.get("session_id", "default")
    model_name = state.get("model")
    history = get_session_history(session_id)
    messages = [system_message] + history + [HumanMessage(content=state["input"])]
    response = get_llm(model_name).invoke(messages)
    return {"response": response.content if hasattr(response, "content") else str(response)}


def build_graph():
    workflow = StateGraph(ChatState)

    workflow.add_node("router", lambda state: route_request(state["input"]))
    workflow.add_node("tool", run_selected_tool)
    workflow.add_node("chat", chat_with_llm)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        lambda state: state.get("route", "chat"),
        {
            "tool": "tool",
            "chat": "chat",
        },
    )
    workflow.add_edge("tool", END)
    workflow.add_edge("chat", END)

    return workflow.compile()


conversation_graph = build_graph()


def invoke_with_tools(input_text: str, session_id: str, model: Optional[str]):
    """使用 LangGraph 先路由再执行，避免小模型自行决定是否调用工具。"""
    state = conversation_graph.invoke({
        "input": input_text,
        "session_id": session_id,
        "model": model
    })
    response_text = state.get("response", "")

    get_session_history(session_id).extend([
        HumanMessage(content=input_text),
        AIMessage(content=response_text),
    ])

    return AIMessage(content=response_text)


# ========================================
# API 端点
# ========================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理聊天请求
    
    Args:
        request: 聊天请求对象
        
    Returns:
        聊天响应对象
        
    Raises:
        HTTPException: 当消息为空或处理失败时
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        logger.info(
            "处理用户消息: %s, session_id: %s, model: %s",
            request.message,
            request.session_id,
            request.model or DEFAULT_MODEL
        )

        response = invoke_with_tools(request.message, request.session_id, request.model)

        if hasattr(response, 'content'):
            return ChatResponse(response=response.content, success=True)
        else:
            return ChatResponse(response=str(response), success=True)

    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")


@app.post("/api/clear", response_model=ClearResponse)
async def clear_conversation(request: ClearRequest = None):
    """
    清空对话历史
    
    Args:
        request: 清空请求对象，包含session_id
        
    Returns:
        清空确认响应
    """
    session_id = request.session_id if request else "default"
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return ClearResponse(message="对话已清空", session_id=session_id)


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """
    获取指定会话的历史记录
    
    Args:
        session_id: 会话ID
        
    Returns:
        历史记录响应
    """
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
    """
    清除指定会话的历史记录
    
    Args:
        session_id: 会话ID
        
    Returns:
        清除确认响应
    """
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return ClearResponse(message=f"会话 {session_id} 已清除", session_id=session_id)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """
    健康检查端点
    
    Returns:
        系统健康状态信息
    """
    ollama_status = "disconnected"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        if response.status_code == 200:
            ollama_status = "connected"
    except Exception as e:
        logger.warning("Ollama 健康检查失败: %s", e)

    return HealthResponse(
        status="ok" if ollama_status == "connected" else "degraded",
        ollama=ollama_status,
        model=DEFAULT_MODEL,
        ollama_host=OLLAMA_HOST
    )


@app.get("/api/models", response_model=ModelsResponse)
async def get_models():
    """
    获取Ollama可用模型列表
    
    Returns:
        可用模型列表
        
    Raises:
        HTTPException: 当获取模型失败时
    """
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get('name', '') for m in data.get('models', [])]
            return ModelsResponse(models=models)
        else:
            raise HTTPException(status_code=500, detail="获取模型列表失败")
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@app.get("/")
async def root():
    """
    根路径 - 返回API信息
    """
    return {
        "name": "AI数字人对话应用",
        "version": "2.0.0",
        "description": "基于Ollama本地大模型的AI数字人对话应用",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# ========================================
# 应用启动和关闭事件
# ========================================
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("应用启动中...")
    logger.info(f"Ollama Host: {OLLAMA_HOST}")
    logger.info(f"Default Model: {DEFAULT_MODEL}")
    logger.info("RAG 系统将在首次查询时懒加载...")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用关闭中...")


# ========================================
# 主入口
# ========================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info"
    )