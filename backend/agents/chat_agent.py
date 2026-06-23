import logging
import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from state import TeamState

logger = logging.getLogger(__name__)


def chat_agent_node(state: TeamState) -> dict:
    """Pure conversation agent. Reads conversation history from shared state."""
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    agent_model = os.environ.get("CHAT_AGENT_MODEL", "qwen3.5:4b")

    try:
        llm = ChatOllama(model=agent_model, base_url=ollama_host, temperature=0.7)
    except Exception as e:
        return {"messages": [AIMessage(content=f"对话模型启动失败：{e}")]}

    # Use recent conversation history (last 20 messages)
    recent = state.get("messages", [])[-20:]
    if not any(isinstance(m, HumanMessage) for m in recent):
        return {"messages": [AIMessage(content="你好！有什么我可以帮你的？")]}

    system = SystemMessage(
        content="""你是一个智能助手，名叫"小智"。你可以：聊天对话、查询天气和时间、查询股票行情、发送邮件和钉钉消息、回答《智能应用系统设计》课程问题、筛选和评估简历。请用中文回复，保持友好、简洁。"""
    )

    try:
        response = llm.invoke([system] + recent)
        content = response.content if hasattr(response, "content") else str(response)
        return {"messages": [AIMessage(content=content)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"对话生成失败：{e}")]}
