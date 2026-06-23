import json
import logging
import os
from langchain_core.messages import AIMessage
from state import TeamState
from tools import get_stock_price_cn

logger = logging.getLogger(__name__)


def finance_agent_node(state: TeamState) -> dict:
    pending = state.get("pending_tasks", [])
    if not pending:
        return {"messages": [AIMessage(content="没有待执行的股票任务。")]}

    task = pending[0]
    task_type = task.get("task_type", "unknown")

    if task_type != "stock":
        return {"messages": [AIMessage(content=f"未知任务类型: {task_type}")]}

    ticker = task.get("ticker", "")
    if not ticker:
        return {"messages": [AIMessage(content="请提供6位股票代码。")]}

    try:
        result = get_stock_price_cn(ticker=ticker)
        data = json.loads(result)
        if data.get("status") == "success":
            display = (
                f"📊 {data['name']} ({data['ticker']})\n"
                f"当前价格：{data['current_price']}元\n"
                f"涨跌幅：{data['change_percent']}%\n"
                f"开盘：{data['open']} | 昨收：{data['last_close']}\n"
                f"最高：{data['high']} | 最低：{data['low']}"
            )
        else:
            display = f"查询失败：{data.get('message', '未知错误')}"

        logger.info("FinanceAgent: ticker=%s", ticker)
        return {"messages": [AIMessage(content=display)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"股票查询失败：{e}")]}
