from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator
from agent_types import BiologicalSpec

class AgentState(TypedDict):
    """
    Represents the state of the Semantic Bond Graph Architect workflow.
    """
    # Metadata
    project_name: str 
    project_notes: str
    user_request: str
    user_id: str
    api_key: str
    
    # --- Workflow Data ---
    
    # Step 1: Architect Output
    spec: Optional[BiologicalSpec]
    planner_thoughts: str # Raw thoughts from decomposition
    
    # Step 2: Physicist Output
    components: List[Dict[str, Any]] # Raw internal data
    physicist_output: Optional[Dict[str, Any]] # UI-formatted data (Step2Data)
    physicist_thoughts: str # Raw thoughts from equation generation

    # Step 3: Composer Output
    composite_model: Optional[Dict[str, Any]]
    generated_code: Optional[str]
    composer_logs: Optional[str] # Detailed logs from the composition engine
    composer_thoughts: str # Raw thoughts from the composer LLM
    unit_audit_log: Optional[List[str]] # NEW: Log of unit conversions performed by the LLM

    # Step 4: Curator Output
    curator_output: Optional[Dict[str, Any]] # UI-formatted data (Step3Data)
    curator_thoughts: str # Raw thoughts from parameter research
    
    # Step 5: Analyst Output
    simulation_report: str
    analyst_thoughts: str # Raw thoughts/reasoning from analyst
    simulation_status: str  # "pending", "success", "failure"
    analyst_attempts: int
    
    # Standard LangGraph message history
    messages: Annotated[List[str], operator.add]