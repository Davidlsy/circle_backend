#!/usr/bin/env python3
"""
启动命令：
  python run.py

然后访问 http://localhost:8000/docs 查看交互式 API 文档（Swagger UI）
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # 开发环境：代码改动自动重载
        log_level="info",
    )
