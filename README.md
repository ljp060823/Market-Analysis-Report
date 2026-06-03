# 金融融资报告分析 Agent - 快速启动

## 1) 启动 Docker 依赖

在项目根目录执行：

```powershell
docker compose up -d mysql neo4j redis prometheus grafana
```

如需同时启动后端容器：

```powershell
docker compose up -d backend
```

如需同时启动 Celery：

```powershell
docker compose up -d celery_worker celery_beat
```

## 2) 本地启动后端（推荐开发模式）

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

## 3) 本地启动前端

```powershell
python -m pip install gradio requests httpx
python frontend/gradio_app.py
```

## 4) 健康检查

- 后端文档：`http://localhost:8000/docs`
- 前端页面：`http://localhost:7860`
- Grafana：`http://localhost:3000`
- Prometheus：`http://localhost:9090`

## 5) 已修复的关键问题

- 修复 `main.py` 导入不存在 `graph` 导致服务启动失败。
- 修复 `research` 接口请求体不匹配（前端 JSON 发送会 422）。
- 修复 JWT 依赖在开发环境无 token 时直接 401 的问题（开发模式允许匿名用户）。
- 修复 Redis 地址和 `.env` 路径硬编码，支持本地与 Docker 场景。
- 修复 Celery 中异步图调用方式错误导致任务执行失败。
- 修复 Dockerfile 中构建路径错误导致镜像无法构建。
