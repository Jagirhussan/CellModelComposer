import json
import re
import os
import subprocess
from typing import Dict, Any, List
from langgraph.types import Command, interrupt
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig 
from dotenv import load_dotenv

# Import Agents
from bio_agents import (
    PromptDecompositionAgent,
    RetrievalGenerationAgent,
    ModelCompositionAgent,
    ParameterResearchAgent,
    AnalystReportingAgent
)
from bg_ast import BondGraphModel
from graph_state import AgentState
from agent_types import BiologicalSpec

load_dotenv()

# --- Helper: Node.js Bridge (Deprecated for TikZ, kept if needed later) ---
def render_tikz_to_svg(tikz_code: str) -> str:
    # This function is no longer used for the primary workflow as we switched to Mermaid.
    # It remains here only as a fallback or for legacy support.
    return None

# --- Nodes ---

def planner_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    print("--- [Node] Planner: Decomposing Request ---")
    api_key = state.get("api_key") or config.get("configurable", {}).get("api_key")
    
    agent = PromptDecompositionAgent(api_key=api_key)
    result = agent.execute(state["user_request"])
    
    if not result.success:
        return {"messages": [f"Planning Failed: {result.report_markdown}"], "simulation_status": "failure", "planner_thoughts": result.thoughts}
    
    spec_data = result.data.__dict__.copy() if hasattr(result.data, '__dict__') else result.data
    if "mechanisms" in spec_data:
        spec_data["components"] = spec_data["mechanisms"]
    
    return {"spec": spec_data, "messages": [result.report_markdown], "components": [], "generated_code": None, "planner_thoughts": result.thoughts}

def retriever_node(state: AgentState) -> Dict[str, Any]:
    print("--- [Node] Retriever: Searching Library ---")
    api_key = state.get("api_key")
    agent = RetrievalGenerationAgent(api_key=api_key)
    
    spec_data = state["spec"]
    if isinstance(spec_data, dict):
        valid_keys = BiologicalSpec.__annotations__.keys()
        clean_spec = {k: v for k, v in spec_data.items() if k in valid_keys}
        spec = BiologicalSpec(**clean_spec)
    else:
        spec = spec_data
        
    result = agent.execute(spec)
    
    if not result.success:
        return {"messages": [f"Retrieval Failed: {result.report_markdown}"], "simulation_status": "failure", "physicist_thoughts": result.thoughts}
    
    components_serialized = [c.to_dict() for c in result.data]
    
    generated_components = []
    for c in result.data:
        is_theoretical = False
        comp_data = {}
        for node in c.nodes.values():
            if node.type == "TheoreticalComponent":
                is_theoretical = True
                comp_data = {
                    "id": node.name,
                    "description": "Theoretically derived component.",
                    "ports": node.ports,
                    "parameters": node.parameters,
                    "structured_equations": node.metadata.get("structured_equations", []),
                    "variables": node.variables
                }
                break
        if is_theoretical:
            generated_components.append(comp_data)
            
    physicist_output = {"generated_components": generated_components}

    return {
        "components": components_serialized, 
        "physicist_output": physicist_output, 
        "messages": [result.report_markdown],
        "physicist_thoughts": result.thoughts
    }

def composer_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    print("--- [Node] Composer: Stitching Models ---")
    
    api_key = state.get("api_key") or config.get("configurable", {}).get("api_key")
    
    component_objects = [BondGraphModel.from_dict(c) for c in state["components"]]
    agent = ModelCompositionAgent(api_key=api_key)
    
    spec_data = state["spec"]
    if isinstance(spec_data, dict):
        valid_keys = BiologicalSpec.__annotations__.keys()
        clean_spec = {k: v for k, v in spec_data.items() if k in valid_keys}
        spec = BiologicalSpec(**clean_spec)
    else:
        spec = spec_data
        
    result = agent.execute(component_objects, spec, state["user_request"])
    
    if not result.success:
        return {"messages": [f"Composition Failed: {result.report_markdown}"], "simulation_status": "failure"}
    
    composite_model_dict = result.data['model']
    unit_audit = result.data.get('unit_audit', [])
    
    # We now use Mermaid which is already in 'model_dict["mermaid"]' 
    # and populated by the LLM in bio_agents.py if enhancement succeeded.
    # No backend rendering required.
    
    return {
        "composite_model": composite_model_dict, 
        "generated_code": result.data['code'], 
        "composer_logs": result.data.get('logs', ''),
        "messages": [result.report_markdown],
        "composer_thoughts": result.thoughts, # <--- Added Composer Thoughts
        "unit_audit_log": unit_audit # <--- New Unit Audit Log
    }

def parameter_researcher_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    print("--- [Node] Researcher: Analyzing Data ---")
    api_key = state.get("api_key") or config.get("configurable", {}).get("api_key")
    
    agent = ParameterResearchAgent(api_key=api_key)
    result = agent.execute(state["user_request"], state["generated_code"], state["composite_model"])
    
    if not result.success: return {"messages": [f"Research Failed: {result.report_markdown}"], "curator_thoughts": result.thoughts}
    
    curator_data = result.data.get('curator_data', {})
    
    return {
        "generated_code": result.data['code'], 
        "curator_output": curator_data, 
        "messages": [result.report_markdown],
        "curator_thoughts": result.thoughts
    }

def analyst_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    print(f"--- [Node] Analyst: Critical Review (Attempt {state.get('analyst_attempts', 0) + 1}) ---")
    api_key = state.get("api_key") or config.get("configurable", {}).get("api_key")
    
    agent = AnalystReportingAgent(api_key=api_key)
    
    user_request = state.get("user_request", "")
    spec = state.get("spec", {})
    code = state.get("generated_code", "")
    curator_data = state.get("curator_output", {})
    
    result = agent.execute(user_request, spec, code, curator_data)
    
    status = "success"
    if not result.success:
        status = "failure"
        report = f"# Analysis Failed\n\nError: {result.report_markdown}"
    else:
        report = result.data

    try: 
        compile(code, "<string>", "exec")
    except Exception as e:
        status = "failure"
        report += f"\n\n## ⚠️ Code Compilation Error\n`{str(e)}`"

    return {
        "simulation_report": report, 
        "simulation_status": status, 
        "analyst_attempts": state.get("analyst_attempts", 0) + 1, 
        "messages": ["Analyst Review Complete."],
        "analyst_thoughts": result.thoughts
    }

def human_help_node(state: AgentState) -> Dict[str, Any]:
    return {"messages": ["# System Alert\n\nEscalated to human."]}