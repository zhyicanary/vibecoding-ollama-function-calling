# 🚀 FastAPI 数字人应用 - 快速开始指南

## 📋 前置要求

- ✅ Python 3.8+
- ✅ Ollama (已在本地安装并运行)
- ✅ pip/conda包管理器

## 🎯 5分钟快速启动

### 1️⃣ 启动Ollama（如果未启动）

```bash
# 终端1 - 启动Ollama服务
ollama serve
```

### 2️⃣ 启动后端FastAPI

```bash
# 终端2 - 进入backend目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

或使用启动脚本：

**Windows:**
```bash
start_fastapi.bat
```

**Linux/macOS:**
```bash
bash start_fastapi.sh
```

### 3️⃣ 启动前端

```bash
# 终端3 - 进入frontend目录
cd frontend

# 安装依赖（仅首次）
npm install

# 启动开发服务器
npm run dev
```

### ✅ 验证应用

打开浏览器访问：

| 功能 | 地址 |
|------|------|
| 前端应用 | http://localhost:5173 |
| API文档 (Swagger) | http://localhost:5000/docs |
| 自动API文档 (ReDoc) | http://localhost:5000/redoc |
| 健康检查 | http://localhost:5000/api/health |

## 📝 配置说明

### .env 配置文件

创建 `backend/.env`：

```env
# Ollama配置
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2  # 确保模型已下载: ollama pull llama3.2

# 可选：SMTP邮件配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
FROM_EMAIL=your-email@qq.com
SMTP_PASSWORD=your-app-password

# 可选：钉钉消息配置
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 可选：课程RAG配置
ENABLE_COURSE_RAG=false
COURSE_DOC_PATH=./docs/courses
```

## 🧪 验证环境

运行验证脚本检查所有配置：

```bash
cd backend
python verify_setup.py
```

输出示例：
```
==================================================
  FastAPI 应用启动验证
==================================================

🔍 检查Python版本...
   ✅ Python 3.10

🔍 检查依赖...
   ✅ fastapi
   ✅ uvicorn
   ✅ pydantic
   ...

🔍 检查Ollama服务...
   ✅ Ollama已连接，可用模型:
      - llama3.2:latest
      - nomic-embed-text:latest
      ...

✅ 所有检查通过！

🚀 启动应用:
   python app.py
```

## 📚 API 使用示例

### 聊天请求

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今天天气怎么样",
    "session_id": "user_123"
  }'
```

### 查询历史记录

```bash
curl http://localhost:5000/api/history/user_123
```

### 清空对话

```bash
curl -X POST http://localhost:5000/api/clear \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user_123"}'
```

## 🔧 可用工具

应用集成了以下工具，可通过对话调用：

| 工具 | 功能 | 示例 |
|------|------|------|
| 获取时间 | 查询当前时间和日期 | "现在几点了" |
| 天气查询 | 获取城市天气信息 | "北京今天天气如何" |
| 股票查询 | 查询A股股票信息 | "查一下600519的股价" |
| 发送邮件 | 发送邮件给指定收件人 | "发邮件给..." |
| 钉钉消息 | 向钉钉群发送消息 | "发送消息到钉钉" |

## 📖 FastAPI 特性

FastAPI相比Flask的优势：

✨ **自动API文档**
- Swagger UI (交互式): `/docs`
- ReDoc (美观文档): `/redoc`
- OpenAPI JSON Schema: `/openapi.json`

⚡ **高性能**
- 异步请求处理
- 比Flask快3-5倍
- 支持高并发连接

🔒 **类型安全**
- 自动请求验证 (Pydantic)
- 类型提示检查
- 自动错误消息

🎯 **开发效率**
- 自动参数验证
- 智能IDE提示
- 内置OpenAPI支持

## 🐛 常见问题

### 问题1：无法连接Ollama

**错误信息:**
```
❌ 无法连接到Ollama服务 (http://localhost:11434)
```

**解决:**
```bash
# 确保Ollama已启动
ollama serve

# 检查Ollama是否运行
curl http://localhost:11434/api/tags
```

### 问题2：模型不存在

**错误信息:**
```
error: model not found
```

**解决:**
```bash
# 列出已下载的模型
ollama list

# 下载模型
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 问题3：端口已被占用

**解决:**
```bash
# 改用其他端口 (例如8000)
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 问题4：依赖冲突

**解决:**
```bash
# 重新安装依赖
pip install --upgrade -r requirements.txt

# 或创建新环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 📂 项目结构

```
├── backend/
│   ├── app.py                    # FastAPI主应用
│   ├── tools.py                  # 工具函数定义
│   ├── course_rag.py            # 课程RAG模块（可选）
│   ├── requirements.txt          # Python依赖
│   ├── .env                      # 环境变量配置
│   ├── verify_setup.py          # 验证脚本
│   ├── start_fastapi.sh         # Linux启动脚本
│   ├── start_fastapi.bat        # Windows启动脚本
│   └── test/
│       └── test_*.py            # 测试文件
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # React主应用
│   │   └── ...
│   ├── package.json             # Node依赖
│   ├── vite.config.js           # Vite配置
│   └── index.html
│
├── FASTAPI_MIGRATION.md         # FastAPI迁移指南
└── README.md                    # 项目说明
```

## 🚀 开发工作流

### 调试模式

FastAPI启动时默认启用热重载（文件改动自动重启）：

```bash
python app.py  # 或 uvicorn app:app --reload
```

### 测试API

使用Swagger UI测试：
1. 打开 http://localhost:5000/docs
2. 点击要测试的端点
3. 点击 "Try it out"
4. 输入参数
5. 点击 "Execute"

## 📞 获取帮助

- 📖 [FastAPI官方文档](https://fastapi.tiangolo.com/)
- 📖 [Ollama文档](https://github.com/ollama/ollama)
- 📖 [LangChain文档](https://python.langchain.com/)
- 📖 [React文档](https://react.dev/)

## ✅ 部署检查清单

在部署到生产环境前，确保：

- [ ] 所有依赖已安装
- [ ] .env配置已完成
- [ ] Ollama服务已部署
- [ ] API文档已验证
- [ ] 前端已构建 (`npm run build`)
- [ ] 防火墙规则已配置
- [ ] 日志系统已设置

## 🎉 开始探索！

现在你已经准备好了！

1. ✅ 启动Ollama
2. ✅ 启动FastAPI应用
3. ✅ 启动React前端
4. 🎯 打开浏览器访问应用

享受使用FastAPI数字人应用！🚀
