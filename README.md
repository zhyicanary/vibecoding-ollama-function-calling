# AI 数字人对话应用

基于 Ollama 本地大模型的 AI 数字人对话应用，采用前后端分离架构。

## 技术栈

- **前端**: React 18 + Vite
- **后端**: Python Flask
- **AI**: Ollama (本地大模型)
- **框架**: LangChain (工具调用、会话记忆、LCEL Chain)

## 项目结构

```
vibecoding-ollama-function-calling/
├── frontend/          # React前端应用
│   ├── src/
│   │   ├── App.jsx    # 主应用组件
│   │   ├── index.css  # 全局样式
│   │   └── main.jsx   # 入口文件
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── backend/           # Flask后端服务
│   ├── app.py        # API服务 (LangChain 集成)
│   ├── tools.py      # 工具函数实现
│   └── requirements.txt
└── README.md
```

## 快速启动

### 1. 启动 Ollama

确保已安装 Ollama 并运行：

```bash
ollama serve
ollama pull llama3.2  # 首次使用需下载模型
```

### 2. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端默认运行在 `http://localhost:5000`

### 3. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端默认运行在 `http://localhost:3000`

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送对话请求 |
| `/api/history/<session_id>` | GET | 获取指定会话的历史记录 |
| `/api/history/<session_id>` | DELETE | 清除指定会话的历史记录 |
| `/api/health` | GET | 健康检查 |

### Chat API

**请求**
```json
{
  "message": "北京今天天气怎么样？",
  "session_id": "user123"
}
```

**响应**
```json
{
  "response": {
    "股票名称": "贵州茅台",
    "股票代码": "600519",
    "当前价格": "1688.00元",
    "涨跌幅": "2.35%",
    ...
  }
}
```

## 环境变量

### 后端 (backend/.env)
```
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2
PORT=5000
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
FROM_EMAIL=your_email@example.com
SMTP_PASSWORD=your_password
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
```

## 功能特性

- ✓ 实时对话交互
- ✓ 对话历史记录（会话隔离）
- ✓ 加载状态提示
- ✓ 连接状态显示
- ✓ 响应式设计
- ✓ 赛博朋克风格UI
- ✓ **LangChain 工具调用** (get_time, get_weather, get_stock_price, send_email, send_dingtalk)
- ✓ **LCEL Chain** 构建
- ✓ **会话记忆** (RunnableWithMessageHistory)
- ✓ **JSON 输出解析** (JsonOutputParser)

## 工具说明

本应用集成了 5 个基于 `@tool` 装饰器定义的 LangChain 工具：

| 工具 | 功能 | 参数 |
|------|------|------|
| `get_time` | 获取当前时间 | `timezone`: 时区，`format`: 日期格式 |
| `get_weather` | 查询城市天气 | `city`: 城市名称 |
| `get_stock_price` | 查询A股股价 | `ticker`: 6位股票代码 |
| `send_email_tool` | 发送邮件 | `to_email`, `subject`, `content` |
| `send_dingtalk` | 发送钉钉消息 | `message`: 消息内容 |

## 架构说明

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  Flask API  │────▶│   Ollama    │
│   (React)   │◀────│ (LangChain) │◀────│   (LLM)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Tools     │
                    │ get_time    │
                    │ get_weather │
                    │ get_stock   │
                    │ send_email  │
                    │ send_ding   │
                    └─────────────┘
```

## 注意事项

1. 首次启动需确保 Ollama 服务正常运行
2. 首次对话可能需要加载模型，等待时间较长
3. 前端通过 Vite 代理连接后端，无需额外配置跨域
4. 邮件和钉钉功能需要配置相应的环境变量