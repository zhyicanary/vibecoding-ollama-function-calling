# BMI 系统详细架构文档

## 系统架构图

### 整体系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户交互层                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   Web 前端        │  │   命令行工具     │  │  第三方应用  │  │
│  │   (React)        │  │   (Python REPL)  │  │  (API 调用)  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                    │           │
└───────────┼─────────────────────┼────────────────────┼───────────┘
            │                     │                    │
┌───────────▼─────────────────────▼────────────────────▼───────────┐
│                    API 与通信层 (Port 8000/8001)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  FastAPI / HTTP Endpoints                                  │ │
│  │  ├─ POST /query_bmi          (同步查询)                   │ │
│  │  ├─ POST /query_bmi_streaming (流式查询)                  │ │
│  │  ├─ POST /invoke_tool        (调用工具)                  │ │
│  │  ├─ GET  /stream_invoke_tool (流式工具调用)              │ │
│  │  ├─ GET  /tools              (获取工具列表)              │ │
│  │  ├─ GET  /health             (健康检查)                  │ │
│  │  └─ GET  /docs               (Swagger 文档)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────┬────────────────────────────────────────────────────┬─┘
            │                                                    │
            │ HTTP / 工具调用                                   │
            │                                                    │
┌───────────▼────────────────────────────────────────────────────▼┐
│                   业务逻辑层 (LangGraph Agent)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Agent 工作流                                            │  │
│  │                                                           │  │
│  │  ┌─────────┐                                            │  │
│  │  │ START   │                                            │  │
│  │  └────┬────┘                                            │  │
│  │       │                                                 │  │
│  │       ▼                                                 │  │
│  │  ┌──────────────────┐                                 │  │
│  │  │  Agent Node      │                                 │  │
│  │  │ (ChatOllama)     │ ◄── 模型推理                   │  │
│  │  │ .bind_tools()    │                                 │  │
│  │  └────────┬─────────┘                                 │  │
│  │           │                                            │  │
│  │           ▼                                            │  │
│  │  ┌──────────────────────────┐                        │  │
│  │  │  条件路由 (Conditional)   │                        │  │
│  │  │  需要调用工具?            │                        │  │
│  │  └──┬─────────────────┬─────┘                        │  │
│  │     │ 是              │ 否                           │  │
│  │     ▼                 ▼                               │  │
│  │ ┌────────────┐    ┌──────┐                          │  │
│  │ │ Tools Node │    │ END  │                          │  │
│  │ └─────┬──────┘    └──────┘                          │  │
│  │       │                                              │  │
│  │       ▼                                              │  │
│  │  ┌──────────────────────────┐                       │  │
│  │  │  工具执行                 │                       │  │
│  │  │ calculate_bmi_tool() ──► MCP Server              │  │
│  │  └─────────┬────────────────┘                       │  │
│  │            │                                         │  │
│  │            ▼                                         │  │
│  │       回到 Agent                                    │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  • 状态管理: messages 列表                                  │
│  • 消息类型: HumanMessage, AIMessage, ToolMessage          │
│  • 工具绑定: .bind_tools() 绑定到 ChatOllama            │
│                                                              │
└────┬────────────────────────────────────────────────────────┬┘
     │                                                        │
     │ 工具调用                                              │
     │                                                        │
┌────▼────────────────────────────────────────────────────────▼┐
│               工具执行层 (MCP Server & Tools)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  calculate_bmi_tool()                                │  │
│  │  ├─ 参数验证                                        │  │
│  │  ├─ HTTP 请求到 MCP 服务                           │  │
│  │  └─ 返回格式化结果                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Server (Port 8001)                              │  │
│  │  ├─ /invoke_tool endpoint                            │  │
│  │  │  ├─ 接收: weight, height                         │  │
│  │  │  └─ 返回: BMI, category                          │  │
│  │  ├─ /stream_invoke_tool endpoint                    │  │
│  │  │  └─ SSE 流式响应                                 │  │
│  │  └─ /tools endpoint                                │  │
│  │     └─ 工具定义列表                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────┬────────────────────────────────────────────────┘
              │
              │ 模型推理
              │
┌─────────────▼────────────────────────────────────────────────┐
│                  AI 模型层 (Ollama Local LLM)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ChatOllama (Port 11434)                             │  │
│  │  │                                                   │  │
│  │  ├─ 模型: qwen2:0.6b (推荐)                         │  │
│  │  │  ├─ 参数: 0.6B                                  │  │
│  │  │  ├─ 速度: ⚡⚡⚡ 快                             │  │
│  │  │  └─ 质量: ⭐⭐⭐ 一般                          │  │
│  │  │                                                  │  │
│  │  ├─ 模型: qwen2:1.5b                               │  │
│  │  │  ├─ 参数: 1.5B                                 │  │
│  │  │  ├─ 速度: ⚡⚡ 中等                            │  │
│  │  │  └─ 质量: ⭐⭐⭐⭐ 好                         │  │
│  │  │                                                  │  │
│  │  ├─ 模型: mistral:latest                           │  │
│  │  │  ├─ 参数: 7B                                   │  │
│  │  │  ├─ 速度: ⚡ 较慢                              │  │
│  │  │  └─ 质量: ⭐⭐⭐⭐⭐ 优秀                      │  │
│  │  │                                                  │  │
│  │  └─ 功能:                                           │  │
│  │     ├─ 识别用户意图                               │  │
│  │     ├─ 参数提取                                   │  │
│  │     ├─ 工具选择                                   │  │
│  │     └─ 响应生成                                   │  │
│  │                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 数据流图

### 完整请求流程

```
用户输入
   │
   ▼
┌─────────────────────────────────────────┐
│ "我身高1.70米，体重60公斤，算一下BMI"  │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────┐
        │   HTTP API   │
        │ (FastAPI)    │
        └──────┬───────┘
               │
               ▼
    ┌──────────────────────┐
    │ bmi_agent_api.py     │
    │ query_bmi() endpoint │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ LangGraph Workflow   │
    │ invoke(state)        │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐     
    │  Agent Node          │
    │  agent()             │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  ChatOllama Model    │
    │  .invoke()           │
    │  (qwen2:0.6b)        │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Model 推理结果      │
    │  tool_calls:         │
    │  [{                  │
    │    "name": ...       │
    │    "args": {         │
    │      "weight": 60,   │
    │      "height": 1.70  │
    │    }                 │
    │  }]                  │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Conditional Routing  │
    │ should_continue()    │
    │ → "tools"            │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Tools Node          │
    │  tools_node()        │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Tool Execution       │
    │ calculate_bmi_tool() │
    └──────┬───────────────┘
           │ HTTP 请求
           ▼
    ┌──────────────────────┐
    │   MCP Server         │
    │   POST /invoke_tool  │
    │   {"weight": 60,     │
    │    "height": 1.70}   │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  calculate_bmi()     │
    │  BMI = 60/(1.70²)    │
    │     = 20.76          │
    │  category = "正常"   │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │   HTTP Response      │
    │   {                  │
    │     "bmi": 20.76,    │
    │     "category": ...  │
    │   }                  │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Tool Result Message  │
    │ ToolMessage(         │
    │   content: "BMI..."  │
    │ )                    │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Routing (回到 agent) │
    │ should_continue()    │
    │ → "tools"            │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Agent Node (再次)   │
    │  agent()             │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  ChatOllama Model    │
    │  生成最终回复        │
    │  (no tool_calls)     │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Routing             │
    │ should_continue()    │
    │ → "end"              │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  END                 │
    │                      │
    │  Final Response:     │
    │  "根据计算，您的     │
    │   BMI指数约为        │
    │   20.76，属于        │
    │   正常范围"          │
    └──────────────────────┘
           │
           ▼
返回给用户
```

## 状态管理

### AgentState 结构

```python
AgentState = {
    "messages": [        # 消息列表（Annotated with add_messages）
        HumanMessage(
            content="我身高1.70米，体重60公斤..."
        ),
        AIMessage(
            content="让我帮您计算...",
            tool_calls=[{
                "id": "call_xxx",
                "name": "calculate_bmi_tool",
                "args": {
                    "weight": 60,
                    "height": 1.70
                }
            }]
        ),
        ToolMessage(
            content="BMI值：20.76，分类：正常...",
            name="calculate_bmi_tool",
            tool_call_id="call_xxx"
        ),
        AIMessage(
            content="根据计算，您的BMI指数约为20.76..."
        )
    ],
    "user_input": "我身高1.70米，体重60公斤..."  # 可选
}
```

### 消息类型说明

| 消息类型 | 来源 | 内容 | 用途 |
|---------|------|------|------|
| HumanMessage | 用户 | 用户提问 | 初始化对话 |
| AIMessage | 模型 | 模型回复或工具调用 | 模型推理结果 |
| ToolMessage | 工具 | 工具执行结果 | 提供工具结果给模型 |

## 模型绑定

### .bind_tools() 工作机制

```python
# 1. 定义工具
@tool
async def calculate_bmi_tool(weight: float, height: float) -> str:
    """计算 BMI"""
    ...

tools = [calculate_bmi_tool]

# 2. 绑定到模型
model_with_tools = ChatOllama(model="qwen2:0.6b").bind_tools(
    tools,
    tool_choice="auto"  # 自动选择是否调用工具
)

# 3. 模型能识别工具并生成调用
response = model_with_tools.invoke(messages)
# response.tool_calls = [
#   {
#     "id": "call_123",
#     "name": "calculate_bmi_tool",
#     "args": {"weight": 60, "height": 1.70}
#   }
# ]
```

## 条件路由逻辑

```python
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    判断是否继续执行工具
    
    逻辑:
    1. 获取最后一条消息
    2. 检查是否为 AIMessage 且包含 tool_calls
    3. 如果有工具调用 → 路由到 "tools"
    4. 否则 → 路由到 "end"
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"  # 执行工具
    else:
        return "end"    # 返回结果
```

## HTTP 流式传输

### Streamable HTTP (SSE)

```python
# MCP 服务器支持 SSE 流式响应
@app.get("/stream_invoke_tool")
async def stream_invoke_tool(tool_name: str, weight: float, height: float):
    async def generate():
        yield f"data: {json.dumps({'status': 'starting'})}\n\n"
        result = calculate_bmi(weight, height)
        yield f"data: {json.dumps({'status': 'completed', 'result': result})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

客户端接收:
```
data: {"status": "starting"}

data: {"status": "completed", "result": {...}}
```

## 工具注册

### 工具定义流程

```
1. 定义计算函数
   ├─ def calculate_bmi(weight, height)
   └─ 实现具体逻辑

2. 创建 LangChain 工具
   ├─ @tool
   ├─ async def calculate_bmi_tool(...)
   └─ 调用 MCP 服务

3. 绑定到模型
   ├─ tools = [calculate_bmi_tool]
   └─ model.bind_tools(tools)

4. 在工具节点执行
   ├─ 检查 tool_calls
   ├─ 执行对应的工具函数
   └─ 返回 ToolMessage

5. 模型继续推理
   ├─ 根据工具结果生成回复
   └─ 决定是否继续调用工具
```

## 配置参数速查

### bmi_mcp_server.py
```python
PORT = 8001                    # 服务器端口
WEIGHT_MIN = 1                 # 最小体重（kg）
WEIGHT_MAX = 500               # 最大体重（kg）
HEIGHT_MIN = 0.5               # 最小身高（m）
HEIGHT_MAX = 3                 # 最大身高（m）
```

### bmi_agent_sync.py / bmi_agent.py
```python
OLLAMA_MODEL = "qwen2:0.6b"    # 使用的模型
MCP_SERVER_URL = "..."         # MCP 服务器地址
TIMEOUT = 10                   # 请求超时（秒）
```

### bmi_agent_api.py
```python
PORT = 8000                    # API 服务端口
HOST = "0.0.0.0"              # 监听地址
```

---

**架构图版本**: 1.0.0
**最后更新**: 2024年
