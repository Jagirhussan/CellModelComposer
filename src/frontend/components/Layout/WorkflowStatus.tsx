import React from 'react';
import { Check, Loader2, Circle, ArrowRight } from 'lucide-react';
import { WorkflowNode, AgentStatus } from '../../types';

interface WorkflowStatusProps {
  current: WorkflowNode;
  status: AgentStatus;
}

const STEPS = [
  { id: WorkflowNode.PLANNER, label: 'Planner' },
  { id: WorkflowNode.RETRIEVER, label: 'Retriever' },
  { id: WorkflowNode.COMPOSER, label: 'Composer' },
  { id: WorkflowNode.RESEARCHER, label: 'Researcher' },
  { id: WorkflowNode.ANALYST, label: 'Analyst' }
];

export const WorkflowStatus: React.FC<WorkflowStatusProps> = ({ current, status }) => {
  const currentIdx = current === WorkflowNode.COMPLETE ? STEPS.length : STEPS.findIndex(s => s.id === current);

  return (
    <div className="w-full bg-[#0B1120] border-b border-slate-800/60 backdrop-blur px-6 py-4 flex items-center justify-center shadow-lg z-10">
      <div className="flex items-center gap-4">
        {STEPS.map((step, idx) => {
          const isActive = step.id === current;
          const isCompleted = idx < currentIdx || current === WorkflowNode.COMPLETE;
          const isPending = !isActive && !isCompleted;

          return (
            <div key={step.id} className="flex items-center">
              <div 
                className={`
                  flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-500
                  ${isActive 
                    ? 'bg-blue-900/20 border-blue-500/50 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.2)] scale-105' 
                    : isCompleted 
                      ? 'bg-emerald-900/10 border-emerald-900/50 text-emerald-500/80' 
                      : 'bg-slate-900/50 border-slate-800 text-slate-600'}
                `}
              >
                {isActive && status === AgentStatus.RUNNING ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : isCompleted ? (
                  <Check size={14} />
                ) : (
                  <Circle size={14} className={isActive ? 'fill-blue-500/20' : ''} />
                )}
                <span className="text-xs font-semibold tracking-wide uppercase">{step.label}</span>
              </div>
              
              {idx < STEPS.length - 1 && (
                <div className={`mx-2 h-[1px] w-8 transition-colors duration-500 ${isCompleted ? 'bg-emerald-900' : 'bg-slate-800'}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};