import os
import uuid
import re
from lxml import etree
from typing import Dict, List, Any, Tuple
import numpy as np # Added for safety in linearization check

MATHML_NS = "http://www.w3.org/1998/Math/MathML"
XLINK_NS = "http://www.w3.org/1999/xlink"

class CellMLLoader:
    """
    A robust CellML parser (supports 1.0 and 1.1).
    Returns structured equation data (LHS, RHS, Type) to avoid regex parsing later.
    """
    
    def __init__(self):
        self.components = {} 
        self.connections = [] 
        self.parsed_files = set()
        self.cellml_ns = "http://www.cellml.org/cellml/1.1#" 

    def parse_file(self, filepath: str):
        abs_path = os.path.abspath(filepath)
        self._parse_recursive(abs_path)
        return {
            "components": self.components,
            "connections": self.connections
        }

    def _parse_recursive(self, filepath: str):
        print(f"[Cellml loader] parsing {filepath}")
        if filepath in self.parsed_files: return
        self.parsed_files.add(filepath)

        if not os.path.exists(filepath):
            print(f"Warning: Import file not found: {filepath}")
            return

        try:
            tree = etree.parse(filepath)
            root = tree.getroot()
            if 'http://www.cellml.org/cellml/1.0#' in root.tag:
                self.cellml_ns = "http://www.cellml.org/cellml/1.0#"
            else:
                self.cellml_ns = "http://www.cellml.org/cellml/1.1#"
        except Exception as e:
            print(f"Error parsing XML {filepath}: {e}")
            return

        ns_map = {'c': self.cellml_ns, 'm': MATHML_NS, 'xlink': XLINK_NS}

        for imp in root.findall('.//c:import', namespaces=ns_map):
            href = imp.get(f"{{{XLINK_NS}}}href")
            if href:
                imp_path = os.path.join(os.path.dirname(filepath), href)
                self._parse_recursive(os.path.abspath(imp_path))

        for comp in root.findall('.//c:component', namespaces=ns_map):
            self._parse_component(comp, ns_map)

        for conn in root.findall('.//c:connection', namespaces=ns_map):
            self._parse_connection(conn, ns_map)

    def _parse_component(self, comp_elem, ns_map):
        name = comp_elem.get('name')
        if not name: return

        if name not in self.components:
            self.components[name] = {
                'variables': {},
                'equations': [], # Legacy support
                'structured_equations': [] # Stores dicts {'lhs':..., 'rhs':..., 'type': 'ode'|'algebraic'}
            }
        
        for var in comp_elem.findall('c:variable', namespaces=ns_map):
            v_name = var.get('name')
            self.components[name]['variables'][v_name] = {
                'units': var.get('units'),
                'initial_value': var.get('initial_value'),
                'public_interface': var.get('public_interface')
            }

        for math in comp_elem.findall('.//m:math', namespaces=ns_map):
            self._extract_structured_equations(math, self.components[name]['structured_equations'])

    def _parse_connection(self, conn_elem, ns_map):
        map_comp = conn_elem.find('c:map_components', namespaces=ns_map)
        if map_comp is not None:
            c1 = map_comp.get('component_1')
            c2 = map_comp.get('component_2')
            
            var_maps = []
            for map_var in conn_elem.findall('c:map_variables', namespaces=ns_map):
                v1 = map_var.get('variable_1')
                v2 = map_var.get('variable_2')
                if v1 and v2:
                    var_maps.append((v1, v2))
            
            if c1 and c2:
                self.connections.append({'c1': c1, 'c2': c2, 'vars': var_maps})

    def _extract_structured_equations(self, math_elem, storage_list):
        """
        Extracts equations and classifies them immediately as ODE or Algebraic.
        """
        for child in math_elem:
            if not isinstance(child.tag, str): continue
            if child.tag.endswith('apply'):
                try:
                    op_tag = child[0].tag.split('}')[-1]
                    
                    # 1. Differential Equation: <eq> <diff> <bvar>... </diff> <rhs>... </eq>
                    if op_tag == 'eq' and len(child) > 1:
                        lhs_elem = child[1]
                        
                        # Check if LHS is a diff
                        if len(lhs_elem) > 0 and lhs_elem.tag.endswith('apply'):
                            lhs_op = lhs_elem[0].tag.split('}')[-1]
                            if lhs_op == 'diff':
                                # ODE Found!
                                # Structure: apply(diff, bvar, target_var)
                                # target_var is usually the 2nd argument (child index 2)
                                if len(lhs_elem) >= 3:
                                    target_var = self._linearize_mathml(lhs_elem[2])
                                    rhs = self._linearize_mathml(child[2], is_root=True)
                                    
                                    if target_var and rhs:
                                        storage_list.append({
                                            'type': 'ode',
                                            'lhs': target_var,
                                            'rhs': rhs
                                        })
                                    continue

                    # 2. Algebraic Equation: <eq> <ci>lhs</ci> <rhs>... </eq>
                    if op_tag == 'eq':
                        lhs_str = self._linearize_mathml(child[1])
                        rhs_str = self._linearize_mathml(child[2], is_root=True)
                        
                        # Safety check: ensure LHS is a valid variable name
                        if lhs_str and rhs_str and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', lhs_str):
                            storage_list.append({
                                'type': 'algebraic',
                                'lhs': lhs_str,
                                'rhs': rhs_str
                            })

                except Exception as e:
                    # Robustness: Skip malformed equations instead of crashing
                    pass

    def _linearize_mathml(self, element, is_root=False):
        if not isinstance(element.tag, str): return ""
        tag = element.tag.split('}')[-1]
        
        if tag == 'ci': return element.text.strip() if element.text else ""
        if tag == 'cn': return element.text.strip() if element.text else "0"
        if tag == 'true': return "True"
        if tag == 'false': return "False"
        if tag == 'pi': return "np.pi"
        if tag == 'exponentiale': return "np.e"
        if tag == 'infinity': return "np.inf"
        
        if tag == 'apply':
            children = [c for c in element if isinstance(c.tag, str)]
            if not children: return ""
            op_tag = children[0].tag.split('}')[-1]
            args = [self._linearize_mathml(c, is_root=False) for c in children[1:]]
            args = [a for a in args if a] # Filter empty args
            
            # Operators
            if op_tag == 'eq': return f"{args[0]} = {args[1]}" if is_root else f"{args[0]} == {args[1]}"
            if op_tag == 'plus': return f"({' + '.join(args)})"
            if op_tag == 'minus': return f"({args[0]} - {args[1]})" if len(args) > 1 else f"-{args[0]}"
            if op_tag == 'times': return f"({' * '.join(args)})"
            if op_tag == 'divide': return f"({args[0]} / {args[1]})"
            
            # Logic
            if op_tag == 'and': return f"({' and '.join(args)})"
            if op_tag == 'or': return f"({' or '.join(args)})"
            if op_tag == 'xor': return f"({' != '.join(args)})"
            if op_tag == 'not': return f"(not {args[0]})"
            if op_tag == 'lt': return f"({args[0]} < {args[1]})"
            if op_tag == 'gt': return f"({args[0]} > {args[1]})"
            if op_tag == 'leq': return f"({args[0]} <= {args[1]})"
            if op_tag == 'geq': return f"({args[0]} >= {args[1]})"
            
            # Math
            if op_tag == 'power': return f"np.power({args[0]}, {args[1]})"
            if op_tag == 'root': return f"np.sqrt({args[1]})"
            if op_tag == 'abs': return f"np.abs({args[0]})"
            if op_tag == 'exp': return f"np.exp({args[0]})"
            if op_tag == 'ln': return f"np.log({args[0]})"
            if op_tag == 'log': return f"np.log10({args[0]})"
            if op_tag == 'floor': return f"np.floor({args[0]})"
            if op_tag == 'ceiling': return f"np.ceil({args[0]})"
            if op_tag == 'sin': return f"np.sin({args[0]})"
            if op_tag == 'cos': return f"np.cos({args[0]})"
            if op_tag == 'tan': return f"np.tan({args[0]})"
            
            return f"{op_tag}({', '.join(args)})"

        if tag == 'piecewise':
            pieces = element.findall(f'{{{MATHML_NS}}}piece')
            otherwise = element.find(f'{{{MATHML_NS}}}otherwise')
            cond_pairs = []
            for piece in pieces:
                children = [c for c in piece if isinstance(c.tag, str)]
                if len(children) >= 2:
                    val = self._linearize_mathml(children[0])
                    cond = self._linearize_mathml(children[1])
                    cond_pairs.append((val, cond))
            res = "0.0"
            if otherwise is not None:
                children = [c for c in otherwise if isinstance(c.tag, str)]
                if children: res = self._linearize_mathml(children[0])
            for val, cond in reversed(cond_pairs):
                res = f"({val} if {cond} else {res})"
            return res

        return ""