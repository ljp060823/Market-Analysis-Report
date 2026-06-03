from langchain_openai import ChatOpenAI
from app.tools import bocha_websearch_tool, news_scraper_tool
from app.metrics import record_llm_usage
from app.db import settings

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key="EMPTY",
    model="/data/Qwen2.5-14B-Instruct",
    temperature=0.3,
    max_tokens=4096,
)

MAX_SEARCH_CHARS = 5000

async def researcher_node(state):
    try:
        messages = state.get("messages", [])
        query = ""
        if messages:
            last = messages[-1]
            if hasattr(last, "content"):
                query = str(last.content)
            elif isinstance(last, dict):
                query = str(last.get("content", ""))
            elif isinstance(last, (list, tuple)):
                query = str(last[1]) if len(last) > 1 else str(last[0])
            else:
                query = str(last)

        enable_news = state.get("enable_news", False)

        raw_results = bocha_websearch_tool.func(query)

        if enable_news:
            try:
                news_raw = news_scraper_tool.func(query)
                if news_raw and "失败" not in news_raw and "未找到" not in news_raw:
                    raw_results = raw_results + "\n\n--- 扩展新闻数据 ---\n\n" + news_raw
            except Exception:
                pass

        truncated = raw_results
        if len(raw_results) > MAX_SEARCH_CHARS:
            truncated = raw_results[:MAX_SEARCH_CHARS] + "\n...(结果已截断)"

        prompt = f"""你是专业金融研究助手。根据以下搜索结果，提取关键数据并结构化整理。

用户问题：{query}

搜索结果：
{truncated}

要求：
1. 提取所有关键数据（数字、日期、事件、公司名称）
2. 按主题分类整理
3. 保留原始引用来源
4. 用中文回答，简洁专业"""

        response = await llm.ainvoke(prompt)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            record_llm_usage(
                tokens=response.usage_metadata.get("total_tokens", 0),
                model="/data/Qwen2.5-14B-Instruct"
            )

        summary = response.content if hasattr(response, "content") else str(response)
        return {
            "research_results": summary,
            "raw_search_results": raw_results,
            "messages": [{"role": "assistant", "content": summary}]
        }
    except Exception as exc:
        fallback = f"研究阶段出错: {exc}"
        return {
            "research_results": fallback,
            "raw_search_results": "",
            "messages": [{"role": "assistant", "content": fallback}]
        }
