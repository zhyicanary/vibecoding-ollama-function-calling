# BMI 系统快速参考卡

## 🚀 5 分钟快速启动

### 前置条件
```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 启动 Ollama
ollama serve

# 3. 下载模型（首次需要）
ollama pull qwen2:0.6b
```

### 启动命令（开3个终端）

**终端 1 - 启动 Ollama**:
```bash
ollama serve
```

**终端 2 - 启动 MCP 服务器**:
```bash
cd backend
python bmi_mcp_server.py 8001
```

**终端 3 - 运行 Agent**:
```bash
cd backend

# 选一个：
python bmi_agent_sync.py        # 同步（简单）
# 或
python bmi_agent.py              # 异步（高级）
# 或
python bmi_agent_api.py          # API（访问 http://localhost:8000/docs）
```

## 📁 文件映射表

| 文件 | 端口 | 用途 | 启动命令 |
|------|------|------|---------|
| `bmi_mcp_server.py` | 8001 | MCP 服务器 | `python bmi_mcp_server.py 8001` |
| `bmi_agent_sync.py` | - | 同步 Agent | `python bmi_agent_sync.py` |
| `bmi_agent.py` | - | 异步 Agent | `python bmi_agent.py` |
| `bmi_agent_api.py` | 8000 | Agent API | `python bmi_agent_api.py 8000` |
| `test_bmi_system.py` | - | 系统测试 | `python test_bmi_system.py` |
| `check_system.py` | - | 环境检查 | `python check_system.py` |
| `launch.py` | - | 启动菜单 | `python launch.py` |

## 🔄 工作流程

```
用户: "我身高1.70米，体重60公斤，算一下BMI"
   │
   ├─ 1️⃣ Agent 接收消息
   ├─ 2️⃣ ChatOllama 推理 → 识别需要调用 calculate_bmi
   ├─ 3️⃣ Tools 执行工具 → 调用 MCP /invoke_tool
   ├─ 4️⃣ MCP 计算 → BMI = 60/(1.70²) = 20.76
   ├─ 5️⃣ Tools 获得结果 → "BMI值：20.76，分类：正常"
   ├─ 6️⃣ Agent 生成回复
   │
结果: "您的BMI指数为20.76，属于正常范围"
```

## 🎯 选择启动方式

### 🟢 同步 Agent (bmi_agent_sync.py)
**适合**: 学习、测试、简单应用
**优点**: 代码简单、易调试
```bash
python bmi_agent_sync.py
```

### 🟡 异步 Agent (bmi_agent.py)
**适合**: 高并发、事件循环
**优点**: 异步高效、支持流式
```bash
python bmi_agent.py
```

### 🔴 API 服务器 (bmi_agent_api.py)
**适合**: 生产环境、Web 服务
**优点**: REST API、自动 Swagger 文档、可扩展
```bash
python bmi_agent_api.py 8000
# 访问 http://localhost:8000/docs
```

## 💻 API 调用示例

### 调用 MCP 工具
```bash
curl -X POST "http://localhost:8001/invoke_tool?tool_name=calculate_bmi" \
  -H "Content-Type: application/json" \
  -d '{"weight": 60, "height": 1.70}'

# 响应
{
  "success": true,
  "result": {
    "bmi": 20.76,
    "category": "正常",
    "weight": 60,
    "height": 1.70
  }
}
```

### 调用 Agent API
```bash
curl -X POST "http://localhost:8000/query_bmi" \
  -H "Content-Type: application/json" \
  -d '{"question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"}'

# 响应
{
  "question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。",
  "answer": "根据计算，您的BMI指数约为20.76，属于正常范围。",
  "status": "success"
}
```

## ⚙️ 配置参数

### 模型选择 (在 bmi_agent_sync.py)
```python
OLLAMA_MODEL = "qwen2:0.6b"  # 轻量级
# 或
OLLAMA_MODEL = "qwen2:1.5b"  # 平衡性能
# 或
OLLAMA_MODEL = "mistral:latest"  # 高质量
```

### MCP 服务器地址 (在 bmi_agent_sync.py)
```python
MCP_SERVER_URL = "http://localhost:8001"
```

### API 服务器端口 (启动时指定)
```bash
python bmi_agent_api.py 8000  # 默认 8000
python bmi_agent_api.py 8888  # 改为 8888
```

## 🐛 常见问题排查

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| Connection error to localhost:11434 | Ollama 未运行 | 运行 `ollama serve` |
| model not found: qwen2:0.6b | 模型未下载 | 运行 `ollama pull qwen2:0.6b` |
| Address already in use: 8001 | 端口占用 | 改用其他端口或关闭占用进程 |
| ModuleNotFoundError: langgraph | 依赖未安装 | 运行 `pip install -r requirements.txt` |
| Connection error to localhost:8001 | MCP 服务器未运行 | 在新终端运行 `python bmi_mcp_server.py 8001` |

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 平均响应时间 | 2-5 秒 |
| BMI 计算时间 | <50ms |
| 模型推理时间 | 1-3 秒 |
| 并发支持 | API 模式下支持 |
| 内存占用 | ~500MB |

## 🔗 支持链接

- **LangGraph 文档**: https://langchain-ai.github.io/langgraph/
- **Ollama 官网**: https://ollama.ai/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **MCP 协议**: https://modelcontextprotocol.io/

## 📝 测试用例

```python
# 测试 1: 基本 BMI 计算
"我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"
预期: "BMI值：20.76，分类：正常"

# 测试 2: 超重人群
"我的身高是 1.75m，体重 85kg，请计算我的 BMI"
预期: "BMI值：27.76，分类：超重"

# 测试 3: 概念问题
"BMI 的计算公式是什么？"
预期: 模型解释公式

# 测试 4: 复合问题
"我身高 1.80 米，体重 72 公斤，这样的身材健康吗？"
预期: "BMI值：22.22，分类：正常...建议..."
```

## 📦 依赖版本

```
fastapi==0.104.1
uvicorn==0.24.0
langchain==0.3.7
langgraph==1.1.10
langchain-ollama==0.2.0
mcp==1.0.0
httpx==0.25.0
```

## 🎓 学习路径

1. **入门**: 使用同步 Agent 理解基本工作流
   ```bash
   python bmi_agent_sync.py
   ```

2. **进阶**: 了解异步模式和并发
   ```bash
   python bmi_agent.py
   ```

3. **生产**: 部署为 API 服务
   ```bash
   python bmi_agent_api.py 8000
   ```

4. **扩展**: 添加新工具到 MCP 服务
   - 编辑 `bmi_mcp_server.py`
   - 添加新工具函数
   - 更新工具列表端点

## ✅ 检查清单

启动前检查：
- [ ] Python 3.9+ 已安装
- [ ] 依赖已安装: `pip install -r requirements.txt`
- [ ] Ollama 已启动: `ollama serve`
- [ ] Qwen 模型已下载: `ollama pull qwen2:0.6b`
- [ ] 选择启动方式（同步/异步/API）

运行中检查：
- [ ] MCP 服务器运行在 8001
- [ ] Agent 能成功连接到 MCP 服务器
- [ ] 能接收用户输入并生成回复

## 🆘 获取帮助

运行系统检查:
```bash
python check_system.py
```

运行测试:
```bash
python test_bmi_system.py
```

查看启动指南:
```bash
python launch.py help
```

---

**最后修改**: 2024年
**版本**: 1.0.0
