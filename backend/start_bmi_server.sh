#!/bin/bash
# 启动 BMI MCP 服务器
cd "$(dirname "$0")"
python bmi_mcp_server.py 8001
