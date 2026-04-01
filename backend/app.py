from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import json
import os
from datetime import datetime
import pytz

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
    }
]

def get_current_time(timezone='Asia/Shanghai', format='full'):
    """获取当前时间"""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        if format == 'date':
            return now.strftime('%Y年%m月%d日')
        elif format == 'time':
            return now.strftime('%H:%M:%S')
        else:
            return now.strftime('%Y年%m月%d日 %H:%M:%S %Z')
    except Exception as e:
        return f"获取时间失败: {str(e)}"

def get_weather(city):
    """获取城市天气"""
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('current_condition', [{}])[0]
            
            weather_desc = current.get('weatherDesc', [{}])[0].get('value', '未知')
            temp_C = current.get('temp_C', 'N/A')
            humidity = current.get('humidity', 'N/A')
            wind_kmh = current.get('windspeedKmh', 'N/A')
            feelslike = current.get('FeelsLikeC', 'N/A')
            
            return f"{city}天气:\n- 温度: {temp_C}°C (体感 {feelslike}°C)\n- 天气: {weather_desc}\n- 湿度: {humidity}%\n- 风速: {wind_kmh} km/h"
        else:
            return f"无法获取{city}的天气信息"
    except Exception as e:
        return f"获取天气失败: {str(e)}"

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
    keywords = ['时间', '几点', '日期', '几号', '现在', '今天', 'timezone', '时区', '天气', '晴', '雨', '雪', '温度', '气候']
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
                'content': '你是一个友好的AI数字人助手。当用户询问时间相关问题时，使用get_current_time工具来获取准确的时间信息。当用户询问天气相关问题时，使用get_weather工具来获取准确的天气信息。'
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