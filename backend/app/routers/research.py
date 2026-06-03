from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.celery_app import redis_client, run_full_pipeline
from app.tools import generate_pdf
from app.utils import verify_jwt
import uuid
import os

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class ResearchRequest(BaseModel):
    query: str

class GeneratePDFRequest(BaseModel):
    type: str = "report"
    report: str = ""
    search_data: str = ""
    query: str = ""
    filename: str = ""

@router.post("/research")
@limiter.limit("10/minute")
async def start_research(request: Request, body: ResearchRequest, token: str = Depends(verify_jwt)):
    user_id = token
    thread_id = str(uuid.uuid4())
    task = run_full_pipeline.delay(body.query, user_id, thread_id)
    redis_client.setex(f"thread_task:{thread_id}", 7200, task.id)
    return {"task_id": task.id, "thread_id": thread_id}

@router.post("/research/generate_pdf")
async def generate_pdf_endpoint(body: GeneratePDFRequest):
    output_dir = "/data/Market Analysis Report/output"
    os.makedirs(output_dir, exist_ok=True)

    if body.type == "report":
        content = body.report or "暂无报告内容"
        filename = f"report_{body.query[:20]}.pdf" if body.query else "report.pdf"
    else:
        content = body.search_data or "暂无搜索数据"
        filename = f"search_data_{body.query[:20]}.pdf" if body.query else "search_data.pdf"

    filepath = os.path.join(output_dir, filename)
    result = generate_pdf.func(content, filepath)

    if os.path.exists(filepath):
        return {"pdf_url": f"/api/files/{filename}", "filename": filename}

    fallback = filepath.replace(".pdf", ".txt")
    if os.path.exists(fallback):
        return {"pdf_url": f"/api/files/{filename.replace('.pdf', '.txt')}", "filename": filename.replace('.pdf', '.txt')}

    return {"error": result}

@router.get("/files/{filename}")
async def serve_file(filename: str):
    filepath = os.path.join("/data/Market Analysis Report/output", filename)
    if os.path.exists(filepath):
        ext = os.path.splitext(filename)[1]
        media_type = "application/pdf" if ext == ".pdf" else "text/plain"
        return FileResponse(filepath, filename=filename, media_type=media_type)
    return {"error": "File not found"}
