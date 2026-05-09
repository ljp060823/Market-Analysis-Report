# Market-Analysis-Report
市场分析agent

外部服务api：https://open.bochaai.com/

# 1. Docker 服务（MySQL、Neo4j、Redis、Prometheus、Grafana）
cd "/data/Market Analysis Report"
docker compose up -d mysql neo4j redis prometheus grafana

# 2. FastAPI 后端
source /root/miniconda3/etc/profile.d/conda.sh && conda activate agent
cd "/data/Market Analysis Report/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Celery Worker（新终端）
source /root/miniconda3/etc/profile.d/conda.sh && conda activate agent
cd "/data/Market Analysis Report/backend"
celery -A app.celery_app.celery_app worker -l info

# 4. Gradio 前端（新终端）
source /root/miniconda3/etc/profile.d/conda.sh && conda activate agent
cd "/data/Market Analysis Report/frontend"
python gradio_app.py   ##可选 改善为fastapi html本地8000端口直接访问
