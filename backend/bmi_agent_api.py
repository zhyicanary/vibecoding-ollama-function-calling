"""
BMI 助手的 FastAPI 集成示例
展示如何将 LangGraph Agent 集成到 FastAPI 应用中
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from typing import Optional

# 导入 Agent
try:
    from bmi_agent_sync import run_bmi_agent_sync
except ImportError:
    print("警告: 无法导入 bmi_agent_sync，请确保在 backend 目录运行此脚本")
    run_bmi_agent_sync = None


app = FastAPI(
    title="BMI 助手 API",
    description="基于 LangGraph 和 Ollama 的 BMI 查询助手",
    version="1.0.0"
)


# ==================== 请求/响应模型 ====================
class BMIQueryRequest(BaseModel):
    """BMI 查询请求"""
    question: str = "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"
    
    class Config:
        example = {
            "question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"
        }


class BMIQueryResponse(BaseModel):
    """BMI 查询响应"""
    question: str
    answer: str
    status: str = "success"
    
    class Config:
        example = {
            "question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。",
            "answer": "根据计算，您的BMI指数约为20.76，属于正常范围。",
            "status": "success"
        }


# ==================== API 端点 ====================
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "BMI Agent API"}


@app.post("/query_bmi", response_model=BMIQueryResponse)
async def query_bmi(request: BMIQueryRequest) -> BMIQueryResponse:
    """
    查询 BMI
    
    接收用户问题，通过 LangGraph Agent 处理，返回 BMI 计算结果
    
    示例:
    ```json
    {
      "question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。"
    }
    ```
    """
    if not run_bmi_agent_sync:
        raise HTTPException(
            status_code=500,
            detail="Agent 未初始化，请检查依赖"
        )
    
    try:
        # 在线程池中运行同步的 Agent（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            run_bmi_agent_sync,
            request.question
        )
        
        return BMIQueryResponse(
            question=request.question,
            answer=answer,
            status="success"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理失败: {str(e)}"
        )


@app.post("/query_bmi_streaming")
async def query_bmi_streaming(request: BMIQueryRequest):
    """
    流式查询 BMI
    
    使用 Server-Sent Events 返回实时结果
    """
    if not run_bmi_agent_sync:
        raise HTTPException(
            status_code=500,
            detail="Agent 未初始化"
        )
    
    async def generate():
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'status': 'processing', 'message': '正在处理您的请求...'})}\n\n"
            
            # 在线程池中运行 Agent
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None,
                run_bmi_agent_sync,
                request.question
            )
            
            # 发送完成事件
            yield f"data: {json.dumps({'status': 'completed', 'answer': answer})}\n\n"
        
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


@app.get("/examples")
async def get_examples():
    """获取使用示例"""
    return {
        "examples": [
            {
                "question": "我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。",
                "description": "基本的 BMI 计算查询"
            },
            {
                "question": "我身高 1.80 米，体重 85 公斤，这样的身材是否正常？",
                "description": "带有评价的 BMI 查询"
            },
            {
                "question": "如何从 BMI 指数 28 降到 25？",
                "description": "关于 BMI 改善的建议"
            },
            {
                "question": "BMI 的计算公式是什么？",
                "description": "关于 BMI 概念的问题"
            }
        ]
    }


# ==================== 文档端点 ====================
@app.get("/")
async def root():
    """根路径 - 返回 API 文档链接"""
    return {
        "message": "欢迎使用 BMI 助手 API",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "query_bmi": "POST /query_bmi",
            "query_bmi_streaming": "POST /query_bmi_streaming",
            "examples": "GET /examples"
        }
    }


if __name__ == "__main__":
    import uvicorn
    import sys
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"启动 BMI 助手 API 在 http://localhost:{port}")
    print(f"文档: http://localhost:{port}/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
