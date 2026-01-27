import os
import json
import time
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
import google.generativeai as genai

# Local Imports
from cellml_loader import CellMLLoader
from bg_ast import BondGraphModel, BGNode, BGBond
from llm_cache import CachedGenAIModel, RateLimiter
from app_config import config

load_dotenv()

# Setup Gemini Global Config
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Warning: GOOGLE_API_KEY not found. LLM features will be disabled.")
else:
    genai.configure(api_key=api_key)

# --- Runtime Converter ---
def convert_cellml_to_bg_ast(filepath: str, protein_name: str) -> BondGraphModel:
    loader = CellMLLoader()
    data = loader.parse_file(filepath)
    model = BondGraphModel(name=f"{protein_name}_Model", protein_id=protein_name)
    
    for comp_name, comp_data in data['components'].items():
        params = {}
        for var_name, var_data in comp_data['variables'].items():
            if var_data.get('initial_value'):
                try: params[var_name] = float(var_data['initial_value'])
                except: params[var_name] = var_data['initial_value']

        node = BGNode(
            name=comp_name,
            type="CellMLComponent", 
            parameters=params,
            variables={}, 
            constitutive_laws=[],
            system_properties={}, # Initialize empty
            metadata={
                "equations": comp_data.get('equations', []), 
                "structured_equations": comp_data.get('structured_equations', []),
                "variables": comp_data.get('variables', {})
            }
        )
        model.add_node(node)

    node_map = {n.name: n for n in model.nodes.values()}
    for con in data['connections']:
        c1, c2 = con['c1'], con['c2']
        if c1 in node_map and c2 in node_map:
            model.add_bond(node_map[c1], node_map[c2], metadata={"variable_map": con.get('vars', [])})
            
    return model

class LibraryBuilder:
    """
    Scans CellML files and uses an LLM to annotate them with 
    DEEP THERMODYNAMICS + VARIABLE SEMANTICS + LAWS + SYSTEM PROPERTIES.
    """
    def __init__(self):
        self.loader = CellMLLoader()
        self.registry = {}
        self.model_name = config.get("llm_models", "annotation") 
        # CachedGenAIModel handles rate limiting internally now
        self.model = CachedGenAIModel(self.model_name)
        
        self.library_dir = config.get("paths", "data_dir", "data")
        self.registry_file = config.get("paths", "registry_file", "data/library_registry.json")

        self._load_registry()

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    self.registry = json.load(f)
                print(f"--- Loaded existing registry with {len(self.registry)} entries ---")
            except Exception as e:
                print(f"   [Warning] Could not load registry: {e}")
                self.registry = {}
        else:
            self.registry = {}

    def _save_registry(self):
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            print(f"   [Error] Failed to save registry: {e}")

    def build_library(self):
        print(f"--- Starting Full Semantic Ingestion (Model: {self.model_name}) ---",flush=True)
        
        if not os.path.exists(self.library_dir):
            print(f"Error: Data directory '{self.library_dir}' not found.")
            return

        model_files = []
        for root, dirs, files in os.walk(self.library_dir):
            for file in files:
                if file.endswith(".cellml") and not file.startswith("units") and not file.startswith("param") and not file.startswith("constant") and not file.startswith("ion"):
                    model_files.append(os.path.join(root, file))

        print(f"Found {len(model_files)} candidate models.",flush=True)

        for fpath in model_files:
            filename = os.path.basename(fpath)
            protein_id = filename.replace("BG_", "").replace(".cellml", "")

            # Re-ingest if version < 4.0 (System Properties Update)
            if protein_id in self.registry:
                if "semantic_version" in self.registry[protein_id] and self.registry[protein_id]["semantic_version"] >= 4.0:
                    print(f"   [Skip] {protein_id} is up to date (v4.0).")
                    continue

            try:
                self._ingest_model(fpath, protein_id)
                self._save_registry()
            except Exception as e:
                print(f"   [Error] Failed to ingest {fpath}: {e}")

        print(f"--- Registry sync complete. Saved to {self.registry_file} ---")

    def _ingest_model(self, fpath: str, protein_id: str):
        print(f"\nProcessing: {protein_id} ({os.path.basename(fpath)})",flush=True)

        data = self.loader.parse_file(fpath)
        
        all_equations = []
        all_variables = {}
        
        for comp_name, comp_data in data['components'].items():
            struct_eqs = comp_data.get('structured_equations', [])
            if struct_eqs:
                for eq in struct_eqs:
                    all_equations.append(f"{eq['lhs']} = {eq['rhs']}")
            else:
                all_equations.extend(comp_data.get('equations', []))
            
            for v, props in comp_data.get('variables', {}).items():
                all_variables[v] = props.get('units', 'unknown')

        semantic_metadata = self._annotate_with_llm(protein_id, all_equations, all_variables)
        
        if not semantic_metadata:
            print(f"   [Skipping] Could not annotate {protein_id}")
            return

        entry = {
            "filepath": fpath,
            "semantic_version": 4.0,
            "description": semantic_metadata.get("description", "No description"),
            "keywords": semantic_metadata.get("keywords", []),
            "global_constants": semantic_metadata.get("global_constants", {}),
            "ports": semantic_metadata.get("ports", {}),
            "variables": semantic_metadata.get("variables", {}), 
            "constitutive_laws": semantic_metadata.get("constitutive_laws", []),
            "system_properties": semantic_metadata.get("system_properties", {}), # NEW: Meta-Physics
            "parameters": semantic_metadata.get("parameters", [])
        }
        
        self.registry[protein_id] = entry
        print(f"   [Success] Registered {len(entry['ports'])} ports, timescale: {entry['system_properties'].get('timescale', 'unknown')}.")

    def _annotate_with_llm(self, protein_id: str, equations: list, variables: dict) -> Dict[str, Any]:
        # self.rate_limiter.wait() <-- Removed
        
        limit = config.get("ingestion", "context_window_equations", 60)
        context_eqs = equations[:limit]
        
        prompt = f"""
        You are an Expert Biophysicist specializing in Bond Graph Modeling.
        
        ## Task
        Perform a **Full Semantic Audit** of the model "{protein_id}".
        Annotate Ports, Internal Variables, Constitutive Laws, AND **System Properties**.
        
        ## Input Context
        Variables: {json.dumps(variables, indent=2)}
        Equations: {context_eqs}
        
        ## 1. Ontology Resolution (OPB, CHEBI, GO)
        Use standard IDs: OPB:00592 (Voltage), OPB:00340 (J/mol), OPB:00425 (Conc), CHEBI:29101 (Na), etc.
        
        ## 2. Interface Analysis (Ports)
        - Identify external connections.
        - Context: Stoichiometry (2.0), Direction (positive_in).
        
        ## 3. Internal Variable Analysis
        - Roles: state, rate, constitutive_parameter, intermediate.
        - Semantic Match: Tag known concepts (e.g. E_rev).
        
        ## 4. Equation Analysis (Constitutive Laws)
        - Classify math: Ohmic, GHK, MassAction, Hill.
        - Bond Graph Type: Re, Ce, Se, Sf.
        
        ## 5. System Properties Analysis (CRITICAL FOR SIMULATION)
        - **Timescale:** Analyze time units and rate constants. Is this 'fast' (microseconds/milliseconds) or 'slow' (minutes/hours)?
        - **Power Scaling:** Analyze the Units of the Ports.
            - If Voltage is mV and Current is pA, Power is femtowatts (1e-15).
            - If Voltage is V and Current is A, Power is Watts (1).
            - State the implied power units.
        - **Linearity:** Are the equations linear differential equations or nonlinear?
        
        ## Output Format (Strict JSON)
        {{
            "description": "...",
            "global_constants": {{ "T": "310 K" }},
            "system_properties": {{
                "timescale": "milliseconds",
                "linearity": "nonlinear",
                "power_scale": "femtowatts",
                "domain": "electrophysiology"
            }},
            "ports": {{ ... }},
            "variables": {{ ... }},
            "constitutive_laws": [ ... ]
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            return self._extract_json(response.text)
        except Exception as e:
            print(f"   [LLM Error] {e}")
            return None

    def _extract_json(self, text: str) -> Dict:
        match = re.search(r"```\w*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                text = text[start:end]

        text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
        try:
            return json.loads(text.strip())
        except Exception as e:
            print(f"   [Parser Error] Could not extract JSON: {e}")
            return None

if __name__ == "__main__":
    builder = LibraryBuilder()
    builder.build_library()