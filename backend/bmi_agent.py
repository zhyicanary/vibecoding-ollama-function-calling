"""
基于 LangGraph 和 ChatOllama 的 BMI 查询助手
连接到 MCP BMI 服务器
"""

import os
import json
import requests
from typing import Annotated, Literal, Optional, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# ==================== 配置 ====================
OLLAMA_MODEL = "qwen3:0.6b"  # 本地模型
MCP_SERVER_URL = "http://localhost:8001"  # MCP 服务器地址
TIMEOUT = 10


# ==================== 状态定义 ====================
class AgentState(TypedDict):
    """Agent 的状态定义"""
    messages: Annotated[list[BaseMessage], add_messages]
    user_input: Optional[str]


# ==================== MCP 客户端工具 ====================
class BMIMCPClientSync:
    """同步 MCP BMI 服务客户端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def calculate_bmi(self, weight: float, height: float) -> dict:
        """调用 MCP 服务计算 BMI"""
        try:
            response = requests.post(
                f"{self.base_url}/invoke_tool",
                params={"tool_name": "calculate_bmi"},
                json={"weight": weight, "height": height},
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_tools(self) -> dict:
        """获取可用工具列表"""
        try:
            response = requests.get(f"{self.base_url}/tools", timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


# 全局 MCP 客户端实例
mcp_client = BMIMCPClientSync(MCP_SERVER_URL)


# ==================== 工具定义 ====================
@tool
def calculate_bmi_tool(weight: float, height: float) -> str:
    """
    计算并返回 BMI 指数
    
    Args:
        weight: 体重，单位公斤
        height: 身高，单位米
    
    Returns:
        BMI 计算结果
    """
    result = mcp_client.calculate_bmi(weight, height)
    
    if result.get("success"):
        data = result.get("result", {})
        return f"BMI值：{data.get('bmi')}，分类：{data.get('category')}（体重：{data.get('weight')}kg，身高：{data.get('height')}m）"
    else:
        return f"计算失败: {result.get('error', '未知错误')}"


# 工具列表
tools = [calculate_bmi_tool]


# ==================== 节点定义 ====================
def agent(state: AgentState) -> dict:
    """
    Agent 节点：使用 ChatOllama 处理消息
    """
    print("\n[Agent 节点] 处理消息...")
    
    # 初始化模型
    model = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0,
        num_gpu=1
    )
    
    # 绑定工具到模型
    model_with_tools = model.bind_tools(tools, tool_choice="auto")
    
    # 获取当前消息
    messages = state["messages"]
    
    # 调用模型
    print(f"[Agent] 输入消息数: {len(messages)}")
    response = model_with_tools.invoke(messages)
    
    print(f"[Agent] 模型响应: {response.content}")
    print(f"[Agent] 工具调用: {response.tool_calls if hasattr(response, 'tool_calls') else 'None'}")
    
    # 返回新的消息
    return {
        "messages": [response]
    }


def tools_node(state: AgentState) -> dict:
    """
    工具节点：执行工具调用
    """
    print("\n[Tools 节点] 执行工具...")
    
    messages = state["messages"]
    last_message = messages[-1]
    
    # 处理工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_results = []
        
        for tool_call in last_message.tool_calls:
            print(f"[Tools] 调用工具: {tool_call['name']}")
            print(f"[Tools] 参数: {tool_call['args']}")
            
            # 执行工具
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            try:
                if tool_name == "calculate_bmi_tool":
                    # 使用 .invoke() 方法调用 StructuredTool
                    result = calculate_bmi_tool.invoke(tool_args)
                else:
                    result = f"未知工具: {tool_name}"
            except Exception as e:
                result = f"工具执行失败: {str(e)}"
                print(f"[Tools] 错误: {e}")
            
            print(f"[Tools] 结果: {result}")
            
            tool_results.append({
                "type": "tool",
                "name": tool_name,
                "content": result,
                "tool_call_id": tool_call["id"]
            })
        
        # 创建工具消息
        tool_messages = [
            ToolMessage(
                content=tr["content"],
                name=tr["name"],
                tool_call_id=tr["tool_call_id"]
            )
            for tr in tool_results
        ]
        
        return {
            "messages": tool_messages
        }
    
    return {"messages": []}


# ==================== 条件路由 ====================
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    条件路由：判断是否需要调用工具
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 如果 AI 消息有工具调用，路由到 tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("\n[路由] → tools")
        return "tools"
    else:
        print("\n[路由] → end")
        return "end"


# ==================== 构建图 ====================
def build_graph():
    """
    构建 LangGraph
    
    流程：
    START → agent → (条件判断)
                    ├→ tools → agent
                    └→ END
    """
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("agent", agent)
    workflow.add_node("tools", tools_node)
    
    # 设置起点
    workflow.set_entry_point("agent")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # tools 执行后回到 agent
    workflow.add_edge("tools", "agent")
    
    # 编译图
    app = workflow.compile()
    return app


# ==================== 主程序 ====================
def run_bmi_agent(user_input: str):
    """
    运行 BMI 助手
    
    Args:
        user_input: 用户输入的问题
    """
    print(f"\n{'='*60}")
    print(f"用户输入: {user_input}")
    print(f"{'='*60}")
    
    # 构建图
    app = build_graph()
    
    # 初始化状态
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input
    }
    
    # 运行图
    try:
        final_state = app.invoke(initial_state)
        
        # 提取最终响应
        messages = final_state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                print(f"\n{'='*60}")
                print(f"助手回复:\n{last_message.content}")
                print(f"{'='*60}")
                return last_message.content
        
        return "无法生成响应"
    
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return f"执行出错: {e}"


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。",
        "我的身高是 1.75m，体重 85kg，请计算我的 BMI",
        "BMI 的计算公式是什么？如果我身高 1.80 米，体重 72 公斤呢？"
    ]
    
    for user_input in test_cases:
        result = run_bmi_agent(user_input)
        print()
