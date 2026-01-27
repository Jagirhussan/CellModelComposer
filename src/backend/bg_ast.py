import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class BGNode:
    name: str
    type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # --- ENHANCED SCHEMA v4.0 ---
    ports: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constitutive_laws: List[Dict[str, Any]] = field(default_factory=list)

    # System Properties: The "Meta-Physics"
    system_properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "ports": self.ports,
            "variables": self.variables,
            "constitutive_laws": self.constitutive_laws,
            "system_properties": self.system_properties,
            "parameters": self.parameters, # Keep as dict for internal state
            "metadata": self.metadata      # Keep as dict for internal state
        }

    @staticmethod
    def from_dict(data: Dict):
        # We handle parameters/metadata carefully if they are JSON strings or dicts
        params = data.get("parameters", {})
        if isinstance(params, str): params = json.loads(params)
        
        meta = data.get("metadata", {})
        if isinstance(meta, str): meta = json.loads(meta)

        return BGNode(
            name=data["name"],
            type=data["type"],
            id=data.get("id", str(uuid.uuid4())),
            parameters=params,
            metadata=meta,
            ports=data.get("ports", {}),
            variables=data.get("variables", {}),
            constitutive_laws=data.get("constitutive_laws", []),
            system_properties=data.get("system_properties", {})
        )

@dataclass
class BGBond:
    source_id: str
    target_id: str
    causal_stroke: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "causal_stroke": self.causal_stroke,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data: Dict):
        meta = data.get("metadata", {})
        if isinstance(meta, str): meta = json.loads(meta)
        return BGBond(
            source_id=data["source_id"],
            target_id=data["target_id"],
            causal_stroke=data.get("causal_stroke"),
            metadata=meta
        )

class BondGraphModel:
    def __init__(self, name: str, protein_id: str):
        self.name = name
        self.protein_id = protein_id
        self.nodes: Dict[str, BGNode] = {}
        self.bonds: List[BGBond] = []

    def add_node(self, node: BGNode):
        self.nodes[node.id] = node

    def add_bond(self, source_node: BGNode, target_node: BGNode, causal_stroke=None, metadata=None):
        if metadata is None:
            metadata = {}
        bond = BGBond(source_node.id, target_node.id, causal_stroke, metadata)
        self.bonds.append(bond)

    def to_json(self):
        # Legacy method returning string
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self):
        # New method for serialization
        return {
            "name": self.name,
            "protein_id": self.protein_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "bonds": [b.to_dict() for b in self.bonds]
        }

    @staticmethod
    def from_dict(data: Dict):
        model = BondGraphModel(name=data["name"], protein_id=data["protein_id"])
        
        # Rehydrate Nodes
        for n_data in data.get("nodes", []):
            node = BGNode.from_dict(n_data)
            model.add_node(node)
            
        # Rehydrate Bonds
        # Note: add_bond requires node objects, but BGBond stores IDs.
        # We can directly append BGBonds since we have the IDs.
        for b_data in data.get("bonds", []):
            bond = BGBond.from_dict(b_data)
            model.bonds.append(bond)
            
        return model