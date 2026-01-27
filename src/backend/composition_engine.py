import uuid
import json
import re
from typing import List, Dict, Any, Tuple
from bg_ast import BondGraphModel, BGNode, BGBond

class CompositionEngine:
    """
    Stitches Bond Graph ASTs together using SEMANTIC ONTOLOGY MATCHING.
    v4.3: Deep Variable Search + v4.0 Schema Support.
    """
    def __init__(self):
        self.unified_model = BondGraphModel(name="Unified_Cell_Model", protein_id="System")
        self.reservoirs: List[Dict] = []
        self.component_instances: Dict[str, BGNode] = {}
        self.log_buffer: List[str] = []

    def log(self, message: str):
        """Captures logs for frontend display and prints them to stdout."""
        self.log_buffer.append(message)
        print(message)

    def create_scaffold(self, scaffold_defs: List[Dict]):
        self.log(f"   [Composition] Building Ontology Scaffold...")
        for domain in scaffold_defs:
            dom_id = domain.get('id', f"Scaffold_{uuid.uuid4().hex[:8]}")
            
            semantics = {
                "physics_id": domain.get('physics_id'),
                "entity_id": domain.get('entity_id'),
                "location_id": domain.get('location_id'),
                "entity_label": domain.get('entity_label', 'Unknown'),
                "location_label": domain.get('location_label', 'Unknown')
            }

            junction = BGNode(
                name=dom_id,
                type="0_junction",
                metadata={
                    "domain": dom_id,
                    "semantics": semantics
                }
            )
            self.unified_model.add_node(junction)
            
            self.reservoirs.append({
                "node_id": junction.id,
                "name": dom_id,
                "semantics": semantics
            })
            
            self.log(f"      -> Created Reservoir: {dom_id} ({semantics['entity_label']} @ {semantics['location_label']})")

    def add_component(self, component_model: BondGraphModel, instance_id: str):
        self.log(f"   [Composition] Instantiating: {component_model.protein_id} as {instance_id}")
        
        # 1. Clone Nodes & Build Instance Map
        instance_nodes = []
        id_map = {}
        
        for node in component_model.nodes.values():
            new_name = f"{instance_id}_{node.name}"
            new_node = BGNode(
                name=new_name,
                type=node.type,
                parameters=node.parameters,
                metadata=node.metadata,
                ports=node.ports,
                variables=node.variables,
                constitutive_laws=node.constitutive_laws,
                system_properties=node.system_properties
            )
            self.unified_model.add_node(new_node)
            id_map[node.id] = new_node.id
            instance_nodes.append(new_node)

        # 2. Clone Internal Bonds
        for bond in component_model.bonds:
            if bond.source_id in id_map and bond.target_id in id_map:
                new_bond = BGBond(
                    source_id=id_map[bond.source_id],
                    target_id=id_map[bond.target_id],
                    causal_stroke=bond.causal_stroke,
                    metadata=bond.metadata
                )
                self.unified_model.bonds.append(new_bond)

        # 3. SEMANTIC RESOLUTION (Deep Search)
        # Find the node that carries the Semantic Port Definitions (Metadata Node)
        # Note: This might NOT be the node that calculates the variables (Compute Node).
        port_def_node = None
        for node in instance_nodes:
            if node.ports:
                port_def_node = node
                break

        if not port_def_node:
            self.log(f"      [Warning] No ports found on {instance_id}")
            return

        for port_key, port_def in port_def_node.ports.items():
            if not isinstance(port_def, dict): continue

            # A. Resolve Port Semantics & Variable Name (v4.0 Schema Support)
            semantics = port_def.get('semantics', {})
            
            # Extract the Flow Variable (this is what drives the Scaffold Conservation)
            logical_flow_var = None
            if 'flow' in port_def and isinstance(port_def['flow'], dict):
                logical_flow_var = port_def['flow'].get('variable')
            elif 'variable' in port_def: # Legacy Fallback
                logical_flow_var = port_def['variable']
            else:
                logical_flow_var = port_key # Desperate Fallback

            # B. Deep Variable Search
            # Find which node in this instance actually computes this variable.
            actual_source_node = port_def_node
            actual_var_name = logical_flow_var
            found_computation = False

            # Helper: Check if node computes variable
            def computes_var(n: BGNode, v_name: str) -> bool:
                if not v_name: return False
                # Check structured equations LHS
                for eq in n.metadata.get('structured_equations', []):
                    if eq['lhs'] == v_name: return True
                return False

            # Search 1: Exact Name Match across all nodes in instance
            for n in instance_nodes:
                if computes_var(n, logical_flow_var):
                    actual_source_node = n
                    actual_var_name = logical_flow_var
                    found_computation = True
                    break
            
            # Search 2: Heuristic Match (If LLM hallucinated a variable name like 'I_mem_total')
            if not found_computation:
                self.log(f"      [Heuristic] '{logical_flow_var}' not found. Searching for candidate fluxes in {instance_id}...")
                candidates = []
                for n in instance_nodes:
                    # Look for computed variables that look like fluxes
                    computed_vars = [eq['lhs'] for eq in n.metadata.get('structured_equations', []) if eq.get('type') != 'ode']
                    for cv in computed_vars:
                        # Current/Flux Heuristics
                        is_flux_name = cv.startswith('I_') or cv.startswith('i_') or cv.startswith('v_') or cv.startswith('J_')
                        if is_flux_name:
                             candidates.append((n, cv))
                
                # Filter candidates based on Port Type
                if candidates:
                    # If Electrical, prefer I_ or i_
                    if 'voltage' in port_key.lower() or 'electrical' in port_key.lower() or 'membrane' in port_key.lower():
                        elec_cands = [c for c in candidates if c[1].startswith('I') or c[1].startswith('i')]
                        if elec_cands:
                            actual_source_node, actual_var_name = elec_cands[0]
                            found_computation = True
                    # If Chemical, prefer v_ or J_
                    elif not found_computation:
                         # Take the first reasonable flux
                         actual_source_node, actual_var_name = candidates[0]
                         found_computation = True

            # C. Ontology Matching
            match = self._find_compatible_reservoir(semantics)
            if not match:
                match = self._heuristic_fallback(port_key, actual_var_name or port_key, semantics)

            if match:
                reservoir_node_id = match['node_id']
                reservoir_name = match['name']
                
                # D. Create Bond from ACTUAL Source Node
                # This ensures the generated code uses the node that actually has the equation.
                bond_meta = {
                    "connection_type": "scaffold_link",
                    "port_name": port_key,
                    "component_variable": actual_var_name, # The variable that exists in equations
                    "scaffold_id": reservoir_name,
                    "semantics": semantics
                }
                
                if found_computation:
                    self.log(f"      -> Wired '{actual_var_name}' (from {actual_source_node.name}) to '{reservoir_name}'")
                else:
                    self.log(f"      -> Wired '{port_key}' (Logic Only) to '{reservoir_name}' [Warning: Variable not found]")

                ext_bond = BGBond(
                    source_id=actual_source_node.id,
                    target_id=reservoir_node_id,
                    metadata=bond_meta
                )
                self.unified_model.bonds.append(ext_bond)
            else:
                self.log(f"      [Unresolved] '{port_key}' - No match found.")

    def _find_compatible_reservoir(self, port_semantics: Dict) -> Dict:
        """
        STRICT Semantic Matching. Returns None if uncertain.
        """
        p_phys = port_semantics.get('physics_id')
        p_entity = port_semantics.get('entity_id')
        p_loc = port_semantics.get('location_id')
        
        if not p_phys: return None # Strict Mode: No physics ID = No strict match

        if p_entity == "null": p_entity = None
        
        for res in self.reservoirs:
            r_sem = res['semantics']
            r_phys = r_sem.get('physics_id')
            r_entity = r_sem.get('entity_id')
            r_loc = r_sem.get('location_id')
            if r_entity == "null": r_entity = None

            if p_phys and r_phys and p_phys != r_phys: continue
            if p_loc and r_loc and p_loc != r_loc: continue
            
            is_electrical = (p_phys == "OPB:00592")
            if not is_electrical:
                if p_entity != r_entity: continue
            else:
                if p_entity and r_entity and p_entity != r_entity: continue

            return res
        return None

    def _heuristic_fallback(self, port_name: str, var_name: str, semantics: Dict) -> Dict:
        """
        Fallback logic for when Semantic Tags are missing.
        Uses variable naming conventions to guess connections.
        """
        name_str = (str(port_name) + "_" + str(var_name)).lower()
        
        for res in self.reservoirs:
            r_sem = res['semantics']
            r_ent = r_sem.get('entity_label', '').lower()
            r_loc = r_sem.get('location_label', '').lower()
            r_phys = r_sem.get('physics_id')
            
            # 1. Voltage / Potential
            if "voltage" in name_str or "potential" in name_str or "v_mem" in name_str:
                if r_phys == "OPB:00592": # Match Electrical Reservoir
                    return res

            # 2. Sodium
            if "sodium" in name_str or "na" in name_str:
                if "sodium" in r_ent or "na" in r_ent:
                    # Check location
                    if "extra" in name_str or "_o" in name_str:
                        if "extra" in r_loc: return res
                    elif "intra" in name_str or "_i" in name_str:
                        if "cytosol" in r_loc or "intra" in r_loc: return res

            # 3. Glucose
            if "glucose" in name_str or "glc" in name_str:
                if "glucose" in r_ent:
                    if "extra" in name_str or "_o" in name_str:
                        if "extra" in r_loc: return res
                    elif "intra" in name_str or "_i" in name_str:
                        if "cytosol" in r_loc or "intra" in r_loc: return res
        return None

    def export_system(self):
        return self.unified_model