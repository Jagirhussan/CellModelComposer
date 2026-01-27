import { Step1Data, Step2Data, Step3Data, DetailedLibraryModel } from './types';

export const INITIAL_STEP_1: Step1Data = {
  "model_name": "Epithelial Glucose Transport",
  "explanation": "This model represents the secondary active transport of glucose across a polarized epithelial cell. The analysis identified four key transport processes: 1) Apical Sodium-Glucose Cotransport (SGLT), 2) Basolateral facilitated glucose diffusion (GLUT), 3) Basolateral Na/K ATPase pumping to maintain the sodium gradient, and 4) Basolateral potassium leak for ion homeostasis.",
  "next_step_context": "The next agent must generate the system of differential equations. Use the library model 'SGLT1_ss_fast' for the 'Apical_SGLT' component and 'Kp' for the 'Basolateral_K_Leak' component.",
  "match_matrix": {
    "description": "Sparse confidence scores.",
    "rows": [
      "An01", "BK", "CHE", "CMDN_buffer", "CaB", "CaL", "CaT", "GLUT2_BG", "GLUT2_kinetic", "GLUT2_ss_io", "GLUT2_ss_oi",
      "IPR", "IPR_Siekmann", "Inhib1", "K1_uterine", "KACh", "K_ATP", "Kp", "Kr", "Ks", "Kto", "NCX", "NKE_BG", "NKE_param",
      "NSCC", "Na", "NaB", "PKA", "PLB", "PMCA", "RyR", "SGLT1_BG", "SGLT1_FIG10", "SGLT1_fast", "SGLT1_kinetic", "SGLT1_ss",
      "SGLT1_ss_fast", "SOC", "TRPN", "TRPN_constant_koff", "TRPN_tension_koff", "Terkildsen_NaK_kinetic_modular", "cAMP",
      "funny", "params_BG", "params_FIG10", "params_fast", "params_kinetic", "params_ss", "params_ss_fast", "sGC",
      "saucerman_PKA", "yang_sGC"
    ],
    "columns": [
      "Apical SGLT",
      "Basolateral GLUT",
      "Basolateral NaK Pump",
      "Basolateral K Leak"
    ],
    "non_zero_entries": [
      { "row": "CaB", "col": "Apical SGLT", "score": 0.9 },
      { "row": "GLUT2_BG", "col": "Apical SGLT", "score": 1.0 },
      { "row": "GLUT2_kinetic", "col": "Apical SGLT", "score": 1.0 },
      { "row": "GLUT2_ss_io", "col": "Apical SGLT", "score": 1.0 },
      { "row": "GLUT2_ss_oi", "col": "Apical SGLT", "score": 1.0 },
      { "row": "NKE_BG", "col": "Apical SGLT", "score": 1.0 },
      { "row": "NKE_param", "col": "Apical SGLT", "score": 1.0 },
      { "row": "SGLT1_BG", "col": "Apical SGLT", "score": 0.9 },
      { "row": "SGLT1_kinetic", "col": "Apical SGLT", "score": 0.9 },
      { "row": "SGLT1_ss_fast", "col": "Apical SGLT", "score": 1.0 },
      { "row": "SOC", "col": "Apical SGLT", "score": 1.0 },
      { "row": "Terkildsen_NaK_kinetic_modular", "col": "Apical SGLT", "score": 1.0 },
      { "row": "BK", "col": "Basolateral K Leak", "score": 0.4 },
      { "row": "K_ATP", "col": "Basolateral K Leak", "score": 0.4 },
      { "row": "Kp", "col": "Basolateral K Leak", "score": 0.9 },
      { "row": "Kr", "col": "Basolateral K Leak", "score": 0.6 },
      { "row": "Ks", "col": "Basolateral K Leak", "score": 0.6 }
    ]
  },
  "mermaid_source": "graph TD\n    subgraph Electrical Domain\n        C_Membrane(C: q_mem) -- V_mem --> J0_Vm(0)\n    end\n\n    subgraph Lumen\n        style Lumen fill:#f9f,stroke:#333,stroke-width:2px\n        C_Lumen_Na(C: n_Na_lum) -- mu_Na_lum --> J0_Lumen(0)\n        C_Lumen_Glc(C: n_Glc_lum) -- mu_Glc_lum --> J0_Lumen\n    end\n\n    subgraph Cytosol\n        style Cytosol fill:#ccf,stroke:#333,stroke-width:2px\n        J0_Cyto(0) -- mu_Na_cyto --> C_Cyto_Na(C: n_Na_cyto)\n        J0_Cyto -- mu_Glc_cyto --> C_Cyto_Glc(C: n_Glc_cyto)\n        J0_Cyto -- mu_K_cyto --> C_Cyto_K(C: n_K_cyto)\n    end\n\n    subgraph Interstitial Space\n        style Interstitial Space fill:#9f9,stroke:#333,stroke-width:2px\n        C_Inter_Na(C: n_Na_int) -- mu_Na_int --> J0_Inter(0)\n        C_Inter_Glc(C: n_Glc_int) -- mu_Glc_int --> J0_Inter\n        C_Inter_K(C: n_K_int) -- mu_K_int --> J0_Inter\n    end\n\n    subgraph Apical Membrane\n        SGLT(MRe: SGLT1_ss_fast)\n        J0_Lumen -- J_Na_SGLT --> SGLT\n        J0_Lumen -- J_Glc_SGLT --> SGLT\n        SGLT -- J_Na_SGLT --> J0_Cyto\n        SGLT -- J_Glc_SGLT --> J0_Cyto\n        SGLT -- I_SGLT --> J0_Vm\n    end\n\n    subgraph Basolateral Membrane\n        NaK_Pump(MRe: NaK Pump)\n        GLUT(Re: GLUT)\n        K_Leak(Re: Kp)\n        \n        J0_Cyto -- J_Na_Pump --> NaK_Pump -- J_Na_Pump --> J0_Inter\n        J0_Inter -- J_K_Pump --> NaK_Pump -- J_K_Pump --> J0_Cyto\n        NaK_Pump -- I_Pump --> J0_Vm\n\n        J0_Cyto -- J_Glc_GLUT --> GLUT -- J_Glc_GLUT --> J0_Inter\n\n        J0_Cyto -- J_K_Leak --> K_Leak -- J_K_Leak --> J0_Inter\n        K_Leak -- I_K_Leak --> J0_Vm\n    end",
  "domains": [
    "Chemical",
    "Electrical"
  ],
  "mechanisms": [
    {
      "id": "Apical_SGLT",
      "name": "Apical Sodium-Glucose Cotransporter",
      "type": "Multiport Resistor",
      "library_id": "SGLT1_ss_fast",
      "match_reason": "Perfect match. This model describes the steady-state kinetics of a 2 Na+/1 Glc electrogenic symporter.",
      "connections": [
        "c_lumen",
        "c_cytosol",
        "c_membrane"
      ]
    },
    {
      "id": "Basolateral_GLUT",
      "name": "Basolateral Glucose Facilitated Transporter",
      "type": "Resistor",
      "library_id": null,
      "match_reason": "No suitable model for passive glucose transport (facilitated diffusion) was found in the library.",
      "connections": [
        "c_cytosol",
        "c_interstitial"
      ]
    },
    {
      "id": "Basolateral_NaK_Pump",
      "name": "Basolateral Na/K ATPase",
      "type": "Multiport Resistor",
      "library_id": null,
      "match_reason": "No model for a primary active Na/K ATPase pump was found in the library.",
      "connections": [
        "c_cytosol",
        "c_interstitial",
        "c_membrane"
      ]
    },
    {
      "id": "Basolateral_K_Leak",
      "name": "Basolateral Potassium Leak Channel",
      "type": "Resistor",
      "library_id": "Kp",
      "match_reason": "Strong match. The 'Kp' model describes a voltage-dependent potassium channel.",
      "connections": [
        "c_cytosol",
        "c_interstitial",
        "c_membrane"
      ]
    }
  ],
  "missing_components": [
    "Basolateral GLUT Transporter",
    "Basolateral Na/K ATPase Pump"
  ]
};

export const INITIAL_STEP_2: Step2Data = {
  "generated_components": [
    {
      "id": "Basolateral_GLUT",
      "description": "A reversible Michaelis-Menten model for the facilitated diffusion of glucose.",
      "ports": {
        "port_cyto": { "mapped_variable": "q_glc_cyto", "units": "fmol" },
        "port_inter": { "mapped_variable": "q_glc_inter", "units": "fmol" }
      },
      "parameters": {
        "V_max_GLUT": { "value": 2.5e5, "units": "fmol/s", "description": "Maximum transport rate." },
        "K_m_glc": { "value": 15.0, "units": "mM", "description": "Michaelis constant for glucose." },
        "V_cyto": { "value": 1.0, "units": "pL", "description": "Volume of cytosol." },
        "V_inter": { "value": 10.0, "units": "pL", "description": "Volume of interstitium." }
      },
      "structured_equations": [
        { "type": "algebraic", "lhs": "Glc_cyto", "rhs": "q_glc_cyto / V_cyto" },
        { "type": "algebraic", "lhs": "Glc_inter", "rhs": "q_glc_inter / V_inter" },
        { "type": "algebraic", "lhs": "v_flux", "rhs": "V_max_GLUT * (Glc_cyto - Glc_inter) / (K_m_glc + Glc_cyto + Glc_inter)" }
      ],
      "variables": {
        "Glc_cyto": { "units": "mM" },
        "Glc_inter": { "units": "mM" },
        "v_flux": { "units": "fmol/s" }
      }
    },
    {
      "id": "Basolateral_NaK_Pump",
      "description": "A model of the Na/K ATPase primary active transporter. It actively pumps 3 Na+ ions out and 2 K+ ions in.",
      "ports": {
        "port_Na_cyto": { "mapped_variable": "q_Na_cyto", "units": "fmol" },
        "port_Na_inter": { "mapped_variable": "q_Na_inter", "units": "fmol" },
        "port_K_cyto": { "mapped_variable": "q_K_cyto", "units": "fmol" },
        "port_K_inter": { "mapped_variable": "q_K_inter", "units": "fmol" },
        "port_mem": { "mapped_variable": "q_mem", "units": "fC" }
      },
      "parameters": {
        "V_max_pump": { "value": 1.2e5, "units": "fmol/s", "description": "Maximum pump rate." },
        "K_m_Na": { "value": 10.0, "units": "mM", "description": "Km for cytosolic sodium." },
        "K_m_K": { "value": 1.5, "units": "mM", "description": "Km for interstitial potassium." },
        "V_cyto": { "value": 1.0, "units": "pL", "description": "Volume of cytosol." },
        "V_inter": { "value": 10.0, "units": "pL", "description": "Volume of interstitium." },
        "F": { "value": 96.485, "units": "fC/fmol", "description": "Faraday constant." }
      },
      "structured_equations": [
        { "type": "algebraic", "lhs": "Na_cyto", "rhs": "q_Na_cyto / V_cyto" },
        { "type": "algebraic", "lhs": "K_inter", "rhs": "q_K_inter / V_inter" },
        { "type": "algebraic", "lhs": "term_Na", "rhs": "np.power(Na_cyto, 3) / (np.power(K_m_Na, 3) + np.power(Na_cyto, 3))" },
        { "type": "algebraic", "lhs": "term_K", "rhs": "np.power(K_inter, 2) / (np.power(K_m_K, 2) + np.power(K_inter, 2))" },
        { "type": "algebraic", "lhs": "v_pump_cycles", "rhs": "V_max_pump * term_Na * term_K" },
        { "type": "algebraic", "lhs": "v_Na_flux", "rhs": "3 * v_pump_cycles" },
        { "type": "algebraic", "lhs": "v_K_flux", "rhs": "2 * v_pump_cycles" },
        { "type": "algebraic", "lhs": "I_pump", "rhs": "F * v_pump_cycles" }
      ],
      "variables": {
        "Na_cyto": { "units": "mM" },
        "K_inter": { "units": "mM" },
        "term_Na": { "units": "dimensionless" },
        "term_K": { "units": "dimensionless" },
        "v_pump_cycles": { "units": "fmol/s" },
        "v_Na_flux": { "units": "fmol/s" },
        "v_K_flux": { "units": "fmol/s" },
        "I_pump": { "units": "fA" }
      }
    }
  ]
};

export const INITIAL_STEP_3: Step3Data = {
  "parameter_set": [
    {
      "component_id": "Basolateral_GLUT_inst_Basolateral_GLUT",
      "parameter_name": "V_max_GLUT",
      "value": 3600,
      "units": "fmol/s",
      "source_citation": "Sala-Rabanal, M. et al. (2012), J. Physiol.",
      "biological_context": "Human intestinal epithelial cell (Caco-2).",
      "confidence_score": 0.6,
      "notes": "Derived from computational model matching experimental data."
    },
    {
      "component_id": "Basolateral_GLUT_inst_Basolateral_GLUT",
      "parameter_name": "K_m_glc",
      "value": 17.0,
      "units": "mM",
      "source_citation": "Thorens, B. et al. (1990), PNAS.",
      "biological_context": "Rat GLUT2 expressed in Xenopus oocytes.",
      "confidence_score": 0.9,
      "notes": "Classic value for GLUT2 Km."
    },
    {
      "component_id": "Basolateral_GLUT_inst_Basolateral_GLUT",
      "parameter_name": "V_cyto",
      "value": 2.0,
      "units": "pL",
      "source_citation": "Pácha, J. (2000), Physiol. Rev.",
      "biological_context": "Mature mammalian enterocyte.",
      "confidence_score": 0.7,
      "notes": "Representative value for mature absorptive cell."
    },
    {
      "component_id": "Basolateral_GLUT_inst_Basolateral_GLUT",
      "parameter_name": "V_inter",
      "value": 10.0,
      "units": "pL",
      "source_citation": "Modeler's Assumption",
      "biological_context": "Effective volume of interstitial space.",
      "confidence_score": 0.5,
      "notes": "Assumption."
    },
    {
      "component_id": "Basolateral_NaK_Pump_inst_Basolateral_NaK_Pump",
      "parameter_name": "V_max_pump",
      "value": 24.9,
      "units": "fmol/s",
      "source_citation": "Jørgensen, P. L. (1986), Kidney Int.",
      "biological_context": "Rat kidney proximal tubule, 37C.",
      "confidence_score": 0.6,
      "notes": "Derived from pump density and turnover rate."
    },
    {
      "component_id": "Basolateral_NaK_Pump_inst_Basolateral_NaK_Pump",
      "parameter_name": "K_m_Na",
      "value": 20.0,
      "units": "mM",
      "source_citation": "Skou, J. C. (1990), FEBS Lett.",
      "biological_context": "General value for Na,K-ATPase.",
      "confidence_score": 0.9,
      "notes": "Apparent Michaelis constant for intracellular sodium."
    },
    {
      "component_id": "Basolateral_NaK_Pump_inst_Basolateral_NaK_Pump",
      "parameter_name": "K_m_K",
      "value": 1.5,
      "units": "mM",
      "source_citation": "Skou, J. C. (1990), FEBS Lett.",
      "biological_context": "General value for Na,K-ATPase.",
      "confidence_score": 0.9,
      "notes": "Apparent Michaelis constant for extracellular potassium."
    },
    {
      "component_id": "Basolateral_NaK_Pump_inst_Basolateral_NaK_Pump",
      "parameter_name": "F",
      "value": 96485.33,
      "units": "fC/fmol",
      "source_citation": "NIST CODATA 2018",
      "biological_context": "Physical constant.",
      "confidence_score": 1.0,
      "notes": "Faraday constant."
    }
  ],
  "global_constants": {
    "T": { "value": 310.15, "units": "K", "note": "Standard mammalian body temperature (37 C)." }
  },
  "issues_report": [
    "Parameter Consistency: Values are curated from multiple sources.",
    "Vmax Estimation: Maximum transport rates are derived, not direct.",
    "Compartment Volumes: V_inter is a model construct."
  ]
};

export const AN01_MODEL: DetailedLibraryModel = {
  "filepath": "data/An01/BG_An01.cellml",
  "semantic_version": 4.0,
  "description": "A semantic audit of An01, a model of a calcium-activated chloride channel (CaCC). The model uses a thermodynamically-compliant Bond Graph-style formulation.",
  "keywords": ["Cl- Channel", "Calcium Activated"],
  "global_constants": {
    "T": { "value": "310.15", "units": "kelvin", "description": "Absolute temperature." },
    "F": { "value": "96485.33", "units": "C_per_mol", "description": "Faraday constant." }
  },
  "ports": {
    "Cl_ext": { "description": "Connection to extracellular Cl.", "direction": "positive_out" },
    "Cl_int": { "description": "Connection to intracellular Cl.", "direction": "positive_in" },
    "charge": { "description": "Connection to membrane capacitor.", "direction": "positive_in" }
  },
  "variables": {
    "q_mem": { "role": "state", "semantic_match": "membrane_charge" },
    "v_ReAn01": { "role": "rate", "semantic_match": "ion_flux" }
  },
  "constitutive_laws": [
    {
      "name": "ThermodynamicFlux",
      "equation": "v_ReAn01 = f(Af, Ar)",
      "description": "Flux relating to electrochemical potential."
    }
  ]
};

export const SGLT1_MODEL: DetailedLibraryModel = {
  "filepath": "data/SGLT1_ss_fast/BG_SGLT1.cellml",
  "semantic_version": 2.1,
  "description": "A steady-state model of the Sodium-Glucose Co-transporter 1 (SGLT1). It models the stoichiometric coupling of 2 Na+ ions to 1 Glucose molecule.",
  "keywords": ["Secondary Active Transport", "Sodium", "Glucose"],
  "global_constants": {
    "T": { "value": "310.15", "units": "kelvin" },
    "F": { "value": "96485.33", "units": "C_per_mol" }
  },
  "ports": {
    "Na_lumen": { "description": "Sodium in lumen", "direction": "positive_in" },
    "Glc_lumen": { "description": "Glucose in lumen", "direction": "positive_in" },
    "Na_cyto": { "description": "Sodium in cytosol", "direction": "positive_out" },
    "Glc_cyto": { "description": "Glucose in cytosol", "direction": "positive_out" }
  },
  "variables": {
    "v_SGLT": { "role": "rate", "semantic_match": "cotransport_rate" }
  },
  "constitutive_laws": [
    {
      "name": "SGLT1_Kinetics",
      "equation": "v_SGLT = k_cat * ( (Na_out^2 * Glc_out) / K_half - (Na_in^2 * Glc_in) )",
      "description": "Simplified kinetic rate law assuming rapid equilibrium binding."
    }
  ]
};

export const KP_MODEL: DetailedLibraryModel = {
  "filepath": "data/Kp/BG_Kp.cellml",
  "semantic_version": 1.5,
  "description": "A generic voltage-gated potassium channel model (Kp) used for background leak currents.",
  "keywords": ["Potassium", "Leak", "Voltage Gated"],
  "global_constants": {
    "T": { "value": "310.15", "units": "kelvin" }
  },
  "ports": {
    "K_int": { "description": "Intracellular Potassium", "direction": "positive_in" },
    "K_ext": { "description": "Extracellular Potassium", "direction": "positive_out" }
  },
  "variables": {
    "v_K": { "role": "rate", "semantic_match": "ion_flux" },
    "V_mem": { "role": "input", "semantic_match": "membrane_potential" }
  },
  "constitutive_laws": [
    {
      "name": "OhmicLeak",
      "equation": "I_K = g_K * (V_mem - E_K)",
      "description": "Standard ohmic relationship for a leak channel."
    }
  ]
};