import React, { useState } from 'react';
import { FileCode, ChevronLeft, ChevronRight, Layers } from 'lucide-react';

interface SidebarProps {
  onSelectModel: (modelName: string) => void;
  selectedModel: string | null;
  libraryList: string[];
}

const Sidebar: React.FC<SidebarProps> = ({ onSelectModel, selectedModel, libraryList }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div 
      className={`${isCollapsed ? 'w-16' : 'w-72'} flex-shrink-0 bg-slate-900 text-slate-300 h-screen flex flex-col transition-all duration-300 ease-in-out border-r border-slate-800 relative shadow-xl`}
    >
      {/* Toggle Button */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-8 bg-slate-800 text-slate-400 hover:text-white border border-slate-700 rounded-full p-1 shadow-md z-50 transform hover:scale-110 transition-transform"
      >
        {isCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </button>

      {/* Header with Custom Logo */}
      <div className={`p-4 border-b border-slate-800 flex items-center ${isCollapsed ? 'justify-center' : 'justify-start'} h-20`}>
        {/* Logo Image */}
        <img 
          src="/uoalogo.jpg" 
          alt="Logo" 
          className={`object-contain transition-all duration-300 ${isCollapsed ? 'h-8 w-8' : 'h-12 w-auto'}`} 
        />
        
        {!isCollapsed && (
          <div className="ml-3 overflow-hidden whitespace-nowrap">
            <h1 className="text-white font-bold text-base tracking-tight">BioSim Agent</h1>
            <p className="text-[10px] text-slate-500 font-medium">Bond Graph Modeler v1.2</p>
          </div>
        )}
      </div>

      {/* Library List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent py-4">
        {!isCollapsed && (
          <h2 className="px-4 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-2">
            <Layers className="h-3 w-3" /> Available Models
          </h2>
        )}
        
        <div className="space-y-1 px-2">
           {/* Hardcoded 'An01' for demo purposes */}
           <button
              onClick={() => onSelectModel("An01")}
              title={isCollapsed ? "An01" : undefined}
              className={`w-full text-left px-2 py-2.5 rounded-lg text-sm transition-all flex items-center gap-3 
                ${selectedModel === "An01" 
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/20 font-medium' 
                  : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'}`}
           >
             <div className="flex-shrink-0 flex items-center justify-center w-6 h-6">
                <FileCode className={`h-4 w-4 ${selectedModel === "An01" ? 'text-white' : 'text-slate-500'}`} />
             </div>
             {!isCollapsed && <span className="truncate">An01</span>}
           </button>
           
           {libraryList.filter(m => m !== 'An01').map(model => (
             <button
                key={model}
                onClick={() => onSelectModel(model)}
                title={isCollapsed ? model : undefined}
                className={`w-full text-left px-2 py-2 rounded-lg text-sm transition-all flex items-center gap-3 
                  ${selectedModel === model 
                    ? 'bg-indigo-600 text-white shadow-md font-medium' 
                    : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200 group'}`}
             >
                <div className="flex-shrink-0 flex items-center justify-center w-6 h-6">
                    <div className={`w-1.5 h-1.5 rounded-full transition-colors ${selectedModel === model ? 'bg-white' : 'bg-slate-600 group-hover:bg-slate-500'}`} />
                </div>
                {!isCollapsed && <span className="truncate">{model}</span>}
             </button>
           ))}
        </div>
      </div>
      
      {/* Footer */}
      {!isCollapsed && (
        <div className="p-4 border-t border-slate-800 text-[10px] text-slate-600 text-center">
          Powered by Auckland Bioengineering Institute
        </div>
      )}
    </div>
  );
};

export default Sidebar;