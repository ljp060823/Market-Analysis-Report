# Market-Analysis-Report

市场分析智能 Agent，基于 LangGraph 多智能体协作架构，自动采集市场新闻与行业数据，构建企业知识图谱，生成结构化市场分析报告（PDF 导出）。

## 系统架构

```
用户输入研究主题（如"特斯拉上海工厂产能"）
            ↓
    ┌──────────────┐
    │  Researcher   │ ← Bocha API 实时新闻/网页搜索
    └──────┬───────┘
           ↓ (搜索失败则直接跳到 Finalizer)
    ┌──────────────┐
    │Graph Reasoner │ ← Neo4j 知识图谱实体关系推理
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │    Writer     │ ← 结构化报告生成
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │    Critic     │ ← 质量评审（最多 2 轮迭代）
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │  Finalizer    │ ← 最终报告输出
    └──────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph + LangChain |
| 后端 | FastAPI + Uvicorn |
| 知识图谱 | Neo4j 4.4 |
| 关系数据库 | MySQL 8.4（LangGraph Checkpoint） |
| 缓存 | Redis 7 |
| 异步任务 | Celery |
| 外部数据 | Bocha Web Search API |
| 前端 | 内嵌 HTML + Gradio（双模式） |
| 监控 | Prometheus + Grafana（自动 provision 面板） |
| 限流 | SlowAPI |
| 日志 | structlog |
| 报告导出 | WeasyPrint PDF |

## 快速开始

### 方式一：Docker Compose 一键部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 BOCHA_API_KEY 和 LLM_BASE_URL

# 启动全部服务
docker compose up -d
```

服务端口：

| 服务 | 端口 |
|------|------|
| 后端 API + 前端页面 | 8000 |
| Gradio 前端 | 7860 |
| MySQL | 3306 |
| Neo4j Web / Bolt | 7474 / 7687 |
| Redis | 6379 |
| Prometheus | 9090 |
| Grafana | 3000 |

访问 `http://localhost:8000` 直接使用。

### 方式二：本地开发

```bash
# 1. 启动基础服务
docker compose up -d mysql neo4j redis prometheus grafana

# 2. 安装依赖
cd backend && pip install -r requirements.txt

# 3. 配置环境变量
export BOCHA_API_KEY="your-key"
export LLM_BASE_URL="http://your-llm:8001/v1"
export MYSQL_URI="mysql+aiomysql://user:password@localhost:3306/aether_invest"
export NEO4J_URI="bolt://localhost:7687"
export REDIS_URI="redis://localhost:6379/0"

# 4. 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. 启动 Celery Worker（可选）
celery -A app.celery_app.celery_app worker -l info

# 6. 启动 Gradio 前端（可选）
cd frontend && python gradio_app.py
```

## 项目结构

```
Market-Analysis-Report/
├── backend/
│   ├── app/
│   │   ├── agents/              # 智能体节点
│   │   │   ├── researcher.py    # 信息采集（Bocha API 搜索）
│   │   │   ├── graph_reasoner.py# 知识图谱推理（Neo4j）
│   │   │   ├── writer.py        # 报告撰写
│   │   │   └── critic.py        # 质量评审
│   │   ├── graph/
│   │   │   ├── builder.py       # LangGraph 工作流编排
│   │   │   └── state.py         # Agent 状态定义
│   │   ├── routers/
│   │   │   └── research.py      # API 路由
│   │   ├── main.py              # FastAPI 入口
│   │   ├── tools.py             # 工具（Bocha 搜索、新闻爬取）
│   │   ├── db.py                # 数据库连接（MySQL/Neo4j/Redis）
│   │   ├── metrics.py           # Prometheus 指标
│   │   └── utils.py             # 日志（structlog）
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 内嵌 HTML 前端
│   ├── gradio_app.py            # Gradio 备选前端
│   ├── history.json             # 历史记录
│   └── Dockerfile
├── grafana/
│   ├── dashboards/              # Grafana 面板 JSON
│   └── provisioning/            # 自动 provision 配置
├── output/                      # 生成的报告样例（PDF）
├── docker-compose.yml
├── prometheus.yml
└── pyproject.toml
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 访问前端页面 |
| POST | `/api/research` | 提交研究任务 |
| GET | `/api/research/{task_id}` | 查询任务状态 |
| GET | `/metrics` | Prometheus 指标 |

## 输出示例

`output/` 目录下包含已生成的报告样例：

- `report_特斯拉上海工厂产能.pdf` — 市场分析报告
- `search_data_特斯拉上海工厂产能.pdf` — 搜索数据汇总

## 核心特性

- **多智能体协作**: Researcher → Graph Reasoner → Writer → Critic 流水线
- **实时数据**: Bocha API 采集最新市场新闻，时效性过滤（oneMonth）
- **知识图谱**: Neo4j 存储企业/行业/产品实体关系，支持图谱推理
- **迭代优化**: Critic 评审不通过自动重写，最多 2 轮
- **错误容错**: Researcher 搜索失败时跳过推理直接输出错误信息
- **全链路监控**: Prometheus 指标 + Grafana 自动 provision 面板
- **限流保护**: SlowAPI 滑动窗口限流
- **双前端**: 内嵌 HTML（零依赖）+ Gradio（可选）
- **PDF 导出**: WeasyPrint 生成结构化报告
- **Docker 一键部署**: docker compose up 即可运行
