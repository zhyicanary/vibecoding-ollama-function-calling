@echo off
REM FastAPI 应用快速启动脚本 (Windows)

echo.
echo ==========================================
echo   FastAPI 数字人应用 - 快速启动脚本
echo ==========================================
echo.

REM 检查依赖
echo 1^) 检查依赖...
python --version >nul 2>&1
if errorlevel 1 (
    echo ^❌ 未找到Python，请先安装Python
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo ^✅ Python 已安装: %%i

REM 检查虚拟环境
echo.
echo 2^) 检查虚拟环境...
if not exist "venv" (
    echo    创建虚拟环境...
    python -m venv venv
)

echo    激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo.
echo 3^) 安装依赖...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ^❌ 依赖安装失败
    exit /b 1
)
echo ^✅ 依赖安装完成

REM 启动应用
echo.
echo 4^) 启动应用...
echo.
echo ==========================================
echo   ^✅ FastAPI应用启动中...
echo   📖 API 文档: http://localhost:5000/docs
echo   📘 ReDoc: http://localhost:5000/redoc
echo ==========================================
echo.

python app.py

pause
