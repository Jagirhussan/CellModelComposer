import json, os
import re
import ast
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque
import google.generativeai as genai

# Imported RateLimiter for compatibility, though explicit waiting is removed
from llm_cache import CachedGenAIModel, RateLimiter
from knowledge_base import LibrarianAgent
from library_builder import convert_cellml_to_bg_ast
from composition_engine import CompositionEngine
from bg_ast import BondGraphModel, BGNode 
from app_config import config
from agent_types import AgentResult, BiologicalSpec, ComponentStatus, ParameterEvidence
from prompt_manager import PromptManager

REGISTRY_FILE = config.get("paths", "registry_file", "data/library_registry.json")

# --- Helper Functions ---

def robust_extract_json(text: str) -> Optional[Dict]:
    """
    Robust extraction logic to find the LAST valid JSON block in the text.
    Handles double-encoded strings and template skipping.
    """
    if not text: return None

    # 0. PRE-PROCESSING: Handle Double-Encoded JSON Strings
    try:
        stripped = text.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            unwrapped = json.loads(text)
            if isinstance(unwrapped, str):
                text = unwrapped
    except:
        pass

    # 1. Regex Match for Markdown Code Blocks
    matches = re.findall(r"```\w*(.*?)```", text, re.DOTALL)
    
    candidates = []
    if matches:
        candidates = matches
    else:
        # Fallback: Find outermost braces
        s = text.find('{')
        e = text.rfind('}') + 1
        if s != -1 and e != -1:
            candidates.append(text[s:e])

    # Iterate REVERSE to find the last valid, non-template JSON block
    for match in reversed(candidates):
        clean_text = re.sub(r"^\s*//.*$", "", match, flags=re.MULTILINE)
        try:
            data = json.loads(clean_text.strip())
            
            # --- HEURISTIC 1: Check for Python Code Template ---
            if "python_code" in data:
                code_val = data["python_code"]
                if "complete, runnable Python code" in code_val or len(code_val) < 150:
                    continue
            
            if "draft_python_code" in data:
                code_val = data["draft_python_code"]
                if "complete, runnable Python code" in code_val or len(code_val) < 150:
                    continue

            # --- HEURISTIC 2: Check for Mermaid Template ---
            if "mermaid_code" in data:
                mermaid_val = data["mermaid_code"]
                if "complete Mermaid code" in mermaid_val or len(mermaid_val) < 20:
                    continue

            return data
        except:
            continue
            
    return None

class PromptDecompositionAgent:
    def __init__(self, api_key: str = None):
        self.model_name = config.get("llm_models", "planning")
        # CachedGenAIModel now handles rate limiting internally
        self.llm = CachedGenAIModel(self.model_name, api_key=api_key)
        self.registry = self._load_registry()

    def _load_registry(self):
        if os.path.exists(REGISTRY_FILE):
            with open(REGISTRY_FILE, 'r') as f: return json.load(f)
        return {}

    def execute(self, user_prompt: str) -> AgentResult:
        print(f"   [Decomposition] Analyzing prompt: {user_prompt}")
        library_context = []
        for pid in sorted(self.registry.keys()):
            data = self.registry[pid]
            desc = data.get('description', 'N/A')
            ports_summary = []
            for p_name, p_data in sorted(data.get('ports', {}).items()):
                sem = p_data.get('semantics', {})
                ports_summary.append(f"{p_name}({sem.get('entity_label', 'Unknown')}@{sem.get('location_label', 'Unknown')})")
            library_context.append(f"- ID: {pid}\n  Desc: {desc}\n  Ports: {', '.join(ports_summary)}")
        
        context_str = "\n".join(library_context)
        
        # Get SYSTEM instruction from manager
        system_instruction = PromptManager.get_bondgraph_system_instruction()
        
        # Construct USER message locally
        user_message = f"""### Available Library (Ontology-Tagged)
You may use the following components in your model. Refer to them by their 'ID'.
{context_str}

### User Query
{user_prompt}
"""

        try:
            # Pass separated system instruction
            response = self.llm.generate_content(user_message, system_instruction=system_instruction)
            blueprint = self._extract_json(response.text)
            if not blueprint: return AgentResult(False, None, "Failed to parse LLM response into JSON.", thoughts=getattr(response, 'thoughts', None))
            spec = self._create_spec_from_blueprint(blueprint)
            return AgentResult(True, spec, self._generate_report(spec), needs_hitl=False, thoughts=getattr(response, 'thoughts', None))
        except Exception as e:
            return AgentResult(False, None, f"Decomposition Error: {e}")

    def refine_plan(self, user_prompt: str, current_spec: Dict) -> AgentResult:
        print(f"   [Decomposition] Refining plan based on user feedback...")
        # Enforce sort_keys=True for deterministic prompting
        matrix_context = json.dumps(current_spec.get('match_matrix', {}), indent=2, sort_keys=True)
        previous_output = json.dumps(current_spec, indent=2, sort_keys=True)

        # Get SYSTEM instruction
        system_instruction = PromptManager.get_update_bondgraph_system_instruction()

        # Construct USER message
        user_message = f"""### Original User Query
{user_prompt}

### Previous Model Output
{previous_output}

### User's Updated Match Matrix (Confidence Scores)
{matrix_context}
"""
        try:
            response = self.llm.generate_content(user_message, system_instruction=system_instruction)
            blueprint = self._extract_json(response.text)
            if not blueprint: return AgentResult(False, None, "Failed to parse LLM response into JSON.", thoughts=getattr(response, 'thoughts', None))
            
            spec = self._create_spec_from_blueprint(blueprint)
            return AgentResult(True, spec, self._generate_report(spec), needs_hitl=False, thoughts=getattr(response, 'thoughts', None))
        except Exception as e:
            return AgentResult(False, None, f"Refinement Error: {e}")

    def _create_spec_from_blueprint(self, blueprint: Dict) -> BiologicalSpec:
        entities = []
        for c in blueprint.get('compartments', []):
            entity = {
                "id": c.get('id'),
                "entity_label": c.get('name'),
                "type": c.get('type'),
                "location_label": c.get('name'), 
                "semantics": c.get('ontology', {})
            }
            if 'ontology' in c and 'go' in c['ontology']:
                entity['location_id'] = c['ontology']['go']
            entities.append(entity)

        mechanisms = []
        for c in blueprint.get('components', []):
            mech = {
                "id": c.get('id'),
                "library_id": c.get('library_id'),
                "name": c.get('name'),
                "type": c.get('type'),
                "match_reason": c.get('library_match_reason'),
                "connections": c.get('connections', [])
            }
            mechanisms.append(mech)
        
        clean_mermaid = self._sanitize_mermaid(blueprint.get('mermaid_source', ""))

        return BiologicalSpec(
            intent_summary=blueprint.get('model_name', "Generated Model"),
            entities=entities,
            mechanisms=mechanisms,
            constraints=blueprint.get('domains', []),
            model_name=blueprint.get('model_name', "Unknown Model"),
            explanation=blueprint.get('explanation', ""),
            next_step_context=blueprint.get('next_step_context', ""),
            match_matrix=blueprint.get('match_matrix', {}),
            mermaid_source=clean_mermaid, 
            missing_components=blueprint.get('missing_components', [])
        )

    def _sanitize_mermaid(self, mermaid_code: str) -> str:
        """
        Robustly sanitizes Mermaid code to prevent rendering errors.
        Fixes common LLM issues like parentheses in IDs.
        """
        lines = mermaid_code.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Fix 1: Subgraph Definitions
            # Bad: subgraph Lumen (Apical) -> Good: subgraph Lumen_Apical ["Lumen (Apical)"]
            if stripped.startswith('subgraph '):
                # Check if there's a parenthesis in the ID part (before any bracket)
                # Regex matches: subgraph [spaces] (ID with spaces/parens) [optional brackets]
                match = re.match(r'subgraph\s+([a-zA-Z0-9_ ]+?\(.+?\))(\s*\[.*\])?', stripped)
                if match:
                    raw_id = match.group(1).strip()
                    safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', raw_id).strip('_')
                    
                    # If user already provided a label [..], use it, otherwise make one
                    label_part = match.group(2) if match.group(2) else f' ["{raw_id}"]'
                    
                    fixed_line = f"{line[:line.find('subgraph ')]}subgraph {safe_id}{label_part}"
                    fixed_lines.append(fixed_line)
                    continue

            fixed_lines.append(line)
        
        code = "\n".join(fixed_lines)

        # Fix 2: Quote Node IDs if they look like function calls or arrays
        def quote_if_needed(match):
            node_id = match.group(1)
            content = match.group(2)
            # If content has brackets [ or ] and is NOT surrounded by quotes, quote it.
            if ('[' in content or ']' in content) and not (content.startswith('"') and content.endswith('"')):
                content = content.replace('"', "'")
                return f'{node_id}("{content}")'
            return match.group(0)

        code = re.sub(r'([A-Za-z0-9_]+)\(([^)]+)\)', quote_if_needed, code)
        
        return code

    def _generate_report(self, spec: BiologicalSpec) -> str:
        report_parts = [f"# Model Plan: {spec.model_name}"]
        if spec.explanation: report_parts.append(f"## Analysis\n{spec.explanation}")
        if spec.mermaid_source: report_parts.append(f"## Topology Diagram\n```mermaid\n{spec.mermaid_source}\n```")
        return "\n\n".join(report_parts)

    def _extract_json(self, text: str) -> Dict:
        return robust_extract_json(text)

class RetrievalGenerationAgent:
    def __init__(self, api_key: str = None):
        self.librarian = LibrarianAgent(api_key=api_key)
        self.registry = self._load_registry()
        self.data_dir = config.get("paths", "data_dir", "data")
        self.model_name = config.get("llm_models", "coding")
        self.llm = CachedGenAIModel(self.model_name, api_key=api_key)

    def _load_registry(self):
        if os.path.exists(REGISTRY_FILE):
            with open(REGISTRY_FILE, 'r') as f: return json.load(f)
        return {}

    def _resolve_filepath(self, relative_path: str) -> str:
        if os.path.isabs(relative_path): return relative_path
        if self.data_dir.rstrip(os.sep).endswith("data") and relative_path.startswith("data/"):
            stripped = relative_path[5:] 
            return os.path.join(self.data_dir, stripped)
        return os.path.join(self.data_dir, relative_path)

    def execute(self, spec: BiologicalSpec) -> AgentResult:
        loaded = []
        status_list = []
        
        found_mechanisms = []
        missing_mechanisms = []
        
        for comp_def in spec.mechanisms:
            if comp_def.get('library_id'): found_mechanisms.append(comp_def)
            else: missing_mechanisms.append(comp_def)

        for comp_def in found_mechanisms:
            lib_id = comp_def.get('library_id')
            instance_id = comp_def.get('id', f"{lib_id}_inst")

            if lib_id in self.registry:
                entry = self.registry[lib_id]
                try:
                    raw_path = entry.get('filepath', '')
                    full_path = self._resolve_filepath(raw_path)
                    if not os.path.exists(full_path) and raw_path.startswith("data/"):
                         full_path_alt = os.path.join(self.data_dir, raw_path)
                         if os.path.exists(full_path_alt): full_path = full_path_alt
                    
                    ast_model = convert_cellml_to_bg_ast(full_path, lib_id)
                    self._inject_semantics_into_ast(ast_model, entry)
                    ast_model.instance_id_hint = instance_id 
                    loaded.append(ast_model)
                    status_list.append(ComponentStatus(instance_id, "Found", lib_id, f"Loaded from {os.path.basename(full_path)}"))
                except Exception as e:
                    status_list.append(ComponentStatus(instance_id, "Error", lib_id, str(e)))
            else:
                status_list.append(ComponentStatus(instance_id, "Missing", lib_id, "Not in registry"))

        synthesis_thoughts = ""
        if missing_mechanisms:
            print(f"   [Retrieval] Batch synthesizing {len(missing_mechanisms)} missing components...")
            try:
                system_context = self._extract_system_equations(loaded)
                theoretical_models, thoughts = self._synthesize_batch_theoretical_components(
                    missing_mechanisms, 
                    spec,
                    system_context
                )
                synthesis_thoughts = thoughts
                for model in theoretical_models:
                    loaded.append(model)
                    status_list.append(ComponentStatus(model.instance_id_hint, "Generated", "LLM", "Batch Synthesized."))
            except Exception as e:
                print(f"   [Error] Batch synthesis failed: {e}")
                synthesis_thoughts += f"\n\n[Error] Batch synthesis failed: {str(e)}"
        
        report = f"# Retrieval Report\nLoaded {len(loaded)} components."
        return AgentResult(True, loaded, report, thoughts=synthesis_thoughts)

    def _inject_semantics_into_ast(self, ast_model: BondGraphModel, registry_entry: Dict):
        if not ast_model.nodes: return
        target_node = list(ast_model.nodes.values())[0]
        for k in ['ports', 'variables', 'constitutive_laws', 'system_properties']:
            if k in registry_entry: setattr(target_node, k, registry_entry[k])

    def _extract_system_equations(self, loaded_models: List[BondGraphModel]) -> str:
        context_lines = []
        for model in loaded_models:
            context_lines.append(f"--- Component: {model.name} ---")
            for node in model.nodes.values():
                if hasattr(node, 'metadata') and 'variables' in node.metadata:
                    vars_str = ", ".join([f"{k} ({v.get('units', '')})" for k, v in node.metadata['variables'].items()])
                    if vars_str: context_lines.append(f"Variables: {vars_str}")
                if hasattr(node, 'metadata') and 'structured_equations' in node.metadata:
                    for eq in node.metadata['structured_equations']:
                        context_lines.append(f"Eq: {eq['lhs']} = {eq['rhs']}")
        return "\n".join(context_lines)

    def _synthesize_batch_theoretical_components(self, missing_defs: List[Dict], spec: BiologicalSpec, system_context: str) -> Tuple[List[BondGraphModel], str]:
        # self.rate_limiter.wait()  <-- Removed, handled by CachedGenAIModel
        spec_dict = spec.__dict__
        
        # Use new PromptManager signature
        sys_inst, user_msg = PromptManager.get_equation_generation_prompts(spec_dict, system_context, missing_defs)
        
        response = self.llm.generate_content(user_msg, system_instruction=sys_inst)
        data = self._extract_json(response.text)
        
        if not data or 'generated_components' not in data:
            raise ValueError("LLM failed to generate valid batch JSON.")
            
        models = []
        for comp_data in data['generated_components']:
            name = comp_data.get('id', 'Unknown')
            protein_id = name.replace(" ", "_")
            model = BondGraphModel(name=name, protein_id=protein_id)
            
            node = BGNode(
                name=protein_id,
                type="TheoreticalComponent",
                ports=comp_data.get('ports', {}),
                variables=comp_data.get('variables', {}),
                parameters=comp_data.get('parameters', {}),
                metadata={
                    "structured_equations": comp_data.get('structured_equations', []),
                    "variables": comp_data.get('variables', {})
                }
            )
            model.add_node(node)
            model.instance_id_hint = name
            models.append(model)
        
        return models, getattr(response, 'thoughts', response.text)

    def _extract_json(self, text: str) -> Dict:
        return robust_extract_json(text)

class ModelCompositionAgent:
    def __init__(self, api_key: str = None):
        self.model_name = config.get("llm_models", "coding")
        self.llm = CachedGenAIModel(self.model_name, api_key=api_key)

    def execute(self, components: List[BondGraphModel], spec: BiologicalSpec, user_request: str = "") -> AgentResult:
        print(f"   [Composer] Starting ALL-LLM Composition for: {user_request}")
        
        # Sort components to ensure deterministic prompt generation
        components.sort(key=lambda c: c.name)

        # 1. Flatten Components into Context String
        component_context = []
        
        for i, model in enumerate(components):
            instance_id = getattr(model, 'instance_id_hint', f"Comp_{i}")
            
            # Extract details from the first substantive node
            main_node = next(iter(model.nodes.values()), None)
            if not main_node: continue
            
            eqs = main_node.metadata.get('structured_equations', [])
            eq_str = "\n".join([f"    {e.get('lhs')} = {e.get('rhs')}" for e in eqs])
            
            params = main_node.parameters
            param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            
            # NOTE: Header format specifically designed for PromptManager regex
            context_block = f"""
            --- Component {i+1}: {model.name} (ID: {instance_id}) ---
            Type: {main_node.type}
            Equations:
            {eq_str}
            Parameters: {param_str}
            """
            component_context.append(context_block)
            
        full_context = "\n".join(component_context)
        spec_dict = spec.__dict__ if hasattr(spec, '__dict__') else spec

        # 2. PHASE 1: Draft Synthesis (Composition)
        # Use new PromptManager signature
        draft_sys, draft_user = PromptManager.get_composition_prompts(user_request, spec_dict, full_context)
        
        # self.rate_limiter.wait() <-- Removed, handled by CachedGenAIModel
        logs = ""
        mermaid_code = ""
        final_code = ""
        thoughts = ""
        unit_audit = []
        
        try:
            print("   [Composer] Phase 1: Drafting Code & Topology...")
            draft_response = self.llm.generate_content(draft_user, system_instruction=draft_sys)
            draft_data = self._extract_json(draft_response.text)
            
            if not draft_data:
                return AgentResult(False, None, "Composer Phase 1 failed: Invalid JSON response.")

            draft_code = draft_data.get("draft_python_code", "")
            unit_audit = draft_data.get("unit_audit_log", [])
            logs = draft_data.get("topology_summary", "Model composed.")
            mermaid_code = draft_data.get("mermaid_code", "") # Draft mermaid
            
            # 3. PHASE 2: Gatekeeping (Validation & Finalization)
            # Takes Draft Code -> Returns Validated Final Code + Final Mermaid
            print("   [Composer] Phase 2: Gatekeeper Validation...")
            
            # Use new PromptManager signature
            gate_sys, gate_user = PromptManager.get_bondgraph_diagram_prompts(user_request, spec_dict, draft_code)
            gatekeeper_response = self.llm.generate_content(gate_user, system_instruction=gate_sys)
            final_data = self._extract_json(gatekeeper_response.text)
            
            if final_data:
                # Overwrite with validated artifacts
                final_code = final_data.get("final_python_code", draft_code)
                mermaid_code = final_data.get("mermaid_source", mermaid_code)
                
                # Append validation report to logs
                val_report = final_data.get("validation_report", [])
                if val_report:
                    logs += "\n\n### Gatekeeper Validation:\n" + "\n".join([f"- {r}" for r in val_report])
                
                thoughts = getattr(gatekeeper_response, 'thoughts', "Gatekeeper validation complete.")
            else:
                # Fallback to draft if gatekeeper fails parsing
                final_code = draft_code
                logs += "\n\n[Warning] Gatekeeper failed to return structured data. Using Draft Code."

            # Cleanup Mermaid
            mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
            
            # Double Sanitization on Server Side
            # Fix: subgraph Lumen (Apical) -> subgraph Lumen_Apical ["Lumen (Apical)"]
            def fix_subgraph_ids(match):
                full_line = match.group(0)
                id_part = match.group(1)
                # Check if ID has parens
                if '(' in id_part:
                     safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', id_part).strip('_')
                     return f'subgraph {safe_id} ["{id_part}"]'
                return full_line

            mermaid_code = re.sub(r'subgraph\s+([a-zA-Z0-9_ ]+?\(.+?\))(?=\s|$|\[)', fix_subgraph_ids, mermaid_code)

        except Exception as e:
            return AgentResult(False, None, f"Composer Execution Error: {e}")

        # 4. Format Output
        if unit_audit:
            logs += "\n\n### Unit Audit Log\n" + "\n".join([f"- {u}" for u in unit_audit])

        model_dict = {
            "name": spec.model_name,
            "mermaid": mermaid_code,
            "description": logs
        }

        report = f"# Composition Complete\nGenerated {len(final_code)} bytes of simulation code.\n\n## Strategy\n{logs}"
        
        result_data = {
            "model": model_dict, 
            "code": final_code, 
            "logs": logs,
            "unit_audit": unit_audit
        }
        
        return AgentResult(True, result_data, report, thoughts=thoughts)

    def _extract_json(self, text: str) -> Dict:
        return robust_extract_json(text)

class ParameterAgent:
    def execute(self, final_package: Dict) -> AgentResult:
        code = final_package.get('code', '')
        unresolved_count = code.count("[Unresolved]")
        return AgentResult(True, final_package, f"# Parameter Report\nUnresolved: {unresolved_count}")

class ParameterResearchAgent:
    def __init__(self, api_key: str = None):
        self.model_name = config.get("llm_models", "research", "gemini-2.0-flash") 
        self.llm = CachedGenAIModel(self.model_name, api_key=api_key)
        self.api_key = api_key
        if self.api_key: genai.configure(api_key=self.api_key)
        try:
            # Compatibility check for new SDK structure vs old tools
            if hasattr(self.llm, 'real_model'):
                self.llm.real_model = genai.GenerativeModel(model_name=self.model_name, tools=[{"google_search": {}}])               
        except:
            pass # Graceful fallback if tools/SDK mismatch

    def execute(self, user_request: str, code: str, composite_model: Dict[str, Any]) -> AgentResult:
        if not code: return AgentResult(False, None, "No code provided.")
        print(f"   [Researcher] Analyzing Data...")
        
        # We pass the code itself as the primary source of 'components' now
        generated_components = self._extract_params_from_code_analysis(code)
        
        # Use new PromptManager signature with current_code
        sys_inst, user_msg = PromptManager.get_parameterization_prompts(
            user_request, 
            generated_components,
            current_code=code
        )
        
        try:
            response = self.llm.generate_content(user_msg, system_instruction=sys_inst)
            json_data = self._extract_json(response.text)
            
            # --- DATA MAPPING FOR NEW PROMPT SCHEMA ---
            # 1. Map conversion logic to notes and new_value to value
            if json_data and "parameter_set" in json_data:
                for param in json_data["parameter_set"]:
                    # Mapping for new_value -> value if value missing
                    if "new_value" in param and "value" not in param:
                        param["value"] = param["new_value"]

                    if "unit_conversion_logic" in param:
                        orig = param.get("original_value", "Unknown")
                        logic = param.get("unit_conversion_logic", "")
                        existing_notes = param.get("notes", "")
                        
                        new_note = f"[Unit Conversion] From {orig}: {logic}"
                        if existing_notes:
                            param["notes"] = f"{existing_notes} | {new_note}"
                        else:
                            param["notes"] = new_note
            
            return AgentResult(
                True, 
                {
                    "code": code,
                    "curator_data": json_data # Populates curator_output
                }, 
                response.text,
                thoughts=getattr(response, 'thoughts', response.text)
            )
        except Exception as e:
            return AgentResult(False, None, f"Research Failed: {str(e)}")

    def _extract_params_from_code_analysis(self, code: str) -> Dict[str, List[Dict]]:
        """
        Since we don't have a structured composite model anymore, we extract params 
        directly from the standardized 'params.get()' calls in the code.
        """
        import ast
        params_found = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'params':
                            # Found params.get('KEY')
                            if node.args:
                                arg = node.args[0]
                                if isinstance(arg, ast.Constant): key = arg.value
                                elif isinstance(arg, ast.Str): key = arg.s
                                else: continue
                                params_found.append(key)
        except:
            pass
            
        # Create a dummy component to hold these
        return {
            "generated_components": [{
                "id": "Global_Parameters",
                "parameters": {p: {"description": "Extracted from code", "units": "Unknown"} for p in set(params_found)}
            }]
        }

    def _extract_json(self, text: str) -> Dict:
        return robust_extract_json(text)

class AnalystReportingAgent:
    """
    Produces a comprehensive 'Validation Plan & Critical Analysis Report'.
    """
    def __init__(self, api_key: str = None):
        # Use a high-reasoning model for critical analysis
        self.model_name = config.get("llm_models", "annotation", "gemini-2.5-pro")
        self.llm = CachedGenAIModel(self.model_name, api_key=api_key)
        
        # Configure Google Search Tool
        if self.llm.api_key:
             genai.configure(api_key=self.llm.api_key)
             try:
                # Compatibility check for new SDK structure vs old tools
                if hasattr(self.llm, 'real_model'):
                    self.llm.real_model = genai.GenerativeModel(model_name=self.model_name, tools=[{"google_search": {}}])               
             except Exception as e:
                 print(f"   [Analyst] Warning: Could not enable Google Search: {e}")

    def execute(self, user_request: str, spec: Dict, code: str, curator_data: Dict) -> AgentResult:
        print(f"   [Analyst] Generating Critical Report...")
        
        # Safe fallback for missing data
        if not spec: spec = {}
        if not code: code = "# No code generated."
        if not curator_data: curator_data = {}

        # Use new PromptManager signature
        sys_inst, user_msg = PromptManager.get_analyst_report_prompts(user_request, spec, code, curator_data)
        
        try:
            response = self.llm.generate_content(user_msg, system_instruction=sys_inst)
            report_markdown = response.text
            return AgentResult(True, report_markdown, report_markdown, thoughts=getattr(response, 'thoughts', report_markdown))
        except Exception as e:
            return AgentResult(False, None, f"Analyst Reporting Failed: {str(e)}")