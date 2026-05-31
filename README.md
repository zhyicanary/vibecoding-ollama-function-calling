# AI 数字人对话应用

基于 Ollama 本地大模型的 AI 数字人对话应用，采用前后端分离架构。

## 技术栈

- **前端**: React 18 + Vite
- **后端**: Python Flask
- **AI**: Ollama (本地大模型)

## 项目结构

```
lab5/
├── frontend/          # React前端应用
│   ├── src/
│   │   ├── App.jsx    # 主应用组件
│   │   ├── index.css # 全局样式
│   │   └── main.jsx  # 入口文件
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── backend/           # Flask后端服务
│   ├── app.py        # API服务
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
| `/api/clear` | POST | 清空对话历史 |
| `/api/history` | GET | 获取对话历史 |
| `/api/health` | GET | 健康检查 |

### Chat API

**请求**
```json
{
  "message": "你好"
}
```

**响应**
```json
{
  "response": "你好！有什么可以帮助你的吗？",
  "success": true
}
```

## 环境变量

### 后端 (backend/.env)
```
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2
PORT=5000
```

## 功能特性

- ✓ 实时对话交互
- ✓ 对话历史记录
- ✓ 加载状态提示
- ✓ 连接状态显示
- ✓ 响应式设计
- ✓ 赛博朋克风格UI

## 注意事项

1. 首次启动需确保 Ollama 服务正常运行
2. 首次对话可能需要加载模型，等待时间较长
3. 前端通过 Vite 代理连接后端，无需额外配置跨域