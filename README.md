# Market-Analysis-Report

市场分析智能 Agent，基于 LangGraph 多智能体架构，自动采集市场数据、构建知识图谱、生成结构化市场分析报告。

## 系统架构

采用与 Financing-Report-Agent 相同的多智能体协作框架，专注于市场领域分析：

- **数据采集层**: Bocha Web Search API 实时获取市场信息
- **知识图谱层**: Neo4j 存储市场实体关系（公司、行业、产品、市场）
- **推理分析层**: LangGraph 驱动的多阶段推理流水线
- **报告生成层**: 自动生成结构化市场分析报告

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | LangGraph + LangChain |
| 后端 | FastAPI + Uvicorn |
| 知识图谱 | Neo4j |
| 关系数据库 | MySQL |
| 缓存/消息队列 | Redis + Celery |
| 外部数据源 | Bocha Web Search API（https://open.bochaai.com/） |
| 前端 | Gradio（可选，也可直接用 FastAPI HTML） |
| 监控 | Prometheus + Grafana |

## 快速开始

### 1. 启动基础服务

```bash
docker compose up -d mysql neo4j redis prometheus grafana
```

### 2. 启动后端

```bash
conda activate agent
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 启动 Celery Worker

```bash
conda activate agent
cd backend
celery -A app.celery_app.celery_app worker -l info
```

### 4. 启动前端（可选）

```bash
conda activate agent
cd frontend
python gradio_app.py
```

或直接访问 `http://localhost:8000` 使用内嵌 HTML 界面。

## 环境变量

```bash
BOCHA_API_KEY=your-bocha-api-key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
MYSQL_URI=mysql+aiomysql://user:password@localhost:3306/数据库名
REDIS_URL=redis://localhost:6379/0
```

## 核心特性

- 自动化市场信息采集与结构化分析
- Neo4j 知识图谱存储市场实体与关系
- Celery 异步任务队列处理长时分析任务
- Prometheus + Grafana 全链路监控
- 支持 Gradio 可视化界面或 FastAPI 内嵌页面
