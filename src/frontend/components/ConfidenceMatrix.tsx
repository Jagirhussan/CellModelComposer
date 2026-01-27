import React, { useState, useRef, useEffect } from 'react';
import { MatchMatrix } from '../types';
import { Settings2, X } from 'lucide-react';

interface ConfidenceMatrixProps {
  matrix: MatchMatrix;
  onCellClick?: (row: string, col: string, score?: number) => void;
}

const ConfidenceMatrix: React.FC<ConfidenceMatrixProps> = ({ matrix, onCellClick }) => {
  // Defensive check for incomplete data during state transitions
  if (!matrix || !matrix.rows || !matrix.columns) {
      return (
          <div className="p-8 text-center border border-slate-200 rounded-xl bg-slate-50 text-slate-400 text-sm italic">
              Confidence matrix data is currently unavailable.
          </div>
      );
  }

  const { rows, columns, non_zero_entries } = matrix;
  const [editingCell, setEditingCell] = useState<{row: string, col: string, score: number} | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const getScore = (row: string, col: string): number => {
    // Safety check for non_zero_entries array
    const entries = non_zero_entries || [];
    const entry = entries.find(e => e.row === row && e.col === col);
    return entry ? entry.score : 0;
  };

  const handleCellClick = (row: string, col: string, currentScore: number) => {
    if (!onCellClick) return;

    // If clicking a cell that is already selected (score 1.0 or user defined), open editor
    // Or if clicking an empty cell, select it first (set to 1.0) then user can edit
    if (currentScore > 0) {
        setEditingCell({ row, col, score: currentScore });
    } else {
        // Select it immediately with default 1.0
        onCellClick(row, col, 1.0);
        // Optionally open editor immediately? Let's wait for user to click again to edit
        // or we can setEditingCell immediately. Let's set it immediately for smoother UX.
        setEditingCell({ row, col, score: 1.0 });
    }
  };

  const handleScoreChange = (newScore: number) => {
    if (editingCell && onCellClick) {
        setEditingCell({ ...editingCell, score: newScore });
        onCellClick(editingCell.row, editingCell.col, newScore);
    }
  };

  const closeEditor = () => setEditingCell(null);

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
        if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
            closeEditor();
        }
    };
    if (editingCell) {
        document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
        document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [editingCell]);


  const getColor = (score: number) => {
    if (score === 0) return 'bg-white hover:bg-slate-50';
    if (score < 0.5) return 'bg-red-50 text-red-700 hover:bg-red-100';
    if (score < 0.8) return 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100';
    if (score < 1.0) return 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100';
    return 'bg-emerald-500 text-white font-bold hover:bg-emerald-600 shadow-md transform scale-105';
  };

  return (
    <div className="w-full border border-slate-200 rounded-xl shadow-sm bg-white flex flex-col max-h-[600px] relative">
      
      {/* Editor Popover */}
      {editingCell && (
        <div 
            ref={popoverRef}
            className="absolute z-50 bg-white rounded-lg shadow-xl border border-slate-200 p-4 w-64 animate-in zoom-in-95 duration-200"
            style={{ 
                top: '50%', 
                left: '50%', 
                transform: 'translate(-50%, -50%)' 
            }}
        >
            <div className="flex justify-between items-center mb-3">
                <h4 className="text-sm font-bold text-slate-700">Adjust Confidence</h4>
                <button onClick={closeEditor} className="text-slate-400 hover:text-slate-600"><X className="h-4 w-4"/></button>
            </div>
            <div className="mb-2 text-xs text-slate-500">
                {editingCell.row} <span className="mx-1">→</span> {editingCell.col}
            </div>
            
            <div className="flex items-center gap-3 mb-4">
                 <input 
                    type="range" 
                    min="0" 
                    max="1" 
                    step="0.1" 
                    value={editingCell.score} 
                    onChange={(e) => handleScoreChange(parseFloat(e.target.value))}
                    className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                 />
                 <span className="font-mono text-sm font-bold w-10 text-right">{editingCell.score.toFixed(1)}</span>
            </div>
            <button onClick={closeEditor} className="w-full py-1.5 bg-slate-800 text-white text-xs font-medium rounded hover:bg-slate-700">
                Done
            </button>
        </div>
      )}
      {/* Overlay to dim background when editing */}
      {editingCell && <div className="absolute inset-0 bg-slate-900/10 z-40 rounded-xl backdrop-blur-[1px]"></div>}


      <div className="overflow-auto scrollbar-thin scrollbar-thumb-slate-300">
        <table className="w-full text-xs text-left border-collapse">
          <thead className="bg-slate-50 z-20 sticky top-0 shadow-sm">
            <tr>
              <th className="p-3 border-b border-r border-slate-200 font-semibold text-slate-500 uppercase tracking-wider min-w-[150px] sticky left-0 bg-slate-50 z-30">
                Library Model
              </th>
              {columns.map(col => (
                <th key={col} className="p-3 border-b border-slate-200 font-semibold text-slate-600 min-w-[120px] text-center">
                  <div className="flex flex-col items-center gap-1">
                      <span>{col}</span>
                      <span className="text-[10px] font-normal text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded-full">
                          Select One
                      </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(row => (
              <tr key={row} className="group">
                <td className="p-2 border-r border-slate-200 font-medium text-slate-600 sticky left-0 bg-white group-hover:bg-slate-50 transition-colors z-10 whitespace-nowrap">
                  {row}
                </td>
                {columns.map(col => {
                  const score = getScore(row, col);
                  const isSelected = score === 1.0 || (score > 0 && editingCell?.row === row && editingCell?.col === col);
                  
                  return (
                    <td 
                        key={`${row}-${col}`} 
                        onClick={() => handleCellClick(row, col, score)}
                        className={`p-1 text-center border-b border-slate-50 transition-all duration-200 cursor-pointer relative h-10 w-32`}
                        title={`Assign ${row} to ${col}`}
                    >
                        <div className={`w-full h-full flex items-center justify-center rounded-lg mx-auto transition-all ${getColor(score)} ${isSelected ? 'ring-2 ring-emerald-200 ring-offset-1' : ''}`}>
                            {score > 0 ? (
                                <div className="flex items-center gap-1">
                                    <span>{score.toFixed(1)}</span>
                                    {isSelected && <Settings2 className="h-3 w-3 opacity-50" />}
                                </div>
                            ) : (
                                <span className="opacity-0 group-hover:opacity-20 text-slate-400 font-bold text-lg">+</span>
                            )}
                        </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ConfidenceMatrix;