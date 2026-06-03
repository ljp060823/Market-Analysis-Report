from langchain_openai import ChatOpenAI
from app.tools import neo4j_graph_reason
from app.metrics import record_llm_usage
from app.db import settings

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key="EMPTY",
    model="/data/Qwen2.5-14B-Instruct",
    temperature=0,
    max_tokens=64,
)

async def graph_reasoner_node(state):
    try:
        messages = state.get("messages", [])
        question_text = ""
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                question_text = str(last_msg.content)
            elif isinstance(last_msg, dict):
                question_text = str(last_msg.get("content", ""))
            else:
                question_text = str(last_msg)

        company = await llm.ainvoke(
            f"从以下文本中只输出公司名称，不要任何解释：{question_text}"
        )
        if hasattr(company, "usage") and company.usage:
            record_llm_usage(tokens=company.usage.total_tokens, model="/data/Qwen2.5-14B-Instruct")

        company_name = (company.content if hasattr(company, "content") else str(company)).strip()
        insight = await neo4j_graph_reason.coroutine(company_name)
        return {"graph_results": insight, "messages": [{"role": "assistant", "content": insight}]}
    except Exception as exc:
        fallback = f"图推理阶段降级输出（服务不可用）: {exc}"
        return {"graph_results": fallback, "messages": [{"role": "assistant", "content": fallback}]}
