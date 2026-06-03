from langgraph.graph import StateGraph, END, START
from app.graph.state import AgentState
from app.agents.researcher import researcher_node
from app.agents.graph_reasoner import graph_reasoner_node
from app.agents.writer import writer_node
from app.agents.critic import critic_node
from app.db import get_checkpointer

async def finalizer_node(state: AgentState):
    final_report = state.get("final_report") or state.get("draft") or ""
    research_results = state.get("research_results", "")
    if isinstance(research_results, str) and research_results.startswith("研究阶段出错"):
        final_report = research_results
    return {
        "final_report": final_report,
        "messages": [{"role": "assistant", "content": final_report}]
    }

MAX_ITERATIONS = 2

def should_continue(state: AgentState):
    if int(state.get("iteration", 0)) >= MAX_ITERATIONS:
        return "finalizer"
    return "writer"

def after_researcher(state: AgentState):
    research_results = state.get("research_results", "")
    if isinstance(research_results, str) and research_results.startswith("研究阶段出错"):
        return "finalizer"
    return "graph_reasoner"

graph_builder = StateGraph(AgentState)
graph_builder.add_node("researcher", researcher_node)
graph_builder.add_node("graph_reasoner", graph_reasoner_node)
graph_builder.add_node("writer", writer_node)
graph_builder.add_node("critic", critic_node)
graph_builder.add_node("finalizer", finalizer_node)

graph_builder.add_edge(START, "researcher")
graph_builder.add_conditional_edges("researcher", after_researcher, {
    "graph_reasoner": "graph_reasoner",
    "finalizer": "finalizer",
})
graph_builder.add_edge("graph_reasoner", "writer")
graph_builder.add_edge("writer", "critic")
graph_builder.add_conditional_edges("critic", should_continue, {"writer": "writer", "finalizer": "finalizer"})
graph_builder.add_edge("finalizer", END)

async def build_graph():
    checkpointer = await get_checkpointer()
    graph = graph_builder.compile(checkpointer=checkpointer)
    return graph
