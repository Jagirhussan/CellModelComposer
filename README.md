# **Agentic Physio-Simulation Framework**

An open-source Agentic AI framework designed to automate the creation, curation, and analysis of biological simulations (CellML/Physiome). This system employs a graph-based workflow of specialized AI agents—Architect, Physicist, Curator, and Analyst—to transform natural language queries into rigorous mathematical models.

## **🌟 Features**

* **Multi-Agent Orchestration:** A directed acyclic graph (DAG) workflow engine coordinates specialized agents.  
  * **Architect:** Plans the simulation logic and structure.  
  * **Physicist:** Generates the mathematical code (Python/CellML).  
  * **Curator:** Validates models against biological ontologies.  
  * **Analyst:** Executes simulations and interprets results.  
* **Visual Workflow:** Real-time visualization of agent interactions and confidence matrices.  
* **Interactive Frontend:** React-based UI for refining prompts, editing generated JSON/Code, and viewing results.  
* **Extensible Backend:** Python-based architecture designed for easy integration of new biological knowledge bases.

## **🚀 Getting Started**

### **Prerequisites**

* **Node.js** (v18 or higher)  
* **Python** (3.9 or higher)  
* **Google Gemini API Key** (or OpenAI Key if configured)

### **Installation**

1. **Clone the repository:**  
   git clone \[hhttps://github.com/Jagirhussan/CellModelComposer.git\](https://github.com/Jagirhussan/CellModelComposer.git)  
   cd agentic-physio-simulation

2. **Run the automated setup script:**  
   chmod \+x install.sh  
   ./install.sh

   *Alternatively, install manually:*  
   *Backend:*  
   cd src/backend  
   python \-m venv venv  
   source venv/bin/activate  
   pip install \-r requirements.txt

   *Frontend:*  
   cd src/frontend  
   npm install

3. **Configuration:**  
   Copy the example environment file and add your API keys.  
   cp .env.example .env  
   \# Edit .env and add your GOOGLE\_API\_KEY

### **Running the Application**

1. **Start the Backend API:**  
   \# In a new terminal  
   cd src/backend  
   source venv/bin/activate  
   python server.py

2. **Start the Frontend UI:**  
   \# In a new terminal  
   cd src/frontend  
   npm run dev

3. Open your browser to http://localhost:5173 (or the port shown in your terminal).

## **📂 Project Structure**

├── src  
│   ├── backend          \# Python Flask API & Agent Logic  
│   │   ├── agents/      \# Specific agent implementations  
│   │   ├── core/        \# Graph workflow engine  
│   │   └── server.py    \# API Entry point  
│   └── frontend         \# React \+ Vite Application  
│       ├── components/  \# UI Components (Matrix, Editors)  
│       └── services/    \# API Clients  
├── install.sh           \# Quick setup script  
└── requirements.txt     \# Python dependencies

## **🛡️ Security Note**

This project uses LLMs to generate and execute code.

* **Sandboxing:** While the agents attempt to validate code, always review the generated Python simulation code before execution in a production environment.  
* **Keys:** Never commit your .env file or hardcode API keys.

## **🤝 Contributing**

Contributions are welcome\! Please read [CONTRIBUTING.md](https://www.google.com/search?q=CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## **📄 License**

This project is licensed under the Apache License v 2.0 \- see the [LICENSE](http://www.apache.org/licenses/) file for details.