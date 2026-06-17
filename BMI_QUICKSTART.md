# BMI 计算助手系统

基于 MCP 和 LangGraph 的智能 BMI 查询助手，使用本地 Ollama 模型和 HTTP Streaming。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                  用户输入                                 │
│         "我身高1.70米，体重60公斤，算一下BMI"            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Agent (bmi_agent.py)             │
│                                                          │
│  START ──→ agent ──→ [条件判断]                         │
│                      │                                   │
│                      ├─→ tools ──┐                      │
│                      │            │                      │
│                      └─→ END    [回到agent]             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│        MCP BMI 服务器 (bmi_mcp_server.py)               │
│                   Port: 8001                             │
│                                                          │
│  ┌─ /tools                 (列出可用工具)               │
│  ├─ /invoke_tool           (调用工具)                   │
│  └─ /stream_invoke_tool    (流式调用工具)               │
└─────────────────────────────────────────────────────────┘
```

## 文件说明

### 1. `bmi_mcp_server.py` - MCP 服务器
- **功能**: 提供 `calculate_bmi` 工具
- **端口**: 8001
- **特性**: 
  - RESTful API 接口
  - Streamable HTTP (Server-Sent Events)
  - 自动 BMI 分类（偏瘦/正常/超重/肥胖）
  - 输入验证

**主要端点**:
```
POST /invoke_tool?tool_name=calculate_bmi
  Body: {"weight": 60, "height": 1.70}

GET /stream_invoke_tool?tool_name=calculate_bmi&weight=60&height=1.70
  (返回 SSE 流式响应)

GET /tools
  (列出所有可用工具)

GET /health
  (健康检查)
```

### 2. `bmi_agent.py` - LangGraph 客户端
- **功能**: AI 助手，使用 ChatOllama 模型
- **特性**:
  - 自动解析用户输入中的身高和体重参数
  - LangGraph 状态管理和工作流
  - 条件路由（工具调用判断）
  - 流式工具执行
  
**工作流**:
1. **Agent 节点**: 接收用户消息，调用 ChatOllama 模型
2. **条件判断**: 检查模型是否需要调用工具
3. **Tools 节点**: 执行工具调用（调用 MCP 服务）
4. **循环**: 工具执行后返回 Agent，生成最终响应

## 快速启动

### 前置条件

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **启动 Ollama**
```bash
# 确保 Ollama 已启动并下载模型
ollama serve
ollama pull qwen2:0.6b  # 首次使用
```

### 启动步骤

#### 方式一：分开启动（Windows）

**终端 1 - 启动 MCP 服务器**:
```bash
cd backend
python bmi_mcp_server.py 8001
```
输出示例:
```
BMI MCP 服务器启动于 http://localhost:8001
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**终端 2 - 启动 BMI 助手**:
```bash
cd backend
python bmi_agent.py
```

#### 方式二：使用启动脚本（Windows）

```bash
# 启动 MCP 服务器
start_bmi_server.bat

# 启动 BMI 助手（新终端）
start_bmi_agent.bat
```

#### 方式三：使用 Shell 脚本（Linux/macOS）

```bash
# 启动 MCP 服务器
./start_bmi_server.sh

# 启动 BMI 助手（新终端）
./start_bmi_agent.sh
```

## 使用示例

### 示例 1：基本 BMI 计算
```
用户输入: 我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。

[Agent 节点] 处理消息...
[Agent] 输入消息数: 1
[Agent] 模型响应: 让我为您计算BMI...
[Agent] 工具调用: [calculate_bmi_tool]

[Tools 节点] 执行工具...
[Tools] 调用工具: calculate_bmi_tool
[Tools] 参数: {"weight": 60, "height": 1.70}
[Tools] 结果: BMI值：20.76，分类：正常（体重：60kg，身高：1.70m）

[路由] → end

助手回复:
根据计算，您的BMI指数约为20.76，属于正常范围。
```

### 示例 2：多参数提取
```
用户输入: 我身高1.75m，体重85kg，请计算我的BMI

工具调用: calculate_bmi_tool
参数: {"weight": 85, "height": 1.75}
结果: BMI值：27.76，分类：超重

助手回复:
您的BMI指数为27.76，属于超重范围。建议适度运动和合理饮食。
```

## API 调用示例

### 1. 调用 MCP 服务计算 BMI

```bash
# 使用 curl
curl -X POST "http://localhost:8001/invoke_tool?tool_name=calculate_bmi" \
  -H "Content-Type: application/json" \
  -d '{"weight": 60, "height": 1.70}'
```

**响应**:
```json
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

### 2. 流式调用 MCP 服务

```bash
curl -X GET "http://localhost:8001/stream_invoke_tool?tool_name=calculate_bmi&weight=60&height=1.70" \
  -H "Accept: text/event-stream"
```

**响应** (SSE 格式):
```
data: {"status": "starting", "tool": "calculate_bmi"}

data: {"status": "calculating", "progress": 50}

data: {"status": "completed", "result": {"bmi": 20.76, "category": "正常", "weight": 60, "height": 1.70}}
```

### 3. 获取可用工具列表

```bash
curl "http://localhost:8001/tools"
```

**响应**:
```json
{
  "tools": [
    {
      "name": "calculate_bmi",
      "description": "计算并返回 BMI 指数 (BMI = weight / height²)",
      "parameters": {
        "type": "object",
        "properties": {
          "weight": {
            "type": "number",
            "description": "体重，单位公斤"
          },
          "height": {
            "type": "number",
            "description": "身高，单位米"
          }
        },
        "required": ["weight", "height"]
      }
    }
  ]
}
```

## 扩展工具

要添加新工具，按以下步骤操作：

### 1. 在 `bmi_mcp_server.py` 中添加函数
```python
def calculate_new_metric(param1: float, param2: float) -> dict:
    """新工具的实现"""
    result = param1 + param2  # 示例
    return {"result": result}
```

### 2. 在 `/invoke_tool` 端点中添加处理
```python
if tool_name == "calculate_new_metric":
    result = calculate_new_metric(...)
```

### 3. 在 `/tools` 端点中添加工具定义
```python
{
    "name": "calculate_new_metric",
    "description": "工具描述",
    "parameters": {...}
}
```

### 4. 在 `bmi_agent.py` 中添加 LangChain 工具
```python
@tool
async def calculate_new_metric_tool(param1: float, param2: float) -> str:
    """工具描述"""
    result = await mcp_client.calculate_new_metric(param1, param2)
    return str(result)
```

### 5. 注册到工具列表
```python
tools = [calculate_bmi_tool, calculate_new_metric_tool]
```

## 配置说明

### `bmi_agent.py` 中的配置

```python
OLLAMA_MODEL = "qwen2:0.6b"        # 本地模型名称
MCP_SERVER_URL = "http://localhost:8001"  # MCP 服务器地址
TIMEOUT = 10                       # 请求超时时间（秒）
```

### 模型选择

支持的模型 (需要先 `ollama pull`):
- `qwen2:0.6b` - 轻量级，速度快
- `qwen2:1.5b` - 平衡性能
- `llama2:latest` - 通用模型
- `mistral:latest` - 高质量

更多模型: https://ollama.ai/library

## 故障排查

### 问题 1: MCP 服务器无法启动
```
Error: Address already in use: ('0.0.0.0', 8001)
```
**解决**: 更改端口或结束占用 8001 端口的进程

### 问题 2: 连接到 Ollama 失败
```
Error: Connection error to http://localhost:11434
```
**解决**: 确保 Ollama 已启动 (`ollama serve`)

### 问题 3: 模型未找到
```
Error: model not found: qwen2:0.6b
```
**解决**: 下载模型 (`ollama pull qwen2:0.6b`)

### 问题 4: 工具调用超时
```
Error: Connection timeout
```
**解决**: 增加 `TIMEOUT` 值或检查网络连接

## 日志输出示例

```
============================================================
用户输入: 我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。
============================================================

[Agent 节点] 处理消息...
[Agent] 输入消息数: 1
[Agent] 模型响应: 让我帮您计算一下BMI指数...
[Agent] 工具调用: [calculate_bmi_tool]

[Tools 节点] 执行工具...
[Tools] 调用工具: calculate_bmi_tool
[Tools] 参数: {'weight': 60, 'height': 1.7}
[Tools] 结果: BMI值：20.76，分类：正常（体重：60kg，身高：1.7m）

[路由] → end

============================================================
助手回复:
根据您的身高和体重数据，我计算出您的BMI指数约为20.76，
这属于正常范围（18.5-24.9）。保持健康的饮食和适度的运动，
您的身体状态很好！
============================================================
```

## 技术栈

- **LangGraph**: Agent 工作流编排
- **LangChain**: AI 模型集成和工具管理
- **ChatOllama**: 本地 LLM 推理
- **FastAPI**: HTTP API 框架
- **httpx**: 异步 HTTP 客户端
- **MCP**: Model Context Protocol 协议

## 参考资源

- LangGraph 文档: https://langchain-ai.github.io/langgraph/
- Ollama: https://ollama.ai/
- Model Context Protocol: https://modelcontextprotocol.io/
- FastAPI: https://fastapi.tiangolo.com/

## 许可证

MIT
