import React, { useState } from 'react';
import { INITIAL_STEP_1, INITIAL_STEP_2, INITIAL_STEP_3 } from '../constants';
import Sidebar from './Sidebar';
import Step1Architect from './Step1Architect';
import Step2Physicist from './Step2Physicist';
import Step3Curator from './Step3Curator';
import Step5Analyst from './Step5Analyst';
import JsonEditor from './JsonEditor';
import ModelDetails from './ModelDetails';
import MermaidRenderer from './MermaidRenderer'; // Import Mermaid Renderer
import { Pencil, Code, AlertOctagon, Loader2, FileTerminal, Network, Eye } from 'lucide-react';
import { AgentState, LibraryModel, Step1Data } from '../types';

// --- Error Boundary ---
interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("WorkflowEditor Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-red-50/50">
          <AlertOctagon className="h-12 w-12 text-red-500 mb-4" />
          <h2 className="text-lg font-bold text-slate-800">Component Error</h2>
          <p className="text-slate-500 mt-2 max-w-md">{this.state.error?.message}</p>
          <button 
            onClick={() => this.setState({ hasError: false })}
            className="mt-4 px-4 py-2 bg-slate-800 text-white rounded hover:bg-slate-700 text-sm"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

interface WorkflowEditorProps {
  agentState: AgentState;
  libraryRegistry: Record<string, LibraryModel>;
  onStateUpdate: (key: keyof AgentState | 'refine_request', value: any) => void;
}

type ComposerTab = 'code' | 'logs' | 'diagram';

const WorkflowEditor: React.FC<WorkflowEditorProps> = ({ agentState, libraryRegistry, onStateUpdate }) => {
  const [activeTab, setActiveTab] = useState<number>(1);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [composerView, setComposerView] = useState<ComposerTab>('code');
  
  const step1Data = agentState.spec;
  const step2Data = agentState.physicist_output;
  const composerCode = agentState.generated_code;
  const composerLogs = agentState.composer_logs;
  const compositeModel = agentState.composite_model;
  const step4Data = agentState.curator_output;
  const analystReport = agentState.simulation_report;

  const libraryList = Object.keys(libraryRegistry);

  const handleReset = () => {
    if (activeTab === 1) onStateUpdate('spec', INITIAL_STEP_1);
    if (activeTab === 2) onStateUpdate('physicist_output', INITIAL_STEP_2);
    if (activeTab === 4) onStateUpdate('curator_output', INITIAL_STEP_3);
    setIsEditing(false);
  };

  const handleSave = (newData: any) => {
    if (activeTab === 1) {
        triggerRefinement(newData);
    } else {
        if (activeTab === 2) onStateUpdate('physicist_output', newData);
        if (activeTab === 4) onStateUpdate('curator_output', newData);
    }
    setIsEditing(false);
  };
  
  const triggerRefinement = async (updatedSpec: Step1Data) => {
      onStateUpdate('spec', updatedSpec);
  };

  const getCurrentData = () => {
    if (activeTab === 1) return step1Data || {};
    if (activeTab === 2) return step2Data || {};
    if (activeTab === 4) return step4Data || {};
    return {};
  };

  const handleMatrixUpdate = (row: string, col: string, score: number = 1.0) => {
    if (!step1Data) return;
    const newSpec = { ...step1Data };
    const newMatrix = { ...newSpec.match_matrix };
    let entries = [...newMatrix.non_zero_entries];
    
    const existingIndex = entries.findIndex(e => e.row === row && e.col === col);
    const isAlreadySelected = existingIndex >= 0;

    if (isAlreadySelected) {
        entries[existingIndex].score = score;
    } else {
        entries = entries.filter(e => e.col !== col);
        entries.push({ row, col, score: score });
    }

    if (score === 0 && isAlreadySelected) {
        entries = entries.filter(e => !(e.row === row && e.col === col));
    }

    newMatrix.non_zero_entries = entries;
    
    if (newSpec.mechanisms) {
        const newMechanisms = newSpec.mechanisms.map(comp => {
            if (comp.name === col || comp.id === col) { 
                const selectedEntry = entries.find(e => e.col === col);
                return {
                    ...comp,
                    library_id: selectedEntry ? selectedEntry.row : null,
                    library_match_reason: selectedEntry ? `User assigned ${selectedEntry.row} (Score: ${selectedEntry.score.toFixed(1)})` : "No model assigned"
                };
            }
            return comp;
        });
        newSpec.mechanisms = newMechanisms;
    }
    
    newSpec.match_matrix = newMatrix;
    onStateUpdate('spec', newSpec);
  };
  
  const getModelDetails = (modelName: string): LibraryModel | null => {
    return libraryRegistry[modelName] || null;
  };

  const getSelectedLibraryModels = (): (LibraryModel | null)[] => {
      if (!step1Data || !step1Data.mechanisms) return [];
      const selectedIDs = step1Data.mechanisms
        .map(c => c.library_id)
        .filter((id): id is string => id !== null);
      return selectedIDs.map(id => getModelDetails(id));
  };
  
  if (!agentState.spec) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-slate-500 bg-slate-50">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-500" />
            <span>Waiting for Architect analysis...</span>
        </div>
      )
  }

  return (
    <div className="flex h-full bg-slate-50 font-sans overflow-hidden">
      <Sidebar 
        onSelectModel={setSelectedModel} 
        selectedModel={selectedModel}
        libraryList={libraryList}
      />

      {selectedModel && (
         <ErrorBoundary>
             <ModelDetails 
                model={getModelDetails(selectedModel)!} 
                onClose={() => setSelectedModel(null)} 
             />
         </ErrorBoundary>
      )}

      <main className="flex-1 flex flex-col min-w-0 h-full relative transition-all">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 z-30 shadow-sm flex-shrink-0">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0 no-scrollbar">
             {[1, 2, 3, 4, 5].map((step) => {
                let label = "";
                if (step === 1) label = "Architect: Analysis";
                if (step === 2) label = "Physicist: Equations";
                if (step === 3) label = "Composer: Assembly";
                if (step === 4) label = "Curator: Parameters";
                if (step === 5) label = "Analyst: Validation";

                return (
                    <button
                    key={step}
                    onClick={() => { setActiveTab(step); setIsEditing(false); }}
                    className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 whitespace-nowrap border
                        ${activeTab === step 
                        ? 'bg-slate-800 text-white border-slate-800 shadow-md' 
                        : 'bg-white text-slate-500 hover:bg-slate-50 border-slate-200 hover:border-slate-300'
                        }`}
                    >
                    <span className={`flex items-center justify-center w-5 h-5 rounded-full text-[10px] ${activeTab === step ? 'bg-slate-600 text-white' : 'bg-slate-200 text-slate-600'}`}>
                        {step}
                    </span>
                    {label}
                    </button>
                );
             })}
          </div>

          <div className="flex items-center gap-3">
            {(activeTab === 1 || activeTab === 2 || activeTab === 4) && !isEditing && (
                <button 
                  onClick={() => setIsEditing(true)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 hover:text-slate-800 rounded-lg shadow-sm transition-all"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit JSON
                </button>
            )}
             <div className="h-6 w-px bg-slate-200 mx-1 hidden md:block"></div>
             <div className="flex -space-x-2 overflow-hidden">
                <div title="Architect Agent" className="inline-block h-8 w-8 rounded-full ring-2 ring-white bg-gradient-to-br from-indigo-400 to-indigo-600 flex items-center justify-center text-xs text-white font-bold shadow-sm cursor-help">A</div>
                <div title="Physicist Agent" className="inline-block h-8 w-8 rounded-full ring-2 ring-white bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center text-xs text-white font-bold shadow-sm cursor-help">P</div>
                <div title="Curator Agent" className="inline-block h-8 w-8 rounded-full ring-2 ring-white bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-xs text-white font-bold shadow-sm cursor-help">C</div>
             </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto bg-slate-50/50">
            <div className="max-w-7xl mx-auto p-4 md:p-8 h-full">
            <ErrorBoundary>
                {isEditing ? (
                    <JsonEditor 
                        data={getCurrentData()} 
                        onSave={handleSave} 
                        onCancel={() => setIsEditing(false)}
                        onReset={handleReset}
                    />
                ) : (
                    <>
                    {/* Step 1: Architect */}
                    {activeTab === 1 && (
                        step1Data ? (
                            <Step1Architect 
                                data={step1Data} 
                                onMatrixUpdate={handleMatrixUpdate} 
                                onSave={() => onStateUpdate('refine_request', step1Data)}
                            />
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                                <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-500" />
                                <p>Loading Architecture...</p>
                            </div>
                        )
                    )}

                    {/* Step 2: Physicist */}
                    {activeTab === 2 && (
                        step2Data ? (
                            <Step2Physicist 
                                data={step2Data} 
                                libraryModels={getSelectedLibraryModels().filter(m => m !== null) as LibraryModel[]}
                            />
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                                <Loader2 className="w-8 h-8 animate-spin mb-4 text-purple-500" />
                                <p>Waiting for Physicist to generate equations...</p>
                            </div>
                        )
                    )}

                    {/* Step 3: Composer */}
                    {activeTab === 3 && (
                        <div className="space-y-4 h-full flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                                    <Code className="h-5 w-5 text-indigo-600" />
                                    Model Assembly
                                </h3>
                                <div className="flex bg-white rounded-lg border border-slate-200 p-1 gap-1">
                                    <button 
                                        onClick={() => setComposerView('code')}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${composerView === 'code' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}
                                    >
                                        <Code className="h-3.5 w-3.5" /> Code
                                    </button>
                                    <button 
                                        onClick={() => setComposerView('diagram')}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${composerView === 'diagram' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}
                                    >
                                        <Network className="h-3.5 w-3.5" /> BG Diagram
                                    </button>
                                    <button 
                                        onClick={() => setComposerView('logs')}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${composerView === 'logs' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'}`}
                                    >
                                        <FileTerminal className="h-3.5 w-3.5" /> Logs
                                    </button>
                                </div>
                            </div>
                            
                            <div className="flex-1 relative rounded-xl overflow-hidden border border-slate-700 shadow-xl bg-[#0d1117]">
                                {composerCode ? (
                                    <>
                                        {composerView === 'code' && (
                                            <pre className="absolute inset-0 p-6 overflow-auto text-sm font-mono text-slate-300 leading-relaxed scrollbar-thin scrollbar-thumb-slate-700">
                                                {composerCode}
                                            </pre>
                                        )}
                                        {composerView === 'logs' && (
                                            <pre className="absolute inset-0 p-6 overflow-auto text-xs font-mono text-emerald-400 leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 whitespace-pre-wrap">
                                                {composerLogs || "No logs available."}
                                            </pre>
                                        )}
                                        {composerView === 'diagram' && (
                                            <div className="absolute inset-0 bg-white flex items-center justify-center overflow-auto p-4">
                                                {/* Use MermaidRenderer instead of dangerouslySetInnerHTML for SVG */}
                                                {compositeModel?.mermaid ? (
                                                    <MermaidRenderer chart={compositeModel.mermaid} />
                                                ) : (
                                                    <div className="flex flex-col items-center text-slate-400">
                                                        <Network className="h-12 w-12 mb-4 opacity-20" />
                                                        <p>No visual diagram available.</p>
                                                        <p className="text-xs mt-1 text-slate-500">The composition engine did not generate a visual model.</p>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
                                        <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-400 opacity-50" />
                                        <p>Waiting for Composer assembly...</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 4: Curator */}
                    {activeTab === 4 && (
                        step4Data ? (
                            <Step3Curator data={step4Data} />
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                                <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
                                <p>Waiting for Curator to parameterize...</p>
                            </div>
                        )
                    )}

                    {/* Step 5: Analyst */}
                    {activeTab === 5 && (
                        analystReport ? (
                            <Step5Analyst report={analystReport} />
                        ) : (
                            <div className="bg-white p-12 rounded-xl border border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400">
                                <Loader2 className="h-10 w-10 mb-3 text-emerald-500 animate-spin opacity-50" />
                                <p>Waiting for Analyst validation...</p>
                            </div>
                        )
                    )}
                    </>
                )}
            </ErrorBoundary>
            </div>
        </div>
      </main>
    </div>
  );
}

export default WorkflowEditor;