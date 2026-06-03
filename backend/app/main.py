from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers.research import limiter, router as research_router
from app.metrics import concurrent_requests
from app.utils import logger
import json
from app.graph.builder import build_graph
from prometheus_client import generate_latest
import os

app = FastAPI(title="financial agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(research_router, prefix="/api")

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")

@app.get("/")
async def serve_frontend():
    html_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

@app.middleware("http")
async def monitor_concurrency(request: Request, call_next):
    concurrent_requests.inc()
    try:
        return await call_next(request)
    finally:
        concurrent_requests.dec()

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/api/research/stream")
async def research_stream(request: Request):
    body = await request.json()
    query = body.get("query", "")
    enable_news = body.get("enable_news", False)
    enable_graph = body.get("enable_graph", True)
    enable_financial = body.get("enable_financial", False)
    enable_deep = body.get("enable_deep", False)
    NL = "\n"

    async def event_generator():
        try:
            graph = await build_graph()
            config = {"configurable": {"thread_id": "stream"}}

            initial_state = {
                "messages": [("human", query)],
                "enable_news": enable_news,
                "enable_graph": enable_graph,
                "enable_financial": enable_financial,
                "enable_deep": enable_deep,
            }

            async for event in graph.astream(
                initial_state,
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    if node_name == "researcher":
                        raw = node_output.get("raw_search_results", "")
                        summary = node_output.get("research_results", "")
                        if raw:
                            text = f"{NL}🔍 搜索数据：{NL}{raw}{NL}"
                            yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                        if summary:
                            text = f"{NL}📝 搜索摘要：{NL}{summary}{NL}"
                            yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                    elif node_name == "graph_reasoner":
                        graph_result = node_output.get("graph_results", "")
                        if graph_result:
                            text = f"{NL}🧠 知识图谱数据：{NL}{graph_result}{NL}"
                            yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                    elif node_name == "writer":
                        draft = node_output.get("draft", "")
                        if draft:
                            text = f"{NL}✍️ 报告草稿：{NL}{draft[:300]}{'...' if len(draft) > 300 else ''}{NL}"
                            yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                    elif node_name == "critic":
                        critique = node_output.get("critique", "")
                        if critique:
                            text = f"{NL}🔎 评审意见：{NL}{critique}{NL}"
                            yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                    elif node_name == "finalizer":
                        msgs = node_output.get("messages", [])
                        for msg in msgs:
                            if isinstance(msg, dict):
                                text = msg.get("content", "")
                            elif hasattr(msg, "content"):
                                text = str(msg.content)
                            else:
                                text = str(msg)
                            if text:
                                text = f"{NL}📄 最终报告：{NL}{text}{NL}"
                                yield f"data: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'content': f'{NL}✅ 研究完成'}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("stream_error", error=str(exc))
            yield f"data: {json.dumps({'content': f'{NL}❌ 错误: {exc}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
