import os
import sys
import uuid
import uvicorn
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure src modules are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from graph_workflow import build_graph
from graph_state import AgentState
from app_config import config
from bio_agents import PromptDecompositionAgent
from agent_types import BiologicalSpec
# render_tikz_to_svg removed as per request

app = FastAPI(title="Bond Graph Architect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()

# --- Config ---
USER_DATA_PATH = config.get("paths", "user_data", "data/users")
USERS_DIR = Path(USER_DATA_PATH)
try:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"INFO:     User projects will be stored in: {USERS_DIR.absolute()}")
except Exception as e:
    print(f"ERROR:    Could not create user data directory at {USERS_DIR}: {e}")

def get_user_dir(username: str) -> Path:
    user_path = USERS_DIR / username
    user_path.mkdir(exist_ok=True)
    return user_path

def save_project(username: str, thread_id: str, state: Dict):
    user_dir = get_user_dir(username)
    file_path = user_dir / f"{thread_id}.json"
    try:
        # SECURITY FIX: Remove API key before saving
        state_to_save = state.copy()
        if "api_key" in state_to_save:
            del state_to_save["api_key"]
            
        with open(file_path, 'w') as f:
            json.dump(state_to_save, f, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o), indent=2)
        print(f"INFO:     Saved project {thread_id} for {username}")
    except Exception as e:
        print(f"ERROR:    Failed to save project {thread_id}: {e}")

def load_project(username: str, thread_id: str) -> Optional[Dict]:
    user_dir = get_user_dir(username)
    file_path = user_dir / f"{thread_id}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r') as f: return json.load(f)
        except: return None
    return None

def delete_project_file(username: str, thread_id: str) -> bool:
    user_dir = get_user_dir(username)
    file_path = user_dir / f"{thread_id}.json"
    if file_path.exists():
        try: os.remove(file_path); return True
        except: return False
    return False

# --- Models ---
class StartRequest(BaseModel):
    username: str
    project_name: str 
    user_request: str
    api_key: Optional[str] = None

class ResumeRequest(BaseModel):
    thread_id: str
    username: str 
    api_key: Optional[str] = None

class UpdateStateRequest(BaseModel):
    thread_id: str
    username: str
    key: str
    value: Any

class RefineRequest(BaseModel):
    thread_id: str
    username: str
    updated_spec: Dict[str, Any]
    api_key: Optional[str] = None

class RenameRequest(BaseModel):
    thread_id: str
    username: str
    new_name: str

class DeleteRequest(BaseModel):
    thread_id: str
    username: str

def get_config(thread_id: str):
    return {"configurable": {"thread_id": thread_id}}

def serialize_state(state: AgentState, next_nodes: tuple, file_stats: os.stat_result = None) -> Dict[str, Any]:
    # Default State
    current_node = "planner"
    status = "running"
    
    # 1. Check for Explicit Success/Failure (Highest Priority)
    if state.get("simulation_status") == "success":
        current_node = "complete"
        status = "success"
    
    elif state.get("simulation_status") == "failure":
        status = "error"
        current_node = "analyst"
        
    # 2. Check for Active Memory Interrupts (Reliable during execution)
    elif next_nodes and "planner" not in next_nodes:
        if "retriever" in next_nodes:
            current_node = "retriever"
            status = "paused"
        elif "composer" in next_nodes:
            current_node = "composer"
            status = "paused"
        elif "researcher" in next_nodes:
            current_node = "researcher"
            status = "paused"
        elif "analyst" in next_nodes:
            current_node = "analyst"
            status = "paused"
            
    # 3. Artifact Inference (Fallback for Disk Load / Server Restart)
    elif state.get("spec"): 
        status = "paused"
        if state.get("simulation_report"):
            current_node = "analyst" 
        elif state.get("curator_output"):
            current_node = "analyst"
        elif state.get("composite_model"):
            current_node = "researcher" 
        elif state.get("physicist_output"):
            current_node = "composer" 
        elif state.get("spec"):
            current_node = "retriever" 
        else:
            current_node = "planner" 
            status = "running"

    now_ms = int(time.time() * 1000)
    last_updated = now_ms
    if file_stats:
        last_updated = int(file_stats.st_mtime * 1000)

    raw_msgs = state.get("messages", [])
    frontend_msgs = []
    for i, msg in enumerate(raw_msgs):
        msg_time = last_updated - ((len(raw_msgs) - 1 - i) * 1000)
        frontend_msgs.append({
            "role": "agent",
            "content": str(msg),
            "timestamp": msg_time
        })

    # Note: JIT RENDERING FIX block for render_tikz_to_svg has been removed.
    composite_model = state.get("composite_model")

    return {
        "project_name": state.get("project_name", "Untitled Project"),
        "project_notes": state.get("project_notes", ""),
        "user_request": state.get("user_request", ""),
        "messages": frontend_msgs,
        
        "spec": state.get("spec"),
        "components": state.get("components", []),
        "physicist_output": state.get("physicist_output"), 
        "curator_output": state.get("curator_output"),
        "composite_model": composite_model,
        "generated_code": state.get("generated_code"),
        "composer_logs": state.get("composer_logs"),
        
        "planner_thoughts": state.get("planner_thoughts"),
        "physicist_thoughts": state.get("physicist_thoughts"),
        "curator_thoughts": state.get("curator_thoughts"),
        "analyst_thoughts": state.get("analyst_thoughts"),
        "composer_thoughts": state.get("composer_thoughts"),
        
        "simulation_report": state.get("simulation_report"),
        "simulation_status": state.get("simulation_status"),
        "currentNode": current_node,
        "status": status,
        "lastUpdated": last_updated
    }

# --- Endpoints ---

@app.get("/api/library")
async def get_library():
    try:
        DATA_PATH = config.get("paths", "data_dir", "data")
        # which is the root for the execution context.
        with open(f"{DATA_PATH}/library_registry.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Library registry file not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read library registry: {e}")

@app.post("/api/start")
async def start_workflow(req: StartRequest):
    thread_id = str(uuid.uuid4())
    print(f"INFO:     Starting workflow {thread_id} for {req.username}")
    config = get_config(thread_id)
    
    initial_input = {
        "project_name": req.project_name, 
        "project_notes": "", 
        "user_request": req.user_request, 
        "user_id": req.username,
        "api_key": req.api_key, # Passed in state, stripped before save
        "messages": [],
        "analyst_attempts": 0
    }
    
    try:
        graph.invoke(initial_input, config=config)
        snapshot = graph.get_state(config)
        save_project(req.username, thread_id, snapshot.values)
        return { "thread_id": thread_id, "state": serialize_state(snapshot.values, snapshot.next) }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume")
async def resume_workflow(req: ResumeRequest):
    config = get_config(req.thread_id)
    snapshot = graph.get_state(config)
    
    # Restore state from disk if memory is empty
    if not snapshot.values:
        saved_state = load_project(req.username, req.thread_id)
        if saved_state: graph.update_state(config, saved_state)
        else: raise HTTPException(status_code=404, detail="Thread not found")

    # Inject API key from request into state memory (ephemeral)
    if req.api_key:
        graph.update_state(config, {"api_key": req.api_key})

    try:
        graph.invoke(None, config=config)
        snapshot = graph.get_state(config)
        save_project(req.username, req.thread_id, snapshot.values)
        return { "thread_id": req.thread_id, "state": serialize_state(snapshot.values, snapshot.next) }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update_state")
async def update_state_part(req: UpdateStateRequest):
    config = get_config(req.thread_id)
    key_map = {
        "spec": "spec", 
        "components": "components", 
        "generated_code": "generated_code", 
        "project_notes": "project_notes",
        "physicist_output": "physicist_output",
        "curator_output": "curator_output"
    }
    if req.key not in key_map: raise HTTPException(status_code=400, detail="Invalid key")
    try:
        graph.update_state(config, {key_map[req.key]: req.value})
        snapshot = graph.get_state(config)
        save_project(req.username, req.thread_id, snapshot.values)
        return {"thread_id": req.thread_id, "state": serialize_state(snapshot.values, snapshot.next)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refine")
async def refine_plan(req: RefineRequest):
    """
    Triggers the prompt refinement logic based on the user's updated Spec/Matrix.
    Resets the workflow to the state after planning, ready for retrieval.
    """
    config = get_config(req.thread_id)
    saved_state = load_project(req.username, req.thread_id)
    if not saved_state: raise HTTPException(status_code=404, detail="Thread not found")
    
    # 1. Initialize Agent with API Key (use request key or stored key)
    api_key = req.api_key or saved_state.get("api_key")
    agent = PromptDecompositionAgent(api_key=api_key)
    
    # 2. Run Refinement
    print(f"INFO:     Refining plan for {req.thread_id}")
    try:
        result = agent.refine_plan(saved_state["user_request"], req.updated_spec)
        
        if not result.success:
             raise HTTPException(status_code=500, detail=f"Refinement Failed: {result.report_markdown}")
        
        # 3. Format Spec Data
        spec_data = result.data.__dict__.copy() if hasattr(result.data, '__dict__') else result.data
        if "mechanisms" in spec_data:
            spec_data["components"] = spec_data["mechanisms"]

        # 4. Construct New State (Resetting downstream artifacts)
        # We preserve metadata but clear execution artifacts to force regeneration
        new_state_updates = {
            "spec": spec_data,
            "messages": saved_state.get("messages", []) + [result.report_markdown],
            # Reset downstream data to force re-execution
            "components": [],
            "physicist_output": None,
            "composite_model": None,
            "generated_code": None,
            "composer_logs": None,
            "curator_output": None,
            "simulation_report": None,
            "simulation_status": "pending",
            "analyst_attempts": 0
        }
        
        # 5. Update Graph State & Save
        graph.update_state(config, new_state_updates)
        snapshot = graph.get_state(config)
        save_project(req.username, req.thread_id, snapshot.values)
        
        # We return the state. The frontend sees 'retriever' as the next step because 
        # we updated the state but haven't run 'retriever' yet. 
        # The graph is naturally paused before 'retriever' if we don't invoke it.
        return { "thread_id": req.thread_id, "state": serialize_state(snapshot.values, snapshot.next) }

    except Exception as e:
        print(f"ERROR:    Refinement error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rename")
async def rename_project(req: RenameRequest):
    config = get_config(req.thread_id)
    snapshot = graph.get_state(config)
    if not snapshot.values:
        saved_state = load_project(req.username, req.thread_id)
        if saved_state: graph.update_state(config, saved_state)
        else: raise HTTPException(status_code=404, detail="Thread not found")
    try:
        graph.update_state(config, {"project_name": req.new_name})
        snapshot = graph.get_state(config)
        save_project(req.username, req.thread_id, snapshot.values)
        return { "thread_id": req.thread_id, "state": serialize_state(snapshot.values, snapshot.next) }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delete")
async def delete_project(req: DeleteRequest):
    success = delete_project_file(req.username, req.thread_id)
    if success: return {"status": "success", "thread_id": req.thread_id}
    else: raise HTTPException(status_code=404, detail="Project not found")

@app.get("/api/poll/{username}/{thread_id}")
async def poll_state(username: str, thread_id: str):
    config = get_config(thread_id)
    snapshot = graph.get_state(config)
    
    # Check if memory is empty (server restart case)
    if not snapshot.values:
        saved_state = load_project(username, thread_id)
        if saved_state:
            # Restore state to memory so serialization can check next_nodes if needed
            # NOTE: update_state creates a new checkpoint, effectively 'resuming' the memory
            graph.update_state(config, saved_state)
            snapshot = graph.get_state(config)
        else:
            raise HTTPException(status_code=404, detail="Thread not found")
    
    return {"thread_id": thread_id, "state": serialize_state(snapshot.values, snapshot.next)}

@app.get("/api/projects/{username}")
async def list_projects(username: str):
    user_dir = get_user_dir(username)
    projects = []
    for f in user_dir.glob("*.json"):
        try:
            stats = f.stat()
            with open(f, 'r') as file:
                data = json.load(file)
                created_ts = stats.st_ctime
                name = data.get("project_name", data.get("user_request", "Untitled")[:30])
                notes = data.get("project_notes", "") 
                # infer state using empty tuple for next_nodes since we are offline
                projects.append({
                    "id": f.stem,
                    "name": name,
                    "notes": notes, 
                    "created_at": datetime.datetime.fromtimestamp(created_ts).isoformat(),
                    "state": serialize_state(data, (), file_stats=stats) 
                })
        except: pass
    projects.sort(key=lambda x: x["state"]["lastUpdated"], reverse=True)
    return projects

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8997, reload=True)