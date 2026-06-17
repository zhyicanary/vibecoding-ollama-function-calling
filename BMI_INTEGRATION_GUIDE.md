# BMI 系统完整集成指南

## 系统组件概览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  ┌──────────────────┐         ┌──────────────────────────┐  │
│  │  Web UI          │         │  FastAPI Agent API       │  │
│  │  (React)         │         │  (bmi_agent_api.py)      │  │
│  └────────┬─────────┘         └──────────┬───────────────┘  │
└───────────┼────────────────────────────────┼────────────────┘
            │                                │
            └────────────────┬───────────────┘
                             │
┌────────────────────────────▼──────────────────────────────────┐
│                 LangGraph Agent 层                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  bmi_agent_sync.py  或  bmi_agent.py (async)         │   │
│  │  ├─ Agent Node: ChatOllama 模型推理                  │   │
│  │  ├─ Tools Node: 工具调用执行                        │   │
│  │  └─ Condition: 路由决策                              │   │
│  └────────────────────────┬────────────────────────────┘   │
└─────────────────────────────┼──────────────────────────────────┘
                              │ HTTP
┌─────────────────────────────▼──────────────────────────────────┐
│              MCP BMI 服务层 (Port 8001)                        │
│  bmi_mcp_server.py                                             │
│  ├─ POST /invoke_tool        (工具调用)                       │
│  ├─ GET  /stream_invoke_tool (流式调用)                       │
│  ├─ GET  /tools              (工具列表)                       │
│  └─ GET  /health             (健康检查)                       │
└──────────────────────────────────────────────────────────────┘
```

## 文件说明

| 文件 | 功能 | 类型 |
|------|------|------|
| `bmi_mcp_server.py` | MCP 服务器，提供 BMI 计算工具 | FastAPI |
| `bmi_agent.py` | 异步 LangGraph Agent 客户端 | 异步 Python |
| `bmi_agent_sync.py` | 同步 LangGraph Agent 客户端 | 同步 Python |
| `bmi_agent_api.py` | FastAPI 集成示例，暴露 Agent 为 API | FastAPI |
| `test_bmi_system.py` | 完整系统测试脚本 | 测试工具 |

## 快速启动 (3 步)

### 步骤 1: 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

如果依赖安装失败，尝试：
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### 步骤 2: 启动 Ollama 和 MCP 服务器

**终端 1 - 启动 Ollama**:
```bash
ollama serve
```

首次运行需要下载模型：
```bash
ollama pull qwen2:0.6b
```

**终端 2 - 启动 MCP 服务器**:
```bash
cd backend
python bmi_mcp_server.py 8001
```

输出示例：
```
BMI MCP 服务器启动于 http://localhost:8001
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 步骤 3: 测试系统

**选项 A - 运行测试脚本** (推荐)：
```bash
# 新终端 3
cd backend
python test_bmi_system.py
```

**选项 B - 启动 Agent**：
```bash
# 新终端 3
cd backend
python bmi_agent_sync.py
```

**选项 C - 启动 Agent API**：
```bash
# 新终端 3
cd backend
python bmi_agent_api.py 8000
# 访问 http://localhost:8000/docs 查看 Swagger 文档
```

## 详细使用指南

### 方案 1: 同步模式 (推荐新手)

最简单的方式，直接运行 Agent：

```python
from bmi_agent_sync import run_bmi_agent_sync

# 运行 Agent
response = run_bmi_agent_sync("我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。")
print(response)
```

**优点**:
- ✓ 简单易用
- ✓ 易于调试
- ✓ 性能足够

**缺点**:
- ✗ 可能会阻塞事件循环（在异步框架中使用需要 executor）

### 方案 2: 异步模式 (推荐高并发)

```python
import asyncio
from bmi_agent import run_bmi_agent

async def main():
    response = await run_bmi_agent("我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。")
    print(response)

asyncio.run(main())
```

**优点**:
- ✓ 高并发支持
- ✓ 事件循环友好
- ✓ 流式处理支持

**缺点**:
- ✗ 代码复杂度较高

### 方案 3: FastAPI 集成 (推荐生产)

启动 Agent API：
```bash
python bmi_agent_api.py 8000
```

通过 HTTP 调用：

**同步调用**:
```bash
curl -X POST "http://localhost:8000/query_bmi" \
  -H "Content-Type: application/json" \
  -d '{"question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"}'
```

**流式调用**:
```bash
curl -X POST "http://localhost:8000/query_bmi_streaming" \
  -H "Content-Type: application/json" \
  -d '{"question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"}'
```

访问 Swagger 文档: http://localhost:8000/docs

### 方案 4: 直接调用 MCP 服务

如果只需要计算 BMI，不需要 AI 推理：

```bash
curl -X POST "http://localhost:8001/invoke_tool?tool_name=calculate_bmi" \
  -H "Content-Type: application/json" \
  -d '{"weight": 60, "height": 1.70}'
```

## 工作流示例

### 场景：用户询问 "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"

```
用户输入
    │
    ▼
[Agent] ChatOllama 接收消息
    │ 模型识别需要调用 calculate_bmi 工具
    ▼
[Tools] 执行工具调用
    │ 调用 MCP 服务: POST /invoke_tool
    │ 参数: weight=60, height=1.70
    ▼
[MCP Server] 计算结果
    │ BMI = 60 / (1.70 * 1.70) = 20.76
    │ 分类: 正常
    ▼
[Tools] 接收工具结果
    │ "BMI值：20.76，分类：正常"
    ▼
[Agent] 生成最终响应
    │ "根据计算，您的BMI指数约为20.76，属于正常范围..."
    ▼
返回给用户
```

## 配置调整

### 修改模型

在 `bmi_agent_sync.py` 或 `bmi_agent.py` 中：

```python
OLLAMA_MODEL = "qwen2:1.5b"  # 改为其他模型
```

可用模型（需要先 `ollama pull`）:
- `qwen2:0.6b` - 轻量级 ⚡
- `qwen2:1.5b` - 平衡性能 ⚙️
- `mistral:latest` - 高质量 🚀
- `llama2:latest` - 通用模型

### 修改 MCP 服务器地址

如果 MCP 服务器在其他机器上：

```python
MCP_SERVER_URL = "http://192.168.1.100:8001"  # 修改为实际地址
```

### 修改超时时间

```python
TIMEOUT = 30  # 改为 30 秒
```

## 常见问题

### Q1: Ollama 连接失败
```
Error: Connection error to http://localhost:11434
```
**解决**: 
```bash
ollama serve  # 在另一个终端启动 Ollama
```

### Q2: 模型未找到
```
Error: model not found: qwen2:0.6b
```
**解决**:
```bash
ollama pull qwen2:0.6b
```

### Q3: MCP 服务器端口被占用
```
Error: Address already in use: ('0.0.0.0', 8001)
```
**解决方案**:
1. 修改端口: `python bmi_mcp_server.py 8002`
2. 或关闭占用该端口的进程

### Q4: 导入错误
```
ModuleNotFoundError: No module named 'langgraph'
```
**解决**:
```bash
pip install -r requirements.txt
```

### Q5: 响应很慢
**可能原因**:
- Ollama 模型较大，首次推理需要时间
- 网络延迟
- 系统资源不足

**优化**:
- 使用更小的模型: `qwen2:0.6b`
- 增加 GPU 内存
- 检查网络连接

## 生产部署

### Docker 部署

创建 `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

CMD ["python", "bmi_agent_api.py", "8000"]
```

构建和运行：
```bash
docker build -t bmi-agent .
docker run -p 8000:8000 -p 8001:8001 bmi-agent
```

### 负载均衡

使用 Nginx 负载均衡多个 Agent 实例：
```nginx
upstream bmi_agents {
    server localhost:8000;
    server localhost:8001;
}

server {
    listen 80;
    location / {
        proxy_pass http://bmi_agents;
    }
}
```

## 监控和日志

### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 性能监控

添加到 `bmi_agent_api.py`:
```python
from time import time

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 下一步

1. **集成到前端**: 连接 React 应用到 Agent API
2. **添加更多工具**: 扩展 MCP 服务，添加新的计算工具
3. **性能优化**: 使用缓存、批处理等优化技术
4. **监控告警**: 集成 Prometheus、ELK 等监控系统

## 参考文档

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Ollama 文档](https://ollama.ai/)
- [MCP 协议](https://modelcontextprotocol.io/)
- [LangChain 文档](https://python.langchain.com/)
