import React from 'react';
import { Step3Data, IssueObject } from '../types';
import { BookOpen, AlertCircle, Thermometer, ExternalLink } from 'lucide-react';

const Step3Curator: React.FC<{ data: Step3Data }> = ({ data }) => {
  
  // Helper to extract clean citation for search
  const getSearchTerm = (text: string) => {
      // 1. Check for "Name et al., Year" or "Name et al (Year)"
      const etAlMatch = text.match(/([A-Z][a-z]+ et al\.?,? (?:\d{4}|\(\d{4}\)))/i);
      if (etAlMatch) return etAlMatch[0];

      // 2. Check for "Name & Name, Year"
      const pairMatch = text.match(/([A-Z][a-z]+ & [A-Z][a-z]+, \d{4})/);
      if (pairMatch) return pairMatch[0];

      // 3. Fallback: just remove "Calculated from" prefix if present
      return text.replace(/^Calculated from\s+/i, '');
  };

  const getScholarLink = (citation: string) => {
      const term = getSearchTerm(citation);
      return `https://scholar.google.com/scholar?q=${encodeURIComponent(term)}`;
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        
        {/* Issues Report */}
        {data.issues_report && data.issues_report.length > 0 && (
             <section className="bg-amber-50 p-4 rounded-lg border border-amber-200">
                <h3 className="text-amber-900 font-bold mb-3 flex items-center gap-2 text-sm uppercase tracking-wide">
                    <AlertCircle className="h-4 w-4" /> Curator Notes
                </h3>
                <ul className="space-y-3">
                    {data.issues_report.map((issue, idx) => {
                        // Handle legacy string format
                        if (typeof issue === 'string') {
                            return (
                                <li key={idx} className="flex gap-2 text-sm text-amber-800">
                                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                                    <span>{issue}</span>
                                </li>
                            );
                        }
                        
                        // Handle new object format
                        const issueObj = issue as IssueObject;
                        return (
                            <li key={idx} className="bg-white/60 p-3 rounded-md border border-amber-200 shadow-sm flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded border border-amber-200">
                                        {issueObj.issue_id}
                                    </span>
                                    {issueObj.severity && (
                                        <span className={`text-[10px] font-bold uppercase tracking-wider ${
                                            issueObj.severity.toLowerCase() === 'high' ? 'text-red-600' : 'text-amber-600'
                                        }`}>
                                            {issueObj.severity} Severity
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-amber-900 leading-relaxed">
                                    {issueObj.description}
                                </p>
                            </li>
                        );
                    })}
                </ul>
            </section>
        )}

        {/* Global Constants */}
        <section className="flex gap-4">
             {Object.entries(data.global_constants).map(([key, val]) => {
                 const v = val as { value: string | number, units: string };
                 return (
                    <div key={key} className="bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm flex items-center gap-3">
                        <div className="bg-indigo-100 p-2 rounded-full text-indigo-600">
                            <Thermometer className="h-4 w-4" />
                        </div>
                        <div>
                            <span className="text-xs text-slate-500 font-bold uppercase">{key}</span>
                            <div className="text-sm font-semibold text-slate-800">{v.value} {v.units}</div>
                        </div>
                    </div>
                 );
             })}
        </section>

        {/* Parameter Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                        <tr>
                            <th className="px-6 py-3">Parameter</th>
                            <th className="px-6 py-3">Value</th>
                            <th className="px-6 py-3">Source & Context</th>
                            <th className="px-6 py-3 text-center">Confidence</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {data.parameter_set.map((param, idx) => {
                            // Fix: Robustly parsing confidence score
                            // @ts-ignore
                            const rawVal = param.confidence_score ?? param.confidence;
                            // Convert to string then float to handle various inputs (0.7, "0.7")
                            const parsed = parseFloat(String(rawVal));
                            // Ensure result is a valid number, default to 0 if NaN
                            const score = !isNaN(parsed) ? parsed : 0;

                            return (
                                <tr key={idx} className="hover:bg-slate-50 group">
                                    <td className="px-6 py-4">
                                        <div className="font-mono font-medium text-slate-800">{param.parameter_name}</div>
                                        <div className="text-xs text-slate-500 mt-1 truncate max-w-[200px]" title={param.component_id}>
                                            {param.component_id.split('_inst_')[1] || param.component_id}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-baseline gap-1">
                                            <span className="font-bold text-slate-900">{param.value}</span>
                                            <span className="text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{param.units}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 max-w-xs">
                                        <div className="flex items-start gap-2">
                                            <BookOpen className="h-3 w-3 text-indigo-400 mt-1 flex-shrink-0" />
                                            <div>
                                                <a 
                                                    href={getScholarLink(param.source_citation)}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="font-medium text-indigo-600 hover:text-indigo-800 hover:underline flex items-center gap-1 transition-colors"
                                                    title={`Search: ${getSearchTerm(param.source_citation)}`}
                                                >
                                                    {param.source_citation}
                                                    <ExternalLink className="h-2.5 w-2.5 opacity-50" />
                                                </a>
                                                <div className="text-xs text-slate-500 mt-0.5">{param.biological_context}</div>
                                            </div>
                                        </div>
                                        <div className="mt-2 text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {param.notes}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="inline-flex flex-col items-center">
                                            <div className={`text-lg font-bold ${score >= 0.8 ? 'text-emerald-600' : score >= 0.5 ? 'text-amber-500' : 'text-red-500'}`}>
                                                {(score * 100).toFixed(0)}%
                                            </div>
                                            <div className="w-16 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                                                <div 
                                                    className={`h-full rounded-full ${score >= 0.8 ? 'bg-emerald-500' : score >= 0.5 ? 'bg-amber-400' : 'bg-red-400'}`} 
                                                    style={{ width: `${score * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
  );
};

export default Step3Curator;