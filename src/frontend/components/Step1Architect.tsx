
import React, { useState } from 'react';
import { Step1Data } from '../types';
import MermaidRenderer from './MermaidRenderer';
import ConfidenceMatrix from './ConfidenceMatrix';
import { CheckCircle, AlertTriangle, ArrowRight, Save } from 'lucide-react';

interface Step1Props {
    data: Step1Data;
    onMatrixUpdate: (row: string, col: string, score?: number) => void;
    onSave?: () => void;
}

const Step1Architect: React.FC<Step1Props> = ({ data, onMatrixUpdate, onSave }) => {
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const handleUpdate = (row: string, col: string, score?: number) => {
      onMatrixUpdate(row, col, score);
      setHasUnsavedChanges(true);
  }

  const handleSaveClick = () => {
      if (onSave) onSave();
      setHasUnsavedChanges(false);
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
      
      {/* Introduction */}
      <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full -mr-16 -mt-16 blur-2xl opacity-50"></div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2 relative z-10">{data.model_name}</h2>
        <p className="text-slate-600 leading-relaxed text-lg relative z-10">{data.explanation}</p>
        <div className="mt-4 flex items-center gap-2 text-sm text-slate-500 bg-slate-50 inline-flex px-3 py-1.5 rounded-full border border-slate-200">
            <span className="font-semibold text-slate-700">Goal:</span>
            {data.next_step_context.split('.')[0]}.
        </div>
      </section>

      {/* Diagram */}
      <section>
        <div className="flex items-center justify-between mb-4">
             <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                <span className="bg-slate-200 text-slate-600 w-6 h-6 rounded flex items-center justify-center text-xs">1</span>
                Topological Analysis
            </h3>
        </div>
        <MermaidRenderer chart={data.mermaid_source} />
      </section>

      {/* Matrix */}
      <section>
          <div className="flex items-center justify-between mb-4">
            <div>
                <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                    <span className="bg-slate-200 text-slate-600 w-6 h-6 rounded flex items-center justify-center text-xs">2</span>
                    Library Match & Selection
                </h3>
                <p className="text-slate-500 text-sm mt-1">
                    Click a cell to assign a library model. Click again to adjust confidence.
                </p>
            </div>
            {hasUnsavedChanges && (
                <button 
                    onClick={handleSaveClick}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg shadow-md hover:bg-emerald-700 transition-all animate-pulse"
                >
                    <Save className="h-4 w-4" /> Save Configuration
                </button>
            )}
          </div>
          <ConfidenceMatrix matrix={data.match_matrix} onCellClick={handleUpdate} />
      </section>

      {/* Components Grid */}
      <section>
        <h3 className="text-lg font-bold text-slate-700 mb-4 flex items-center gap-2">
             <span className="bg-slate-200 text-slate-600 w-6 h-6 rounded flex items-center justify-center text-xs">3</span>
             Component Resolution
        </h3>
        <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-emerald-50/50 p-6 rounded-xl border border-emerald-100">
            <h3 className="text-emerald-900 font-bold mb-4 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-emerald-600" /> Matched Components
            </h3>
            <ul className="space-y-3">
                {data.mechanisms && data.mechanisms.filter(c => c.library_id).map(c => (
                    <li key={c.id} className="bg-white p-4 rounded-lg border border-emerald-100 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-2">
                            <span className="font-bold text-slate-800">{c.name}</span>
                            <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-2 py-1 rounded border border-emerald-200">
                                {c.library_id}
                            </span>
                        </div>
                        <p className="text-sm text-slate-600 leading-snug">{c.match_reason}</p>
                    </li>
                ))}
            </ul>
            </div>

            <div className="bg-amber-50/50 p-6 rounded-xl border border-amber-100">
            <h3 className="text-amber-900 font-bold mb-4 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" /> Theoretical Components
            </h3>
            <ul className="space-y-3">
                {data.mechanisms && data.mechanisms.filter(c => !c.library_id).map(c => (
                    <li key={c.id} className="bg-white p-4 rounded-lg border border-amber-100 shadow-sm hover:shadow-md transition-shadow">
                        <span className="font-bold text-slate-800 block mb-2">{c.name}</span>
                        <p className="text-sm text-slate-600 leading-snug">{c.match_reason}</p>
                        <div className="mt-3 flex items-center gap-2 text-xs font-medium text-amber-700">
                            <ArrowRight className="h-3 w-3" />
                            Requires Physics Generation
                        </div>
                    </li>
                ))}
            </ul>
            </div>
        </div>
      </section>

    </div>
  );
};

export default Step1Architect;
