import json
import re
import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph_state import AgentState
from graph_nodes import (
    planner_node,
    retriever_node,
    composer_node,
    parameter_researcher_node,
    analyst_node,
    human_help_node
)

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("composer", composer_node)
    builder.add_node("researcher", parameter_researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("human_help", human_help_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "composer")
    builder.add_edge("composer", "researcher")
    builder.add_edge("researcher", "analyst")

    def should_continue(state: AgentState):
        status = state.get("simulation_status")
        attempts = state.get("analyst_attempts", 0)
        
        if status == "success": return END
        if attempts < 3: return "researcher" 
        return "human_help"

    builder.add_conditional_edges(
        "analyst",
        should_continue,
        {
            END: END,
            "researcher": "researcher",
            "human_help": "human_help"
        }
    )

    memory = MemorySaver()
    
    # UPDATED: Added "researcher" and "analyst" to interrupts for step-by-step progression
    graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["retriever", "composer", "researcher", "analyst"]
    )
    
    return graph