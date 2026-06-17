@echo off
REM 启动 BMI Agent 客户端
cd /d "%~dp0"
python -m asyncio -c "import asyncio; from bmi_agent import run_bmi_agent; asyncio.run(run_bmi_agent('我身高 1.70 米，体重 60 公斤，帮我算一下 BMI。'))"
