
import React from 'react';
import { Step2Data, Port, ParameterDef, LibraryModel } from '../types';
import { FunctionSquare, Network, BookMarked, Zap } from 'lucide-react';

interface Step2Props {
    data: Step2Data;
    libraryModels: LibraryModel[];
}

const Step2Physicist: React.FC<Step2Props> = ({ data, libraryModels }) => {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <section className="bg-blue-50 p-6 rounded-xl border border-blue-100 mb-6">
            <h2 className="text-lg font-bold text-blue-900 mb-2 flex items-center gap-2">
                <FunctionSquare className="h-5 w-5" />
                Physics Derivation
            </h2>
            <p className="text-blue-800">
                The physicist agent has derived the mathematical structures for the missing components identified in Step 1.
            </p>
        </section>

        {/* Generated Components Section */}
        <div className="grid gap-8">
            <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                <span className="bg-slate-200 text-slate-600 w-6 h-6 rounded flex items-center justify-center text-xs">A</span>
                Generated Theoretical Models
            </h3>
            {data.generated_components.map((comp) => (
                <div key={comp.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                    <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
                        <h3 className="text-lg font-semibold text-slate-800">{comp.id}</h3>
                        <p className="text-sm text-slate-600 mt-1">{comp.description}</p>
                    </div>
                    
                    <div className="p-6 grid lg:grid-cols-2 gap-8">
                        {/* Ports & Vars */}
                        <div className="space-y-6">
                            <div>
                                <h4 className="text-xs font-bold uppercase text-slate-400 mb-3 tracking-wider flex items-center gap-2">
                                    <Network className="h-3 w-3" /> Ports
                                </h4>
                                <div className="space-y-2">
                                    {(Object.entries(comp.ports) as [string, Port][]).map(([key, port]) => (
                                        <div key={key} className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded border border-slate-100">
                                            <span className="font-mono text-slate-700">{key}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-slate-500 italic">{port.mapped_variable}</span>
                                                <span className="px-1.5 py-0.5 bg-slate-200 text-slate-600 rounded text-xs">{port.units}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            
                            <div>
                                <h4 className="text-xs font-bold uppercase text-slate-400 mb-3 tracking-wider">Internal Parameters</h4>
                                <div className="space-y-2">
                                    {(Object.entries(comp.parameters) as [string, ParameterDef][]).map(([key, param]) => (
                                        <div key={key} className="text-sm border-l-2 border-emerald-400 pl-3">
                                            <div className="flex items-baseline gap-2">
                                                <span className="font-mono font-semibold text-slate-800">{key}</span>
                                                <span className="text-xs text-slate-400">({param.units})</span>
                                            </div>
                                            <p className="text-slate-500 text-xs mt-0.5">{param.description}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Equations */}
                        <div>
                             <h4 className="text-xs font-bold uppercase text-slate-400 mb-3 tracking-wider">Governing Equations</h4>
                             <div className="bg-slate-900 rounded-lg p-4 font-mono text-sm text-emerald-400 overflow-x-auto shadow-inner">
                                {comp.structured_equations.map((eq, idx) => (
                                    <div key={idx} className="mb-2 last:mb-0">
                                        <span className="text-slate-300">{eq.lhs}</span>
                                        <span className="text-slate-500 mx-2">=</span>
                                        <span>{eq.rhs}</span>
                                    </div>
                                ))}
                             </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>

        {/* Library Models Section */}
        {libraryModels.length > 0 && (
            <div className="grid gap-8 mt-12">
                <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                    <span className="bg-slate-200 text-slate-600 w-6 h-6 rounded flex items-center justify-center text-xs">B</span>
                    Selected Library Models
                </h3>
                {libraryModels.map((model, idx) => (
                    <div key={idx} className="bg-slate-50 rounded-xl shadow-sm border border-slate-200 overflow-hidden relative">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            <BookMarked className="h-24 w-24 text-slate-900" />
                        </div>
                        <div className="px-6 py-4 border-b border-slate-200 bg-white">
                             <div className="flex items-center gap-2">
                                <h3 className="text-lg font-semibold text-slate-800">
                                    {model.filepath.split('/').pop()?.replace('.cellml', '')}
                                </h3>
                                <span className="bg-slate-100 text-slate-500 text-xs px-2 py-0.5 rounded border border-slate-200">Library Asset</span>
                             </div>
                             <p className="text-sm text-slate-600 mt-1">{model.description}</p>
                        </div>
                        
                        <div className="p-6 grid lg:grid-cols-2 gap-8 relative z-10">
                             <div>
                                <h4 className="text-xs font-bold uppercase text-slate-400 mb-3 tracking-wider flex items-center gap-2">
                                    <Zap className="h-3 w-3" /> Constitutive Laws
                                </h4>
                                <div className="space-y-4">
                                    {model.constitutive_laws.map((law: any, i: number) => (
                                        <div key={i} className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
                                            <div className="text-sm font-bold text-slate-700 mb-1">{law.name}</div>
                                            <div className="font-mono text-xs text-slate-600 bg-slate-50 p-2 rounded">{law.equation}</div>
                                        </div>
                                    ))}
                                </div>
                             </div>

                             <div>
                                <h4 className="text-xs font-bold uppercase text-slate-400 mb-3 tracking-wider flex items-center gap-2">
                                    <Network className="h-3 w-3" /> State Variables
                                </h4>
                                <div className="grid grid-cols-2 gap-2">
                                    {Object.entries(model.variables).map(([k, v]: any) => (
                                        <div key={k} className="flex flex-col bg-white border border-slate-200 p-2 rounded text-xs">
                                            <span className="font-mono font-bold text-slate-800">{k}</span>
                                            <span className="text-slate-400 truncate" title={v.semantic_match}>{v.semantic_match}</span>
                                        </div>
                                    ))}
                                </div>
                             </div>
                        </div>
                    </div>
                ))}
            </div>
        )}
    </div>
  );
};

export default Step2Physicist;
