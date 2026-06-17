#!/bin/bash
# FastAPI 应用快速启动脚本 (Linux/macOS)

set -e

echo "=========================================="
echo "  FastAPI 数字人应用 - 快速启动脚本"
echo "=========================================="
echo ""

# 检查依赖
echo "1️⃣  检查依赖..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    exit 1
fi
echo "✅ Python3 已安装: $(python3 --version)"

echo ""
echo "2️⃣  检查虚拟环境..."
if [ ! -d "venv" ]; then
    echo "   创建虚拟环境..."
    python3 -m venv venv
fi

echo "   激活虚拟环境..."
source venv/bin/activate

echo ""
echo "3️⃣  安装依赖..."
pip install -q -r requirements.txt
echo "✅ 依赖安装完成"

echo ""
echo "4️⃣  启动应用..."
echo ""
echo "=========================================="
echo "  ✅ FastAPI应用启动中..."
echo "  📖 API 文档: http://localhost:5000/docs"
echo "  📘 ReDoc: http://localhost:5000/redoc"
echo "=========================================="
echo ""

# 启动应用
python app.py
