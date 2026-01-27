import uuid
import json
import re
from pprint import pprint
import sys

# Ensure backend modules are in path
sys.path.append("backend")

from graph_workflow import build_graph
from graph_state import AgentState

def print_markdown(text: str):
    """Helper to print markdown with visual separation and diagram detection"""
    lines = text.split('\n')
    print("\n" + "="*80)
    in_mermaid = False
    
    for line in lines:
        if "```mermaid" in line:
            in_mermaid = True
            print("\n  [MERMAID DIAGRAM DETECTED - RENDERED IN UI]\n")
            print("  -------------------------------------------")
            print("  |   (Graph Topology Visualized Here)      |")
            print("  -------------------------------------------")
            continue
        if "```" in line and in_mermaid:
            in_mermaid = False
            continue
        if in_mermaid:
            # Skip printing raw mermaid code in CLI to reduce noise, 
            # or uncomment to see raw code
            # print(f"  | {line}") 
            continue
            
        # Simple indentation for clean reading
        print(f"  {line}")
    print("="*80 + "\n")

def main():
    print("=== Initializing LangGraph Semantic Architect ===")
    
    # 1. Setup Graph and Config
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Initial User Prompt
    user_prompt = "Create a model of SGLT1 cotransport involving Intracellular Sodium and Membrane Voltage."
    user_prompt = "Create a model of Glucose transport in an epithelial cell"
    initial_state = {
        "user_request": user_prompt,
        "analyst_attempts": 0,
        "messages": []
    }
    
    print(f"\nUser Prompt: {user_prompt}")
    print(f"Session ID: {thread_id}")

    # 3. Execution Loop
    current_input = initial_state
    resume_mode = False
    
    while True:
        try:
            print("\n--- Executing Graph Step ---")
            inputs = None if resume_mode else current_input
            
            for event in graph.stream(inputs, config=config):
                for key, value in event.items():
                    print(f"Finished Node: {key}")
                    
                    # Markdown Report Printing
                    if value and "messages" in value:
                        for msg in value["messages"]:
                            # Heuristic to detect markdown-heavy content
                            if "# " in msg or "| " in msg or "**" in msg: 
                                print_markdown(msg)
                            else:
                                print(f"   > {msg}")

            # 4. Check Snapshot
            snapshot = graph.get_state(config)
            
            if not snapshot.next:
                print("\n>>> Workflow Completed Successfully! <<<")
                final_code = snapshot.values.get("generated_code")
                if final_code:
                    print("\n--- Final Generated Code ---")
                    # Print first 20 lines and last 20 lines to keep it clean
                    lines = final_code.split('\n')
                    print('\n'.join(lines[:20]))
                    print(f"\n... [{len(lines)-40} lines hidden] ...\n")
                    print('\n'.join(lines[-20:]))
                else:
                    print("Process finished but no code generated.")
                break

            # 5. Handle Interrupts (HITL)
            next_step = snapshot.next[0]
            print(f"\n>>> HITL Paused before: '{next_step}' <<<")
            
            if next_step == "retriever":
                spec = snapshot.values.get("spec")
                if spec:
                    print(f"\nIntent: {spec.intent_summary}")
                    if spec.match_matrix:
                         print("\n[INFO] Confidence Matrix available in report.")
                
                decision = input("Approve Plan? (y/n/edit): ").strip().lower()
                if decision == 'n': break
                elif decision == 'edit':
                    new_intent = input("Enter new intent: ")
                    # Note: Editing intent here is simple; in production we'd edit the full spec
                    graph.update_state(config, {"spec": {"intent_summary": new_intent}}) 
            
            elif next_step == "composer":
                components = snapshot.values.get("components")
                print(f"\nRetrieved {len(components)} Components.")
                
                decision = input("Proceed to Composition? (y/n): ").strip().lower()
                if decision == 'n': break

            resume_mode = True
            print("Resuming...")

        except Exception as e:
            print(f"Runtime Error: {e}")
            import traceback
            traceback.print_exc()
            break

if __name__ == "__main__":
    main()