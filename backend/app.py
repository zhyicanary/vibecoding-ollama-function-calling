from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import json
import os
from dotenv import load_dotenv
load_dotenv()

from tools import get_current_time, get_weather, get_stock_price_cn, send_email as _send_email

SMTP_CONFIG = {
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.qq.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
    'from_email': os.environ.get('FROM_EMAIL', ''),
    'from_password': os.environ.get('SMTP_PASSWORD', '')
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')

conversation_history = []

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间信息，可以查询当前日期和时间，支持指定时区。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区名称，如 'Asia/Shanghai', 'America/New_York', 'UTC' 等，默认为 'Asia/Shanghai'"
                    },
                    "format": {
                        "type": "string",
                        "description": "返回格式，可选 'full'(完整), 'date'(仅日期), 'time'(仅时间)，默认为 'full'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息，支持全球城市查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '上海', '北京', 'Tokyo', 'New York' 等"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price_cn",
            "description": "获取A股股票价格信息，支持查询A股实时行情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "6位股票代码，如 '600519' (贵州茅台), '000001' (平安银行)"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "通过SMTP协议发送邮件，可用于发送邮件给指定收件人。",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "收件人邮箱地址，如 'example@example.com'"
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题"
                    },
                    "content": {
                        "type": "string",
                        "description": "邮件正文内容"
                    }
                },
                "required": ["to_email", "subject", "content"]
            }
        }
    }
]


def execute_tool(tool_call):
    """执行工具调用"""
    func_data = tool_call.get('function', {})
    func_name = func_data.get('name', '')
    func_args = func_data.get('arguments', '{}')
    
    if isinstance(func_args, dict):
        args_dict = func_args
    else:
        args_dict = json.loads(func_args) if isinstance(func_args, str) else {}
    
    logger.info(f"Executing tool: {func_name} with args: {args_dict}")
    
    if func_name == 'get_current_time':
        result = get_current_time(
            timezone=args_dict.get('timezone', 'Asia/Shanghai'),
            format=args_dict.get('format', 'full')
        )
    elif func_name == 'get_weather':
        result = get_weather(city=args_dict.get('city', ''))
    elif func_name == 'get_stock_price_cn':
        ticker = args_dict.get('ticker', '')
        if not ticker:
            result = "错误: 请提供股票代码"
        else:
            json_result = get_stock_price_cn(ticker=ticker)
            try:
                data = json.loads(json_result)
                if data.get('status') == 'success':
                    result = (
                        f"股票: {data['name']} ({data['ticker']})\n"
                        f"当前价: {data['current_price']}元\n"
                        f"涨跌幅: {data['change_percent']}%\n"
                        f"开盘: {data['open']} | 昨收: {data['last_close']}\n"
                        f"最高: {data['high']} | 最低: {data['low']}"
                    )
                else:
                    result = f"查询失败: {data.get('message')}"
            except Exception as e:
                logger.error(f"解析股票数据失败: {e}")
                result = f"查询失败: {str(e)}"
    elif func_name == 'send_email':
        result = _send_email(
            to_email=args_dict.get('to_email', ''),
            subject=args_dict.get('subject', ''),
            content=args_dict.get('content', ''),
            from_email=SMTP_CONFIG['from_email'],
            from_password=SMTP_CONFIG['from_password'],
            smtp_server=SMTP_CONFIG['smtp_server'],
            smtp_port=SMTP_CONFIG['smtp_port']
        )
    else:
        result = f"Unknown tool: {func_name}"
    
    return {
        "name": func_name,
        "content": result
    }

def format_response(response_text):
    """格式化模型响应"""
    return response_text.strip()

def should_use_tools(message):
    """判断消息是否需要使用工具"""
    keywords = ['时间', '几点', '日期', '几号', '现在', '今天', 'timezone', '时区', '天气', '晴', '雨', '雪', '温度', '气候', '股票', '股价', '行情', '上证', '深证', '邮件', '发邮件', 'email', '发送邮件']
    return any(kw in message for kw in keywords)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '')
        model = request.json.get('model', DEFAULT_MODEL)
        use_tools = request.json.get('use_tools', should_use_tools(user_message))
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        conversation_history.append({
            'role': 'user',
            'content': user_message,
            'model': model
        })
        
        messages = [
            {
                'role': 'system',
                'content': '''你是一个友好的AI数字人助手。请根据用户问题选择合适的工具进行回答。

## 可用工具

### 1. get_current_time
- **功能**: 获取当前时间信息
- **参数**:
  - `timezone` (string, optional): 时区名称，如 'Asia/Shanghai', 'America/New_York', 'UTC'，默认 'Asia/Shanghai'
  - `format` (string, optional): 返回格式，可选 'full'(完整), 'date'(仅日期), 'time'(仅时间)，默认 'full'

### 2. get_weather
- **功能**: 获取指定城市的天气信息
- **参数**:
  - `city` (string, required): 城市名称，如 '上海', '北京', 'Tokyo', 'New York'

### 3. get_stock_price_cn
- **功能**: 获取A股股票价格信息
- **参数**:
  - `ticker` (string, required): 6位股票代码，如 '600519' (贵州茅台), '000001' (平安银行)

### 4. send_email
- **功能**: 通过SMTP协议发送邮件
- **参数**:
  - `to_email` (string, required): 收件人邮箱地址
  - `subject` (string, required): 邮件主题
  - `content` (string, required): 邮件正文内容

## 使用规则
- 用户询问时间 → 使用 get_current_time
- 用户询问天气 → 使用 get_weather
- 用户询问股票价格/行情 → 使用 get_stock_price_cn
- 用户要求发送邮件 → 使用 send_email'''
            }
        ] + conversation_history[-10:]
        
        logger.info(f"Sending request to Ollama with model: {model}")
        
        request_data = {
            'model': model,
            'messages': messages,
            'stream': False
        }
        
        if use_tools:
            request_data['tools'] = TOOLS
        
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=request_data,
            timeout=120
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to get response from model'}), 502
        
        result = response.json()
        
        tool_calls = result.get('message', {}).get('tool_calls', [])
        
        if tool_calls:
            logger.info(f"Tool calls detected: {len(tool_calls)}")
            
            tool_results = []
            for tool_call in tool_calls:
                tool_result = execute_tool(tool_call)
                tool_results.append(tool_result)
            
            messages.append({
                'role': 'assistant',
                'content': result.get('message', {}).get('content', ''),
                'tool_calls': tool_calls
            })
            
            for tool_result in tool_results:
                messages.append({
                    'role': 'tool',
                    'content': tool_result['content'],
                    'name': tool_result['name']
                })
            
            second_response = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    'model': model,
                    'messages': messages[-15:],
                    'stream': False
                },
                timeout=120
            )
            
            if second_response.status_code == 200:
                second_result = second_response.json()
                ai_response = format_response(second_result.get('message', {}).get('content', ''))
            else:
                tool_result_text = '\n'.join([f"{t['name']}: {t['content']}" for t in tool_results])
                ai_response = f"工具调用结果:\n{tool_result_text}"
        else:
            ai_response = format_response(result.get('message', {}).get('content', ''))
        
        conversation_history.append({
            'role': 'assistant',
            'content': ai_response
        })
        
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        
        return jsonify({
            'response': ai_response,
            'success': True,
            'tool_used': bool(tool_calls),
            'tool_calls': [{'name': t['name'], 'result': t['content']} for t in tool_results] if tool_calls else []
        })
        
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama")
        return jsonify({'error': 'Cannot connect to Ollama service'}), 503
    except requests.exceptions.Timeout:
        logger.error("Ollama request timeout")
        return jsonify({'error': 'Model request timeout'}), 504
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_history():
    """清除对话历史"""
    conversation_history.clear()
    return jsonify({'success': True})

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取对话历史"""
    return jsonify({'history': conversation_history})

@app.route('/api/models', methods=['GET'])
def list_models():
    """获取可用模型列表"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return jsonify({'models': [m.get('name') for m in models]})
        return jsonify({'models': []})
    except:
        return jsonify({'models': []})

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        ollama_status = 'connected' if response.status_code == 200 else 'disconnected'
    except:
        ollama_status = 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'ollama': ollama_status,
        'conversation_length': len(conversation_history)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)