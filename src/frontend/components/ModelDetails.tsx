import React from 'react';
import { LibraryModel } from '../types';
import { Thermometer, Zap, Activity, ArrowRightLeft, Database } from 'lucide-react';

interface ModelDetailsProps {
  model: LibraryModel;
  onClose: () => void;
}

const ModelDetails: React.FC<ModelDetailsProps> = ({ model, onClose }) => {
  // Defensive check
  if (!model) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-xl shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-start bg-white sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-xl font-bold text-slate-800">{model.filepath?.split('/').pop()?.replace('.cellml', '') || 'Unknown Model'}</h2>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200">
                v{model.semantic_version || '1.0'}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {model.keywords?.map(k => (
                <span key={k} className="text-xs text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                  {k}
                </span>
              ))}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto p-6 space-y-6">
          
          {/* Description */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <p className="text-sm text-slate-600 leading-relaxed">{model.description || "No description available."}</p>
          </div>

          {/* Constants & Properties */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Global Constants */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Thermometer className="w-3 h-3" /> Global Constants
              </h3>
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                {model.global_constants && Object.entries(model.global_constants).length > 0 ? (
                    Object.entries(model.global_constants).map(([k, v]: any, idx) => (
                    <div key={k} className={`flex justify-between items-center p-3 text-sm ${idx !== 0 ? 'border-t border-slate-100' : ''}`}>
                        <span className="font-mono font-medium text-slate-700">{k}</span>
                        <div className="text-right">
                        <div className="font-semibold text-slate-900">{v.value}</div>
                        <div className="text-[10px] text-slate-400">{v.units}</div>
                        </div>
                    </div>
                    ))
                ) : (
                    <div className="p-3 text-xs text-slate-400 italic">None defined</div>
                )}
              </div>
            </div>

            {/* Ports */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <ArrowRightLeft className="w-3 h-3" /> Interface Ports
              </h3>
              <div className="space-y-2">
                {model.ports && Object.entries(model.ports).length > 0 ? (
                    Object.entries(model.ports).map(([k, v]: any) => (
                    <div key={k} className="flex items-center justify-between bg-white border border-slate-200 p-2.5 rounded-lg shadow-sm">
                        <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${v.direction?.includes('in') ? 'bg-indigo-400' : 'bg-orange-400'}`} />
                        <span className="font-mono text-sm font-semibold text-slate-700">{k}</span>
                        </div>
                        <span className="text-[10px] uppercase font-medium text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                        {v.direction?.replace('positive_', '') || 'N/A'}
                        </span>
                    </div>
                    ))
                ) : (
                    <div className="text-xs text-slate-400 italic">No ports defined</div>
                )}
              </div>
            </div>
          </div>

          {/* Variables & Laws */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Activity className="w-3 h-3" /> State Variables
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {model.variables && Object.keys(model.variables).length > 0 ? (
                    Object.entries(model.variables).slice(0, 8).map(([k, v]: any) => (
                    <div key={k} className="flex flex-col bg-white border border-slate-200 p-3 rounded-lg hover:border-emerald-300 transition-colors">
                        <span className="font-mono text-sm font-bold text-slate-800">{k}</span>
                        <span className="text-xs text-slate-500 mt-1 truncate" title={v.semantic_match}>
                        {v.semantic_match?.replace(/_/g, ' ') || 'Unknown'}
                        </span>
                    </div>
                    ))
                ) : (
                    <div className="col-span-2 text-xs text-slate-400 italic">No variables exposed</div>
                )}
                {model.variables && Object.keys(model.variables).length > 8 && (
                   <div className="flex items-center justify-center text-xs text-slate-400 italic">
                      + {Object.keys(model.variables).length - 8} more variables
                   </div>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Zap className="w-3 h-3" /> Constitutive Laws
              </h3>
               <div className="space-y-2">
                  {model.constitutive_laws && model.constitutive_laws.length > 0 ? (
                      model.constitutive_laws.map((law: any, i: number) => (
                        <div key={i} className="bg-slate-800 text-slate-200 p-3 rounded-lg text-xs font-mono shadow-sm">
                            <div className="text-emerald-400 font-bold mb-1">{law.name}</div>
                            <div className="opacity-70 truncate" title={law.equation}>{law.equation}</div>
                        </div>
                      ))
                  ) : (
                      <div className="text-xs text-slate-400 italic">None defined</div>
                  )}
               </div>
            </div>
          </div>

        </div>
        
        {/* Footer */}
        <div className="bg-slate-50 p-4 border-t border-slate-200 text-xs text-center text-slate-400 flex justify-between items-center">
            <span>ID: {model.filepath}</span>
            <span className="flex items-center gap-1"><Database className="w-3 h-3"/> CellML Repository</span>
        </div>
      </div>
    </div>
  );
};

export default ModelDetails;