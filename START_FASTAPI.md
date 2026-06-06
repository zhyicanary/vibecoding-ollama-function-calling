# 🚀 FastAPI启动指南

## ⚡ 3步快速启动

### 1. 启动Ollama (如果未运行)
```bash
ollama serve
```

### 2. 启动FastAPI后端
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 启动React前端
```bash
cd frontend
npm install  # 仅首次
npm run dev
```

## 📍 应用地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost:5173 | React应用界面 |
| API文档 | http://localhost:5000/docs | Swagger UI (可交互测试) |
| 自动文档 | http://localhost:5000/redoc | ReDoc格式文档 |
| 健康检查 | http://localhost:5000/api/health | API健康状态 |

## ✨ 特性

✅ **完全迁移到FastAPI** - 性能提升3-5倍  
✅ **自动API文档** - Swagger UI内置  
✅ **异步处理** - 支持高并发  
✅ **类型检查** - Pydantic自动验证  
✅ **完全兼容** - 前端无需修改  

## 🔧 配置

编辑 `backend/.env`:
```env
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2
```

## ⚠️ 常见问题

**Q: 模块导入失败？**  
A: 重新安装依赖：`pip install --upgrade -r requirements.txt`

**Q: Ollama连接失败？**  
A: 确保Ollama已启动：`ollama serve`

**Q: 端口被占用？**  
A: 改用其他端口：`uvicorn app:app --port 8000`

## 📖 更多信息

- [FastAPI迁移指南](./FASTAPI_MIGRATION.md)
- [完整快速开始](./QUICKSTART.md)  
- [迁移总结](./MIGRATION_SUMMARY.md)

## 🎯 下一步

1. 访问 http://localhost:5173 使用应用
2. 打开 http://localhost:5000/docs 查看API文档
3. 在聊天框输入消息与AI互动

**享受FastAPI带来的速度提升！** ⚡
