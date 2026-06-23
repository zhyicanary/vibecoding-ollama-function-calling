import logging
from langchain_core.messages import AIMessage
from state import TeamState
from tools import query_course, init_rag

logger = logging.getLogger(__name__)


def knowledge_agent_node(state: TeamState) -> dict:
    pending = state.get("pending_tasks", [])
    if not pending:
        return {"messages": [AIMessage(content="没有待执行的课程问答任务。")]}
    
    task = pending[0]
    task_type = task.get("task_type", "unknown")
    
    if task_type != "course_qa":
        return {"messages": [AIMessage(content=f"未知任务类型: {task_type}")]}
    
    question = task.get("question", "")
    if not question:
        return {"messages": [AIMessage(content="请提供课程相关问题。")]}
    
    try:
        init_rag()  # idempotent
        answer = query_course(question=question)
        logger.info("KnowledgeAgent: answered question")
        return {"messages": [AIMessage(content=answer)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"课程查询失败：{e}")]}
