# **Library Builder & CellML Processing Documentation**

## **Overview**

The **Library Builder** is the backend module responsible for ingesting, validating, and standardizing external biological models for use within the Agentic simulation framework. It serves as the bridge between the **Physiome Model Repository (PMR)** and the internal knowledge graph used by the Architect and Physicist agents.

## **1\. Source: Physiome Model Repository (PMR)**

The primary source for models is the [Physiome Model Repository](https://models.physiomeproject.org). The Library Builder targets **CellML** files, particularly those designed with **Bond Graph** formalism.

* **Repository URL:** https://models.physiomeproject.org  
* **Target Models:** CellML 2.0 (and 1.0/1.1 compatible) files.

### **Finding Bond Graph Models**

Users or agents can identify compatible models on PMR by searching for specific conventions:

1. **Keywords:** Search for "bond graph", "thermodynamic", or "energy based".  
2. **Naming Convention:** Many bond graph models in PMR use the prefix BG\_ (e.g., BG\_SGLT1.cellml).  
3. **Workspaces:** Look for workspaces that contain "BG" or "Bond Graph" in their title.

## **2\. The Build Process**

The LibraryBuilder class executes a multi-step pipeline to transform a raw internet download into a semantic agent resource.

### **A. Fetching**

* The builder accepts a query or a direct URL to a PMR workspace.  
* It downloads the raw .cellml XML file.

### **B. Post-Processing**

Raw CellML describes *mathematics* but often lacks the *semantic* information required for modular composition. The post-processing step bridges this gap:

1. **XML Parsing & Validation:**  
   * Uses lxml or libcellml to parse the document structure.  
   * Validates that the file contains valid components, variables, and math blocks.  
2. **Bond Graph Port Identification:**  
   * The builder analyzes the variable names and units to identify **Port Pairs** (Energy Bonds).  
   * **Heuristic:** It looks for pairs of variables representing:  
     * **Effort (![][image1]):** Potential, Voltage, Pressure.  
     * **Flow (![][image2]):** Molar flow, Current, Volumetric flow.  
   * *Example:* If a component has public interface variables v\_in (fmole/s) and u\_in (J/mol), the builder tags these as a generic input port.  
3. **Semantic Enrichment (LLM-Assisted):**  
   * Since variable naming varies (e.g., V\_m vs membrane\_voltage), the builder may pass the component header to the LLM.  
   * **Goal:** To generate a standardized JSON description of what the model *does* (e.g., "Passive Potassium Channel") and what its ports represent physically.

### **C. Storage**

Processed models are stored in the local file system to allow offline access and faster retrieval by agents.

* **Base Directory:** src/backend/data/library/  
* **Structure:**  
  data/library/  
  ├── {model\_unique\_id}/          \# e.g., "bg\_potassium\_channel"  
  │   ├── source.cellml           \# The immutable raw file from PMR  
  │   ├── model.json              \# The processed metadata (Ports, Variables, Equations)  
  │   └── index.json              \# Searchable tags for the Architect agent

## **3\. Data Structure (processed model.json)**

The post-processing generates a JSON structure that the agents prefer over raw XML:

{  
  "id": "bg\_slc\_transporter",  
  "source\_url": "\[https://models.physiomeproject.org/e/\](https://models.physiomeproject.org/e/)...",  
  "description": "Bond graph model of a Solute Carrier",  
  "ports": \[  
    {  
      "name": "membrane\_port",  
      "type": "electrical",  
      "variables": {"effort": "V\_m", "flow": "I\_m"}  
    },  
    {  
      "name": "sodium\_port",  
      "type": "chemical",  
      "variables": {"effort": "mu\_Na", "flow": "v\_Na"}  
    }  
  \],  
  "parameters": \[  
    {"name": "G\_max", "value": 12.0, "units": "S"}  
  \]  
}

## **4\. Usage in Workflow**

* **Architect Agent:** Queries the index.json files to see if a requested biological part (e.g., "sodium channel") already exists in the library.  
* **Physicist Agent:** Reads model.json to know how to connect this sub-model to the main graph (i.e., connecting the "membrane\_port" to the global membrane capacitor).
