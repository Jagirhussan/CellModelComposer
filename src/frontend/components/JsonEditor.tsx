import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, X } from 'lucide-react';

interface JsonEditorProps {
  data: any;
  onSave: (newData: any) => void;
  onCancel: () => void;
  onReset: () => void;
}

const JsonEditor: React.FC<JsonEditorProps> = ({ data, onSave, onCancel, onReset }) => {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValue(JSON.stringify(data, null, 2));
  }, [data]);

  const handleSave = () => {
    try {
      const parsed = JSON.parse(value);
      onSave(parsed);
      setError(null);
    } catch (e: any) {
      setError(`Invalid JSON: ${e.message}`);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 border rounded-lg overflow-hidden relative">
      <div className="flex items-center justify-between bg-white px-4 py-2 border-b border-slate-200">
        <h3 className="font-semibold text-slate-700">Raw JSON Editor</h3>
        <div className="flex gap-2">
            <button onClick={onReset} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded">
                <RotateCcw className="h-3 w-3" /> Reset to Original
            </button>
            <button onClick={onCancel} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-800 bg-red-50 hover:bg-red-100 rounded">
                <X className="h-3 w-3" /> Cancel
            </button>
            <button onClick={handleSave} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded shadow-sm">
                <Save className="h-3 w-3" /> Save Changes
            </button>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 text-sm border-b border-red-200">
          {error}
        </div>
      )}

      <textarea
        className="flex-1 w-full p-4 font-mono text-sm bg-slate-900 text-slate-50 resize-none focus:outline-none"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        spellCheck={false}
      />
    </div>
  );
};

export default JsonEditor;