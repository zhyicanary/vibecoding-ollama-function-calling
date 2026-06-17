"""
FastAPI应用启动和配置验证脚本
"""
import subprocess
import sys
import time
import requests
from pathlib import Path

def check_python():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"   ✅ Python {version}")
    if sys.version_info < (3, 8):
        print("   ⚠️  警告: 推荐使用Python 3.8+")

def check_dependencies():
    """检查依赖"""
    print("\n🔍 检查依赖...")
    required = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'langchain',
        'langchain_ollama',
        'requests'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - 未安装")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  缺少以下依赖: {', '.join(missing)}")
        print("   运行: pip install -r requirements.txt")
        return False
    return True

def check_ollama():
    """检查Ollama服务"""
    print("\n🔍 检查Ollama服务...")
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            if models:
                print(f"   ✅ Ollama已连接，可用模型:")
                for model in models[:5]:
                    name = model.get('name', 'unknown')
                    print(f"      - {name}")
                if len(models) > 5:
                    print(f"      ... 及其他 {len(models)-5} 个模型")
            else:
                print("   ⚠️  Ollama已连接，但无可用模型")
            return True
        else:
            print("   ❌ Ollama连接失败")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ 无法连接到Ollama服务 (http://localhost:11434)")
        print("      请确保Ollama已启动")
        return False
    except Exception as e:
        print(f"   ❌ 检查Ollama失败: {e}")
        return False

def check_env_file():
    """检查.env配置文件"""
    print("\n🔍 检查.env配置...")
    env_file = Path('.env')
    if env_file.exists():
        print("   ✅ .env文件已存在")
        # 检查关键配置
        with open(env_file) as f:
            content = f.read()
            configs = {
                'OLLAMA_HOST': 'Ollama服务地址',
                'DEFAULT_MODEL': '默认模型',
                'SMTP_SERVER': 'SMTP服务器'
            }
            for key, desc in configs.items():
                if key in content:
                    print(f"   ✅ {key} 已配置 ({desc})")
                else:
                    print(f"   ⚠️  {key} 未配置 ({desc})")
        return True
    else:
        print("   ⚠️  .env文件不存在")
        print("      创建默认配置...")
        create_env()
        return True

def create_env():
    """创建默认.env文件"""
    env_content = """# Ollama配置
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2

# SMTP配置 (可选)
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
FROM_EMAIL=your-email@qq.com
SMTP_PASSWORD=your-password

# 钉钉配置 (可选)
DINGTALK_WEBHOOK_URL=

# 课程RAG配置 (可选)
COURSE_DOC_PATH=./docs/courses
COURSE_EMBEDDING_MODEL=nomic-embed-text
COURSE_LLM_MODEL=qwen3:8b
COURSE_CHROMA_DB_DIR=./chroma_db
COURSE_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
ENABLE_COURSE_RAG=false
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    print("   ✅ .env文件已创建")

def test_api():
    """测试API端点"""
    print("\n🔍 测试API端点...")
    base_url = 'http://localhost:5000'
    
    # 等待服务启动
    print("   ⏳ 等待服务启动...", end='', flush=True)
    for i in range(30):  # 最多等待30秒
        try:
            response = requests.get(f'{base_url}/api/health', timeout=1)
            if response.status_code == 200:
                print(" ✅")
                break
        except:
            print('.', end='', flush=True)
            time.sleep(1)
    else:
        print(" ❌ 超时")
        return False
    
    # 测试各个端点
    endpoints = [
        ('GET', '/api/health', 'health'),
        ('GET', '/api/models', 'models'),
        ('GET', '/', 'root'),
    ]
    
    for method, path, name in endpoints:
        try:
            if method == 'GET':
                response = requests.get(f'{base_url}{path}', timeout=5)
            else:
                response = requests.post(f'{base_url}{path}', json={}, timeout=5)
            
            if response.status_code in [200, 422]:  # 422是Pydantic验证错误
                print(f"   ✅ {method} {path}")
            else:
                print(f"   ❌ {method} {path} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {method} {path} - {e}")
    
    return True

def main():
    """主程序"""
    print("=" * 50)
    print("  FastAPI 应用启动验证")
    print("=" * 50)
    
    # 检查Python
    check_python()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 缺少必要依赖，请先安装")
        sys.exit(1)
    
    # 检查.env
    check_env_file()
    
    # 检查Ollama
    ollama_ok = check_ollama()
    if not ollama_ok:
        print("\n⚠️  Ollama服务未运行或配置不正确")
        print("   请确保Ollama已启动: ollama serve")
    
    # 总结
    print("\n" + "=" * 50)
    print("  验证完成")
    print("=" * 50)
    
    if ollama_ok:
        print("\n✅ 所有检查通过！")
        print("\n🚀 启动应用:")
        print("   python app.py")
        print("\n📖 访问API文档:")
        print("   http://localhost:5000/docs")
    else:
        print("\n⚠️  某些检查失败，请检查配置")

if __name__ == '__main__':
    main()
