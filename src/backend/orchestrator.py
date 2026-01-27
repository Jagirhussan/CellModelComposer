import os
import datetime
from typing import Optional
from agent_types import AgentResult
from bio_agents import (
    PromptDecompositionAgent, 
    RetrievalGenerationAgent,
    ModelCompositionAgent,
    ParameterAgent
)

class OR_LLM:
    """
    The Supervisory Orchestration Agent.
    Manages the state machine and HITL checkpoints.
    """
    def __init__(self):
        self.state = "IDLE"
        self.context = {
            "user_prompt": "",
            "spec": None,
            "components": None,      # List[BondGraphModel]
            "composite_model": None, # Dict with 'model' and 'code'
            "final_package": None,
            "reports": {}
        }
        
        # Instantiate Workers
        # Note: We don't need to pass model names here anymore because
        # the agents now instantiate their own internal legacy agents.
        self.agents = {
            "Decomposition": PromptDecompositionAgent(),
            "Retrieval": RetrievalGenerationAgent(),
            "Composition": ModelCompositionAgent(),
            "Parameters": ParameterAgent()
        }

    def start_pipeline(self, user_prompt: str) -> str:
        """Starts the workflow."""
        self.context["user_prompt"] = user_prompt
        self.state = "DECOMPOSING"
        return self.run_step()

    def run_step(self, user_feedback: str = None) -> AgentResult:
        """
        Executes the current step in the pipeline.
        """
        
        # --- STEP 1: DECOMPOSITION ---
        if self.state == "DECOMPOSING":
            print(">>> [OR_LLM] Dispatching to Decomposition Agent...")
            result = self.agents["Decomposition"].execute(self.context["user_prompt"])
            self.context["reports"]["decomposition"] = result.report_markdown
            
            if result.success:
                self.context["spec"] = result.data
                if result.needs_hitl and not user_feedback:
                    self.state = "HITL_1"
                    return result 
                
                self.state = "RETRIEVING"
                return self.run_step()
            else:
                return result

        # --- HITL CHECKPOINTS ---
        if self.state.startswith("HITL"):
            print(f">>> [OR_LLM] Received User Feedback: {user_feedback}")
            if self.state == "HITL_1": self.state = "RETRIEVING"
            elif self.state == "HITL_2": self.state = "COMPOSING"
            elif self.state == "HITL_3": self.state = "PARAMETRIZING"
            elif self.state == "HITL_4": self.state = "FINALIZING"
            return self.run_step()

        # --- STEP 2: RETRIEVAL ---
        if self.state == "RETRIEVING":
            print(">>> [OR_LLM] Dispatching to Retrieval Agent...")
            result = self.agents["Retrieval"].execute(self.context["spec"])
            self.context["reports"]["retrieval"] = result.report_markdown
            
            if result.success:
                self.context["components"] = result.data
                self.state = "COMPOSING"
                return self.run_step() # Auto-proceed for demo
            return result

        # --- STEP 3: COMPOSITION ---
        if self.state == "COMPOSING":
            print(">>> [OR_LLM] Dispatching to Composition Agent...")
            result = self.agents["Composition"].execute(
                self.context["components"], 
                self.context["spec"]
            )
            self.context["reports"]["composition"] = result.report_markdown
            
            if result.success:
                self.context["composite_model"] = result.data
                self.state = "PARAMETRIZING"
                return self.run_step()
            return result

        # --- STEP 4: PARAMETERS ---
        if self.state == "PARAMETRIZING":
            print(">>> [OR_LLM] Dispatching to Parameter Agent...")
            # Pass the code/model from composition
            result = self.agents["Parameters"].execute(self.context["composite_model"])
            self.context["reports"]["parameters"] = result.report_markdown
            self.context["final_package"] = result.data
            
            self.state = "FINALIZING"
            return self.run_step()

        # --- FINAL ASSEMBLY ---
        if self.state == "FINALIZING":
            final_report = self._generate_final_report()
            return AgentResult(True, self.context["final_package"], final_report)

        return AgentResult(False, None, "Unknown State")

    def _generate_final_report(self) -> str:
        return f"""
# Final System Deliverable
**Generated:** {datetime.datetime.now()}

## Executive Summary
The system successfully composed a model based on the prompt:
> "{self.context['user_prompt']}"

## Workflow Trace
1. **Decomposition:** Extracted {len(self.context['spec'].entities)} reservoirs.
2. **Retrieval:** Loaded {len(self.context['components'])} components.
3. **Composition:** Generated {len(self.context['composite_model']['code'])} bytes of Python code.

## Final Code
```python
{self.context['final_package']['code']}
```
"""