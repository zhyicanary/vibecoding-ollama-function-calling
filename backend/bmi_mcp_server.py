"""
BMI MCP 服务器
提供 calculate_bmi 工具，通过 HTTP 暴露
"""

import json
import asyncio
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn


app = FastAPI(title="BMI MCP Server")


def calculate_bmi(weight: float, height: float) -> dict:
    """
    计算 BMI 指数
    
    Args:
        weight: 体重（公斤）
        height: 身高（米）
    
    Returns:
        包含 BMI 值的字典
    """
    if weight <= 0 or height <= 0:
        raise ValueError("体重和身高必须大于0")
    
    if height > 3 or height < 0.5:
        raise ValueError("身高范围应该在0.5米到3米之间")
    
    if weight > 500 or weight < 1:
        raise ValueError("体重范围应该在1公斤到500公斤之间")
    
    bmi = weight / (height ** 2)
    
    # 判断 BMI 等级
    if bmi < 18.5:
        category = "偏瘦"
    elif 18.5 <= bmi < 25:
        category = "正常"
    elif 25 <= bmi < 30:
        category = "超重"
    else:
        category = "肥胖"
    
    return {
        "bmi": round(bmi, 2),
        "category": category,
        "weight": weight,
        "height": height
    }


@app.post("/invoke_tool")
async def invoke_tool(tool_name: str, params: dict) -> dict:
    """
    调用工具的端点
    
    Args:
        tool_name: 工具名称
        params: 工具参数
    
    Returns:
        工具执行结果
    """
    if tool_name == "calculate_bmi":
        try:
            result = calculate_bmi(
                weight=params.get("weight"),
                height=params.get("height")
            )
            return {
                "success": True,
                "result": result
            }
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=404, detail=f"未知工具: {tool_name}")


@app.get("/tools")
async def list_tools() -> dict:
    """
    列出所有可用工具
    """
    return {
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


@app.get("/stream_invoke_tool")
async def stream_invoke_tool(tool_name: str, weight: float, height: float):
    """
    流式调用工具的端点 (Streamable HTTP)
    
    使用 Server-Sent Events 返回流式结果
    """
    async def generate():
        try:
            # 发送开始信息
            yield f"data: {json.dumps({'status': 'starting', 'tool': tool_name})}\n\n"
            
            # 计算 BMI
            result = calculate_bmi(weight=weight, height=height)
            
            # 发送中间步骤
            yield f"data: {json.dumps({'status': 'calculating', 'progress': 50})}\n\n"
            
            # 稍微延迟以演示流式传输
            await asyncio.sleep(0.1)
            
            # 发送最终结果
            yield f"data: {json.dumps({'status': 'completed', 'result': result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"BMI MCP 服务器启动于 http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
