from langchain_openai import ChatOpenAI
from app.metrics import record_llm_usage
from app.db import settings

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key="EMPTY",
    model="/data/Qwen2.5-14B-Instruct",
    temperature=0.3,
    max_tokens=4096,
)

MAX_RAW_CHARS = 6000

async def writer_node(state):
    research_summary = state.get("research_results", "")
    raw_search = state.get("raw_search_results", "")
    graph_results = state.get("graph_results", "")
    enable_news = state.get("enable_news", False)
    enable_financial = state.get("enable_financial", False)
    enable_deep = state.get("enable_deep", False)

    if isinstance(research_summary, list):
        research_summary = "\n".join(
            str(m.content) if hasattr(m, "content") else str(m)
            for m in research_summary
        )
    else:
        research_summary = str(research_summary)

    raw_truncated = str(raw_search)
    if len(raw_truncated) > MAX_RAW_CHARS:
        raw_truncated = raw_truncated[:MAX_RAW_CHARS] + "\n...(已截断，保留关键数据)"

    financial_prompt = """
【财务分析要求】
- 盈利能力：毛利率、净利率、ROE、ROA
- 偿债能力：资产负债率、流动比率、速动比率
- 运营能力：应收账款周转率、存货周转率
- 成长能力：营收增长率、净利润增长率、EPS增长""" if enable_financial else ""

    depth_prompt = """
【深度分析要求】
- 行业基准对比：与同行业可比公司对比
- 估值参考：PE/PB/PS估值区间
- 催化剂与风险事件""" if enable_deep else ""

    prompt = f"""你是资深金融分析师，擅长撰写专业市场研究报告。根据以下资料撰写一份高质量的市场分析报告。

【原始搜索数据】
{raw_truncated}

【搜索摘要】
{research_summary}

【知识图谱数据】
{graph_results}

【报告格式要求】

## 一、执行摘要
- 核心观点与投资评级（买入/增持/中性/减持/卖出）
- 关键发现（3-5条）
- 目标价位与预期收益

## 二、公司/行业概况
- 主营业务与商业模式
- 市场地位与竞争壁垒
- 发展历程与重要里程碑

## 三、关键数据分析
- 财务指标分析（必须引用具体数字）
- 增长趋势与驱动因素
- 市场份额与行业地位
{financial_prompt}

## 四、竞争格局
- 主要竞争对手分析
- 竞争优势与护城河
- 行业集中度与进入壁垒

## 五、SWOT分析
- 优势（Strengths）：核心竞争力
- 劣势（Weaknesses）：内部短板
- 机会（Opportunities）：外部机遇
- 威胁（Threats）：潜在风险

## 六、风险因素
- 政策风险
- 市场风险
- 经营风险
- 技术风险

## 七、投资展望
- 未来6-12个月展望
- 催化剂与潜在事件
- 投资建议与风险提示
{depth_prompt}

【写作规范】
1. 用中文撰写，专业严谨，数据驱动
2. 每个部分至少2-3段，内容充实
3. 必须引用搜索数据中的具体数字、日期、事件
4. 使用专业金融术语，但保持可读性
5. 避免空泛描述，每句话都要有数据或事实支撑"""

    try:
        response = await llm.ainvoke(prompt)
        if hasattr(response, "usage") and response.usage:
            record_llm_usage(
                tokens=response.usage.total_tokens,
                model="/data/Qwen2.5-14B-Instruct"
            )
        return {"draft": response.content, "messages": [response]}
    except Exception as exc:
        draft = f"写作阶段降级输出（LLM不可用）\n\n研究摘要：{research_summary}\n\n错误：{exc}"
        return {"draft": draft, "messages": [{"role": "assistant", "content": draft}]}
