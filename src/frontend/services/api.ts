// src/frontend/services/api.ts
import { AgentState, Project } from "../types";

const API_BASE = '/api'; // Proxied by Vite to http://localhost:8997

export interface WorkflowResponse {
  thread_id: string;
  state: AgentState;
}

export const api = {
  async startWorkflow(username: string, projectName: string, userRequest: string, apiKey?: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, project_name: projectName, user_request: userRequest, api_key: apiKey }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resumeWorkflow(username: string, threadId: string, apiKey?: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, thread_id: threadId, api_key: apiKey }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async updateState(username: string, threadId: string, key: string, value: any): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/update_state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, thread_id: threadId, key, value }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async refinePlan(username: string, threadId: string, updatedSpec: any, apiKey?: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/refine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, thread_id: threadId, updated_spec: updatedSpec, api_key: apiKey }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async renameProject(username: string, threadId: string, newName: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/rename`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, thread_id: threadId, new_name: newName }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteProject(username: string, threadId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, thread_id: threadId }),
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async pollState(username: string, threadId: string): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE}/poll/${username}/${threadId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listProjects(username: string): Promise<Project[]> {
    try {
        const res = await fetch(`${API_BASE}/projects/${username}`);
        if (!res.ok) throw new Error("Failed to load projects");
        return res.json();
    } catch (e) {
        console.error("List projects error:", e);
        return [];
    }
  },

  async getLibrary(): Promise<Record<string, any>> {
    const res = await fetch(`${API_BASE}/library`);
    if (!res.ok) throw new Error("Failed to load library");
    return res.json();
  }
};