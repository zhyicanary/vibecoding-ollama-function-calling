import logging
from langchain_core.messages import AIMessage
from state import TeamState
from tools import get_weather, get_current_time

logger = logging.getLogger(__name__)


def utility_agent_node(state: TeamState) -> dict:
    """
    Task-driven utility agent.
    Reads the first pending task from state['pending_tasks'], executes the
    appropriate tool, and returns the result. No LLM — the Supervisor already
    planned everything and filled the task params.
    """
    pending = state.get("pending_tasks", [])
    if not pending:
        return {"messages": [AIMessage(content="没有待执行的工具任务。")]}

    task = pending[0]
    task_type = task.get("task_type", "unknown")

    if task_type == "weather":
        city = task.get("city", "")
        if not city:
            return {"messages": [AIMessage(content="请告诉我你想查询哪个城市的天气。")]}
        result = get_weather(city=city)
    elif task_type == "time":
        fmt = task.get("format", "full")
        result = get_current_time(timezone="Asia/Shanghai", format=fmt)
    else:
        result = f"未知任务类型: {task_type}"

    logger.info("UtilityAgent: executed %s → %s", task_type, str(result)[:50])
    return {"messages": [AIMessage(content=result)]}
