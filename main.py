"""AI数字人对话应用 — 入口点"""
import uvicorn


def main():
    uvicorn.run("backend.app:app", host="0.0.0.0", port=5000, reload=False)


if __name__ == "__main__":
    main()
