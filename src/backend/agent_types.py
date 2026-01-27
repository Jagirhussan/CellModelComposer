from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json

@dataclass
class AgentResult:
    """
    Standardized output for all agents.
    """
    success: bool
    data: Any  # The structural payload (JSON, AST, Code, etc.)
    report_markdown: str  # The human-readable report
    needs_hitl: bool = False
    hitl_questions: List[str] = field(default_factory=list)
    thoughts: str = "" # Raw LLM thought process/output

@dataclass
class BiologicalSpec:
    """
    Output of the Prompt Decomposition Agent.
    Updated to match the v2 Prompt output structure (pres.txt) and system prompt.
    """
    # Core Fields (Legacy Mappings)
    intent_summary: str # Maps to 'model_name'
    entities: List[Dict[str, Any]]  # Maps to 'compartments'
    mechanisms: List[Dict[str, Any]] # Maps to 'components'
    constraints: List[str] # Maps to 'domains'
    
    # Enhanced Metadata (v2 Schema Support)
    model_name: str = "Unknown Model"
    explanation: str = ""
    next_step_context: str = ""
    match_matrix: Dict[str, Any] = field(default_factory=dict)
    mermaid_source: str = ""
    missing_components: List[str] = field(default_factory=list)

    def to_json(self):
        return json.dumps(self.__dict__, indent=2, default=lambda o: str(o))

@dataclass
class ComponentStatus:
    """
    Track provenance of model parts.
    """
    component_id: str
    status: str  # "Found", "Generated", "Missing"
    source: str  # Library ID or "LLM-Synthesized"
    validation_notes: str = ""

@dataclass
class ParameterEvidence:
    """
    Evidence for a specific parameter.
    """
    param_name: str
    value: float
    units: str
    source_citation: str
    confidence: str # "High", "Medium", "Low/Prior"
    notes: str