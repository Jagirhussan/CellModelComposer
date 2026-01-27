import { useState, useRef, useCallback } from 'react';
import { AgentState, AgentStatus, WorkflowNode } from '../types';
import { api } from './api';

export const useAgentGraph = (initialState: AgentState, apiKey: string) => {
  const [state, setState] = useState<AgentState>(initialState);
  const [threadId, setThreadId] = useState<string | null>(null);
  const processingRef = useRef<boolean>(false);
  const pollIntervalRef = useRef<number | null>(null);

  // Stop polling helper
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      window.clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Polling logic to detect state changes from the backend
  // In a real streaming implementation, this would be a WebSocket or SSE
  const startPolling = useCallback((tid: string) => {
    stopPolling();
    
    pollIntervalRef.current = window.setInterval(async () => {
      try {
        const data = await api.pollState(tid);
        setState(prev => ({ ...prev, ...data.state, lastUpdated: Date.now() }));

        // Stop polling if paused or complete or error
        const s = data.state.status;
        if (s === AgentStatus.PAUSED || s === AgentStatus.SUCCESS || s === AgentStatus.ERROR) {
          stopPolling();
          processingRef.current = false;
        }
      } catch (e) {
        console.error("Polling error:", e);
        stopPolling();
        processingRef.current = false;
      }
    }, 2000); // Poll every 2 seconds
  }, [stopPolling]);

  // 1. Start Workflow
  const startWorkflow = async (request: string) => {
    if (processingRef.current) return;
    processingRef.current = true;
    
    setState(prev => ({ 
      ...prev, 
      user_request: request, 
      status: AgentStatus.RUNNING,
      messages: [] 
    }));

    try {
      const data = await api.startWorkflow(request, apiKey);
      setThreadId(data.thread_id);
      
      // Merge state
      setState(prev => ({ ...prev, ...data.state, lastUpdated: Date.now() }));

      // If backend paused immediately (e.g. planner done), stop processing flag
      if (data.state.status === AgentStatus.PAUSED) {
        processingRef.current = false;
      } else {
        // Otherwise poll
        startPolling(data.thread_id);
      }

    } catch (e) {
      console.error(e);
      setState(prev => ({ ...prev, status: AgentStatus.ERROR }));
      processingRef.current = false;
    }
  };

  // 2. Approve / Resume Step
  const approveStep = async () => {
    if (!threadId || processingRef.current) return;
    processingRef.current = true;
    
    // Optimistic update
    setState(prev => ({ ...prev, status: AgentStatus.RUNNING }));

    try {
      const data = await api.resumeWorkflow(threadId);
      setState(prev => ({ ...prev, ...data.state, lastUpdated: Date.now() }));
      startPolling(threadId);
    } catch (e) {
      console.error(e);
      setState(prev => ({ ...prev, status: AgentStatus.ERROR }));
      processingRef.current = false;
    }
  };

  // 3. Update State (Edit Artifacts)
  const updateStatePart = async (key: string, value: any) => {
    if (!threadId) return;

    // Optimistic local update
    setState(prev => ({ ...prev, [key]: value }));

    try {
      const data = await api.updateState(threadId, key, value);
      // Sync full state to be safe
      setState(prev => ({ ...prev, ...data.state, lastUpdated: Date.now() }));
    } catch (e) {
      console.error("Failed to update remote state:", e);
      // Revert or show error
    }
  };

  return {
    state,
    startWorkflow,
    approveStep,
    updateStatePart,
    isProcessing: processingRef.current
  };
};