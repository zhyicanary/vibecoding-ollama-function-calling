"""
BMI 系统健康检查脚本
验证所有依赖和服务是否就绪
"""

import sys
import subprocess
import importlib
from typing import Tuple


def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"
    else:
        return False, f"Python 版本过低: {version.major}.{version.minor} (需要 3.9+)"


def check_package(package_name: str, import_name: str = None) -> Tuple[bool, str]:
    """检查 Python 包是否安装"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", "unknown")
        return True, f"{package_name} ({version}) ✓"
    except ImportError:
        return False, f"{package_name} ✗ (未安装)"


def check_ollama() -> Tuple[bool, str]:
    """检查 Ollama 是否运行"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            return True, f"Ollama ✓ (已安装 {len(models)} 个模型: {', '.join(model_names[:3])}...)"
        else:
            return False, "Ollama ✗ (服务异常)"
    except Exception as e:
        return False, f"Ollama ✗ (未运行: {str(e)})"


def check_mcp_server() -> Tuple[bool, str]:
    """检查 MCP 服务器是否运行"""
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=2)
        if response.status_code == 200:
            return True, "MCP 服务器 ✓ (运行在 8001 端口)"
        else:
            return False, "MCP 服务器 ✗ (服务异常)"
    except Exception as e:
        return False, f"MCP 服务器 ✗ (未运行: {str(e)})"


def check_qwen_model() -> Tuple[bool, str]:
    """检查 Qwen 模型是否下载"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        # 检查是否有 qwen 模型
        qwen_models = [m for m in model_names if "qwen" in m]
        if qwen_models:
            return True, f"Qwen 模型 ✓ (已安装: {', '.join(qwen_models)})"
        else:
            return False, "Qwen 模型 ✗ (需要运行: ollama pull qwen2:0.6b)"
    except Exception as e:
        return False, f"Qwen 模型 ✗ (检查失败: {str(e)})"


def main():
    """运行所有检查"""
    print("\n" + "="*60)
    print("BMI 系统健康检查")
    print("="*60 + "\n")
    
    checks = [
        ("Python 版本", check_python_version),
        ("LangChain", lambda: check_package("langchain", "langchain")),
        ("LangGraph", lambda: check_package("langgraph", "langgraph")),
        ("FastAPI", lambda: check_package("fastapi", "fastapi")),
        ("Ollama", check_ollama),
        ("Qwen 模型", check_qwen_model),
        ("MCP 服务器", check_mcp_server),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            success, message = check_func()
            results.append((check_name, success, message))
            print(f"{check_name:20} {message}")
        except Exception as e:
            results.append((check_name, False, str(e)))
            print(f"{check_name:20} ✗ ({str(e)})")
    
    # 总结
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print("\n" + "="*60)
    print(f"检查结果: {passed}/{total} 通过")
    print("="*60 + "\n")
    
    # 提供建议
    failed_checks = [(name, msg) for name, success, msg in results if not success]
    
    if failed_checks:
        print("需要修复的问题:\n")
        for name, msg in failed_checks:
            print(f"• {msg}")
        
        print("\n快速修复步骤:")
        
        for name, msg in failed_checks:
            if "Ollama" in name:
                print("  1. 启动 Ollama: ollama serve")
            elif "Qwen" in name:
                print("  2. 下载模型: ollama pull qwen2:0.6b")
            elif "MCP" in name:
                print("  3. 启动 MCP 服务器: python bmi_mcp_server.py 8001")
            elif "LangGraph" in name or "FastAPI" in name or "LangChain" in name:
                print("  4. 安装依赖: pip install -r requirements.txt")
        
        print("\n")
        return False
    else:
        print("✓ 所有检查都已通过！系统已就绪。")
        print("\n启动命令:")
        print("  1. python bmi_agent_sync.py        # 同步 Agent")
        print("  2. python bmi_agent.py              # 异步 Agent")
        print("  3. python bmi_agent_api.py          # API 服务器")
        print("  4. python test_bmi_system.py        # 运行测试")
        print("\n")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
