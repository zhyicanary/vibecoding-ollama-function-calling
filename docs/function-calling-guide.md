# Ollama Function Calling 完整指南

## 1. 项目概述

### 1.1 项目架构

本项目是一个基于 Ollama 大模型的 AI 数字人助手，支持 Function Calling（函数调用）功能。

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  前端React  │ → │  Flask后端  │ → │   Ollama    │
│  :3000      │    │  :5000     │    │   :11434   │
└─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │
  用户界面            API服务            大模型
                   工具执行           function calling
```

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + Vite |
| 后端 | Flask + Python |
| 大模型 | Ollama (llama3.2) |
| 工具 | get_current_time, get_weather, get_stock_price_cn, send_email |

### 1.3 项目目录结构

```
vibecoding-ollama-function-calling/
├── backend/
│   ├── app.py           # Flask API 服务（核心）
│   ├── tools.py         # 工具实现
│   ├── .env            # 环境配置
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx     # 前端主组件
│   │   └── index.css   # 样式
│   ├── vite.config.js   # Vite 配置（代理设置）
│   └── package.json
└── docs/
    └── function-calling-guide.md  # 本文档
```

---

## 2. Function Calling 工作流程

### 2.1 完整数据流程

```
1. 用户输入 "上海天气怎么样"
          ↓
2. 前端 → POST /api/chat {message: "上海天气怎么样"}
          ↓
3. Flask 后端检查关键词 → should_use_tools("上海天气怎么样") = True
          ↓
4. Flask 发送请求给 Ollama:
   {
     "model": "llama3.2",
     "messages": [
       {"role": "system", "content": "你是AI助手...## 可用工具..."},
       {"role": "user", "content": "上海天气怎么样"}
     ],
     "tools": TOOLS  ← 关键！必须传入工具定义
   }
          ↓
5. Ollama 分析用户意图，识别需要调用 get_weather，返回:
   {
     "message": {
       "role": "assistant",
       "content": "",
       "tool_calls": [
         {
           "id": "call_xxx",
           "type": "function",
           "function": {
             "name": "get_weather",
             "arguments": "{\"city\": \"上海\"}"
           }
         }
       ]
     }
   }
          ↓
6. Flask 执行工具: result = get_weather(city="上海")
   返回: "上海天气: 晴, 20°C, 湿度60%"
          ↓
7. Flask 再次发送工具结果给 Ollama:
   {
     "model": "llama3.2",
     "messages": [
       {"role": "system", "content": "..."},
       {"role": "user", "content": "上海天气怎么样"},
       {"role": "assistant", "tool_calls": [...], "content": ""},
       {"role": "tool", "name": "get_weather", "content": "上海天气: 晴..."}
     ]
   }
          ↓
8. Ollama 根据工具结果生成最终回复
          ↓
9. 前端显示: "上海天气: 晴, 20°C, 湿度60%"
```

### 2.2 关键词检测流程

```
用户消息 → should_use_tools() → 是否开启工具？
         ↓
检查消息中是否包含关键词:
['时间', '几点', '日期', '天气', '股票', '邮件', ...]

包含任一关键词 → use_tools = True → 传入 tools 参数
不包含 → use_tools = False → 不传 tools（普通对话）
```

---

## 3. 标准 Function Calling 格式

### 3.1 工具定义 (TOOLS)

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tool_name",           # 工具唯一标识
            "description": "工具用途描述",   # 帮助模型理解何时使用
            "parameters": {                # 参数 JSON Schema
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数说明"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "参数说明"
                    }
                },
                "required": ["param1"]      # 必填参数列表
            }
        }
    }
]
```

**字段说明：**

| 字段 | 说明 | 必需 |
|------|------|------|
| type | 固定值 "function" | 是 |
| function.name | 工具函数名 | 是 |
| function.description | 工具用途描述 | 是 |
| function.parameters | 参数 JSON Schema | 是 |
| parameters.properties | 参数属性定义 | 是 |
| parameters.required | 必填参数列表 | 否 |

### 3.2 发送给模型的请求

```python
response = requests.post(f"{OLLAMA_HOST}/api/chat", json={
    "model": "llama3.2",
    "messages": [
        {"role": "user", "content": "用户消息"}
    ],
    "tools": TOOLS,              # 必填！工具定义
    "stream": False
})
```

### 3.3 模型返回格式

**当需要调用工具时：**

```python
{
    "message": {
        "role": "assistant",
        "content": None,                    # 通常为空
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"city": "上海"}'  # JSON 字符串
                }
            }
        ]
    }
}
```

**当直接回答时（不需要工具）：**

```python
{
    "message": {
        "role": "assistant",
        "content": "你好！有什么可以帮助你的吗？",
        "tool_calls": None
    }
}
```

### 3.4 工具结果返回格式

```python
# 执行工具后，再次发送给模型
{
    "model": "llama3.2",
    "messages": [
        {"role": "user", "content": "上海天气"},
        {"role": "assistant", "tool_calls": [...], "content": ""},
        {"role": "tool",                               # 固定角色
         "tool_call_id": "call_abc123",               # 对应调用的ID
         "name": "get_weather",                      # 工具名
         "content": "上海天气: 晴, 20°C"}             # 工具返回结果
        }
    ]
}
```

---

## 4. 你的项目关键代码详解

### 4.1 app.py 核心函数

#### 4.1.1 TOOLS 工具定义 (app.py:30-111)

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间信息，可以查询当前日期和时间，支持指���时区。",
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
    # ... 其他工具类似
]
```

**已定义的4个工具：**

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| get_current_time | 获取当前时间 | 无 |
| get_weather | 获取城市天气 | city |
| get_stock_price_cn | A股股票价格 | ticker |
| send_email | 发送邮件 | to_email, subject, content |

#### 4.1.2 execute_tool 执行工具 (app.py:114-171)

```python
def execute_tool(tool_call):
    """执行工具调用"""
    func_data = tool_call.get('function', {})
    func_name = func_data.get('name', '')
    func_args = func_data.get('arguments', '{}')
    
    # 解析参数（支持 dict 或 JSON 字符串）
    if isinstance(func_args, dict):
        args_dict = func_args
    else:
        args_dict = json.loads(func_args) if isinstance(func_args, str) else {}
    
    logger.info(f"Executing tool: {func_name} with args: {args_dict}")
    
    # 根据工具名调用对应函数
    if func_name == 'get_current_time':
        result = get_current_time(timezone=..., format=...)
    elif func_name == 'get_weather':
        result = get_weather(city=...)
    elif func_name == 'get_stock_price_cn':
        result = get_stock_price_cn(ticker=...)
    elif func_name == 'send_email':
        result = _send_email(...)  # 传入 SMTP 配置
    else:
        result = f"Unknown tool: {func_name}"
    
    return {"name": func_name, "content": result}
```

#### 4.1.3 should_use_tools 关键词检测 (app.py:177-180)

```python
def should_use_tools(message):
    """判断消息是否需要使用工具"""
    keywords = [
        '时间', '几点', '日期', '几号', '现在', '今天',   # 时间相关
        'timezone', '时区', '天气', '晴', '雨', '雪',    # 天气相关
        '温度', '气候',                                 # 天气相关
        '股票', '股价', '行情', '上证', '深证',         # 股票相关
        '邮件', '发邮件', 'email', '发送邮件'            # 邮件相关
    ]
    return any(kw in message for kw in keywords)
```

#### 4.1.4 chat 主处理函数 (app.py:182-323)

核心流程：

```python
@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    use_tools = request.json.get('use_tools', should_use_tools(user_message))
    
    # 构建消息列表（包含系统提示）
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        ...
    ]
    
    # 构建请求
    request_data = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    
    # 只有需要工具时才传入 tools 参数
    if use_tools:
        request_data["tools"] = TOOLS
    
    # 发送给 Ollama
    response = requests.post(f"{OLLAMA_HOST}/api/chat", json=request_data)
    result = response.json()
    
    # 检查是否有工具调用
    tool_calls = result.get('message', {}).get('tool_calls', [])
    
    if tool_calls:
        # 执行所有工具调用
        tool_results = []
        for tool_call in tool_calls:
            tool_result = execute_tool(tool_call)
            tool_results.append(tool_result)
        
        # 把工具结果加入消息
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
        
        # 再次发送给 Ollama 获取最终回复
        second_response = requests.post(..., json={
            "model": model,
            "messages": messages[-15:],  # 限制上下文
            "stream": False
        })
        ...
    
    return jsonify({
        "response": ai_response,
        "success": True,
        "tool_used": bool(tool_calls),
        "tool_calls": [...]  # 返回给前端显示
    })
```

### 4.2 tools.py 工具实现

```python
def get_current_time(timezone='Asia/Shanghai', format='full'):
    """获取当前时间"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    if format == 'date':
        return now.strftime('%Y年%m月%d日')
    elif format == 'time':
        return now.strftime('%H:%M:%S')
    else:
        return now.strftime('%Y年%m月%d日 %H:%M:%S %Z')

def get_weather(city):
    """获取城市天气"""
    url = f"https://wttr.in/{city}?format=j1"
    response = requests.get(url, timeout=10)
    data = response.json()
    current = data.get('current_condition', [{}])[0]
    return f"{city}天气: {weather}, {temp_C}°C"

def get_stock_price_cn(ticker):
    """获取A股股票价格"""
    code = f"sh{ticker}" if ticker.startswith("6") else f"sz{ticker}"
    url = f"https://hq.sinajs.cn/list={code}"
    res = requests.get(url, headers={"Referer": "https://finance.sina.com/"})
    data = res.text.split('"')[1].split(',')
    return json.dumps({
        "name": data[0],
        "current_price": float(data[3]),
        "change_percent": round(...),
        "status": "success"
    })

def send_email(to_email, subject, content, from_email, from_password, smtp_server, smtp_port):
    """发送邮件"""
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = from_email
    msg['To'] = to_email
    
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(from_email, from_password)
        server.sendmail(from_email, [to_email], msg.as_string())
    
    return json.dumps({"status": "success", "message": "邮件发送成功"})
```

### 4.3 前端处理 (App.jsx:255-291)

```javascript
const sendMessage = async (e) => {
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            message: userMessage,
            model: currentModel || undefined
        })
    })
    
    const data = await res.json()
    
    if (data.success) {
        // 添加 AI 回复
        setMessages(prev => [...prev, { role: 'ai', content: data.response }])
        
        // 如果使用了工具，添加工具结果消息
        if (data.tool_used && data.tool_calls) {
            data.tool_calls.forEach(tool => {
                setMessages(prev => [...prev, { 
                    'role': 'tool', 
                    content: `[调用工具: ${tool.name}] ${tool.result}`
                }])
            })
        }
    }
}
```

---

## 5. 环境配置

### 5.1 .env 文件

```env
# SMTP 邮件配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=youremail@qq.com
SMTP_PASSWORD=your_auth_code
FROM_EMAIL=youremail@qq.com

# Ollama 配置
OLLAMA_HOST=http://127.0.0.1:11434
DEFAULT_MODEL=llama3.2

# 服务器配置
HOST=127.0.0.1
PORT=5000
```

### 5.2 Vite 代理配置

```javascript
// vite.config.js
export default defineConfig({
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://localhost:5000',
                changeOrigin: true
            }
        }
    }
})
```

---

## 6. 常见问题与调试

### 6.1 工具不调用

**症状：** 用户提到天气/股票/邮件，但模型不调用工具

**原因：** 关键词不在检测列表中

**解决方法：** 在 `should_use_tools()` 函数的关键词列表中添加相关关键词

### 6.2 端口冲突

**症状：** `EADDRINUSE` 错误

**解决方法：**

```bash
# 查看端口占用
netstat -ano | findstr ":3000"

# 终止占用进程
taskkill /PID <PID号> /F
```

### 6.3 前端无法连接后端

**症状：** 前端显示 Ollama 离线

**检查步骤：**

```bash
# 1. 检查后端是否运行
curl http://localhost:5000/api/health

# 2. 检查前端代理
curl http://localhost:3000/api/health

# 3. 检查 Ollama 是否运行
curl http://localhost:11434/api/tags
```

### 6.4 邮件发送失败

**可能原因：**

1. QQ 邮箱授权码过期
2. SMTP 端口不正确

**检查方法：** 测试发送邮件

```python
import smtplib
from email.mime.text import MIMEText

smtp_server = 'smtp.qq.com'
smtp_port = 465
from_email = 'your_email@qq.com'
password = 'your_auth_code'

msg = MIMEText('测试', 'plain', 'utf-8')
msg['Subject'] = '测试'
msg['From'] = from_email
msg['To'] = from_email

with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
    server.login(from_email, password)
    server.sendmail(from_email, [from_email], msg.as_string())
print('发送成功')
```

---

## 7. 修��记录

### 7.1 端口配置修复

- **问题**：前端代理指向 5000，但 Vite 也用 3000 端口，导致冲突
- **解决**：后端改为 5000，Vite 代理指向 5000

### 7.2 关键词添加

- **问题**：说"发邮件"时工具不调用
- **解决**：在 `should_use_tools()` 添加 '邮件', '发邮件', 'email', '发送邮件'

### 7.3 SMTP 配置

- **问题**：邮件发送失败
- **解决**：将 SMTP 配置从 `.env` 传递给 `send_email` 函数

---

## 8. 启动项目

### 8.1 启动 Ollama

```bash
ollama serve
# 默认 http://localhost:11434
```

### 8.2 启动后端

```bash
cd backend
python app.py
# 访问 http://localhost:5000
```

### 8.3 启动前端

```bash
cd frontend
npm run dev
# 访问 http://localhost:3000
```

---

## 9. 测试 Function Calling

### 9.1 测试时间

```
用户: 现在几点了？
期望: 调用 get_current_time → 返回当前时间
```

### 9.2 测试天气

```
用户: 上海天气怎么样？
期望: 调用 get_weather → 返回天气信息
```

### 9.3 测试股票

```
用户: 600519 股票价格？
期望: 调用 get_stock_price_cn → 返回股价信息
```

### 9.4 测试邮件

```
用户: 发邮件给 xxx@qq.com，主题是测试，内容是你好
期望: 调用 send_email → 发送邮件成功
```