@echo off
REM 启动 BMI MCP 服务器
cd /d "%~dp0"
python bmi_mcp_server.py 8001
