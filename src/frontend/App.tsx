import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Terminal, Play, Save, FolderOpen, 
  Search, Plus, LogOut, ChevronRight, 
  LayoutGrid, Trash2, Info, StickyNote, X, Key, Loader2, BrainCircuit, MessageSquare
} from 'lucide-react';
import { 
  AgentState, LibraryModel, Project, UserSession, WorkflowNode, AgentStatus 
} from './types';
import { api } from './services/api';
import { WorkflowStatus } from './components/Layout/WorkflowStatus';
import WorkflowEditor from './components/WorkflowEditor';

// --- MAIN APP COMPONENT ---

const EMPTY_STATE: AgentState = {
  project_name: "New Project",
  project_notes: "",
  user_request: '',
  messages: [],
  currentNode: WorkflowNode.PLANNER,
  status: AgentStatus.IDLE,
  analyst_attempts: 0,
  lastUpdated: Date.now()
};

// --- Deep Equality Check (Fixes Flickering) ---
function isStateEqual(prev: AgentState, next: AgentState): boolean {
    if (prev.status !== next.status) return false;
    if (prev.currentNode !== next.currentNode) return false;
    if (prev.messages.length !== next.messages.length) return false;
    
    // Check content of latest message to detect changes without size change
    if (prev.messages.length > 0 && next.messages.length > 0) {
        if (prev.messages[0].content !== next.messages[0].content) return false;
    }

    // Artifact checks
    if (JSON.stringify(prev.spec) !== JSON.stringify(next.spec)) return false;
    // Check mermaid string specifically for model updates
    if (prev.composite_model?.mermaid !== next.composite_model?.mermaid) return false;
    if (prev.generated_code !== next.generated_code) return false;
    if (prev.simulation_report !== next.simulation_report) return false;
    
    return true;
}

export default function App() {
  const [session, setSession] = useState<UserSession | null>(() => {
    try {
        const saved = localStorage.getItem('sbg_session');
        return saved ? JSON.parse(saved) : null;
    } catch(e) { return null; }
  });

  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  
  const [username, setUsername] = useState('');
  const [apiKey, setApiKey] = useState('');
  
  const [searchTerm, setSearchTerm] = useState('');
  const [showDashboardNotes, setShowDashboardNotes] = useState<string | null>(null);
  
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [isSubmittingProject, setIsSubmittingProject] = useState(false); // New loading state
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectRequest, setNewProjectRequest] = useState('');

  const [isNotesOpen, setIsNotesOpen] = useState(false);
  const [workspaceNotes, setWorkspaceNotes] = useState('');
  const [state, setState] = useState<AgentState>(EMPTY_STATE);
  const [activeSidebarTab, setActiveSidebarTab] = useState<'chat' | 'thoughts'>('chat');
  
  const [libraryRegistry, setLibraryRegistry] = useState<Record<string, LibraryModel> | null>(null);

  const pollInterval = useRef<number | null>(null);

  // Persist Session
  useEffect(() => {
    if (session) localStorage.setItem('sbg_session', JSON.stringify(session));
    else localStorage.removeItem('sbg_session');
  }, [session]);

  // Load Projects & Library on Session Start
  useEffect(() => {
    if (session) {
      api.listProjects(session.username).then(setProjects);
      api.getLibrary().then(setLibraryRegistry);
    }
  }, [session]);

  // Sync State when switching projects
  useEffect(() => {
    if (activeProjectId) {
      // Load initial state from local project list if available
      const proj = projects.find(p => p.id === activeProjectId);
      if (proj) {
          // Only update local state if we are switching to a new project
          // Note: We deliberately update even if names match to ensure 'currentNode' inference from list_projects is applied
          if (state.project_name !== proj.name || state.lastUpdated !== proj.state.lastUpdated) { 
             setState(proj.state);
             setWorkspaceNotes(proj.state.project_notes);
          }
      }
      startPolling(activeProjectId);
    } else {
      stopPolling();
      setState(EMPTY_STATE);
      setIsNotesOpen(false);
    }
    return () => stopPolling();
  }, [activeProjectId]); 

  const stopPolling = () => {
    if (pollInterval.current) {
        window.clearInterval(pollInterval.current);
        pollInterval.current = null;
    }
  };

  const startPolling = (threadId: string) => {
    stopPolling();
    pollInterval.current = window.setInterval(async () => {
      try {
        const data = await api.pollState(session!.username, threadId);
        
        setState(prev => {
            if (isStateEqual(prev, data.state)) {
                return prev;
            }
            return { ...prev, ...data.state, lastUpdated: Date.now() };
        });
        
        setProjects(prev => prev.map(p => p.id === threadId ? { ...p, state: data.state, notes: data.state.project_notes } : p));
        
        // Stop polling if Paused, Success, or Error
        if (
            data.state.status === AgentStatus.SUCCESS || 
            data.state.status === AgentStatus.ERROR || 
            data.state.status === AgentStatus.PAUSED
        ) {
          stopPolling();
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 1500);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username && apiKey) {
        setSession({ username, apiKey });
    } else {
        alert("API Key is required.");
    }
  };

  const openCreateModal = () => {
    setNewProjectName(`BioModel-${Math.floor(Math.random() * 1000)}`);
    setNewProjectRequest('');
    setIsCreatingProject(true);
  };

  const submitNewProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectRequest.trim()) return;

    setIsSubmittingProject(true); // Start loading feedback
    
    try {
      const res = await api.startWorkflow(session!.username, newProjectName, newProjectRequest, session!.apiKey);
      
      const newProj: Project = {
          id: res.thread_id,
          name: newProjectName,
          notes: "",
          created_at: new Date().toISOString(),
          state: res.state
      };
      
      setProjects(prev => [newProj, ...prev]);
      setState(res.state);
      
      // Close modal first
      setIsCreatingProject(false);
      
      // Then open the project
      setActiveProjectId(res.thread_id);
      
      // Ensure we start polling immediately after creation
      startPolling(res.thread_id);
      
    } catch (error) {
      console.error("Failed to start workflow", error);
      alert("Failed to initialize project.");
    } finally {
      setIsSubmittingProject(false); // Stop loading
    }
  };

  const handleDeleteProject = async (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      if (window.confirm("Are you sure?")) {
          await api.deleteProject(session!.username, id);
          setProjects(prev => prev.filter(p => p.id !== id));
          if (activeProjectId === id) setActiveProjectId(null);
      }
  };

  const handleResume = async () => {
    if (!activeProjectId) return;
    try {
        // Optimistic UI update
        setState(prev => ({ ...prev, status: AgentStatus.RUNNING }));
        
        const res = await api.resumeWorkflow(session!.username, activeProjectId, session!.apiKey);
        setState(res.state);
        
        // Restart polling now that we are running again
        startPolling(activeProjectId);
    } catch(e) {
        console.error("Resume failed", e);
    }
  };

  const handleSaveNotes = async () => {
      if (!activeProjectId) return;
      await api.updateState(session!.username, activeProjectId, 'project_notes', workspaceNotes);
      setState(prev => ({...prev, project_notes: workspaceNotes}));
  };

  const handleStateUpdate = async (key: keyof AgentState | 'refine_request', value: any) => {
    if (!activeProjectId) return;
    
    // SPECIAL HANDLING: If key is 'refine_request', we call the Refine endpoint instead
    if (key === 'refine_request') {
        try {
            // Optimistic update to show busy state AND reset current node to Planner
            setState(prev => ({ 
              ...prev, 
              status: AgentStatus.RUNNING,
              currentNode: WorkflowNode.PLANNER 
            }));
            
            const res = await api.refinePlan(session!.username, activeProjectId, value, session!.apiKey);
            setState(res.state);
            startPolling(activeProjectId); // Ensure polling is active
        } catch (e) {
            console.error("Failed to refine plan:", e);
            alert("Refinement failed. Check console.");
        }
        return;
    }

    try {
      setState(prev => ({ ...prev, [key]: value, lastUpdated: Date.now() }));
      await api.updateState(session!.username, activeProjectId, key, value);
    } catch (e) {
      console.error(`Failed to update state for key: ${key}`, e);
    }
  };

  // --- Render Helper ---

  const LoadingState = ({ text }: { text: string }) => (
    <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-3">
        <div className="relative">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-ping absolute"/>
            <div className="w-3 h-3 bg-blue-500 rounded-full"/>
        </div>
        <span className="text-xs font-mono uppercase tracking-widest">{text}</span>
    </div>
  );

  // --- View: Login ---
  if (!session) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center relative overflow-hidden font-sans">
        <div className="w-full max-w-md z-10 p-8">
            <div className="flex flex-col items-center mb-10">
                <div className="w-32 h-32 rounded-2xl flex items-center justify-center mb-6 p-4 bg-white/5 border border-white/10">
                    <img src="/uoalogo.jpg" alt="FCUComposer Logo" className="w-full h-full object-contain" />
                </div>
                <h1 className="text-4xl font-bold text-white tracking-tight mb-2">FCUComposer</h1>
                <p className="text-slate-400 text-center text-sm font-medium tracking-wide uppercase text-blue-200/50">Bio-Architect</p>
            </div>
            <form onSubmit={handleLogin} className="bg-slate-900/40 backdrop-blur-xl border border-white/10 p-8 rounded-3xl shadow-2xl space-y-6">
                <div className="space-y-4">
                    <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 block ml-1">Operator ID</label>
                        <div className="relative">
                             <input className="w-full bg-[#0B1120] border border-slate-700 rounded-xl p-4 pl-11 text-white text-sm outline-none focus:border-blue-500 transition-all" 
                                placeholder="username" value={username} onChange={e => setUsername(e.target.value)} required />
                            <Terminal size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        </div>
                    </div>
                    <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 block ml-1">API Key</label>
                        <div className="relative">
                            <input type="password" className="w-full bg-[#0B1120] border border-slate-700 rounded-xl p-4 pl-11 text-white text-sm outline-none focus:border-emerald-500 transition-all" 
                                placeholder="sk-..." value={apiKey} onChange={e => setApiKey(e.target.value)} required />
                            <Key size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        </div>
                    </div>
                </div>
                <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-900/20">
                    Initialize <ChevronRight size={16} />
                </button>
            </form>
        </div>
      </div>
    );
  }

  // --- View: Dashboard ---
  if (!activeProjectId) {
    const filteredProjects = projects.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()));

    return (
        <div className="min-h-screen bg-[#020617] text-slate-200 font-sans selection:bg-blue-500/30">
            {isCreatingProject && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
                    <div className="bg-[#0B1120] border border-slate-700 rounded-2xl p-8 w-full max-w-lg shadow-2xl animate-fade-in relative">
                        <button onClick={() => !isSubmittingProject && setIsCreatingProject(false)} className="absolute top-4 right-4 text-slate-500 hover:text-white" disabled={isSubmittingProject}><X size={20} /></button>
                        <h3 className="text-xl font-bold text-white mb-6">New Project</h3>
                        <form onSubmit={submitNewProject} className="space-y-5">
                            <div>
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5 block">Project Name</label>
                                <input autoFocus className="w-full bg-[#0f172a] border border-slate-700 rounded-xl p-3 text-white text-sm focus:border-blue-500 outline-none"
                                    value={newProjectName} onChange={e => setNewProjectName(e.target.value)} required disabled={isSubmittingProject} />
                            </div>
                            <div>
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5 block">Objective</label>
                                <textarea className="w-full bg-[#0f172a] border border-slate-700 rounded-xl p-3 text-white text-sm focus:border-blue-500 outline-none h-32 resize-none"
                                    placeholder="e.g. Create a model of epithelial glucose transport" value={newProjectRequest} onChange={e => setNewProjectRequest(e.target.value)} required disabled={isSubmittingProject} />
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button type="button" onClick={() => setIsCreatingProject(false)} className="px-4 py-2 rounded-lg text-slate-400 hover:bg-slate-800 text-sm" disabled={isSubmittingProject}>Cancel</button>
                                <button 
                                    type="submit" 
                                    disabled={isSubmittingProject}
                                    className={`bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg text-sm font-bold flex items-center gap-2 ${isSubmittingProject ? 'opacity-80 cursor-not-allowed' : ''}`}
                                >
                                    {isSubmittingProject ? (
                                        <><Loader2 size={14} className="animate-spin"/> Creating...</>
                                    ) : (
                                        <><Play size={14} /> Create</>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <header className="h-20 border-b border-slate-800/60 bg-[#0B1120]/80 backdrop-blur-md sticky top-0 z-50 px-8 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center overflow-hidden">
                        <img src="/uoalogo.jpg" alt="Logo" className="w-full h-full object-contain" />
                    </div>
                    <h1 className="font-bold text-lg text-white">FCUComposer</h1>
                </div>
                <div className="flex-1 max-w-xl mx-8 relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input type="text" placeholder="Search projects..." className="w-full bg-[#020617] border border-slate-700/50 rounded-full py-2.5 pl-12 pr-4 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
                        value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                </div>
                <div className="flex items-center gap-6">
                    <span className="text-sm font-semibold text-white">{session.username}</span>
                    <button onClick={() => setSession(null)} className="p-2.5 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white"><LogOut size={18}/></button>
                </div>
            </header>

            <main className="max-w-7xl mx-auto p-8">
                <div className="flex justify-between items-end mb-10">
                    <h2 className="text-3xl font-bold text-white tracking-tight">Projects</h2>
                    <button onClick={openCreateModal} className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 shadow-lg hover:translate-y-[-2px] transition-all">
                        <Plus size={18} /> New Project
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredProjects.map(p => (
                        <div key={p.id} onClick={() => setActiveProjectId(p.id)} className="bg-[#0B1120] border border-slate-800 rounded-2xl p-6 cursor-pointer hover:border-blue-500/50 hover:shadow-2xl transition-all group relative overflow-hidden">
                            <div className="flex justify-between items-start mb-5">
                                <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center group-hover:bg-blue-900/20 group-hover:border-blue-500/30 transition-all">
                                    <FolderOpen size={20} className="text-slate-500 group-hover:text-blue-400" />
                                </div>
                                <div className="flex gap-2">
                                     <button 
                                        onClick={(e) => { e.stopPropagation(); setShowDashboardNotes(showDashboardNotes === p.id ? null : p.id); }}
                                        className={`p-2 rounded-lg transition-colors ${showDashboardNotes === p.id ? 'bg-indigo-500/20 text-indigo-300' : 'hover:bg-slate-800 text-slate-500 hover:text-indigo-400'}`}
                                     >
                                        <Info size={16} />
                                     </button>
                                     <button onClick={(e) => handleDeleteProject(e, p.id)} className="p-2 hover:bg-red-900/20 rounded-lg text-slate-500 hover:text-red-400 transition-colors">
                                        <Trash2 size={16} />
                                     </button>
                                </div>
                            </div>
                            <h3 className="text-lg font-bold text-slate-100 mb-1 group-hover:text-blue-400 transition-colors truncate">{p.name}</h3>
                            
                            {showDashboardNotes === p.id ? (
                                <div className="bg-slate-900/50 rounded-lg p-3 mb-4 text-xs text-slate-300 min-h-[60px] border border-indigo-500/20">
                                    <p className="font-bold text-indigo-400 mb-1 flex items-center gap-1"><StickyNote size={10}/> Notes:</p>
                                    {p.notes || <span className="italic opacity-50">No notes.</span>}
                                </div>
                            ) : (
                                <p className="text-sm text-slate-500 line-clamp-2 mb-4 h-10 leading-relaxed">{p.state.user_request}</p>
                            )}

                            <div className="flex items-center justify-between text-[10px] text-slate-600 pt-4 border-t border-slate-800/50 uppercase tracking-wider font-semibold">
                                <span>Updated {new Date(p.state.lastUpdated).toLocaleDateString()}</span>
                                <span className="group-hover:translate-x-1 transition-transform">Open &rarr;</span>
                            </div>
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
  }

  // --- View: Workspace ---
  return (
    <div className="h-screen bg-[#020617] text-slate-200 font-sans flex flex-col overflow-hidden selection:bg-blue-500/30">
        <header className="h-14 bg-[#0B1120] border-b border-slate-800/60 flex items-center justify-between px-4 shrink-0 z-30 shadow-md">
            <div className="flex items-center gap-4">
                <button onClick={() => setActiveProjectId(null)} className="text-slate-500 hover:text-white transition-colors hover:bg-slate-800 p-1.5 rounded-md">
                    <LayoutGrid size={20} />
                </button>
                <div className="h-5 w-px bg-slate-800"></div>
                <h1 className="font-bold text-sm text-slate-200 tracking-tight">{state.project_name}</h1>
            </div>
            
            <WorkflowStatus current={state.currentNode} status={state.status} />
            
            <div className="flex items-center gap-3">
                 <button onClick={() => setIsNotesOpen(true)} className="text-xs font-medium px-3 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-slate-400 hover:text-indigo-400 hover:border-indigo-500/50 flex items-center gap-2">
                    <StickyNote size={14} /> Notes
                </button>
                {state.status === AgentStatus.PAUSED && (
                    <button onClick={handleResume} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-1.5 rounded-md flex items-center gap-2 animate-pulse shadow-lg shadow-emerald-900/20">
                        <Play size={12} fill="currentColor"/> Continue
                    </button>
                )}
            </div>
        </header>

        <div className="flex-1 flex overflow-hidden relative">
            {/* Sidebar (Chat & Thoughts) */}
            <div className="w-[380px] flex flex-col border-r border-slate-800/60 bg-[#0B1120]/50 backdrop-blur-sm z-20">
                {/* Tab Header */}
                <div className="flex border-b border-slate-800/60 bg-[#0B1120]">
                    <button 
                        onClick={() => setActiveSidebarTab('chat')}
                        className={`flex-1 py-3 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-colors ${activeSidebarTab === 'chat' ? 'text-blue-400 border-b-2 border-blue-500 bg-slate-900/30' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <MessageSquare size={14} /> Agent Stream
                    </button>
                    <button 
                        onClick={() => setActiveSidebarTab('thoughts')}
                        className={`flex-1 py-3 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-colors ${activeSidebarTab === 'thoughts' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-slate-900/30' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <BrainCircuit size={14} /> Thoughts
                    </button>
                </div>

                {activeSidebarTab === 'chat' ? (
                    // Chat View
                    <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-800">
                        {state.messages.map((msg, i) => (
                            <div key={i} className="flex gap-4 animate-fade-in group">
                                <div className={`mt-0.5 w-6 h-6 rounded-md flex items-center justify-center shrink-0 border text-[10px] font-bold shadow-lg
                                    ${msg.role === 'agent' ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-slate-800 border-slate-700 text-slate-300'}`}>
                                    {msg.role === 'agent' ? 'AI' : 'ME'}
                                </div>
                                <div className="space-y-1 max-w-[85%]">
                                    <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex justify-between">
                                        <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    <div className="text-xs leading-relaxed text-slate-300 markdown-prose">
                                        <ReactMarkdown
                                            components={{
                                                h1: ({node, ...props}) => <h1 className="text-sm font-bold text-white mt-2 mb-1" {...props} />,
                                                h2: ({node, ...props}) => <h2 className="text-xs font-bold text-white mt-2 mb-1" {...props} />,
                                                h3: ({node, ...props}) => <h3 className="text-xs font-semibold text-white mt-1" {...props} />,
                                                p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                                                ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 pl-1" {...props} />,
                                                ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 pl-1" {...props} />,
                                                li: ({node, ...props}) => <li className="mb-0.5" {...props} />,
                                                code: ({node, ...props}) => <code className="bg-slate-800 text-emerald-400 px-1 py-0.5 rounded font-mono text-[10px]" {...props} />,
                                                pre: ({node, ...props}) => <pre className="bg-slate-800 p-2 rounded-lg my-2 overflow-x-auto text-[10px] scrollbar-thin scrollbar-thumb-slate-600" {...props} />,
                                                blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-indigo-500 pl-2 italic text-slate-400 my-2" {...props} />,
                                            }}
                                        >
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div ref={(el) => el?.scrollIntoView({ behavior: 'smooth' })} />
                    </div>
                ) : (
                    // Thoughts View
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
                        {[
                            { title: "Planner Thoughts", content: state.planner_thoughts, icon: "A" },
                            { title: "Physicist Thoughts", content: state.physicist_thoughts, icon: "P" },
                            { title: "Composer Thoughts", content: state.composer_thoughts, icon: "M" }, // <--- New Entry
                            { title: "Curator Thoughts", content: state.curator_thoughts, icon: "C" },
                            { title: "Analyst Thoughts", content: state.analyst_thoughts, icon: "V" }
                        ].map((thought, idx) => thought.content ? (
                            <div key={idx} className="bg-slate-900/50 rounded-lg border border-slate-700/50 overflow-hidden mb-4">
                                <div className="bg-slate-800/50 px-3 py-2 border-b border-slate-700/50 flex items-center gap-2">
                                    <span className="w-5 h-5 rounded flex items-center justify-center bg-indigo-500/20 text-indigo-400 text-[10px] font-bold border border-indigo-500/30">{thought.icon}</span>
                                    <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider">{thought.title}</span>
                                </div>
                                <div className="p-3 text-[10px] font-mono text-slate-400 leading-relaxed max-h-64 overflow-y-auto">
                                    <ReactMarkdown>{thought.content}</ReactMarkdown>
                                </div>
                            </div>
                        ) : null)}
                        
                        {!state.planner_thoughts && !state.physicist_thoughts && !state.curator_thoughts && !state.analyst_thoughts && !state.composer_thoughts && (
                            <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-2">
                                <BrainCircuit size={24} className="opacity-20" />
                                <p className="text-xs">No reasoning traces available yet.</p>
                            </div>
                        )}
                    </div>
                )}

                <div className="p-4 border-t border-slate-800/60 bg-[#0B1120]">
                     <textarea readOnly value={state.user_request} className="w-full bg-[#020617] border border-slate-800 rounded-lg p-3 text-xs text-slate-400 resize-none focus:outline-none" rows={3}/>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col bg-[#0f172a] relative overflow-hidden">
              <div className="flex-1 p-6 overflow-hidden relative z-0 bg-slate-900/50">
                  {libraryRegistry ? (
                    <WorkflowEditor
                      agentState={state}
                      libraryRegistry={libraryRegistry}
                      onStateUpdate={handleStateUpdate}
                    />
                  ) : (
                    <LoadingState text="Loading Model Library..." />
                  )}
                </div>
                
                {isNotesOpen && (
                    <div className="absolute inset-y-0 right-0 w-[400px] bg-[#0B1120] border-l border-slate-800 shadow-2xl z-30 flex flex-col animate-slide-in-right">
                        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
                            <h3 className="font-bold text-sm text-white flex items-center gap-2"><StickyNote size={16} className="text-indigo-400"/> Research Notes</h3>
                            <button onClick={() => setIsNotesOpen(false)} className="text-slate-500 hover:text-white"><X size={18}/></button>
                        </div>
                        <div className="flex-1 p-4">
                            <textarea className="w-full h-full bg-slate-900/50 border border-slate-800 rounded-lg p-4 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/50 resize-none leading-relaxed"
                                placeholder="Log observations..." value={workspaceNotes} onChange={(e) => setWorkspaceNotes(e.target.value)} />
                        </div>
                        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end">
                             <button onClick={handleSaveNotes} className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg flex items-center gap-2">
                                <Save size={14} /> Save Notes
                             </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    </div>
  );
}