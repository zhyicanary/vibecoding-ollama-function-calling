from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import json
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.tools import tool

from tools import get_current_time as _get_current_time, get_weather as _get_weather, get_stock_price_cn as _get_stock_price_cn, send_email as _send_email, send_dingtalk as _send_dingtalk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')

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


def get_session_history(session_id: str):
    """获取指定会话ID的历史记录"""
    if session_id not in session_history_store:
        session_history_store[session_id] = []
    return session_history_store[session_id]


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


TOOLS = [get_time, get_weather, get_stock_price, send_email_tool, send_dingtalk]

tool_map = {tool.name: tool for tool in TOOLS}

llm = ChatOllama(
    model=DEFAULT_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0.7
)

llm_with_tools = llm.bind_tools(TOOLS)

output_parser = JsonOutputParser()

system_message = SystemMessage(content="""你是一个智能助手，可以帮助用户查询时间、天气、股票信息，发送邮件和钉钉消息。

当用户请求执行工具操作时，请调用相应的工具。工具返回的结果会直接展示给用户。

回答问题时请简洁明了，对于工具返回的信息，适当整理后告知用户。""")


def build_chain():
    """构建LCEL Chain"""
    from langchain_core.runnables import RunnablePassthrough

    def prepare_messages(x):
        session_id = x.get("session_id", "default")
        history = get_session_history(session_id)
        messages = [system_message] + history + [HumanMessage(content=x["input"])]
        return {"messages": messages, "session_id": session_id}

    chain = (
        RunnablePassthrough.assign(messages=prepare_messages)
        | (lambda x: x["messages"])
        | llm_with_tools
    )

    return chain


chain = build_chain()

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)


def invoke_with_tools(input_text, session_id):
    """带工具执行的完整调用，使用 LCEL Chain 和 Memory"""
    messages = [system_message] + get_session_history(session_id) + [HumanMessage(content=input_text)]

    max_iterations = 5
    current_iteration = 0

    while current_iteration < max_iterations:
        current_iteration += 1
        response = llm_with_tools.invoke(messages)

        if not hasattr(response, 'tool_calls') or not response.tool_calls:
            get_session_history(session_id).extend([HumanMessage(content=input_text), response])
            return response

        for tool_call in response.tool_calls:
            tool_name = tool_call.get('name')
            tool_args = tool_call.get('args', {})

            logger.info(f"执行工具: {tool_name}, 参数: {tool_args}")

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call.get('id')))
                except Exception as e:
                    logger.error(f"工具执行失败: {e}")
                    messages.append(ToolMessage(content=f"工具执行失败: {str(e)}", tool_call_id=tool_call.get('id')))
            else:
                messages.append(ToolMessage(content=f"未知工具: {tool_name}", tool_call_id=tool_call.get('id')))

        get_session_history(session_id).extend([HumanMessage(content=input_text), response])

    return response


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求"""
    data = request.get_json()
    user_input = data.get('message', '')
    session_id = data.get('session_id', 'default')

    if not user_input:
        return jsonify({"error": "消息不能为空"}), 400

    try:
        logger.info(f"处理用户消息: {user_input}, session_id: {session_id}")

        response = invoke_with_tools(user_input, session_id)

        if hasattr(response, 'content'):
            return jsonify({"response": response.content, "success": True})
        else:
            return jsonify({"response": str(response), "success": True})

    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        return jsonify({"error": f"处理消息失败: {str(e)}", "success": False}), 500


@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """清空对话历史"""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', 'default')
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return jsonify({"message": "对话已清空", "session_id": session_id})


@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """获取指定会话的历史记录"""
    history = get_session_history(session_id)
    messages = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    return jsonify({"session_id": session_id, "history": messages})


@app.route('/api/history/<session_id>', methods=['DELETE'])
def clear_history(session_id):
    """清除指定会话的历史记录"""
    if session_id in session_history_store:
        session_history_store[session_id] = []
    return jsonify({"message": f"会话 {session_id} 已清除"})


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "ollama": "connected",
        "model": DEFAULT_MODEL,
        "ollama_host": OLLAMA_HOST
    })


@app.route('/api/models', methods=['GET'])
def get_models():
    """获取Ollama可用模型列表"""
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get('name', '') for m in data.get('models', [])]
            return jsonify({"models": models})
        else:
            return jsonify({"error": "Failed to fetch models", "models": []}), 500
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return jsonify({"error": str(e), "models": []}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)