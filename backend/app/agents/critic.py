from langchain_openai import ChatOpenAI
from app.metrics import record_llm_usage
from app.db import settings

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key="EMPTY",
    model="/data/Qwen2.5-14B-Instruct",
    temperature=0.3,
    max_tokens=512,
)

async def critic_node(state):
    draft = state.get("draft", "")
    prompt = f"""你是资深报告审阅专家。用3-5条简洁要点指出以下报告的不足和改进方向，每条不超过30字：

{draft}"""

    try:
        critique = await llm.ainvoke(prompt)
        critique_text = critique.content
        if hasattr(critique, "usage") and critique.usage:
            record_llm_usage(
                tokens=critique.usage.total_tokens,
                model="/data/Qwen2.5-14B-Instruct"
            )
    except Exception as exc:
        critique_text = f"评审阶段降级输出（LLM不可用）: {exc}"

    next_iteration = int(state.get("iteration", 0)) + 1
    final_report = f"{draft}\n\n---\n评审意见：\n{critique_text}"
    return {
        "critique": critique_text,
        "iteration": next_iteration,
        "final_report": final_report,
        "messages": [{"role": "assistant", "content": critique_text}],
    }
