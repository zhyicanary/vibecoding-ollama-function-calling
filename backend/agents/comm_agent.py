import json
import logging
import os
from langchain_core.messages import AIMessage
from state import TeamState
from tools import send_email, send_dingtalk

logger = logging.getLogger(__name__)

SMTP_CONFIG = {
    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.qq.com"),
    "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
    "from_email": os.environ.get("FROM_EMAIL", ""),
    "from_password": os.environ.get("SMTP_PASSWORD", ""),
}

DINGTALK_CONFIG = {"webhook_url": os.environ.get("DINGTALK_WEBHOOK_URL", "")}


def comm_agent_node(state: TeamState) -> dict:
    pending = state.get("pending_tasks", [])
    if not pending:
        return {"messages": [AIMessage(content="没有待执行的通讯任务。")]}

    task = pending[0]
    task_type = task.get("task_type", "unknown")

    try:
        if task_type == "email":
            to_email = task.get("to_email", "")
            subject = task.get("subject", "")
            content = task.get("content", "")
            if not to_email or not subject:
                return {"messages": [AIMessage(content="邮件任务缺少收件人或主题。")]}
            result = send_email(
                to_email=to_email, subject=subject, content=content,
                from_email=SMTP_CONFIG["from_email"],
                from_password=SMTP_CONFIG["from_password"],
                smtp_server=SMTP_CONFIG["smtp_server"],
                smtp_port=SMTP_CONFIG["smtp_port"],
            )
        elif task_type == "dingtalk":
            message = task.get("message", "")
            if not message:
                return {"messages": [AIMessage(content="钉钉任务缺少消息内容。")]}
            result = send_dingtalk(message=message, webhook_url=DINGTALK_CONFIG["webhook_url"])
        else:
            result = json.dumps({"status": "error", "message": f"未知任务类型: {task_type}"}, ensure_ascii=False)

        # Parse result for display
        try:
            data = json.loads(result) if isinstance(result, str) else result
            status = data.get("status", "unknown")
            if status == "success":
                display = f"✅ {data.get('message', '成功')}"
            else:
                display = f"❌ {data.get('message', '失败')}"
        except Exception:
            display = str(result)

        logger.info("CommAgent: executed %s", task_type)
        return {"messages": [AIMessage(content=display)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"通讯任务失败：{e}")]}
