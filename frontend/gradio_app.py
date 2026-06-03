import gradio as gr
import json
import httpx
import os
import tempfile
import asyncio
import re
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_history_entry(query, report, search_data, graph):
    records = load_history()
    records.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "report": report,
        "search_data": search_data,
        "graph": graph,
    })
    if len(records) > 50:
        records = records[-50:]
    save_history(records)

def get_history_dropdown():
    records = load_history()
    if not records:
        return gr.Dropdown(choices=[], label="选择历史记录")
    choices = [f"[{r['time']}] {r['query']}" for r in records]
    return gr.Dropdown(choices=choices, label="选择历史记录")

def load_history_by_index(evt: gr.SelectData):
    records = load_history()
    if not records:
        return "", "", ""
    idx = evt.index[0]
    if 0 <= idx < len(records):
        r = records[idx]
        return r["query"], r.get("report", ""), r.get("search_data", ""), r.get("graph", "")
    return "", "", ""

async def run_research(message: str, history, enable_news: bool):
    headers = {}
    if JWT_TOKEN:
        headers["Authorization"] = f"Bearer {JWT_TOKEN}"

    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})

    full_response = ""
    search_text = ""
    graph_text = ""
    report_text = ""

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/api/research/stream",
                json={"query": message, "enable_news": enable_news},
                headers=headers,
            ) as response:
                response.raise_for_status()
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode("utf-8", errors="ignore")
                    while "\n\n" in buffer:
                        line, buffer = buffer.split("\n\n", 1)
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                content = data.get("content", "")
                                full_response += content
                                if "搜索数据" in content:
                                    search_text += content
                                if "知识图谱数据" in content:
                                    graph_text += content
                                if "最终报告" in content or "评审意见" in content:
                                    report_text += content
                                history[-1]["content"] = full_response
                                yield history, "", "", "", gr.update(visible=False)
                            except Exception:
                                continue
    except Exception as e:
        full_response = f"连接后端失败: {e}"
        history[-1]["content"] = full_response
        yield history, full_response, "", "", gr.update(visible=False)
        return

    add_history_entry(message, report_text or full_response, search_text, graph_text)
    yield history, report_text or full_response, search_text, graph_text, gr.update(visible=True)


def sanitize(text):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text.strip()

async def generate_pdf_click(report_content: str, search_content: str, graph_content: str):
    if not report_content.strip() and not search_content.strip() and not graph_content.strip():
        return gr.update(visible=False), None, None

    headers = {}
    if JWT_TOKEN:
        headers["Authorization"] = f"Bearer {JWT_TOKEN}"

    files = []

    sections = [
        ("report", report_content, "研究报告"),
        ("search_data", search_content + "\n\n" + graph_content, "搜索与图谱数据"),
    ]

    for key, content, title in sections:
        if not content.strip():
            files.append(None)
            continue
        safe_content = sanitize(content)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/generate-pdf",
                json={"report_content": safe_content, "filename": f"{key}.pdf", "title": title},
                headers=headers,
            )
        if resp.status_code == 200:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{key}.pdf")
            tmp.write(resp.content)
            tmp.close()
            files.append(tmp.name)
        else:
            files.append(None)

    has_any = any(f is not None for f in files)
    return gr.update(visible=has_any), files[0], files[1]


with gr.Blocks(title="市场分析Agent") as demo:
    gr.HTML("""
    <div class="main-header">
        <h1>市场分析 Agent</h1>
        <p>多源数据采集 · 智能分析 · 报告生成</p>
    </div>
    """)

    with gr.Tabs():
        with gr.Tab("研究分析"):
            report_state = gr.State("")
            search_state = gr.State("")
            graph_state = gr.State("")

            chatbot = gr.Chatbot(height=450, elem_classes="chatbot")
            msg_input = gr.Textbox(
                label="研究主题",
                placeholder="输入公司名、行业或事件，例如：比亚迪最新融资动态",
                lines=2,
            )

            with gr.Row():
                news_checkbox = gr.Checkbox(label="启用新闻爬取", value=False)
                submit_btn = gr.Button("开始分析", variant="primary")
                clear_btn = gr.Button("清空对话")

            with gr.Row(visible=False) as pdf_row:
                generate_pdf_btn = gr.Button("导出 PDF")
                pdf_report = gr.File(label="研究报告", visible=False)
                pdf_search = gr.File(label="搜索与图谱数据", visible=False)

            gr.Examples(
                examples=[
                    ["比亚迪最新融资动态"],
                    ["阿里巴巴集团2024年财报分析"],
                    ["宁德时代电池技术专利"],
                    ["特斯拉上海工厂产能"],
                ],
                inputs=[msg_input],
            )

        with gr.Tab("历史记录"):
            history_dropdown = gr.Dropdown(label="选择历史记录", interactive=False)
            history_query = gr.Textbox(label="查询主题", interactive=False)
            history_report = gr.Textbox(label="研究报告", lines=10, interactive=False)
            history_search = gr.Textbox(label="搜索数据", lines=8, interactive=False)
            history_graph = gr.Textbox(label="知识图谱数据", lines=6, interactive=False)

    submit_btn.click(
        fn=run_research,
        inputs=[msg_input, chatbot, news_checkbox],
        outputs=[chatbot, report_state, search_state, graph_state, pdf_row],
        show_progress="hidden",
    )

    msg_input.submit(
        fn=run_research,
        inputs=[msg_input, chatbot, news_checkbox],
        outputs=[chatbot, report_state, search_state, graph_state, pdf_row],
        show_progress="hidden",
    )

    generate_pdf_btn.click(
        fn=generate_pdf_click,
        inputs=[report_state, search_state, graph_state],
        outputs=[pdf_row, pdf_report, pdf_search],
    )

    clear_btn.click(
        fn=lambda: ([], "", "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)),
        outputs=[chatbot, report_state, search_state, graph_state, pdf_row, pdf_report, pdf_search],
    )

    demo.load(fn=get_history_dropdown, outputs=[history_dropdown])
    history_dropdown.select(fn=load_history_by_index, outputs=[history_query, history_report, history_search, history_graph])

    gr.HTML('<div class="footer">市场分析 Agent v1.0</div>')

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css="""
            .main-header {
                text-align: center;
                padding: 20px 0;
                background: #fff;
                border-bottom: 1px solid #e5e7eb;
                margin-bottom: 0;
            }
            .main-header h1 {
                font-size: 1.5em;
                font-weight: 600;
                color: #111827;
                margin: 0;
                letter-spacing: 0.5px;
            }
            .main-header p {
                font-size: 0.85em;
                color: #6b7280;
                margin: 4px 0 0;
            }
            .gradio-container {
                max-width: 960px !important;
            }
            .chatbot {
                border-radius: 8px !important;
                border: 1px solid #e5e7eb !important;
            }
            .footer {
                text-align: center;
                padding: 10px 0;
                color: #9ca3af;
                font-size: 0.75em;
            }
        """,
    )
