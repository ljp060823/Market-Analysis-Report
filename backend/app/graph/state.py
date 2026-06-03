from typing import TypedDict, Annotated, List
from typing_extensions import NotRequired
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    research_results: NotRequired[List[dict]]
    raw_search_results: NotRequired[str]
    news_results: NotRequired[str]
    graph_results: NotRequired[str]
    draft: NotRequired[str]
    critique: NotRequired[str]
    iteration: NotRequired[int]
    final_report: NotRequired[str]
    final_pdf_path: NotRequired[str | None]
    human_feedback: NotRequired[str | None]
    user_id: NotRequired[str]
    enable_news: NotRequired[bool]
    enable_graph: NotRequired[bool]
    enable_hitl: NotRequired[bool]
    enable_deep: NotRequired[bool]