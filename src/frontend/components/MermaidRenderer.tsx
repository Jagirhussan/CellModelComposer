import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Loader2, AlertCircle, ZoomIn, ZoomOut, RotateCcw, Move } from 'lucide-react';

// --- Types ---

// Define the shape of the window object extended with mermaid
declare global {
  interface Window {
    mermaid: {
      initialize: (config: any) => void;
      render: (id: string, code: string) => Promise<{ svg: string }>;
    };
  }
}

interface MermaidRendererProps {
  chart: string;
}

interface NodeStyle {
  id: string;
  type: 'green' | 'red';
}

// --- Logic for Categorizing Nodes (potentials vs flows)---

const isGreenVariable = (id: string, label: string): boolean => {
  const text = (id + " " + label).toLowerCase();
  // Criteria: q (Quantity), v (Velocity), d (Displacement)
  // Also mapping common Bond Graph kinematics: C (Storage/Quantity), 0 (Junction), 1 (Junction)
  if (text.includes('q_') || text.includes('v_') || text.includes('d_')) return true;
  if (id.startsWith('C_') || id.startsWith('0_') || id.startsWith('1_')) return true;
  return false;
};

const isRedVariable = (id: string, label: string): boolean => {
  const text = (id + " " + label).toLowerCase();
  // Criteria: u (Energy/Pressure), T (Tension/Force)
  // Also mapping common Bond Graph kinetics: Se (Source Effort), Sf (Source Flow - debatable, but drives), T (Transformer/Tension)
  if (text.includes('u_') || text.includes('t_') || text.includes('pressure') || text.includes('force')) return true;
  if (id.startsWith('Se_') || id.startsWith('Sf_')) return true;
  return false;
};

// --- Main Component ---

export default function MermaidRenderer({ chart }: MermaidRendererProps) {
  const [processedCode, setProcessedCode] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [mermaidLoaded, setMermaidLoaded] = useState<boolean>(false);
  
  // Zoom & Pan State
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Settings - Hardcoded to true as per requirements
  const applyColors = true;
  
  const mermaidRef = useRef<HTMLDivElement>(null);

  // Load Mermaid via CDN to avoid bundler node-polyfill issues
  useEffect(() => {
    if (window.mermaid) {
      setMermaidLoaded(true);
      return;
    }

    const script = document.createElement('script');
    // Using jsdelivr and a stable version
    // Updated to a robust version that handles complex syntax better (10.9.1)
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js';
    script.async = true;
    script.onload = () => {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose', // Allows for more creative node definitions
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
      });
      setMermaidLoaded(true);
    };
    script.onerror = () => setError("Failed to load Mermaid library");
    document.body.appendChild(script);

    return () => {
      // Clean up script if needed, though usually persistent
    };
  }, []);

  const processMermaid = useCallback((code: string): string => {
    if (!code) return '';
    
    // Robust split handling for various OS line endings
    let lines = code.trim().split(/\r?\n/);
    let nodesToStyle: NodeStyle[] = [];
    
    // Regex to identify standard Mermaid nodes: ID + Shape Start + Content + Shape End
    // Captures: 1=ID, 2=Start(e.g. [ or [(), 3=Content, 4=End
    // Note: Content matching is strict about excluding unquoted delimiters to prevent breaking structure
    const nodeRegex = /([a-zA-Z0-9_]+)\s*([\[\(\{]+)((?:[^\[\]\(\)\{\}"]|"[^"]*")*)([\]\}\)]+)/g;
    
    const processedLines = lines.map(line => {
        let processedLine = line.trim();

        // 1. Cleanup: Remove known LLM hallucinations/artifacts like "-- Missing --"
        processedLine = processedLine.replace(/\s*--\s*Missing\s*--\s*/gi, '');

        // 2. AGGRESSIVE UNIT STRIPPING (Fixes 'CYLINDEREND' and Parse Errors)
        
        // A) Remove Quote-wrapped Units in Brackets: ["(mM)"]
        processedLine = processedLine.replace(/\["[\(\[].*?[\)\]]"\]/g, ''); 
        
        // B) Remove Bracket-wrapped Units: [(mM)]
        processedLine = processedLine.replace(/\[[\(\[].*?[\)\]]\]/g, ''); 

        // C) Remove Parenthesis-wrapped Units with Quotes: ("mM") or ("10 mM")
        // This fixes the specific error: C_Na_cyto[C_Na_cyto("mM")] -> C_Na_cyto[C_Na_cyto]
        processedLine = processedLine.replace(/\(".*?"\)/g, '');

        // D) Remove simple Parenthesis Units: (mM) or (10 uM)
        // Matches (word) or (number word) patterns loosely
        processedLine = processedLine.replace(/\([a-zA-Z0-9\sμµ\/]+\)/g, '');
        
        // 3. Skip structural lines and comments
        if (processedLine.startsWith('%%') || processedLine.startsWith('classDef') || processedLine.startsWith('style') || processedLine.startsWith('class')) return line;
        
        // Skip structural keywords to avoid breaking subgraphs or graph definitions
        if (processedLine.toLowerCase().startsWith('subgraph') || processedLine.startsWith('graph ') || processedLine.startsWith('flowchart ')) return line;

        // 4. Process Nodes
        return processedLine.replace(nodeRegex, (match, id, open, label, close) => {
            let cleanLabel = label.trim();

            // Safety check: ignore arrow definitions if they accidentally matched
            if (match.includes('-->') || match.includes('---')) {
                 return match;
            }

            // --- Label Sanitization ---
            // 1. Strip existing outer quotes if present
            if (cleanLabel.startsWith('"') && cleanLabel.endsWith('"')) {
                cleanLabel = cleanLabel.slice(1, -1);
            }
            
            // 2. Escape internal double quotes
            cleanLabel = cleanLabel.replace(/"/g, "'");

            // 3. Remove duplicated ID from label
            const idPattern = new RegExp(`^${id}\\s*`, 'i');
            cleanLabel = cleanLabel.replace(idPattern, '').trim();

            // 4. STRIP REMAINING UNITS inside the label (Last line of defense)
            cleanLabel = cleanLabel.replace(/\s*[\(\[].*?[\)\]]/g, '').trim();

            // --- Color Logic ---
            if (applyColors) {
                if (isGreenVariable(id, cleanLabel)) {
                    nodesToStyle.push({ id, type: 'green' });
                } else if (isRedVariable(id, cleanLabel)) {
                    nodesToStyle.push({ id, type: 'red' });
                }
            }

            // --- Reconstruction ---
            // If label is empty (e.g. stripped units), we rely on the ID.
            if (cleanLabel.length === 0) {
                return `${id} `;
            }
            
            // Otherwise, Quote the label safely
            const quotedFinalLabel = `"${cleanLabel}"`;
            return `${id}${open}${quotedFinalLabel}${close} `;
        });
    });

    // --- Inject Styles ---
    let finalCode = processedLines.join('\n');

    if (applyColors && nodesToStyle.length > 0) {
      const greenClasses = `\nclassDef greenNode fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px,color:#0d652d;`; // Material Green 50/700
      const redClasses = `\nclassDef redNode fill:#fce8e6,stroke:#c5221f,stroke-width:2px,color:#a50e0e;`;   // Material Red 50/700
      
      let styleApplications = '\n';
      const processedIds = new Set();
      
      nodesToStyle.forEach(node => {
        if (!processedIds.has(node.id)) {
            styleApplications += `class ${node.id} ${node.type === 'green' ? 'greenNode' : 'redNode'}\n`;
            processedIds.add(node.id);
        }
      });

      finalCode += greenClasses + redClasses + styleApplications;
    }
    console.log(finalCode)
    return finalCode;
  }, [applyColors]); 

  useEffect(() => {
    const renderDiagram = async () => {
      if (!mermaidLoaded || !window.mermaid) return;
      if (!chart) {
          // Clear if no chart provided
          if (mermaidRef.current) mermaidRef.current.innerHTML = '';
          return;
      }

      try {
        const final = processMermaid(chart);
        setProcessedCode(final);
        
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = '';
          const id = `mermaid-${Date.now()}`;
          const { svg } = await window.mermaid.render(id, final);
          mermaidRef.current.innerHTML = svg;
          setError(null);
        }
      } catch (err: any) {
        // Only surface the error if it's not the internal Mermaid parsing/rendering failure 
        // that results in a generic message like 'Parse error'.
        const errorMessage = err.message || "Syntax Error in Mermaid Code";
        console.error("Mermaid Render Error:", err);
        setError(errorMessage);
      }
    };

    const timeoutId = setTimeout(renderDiagram, 100); // Debounce slightly
    return () => clearTimeout(timeoutId);
  }, [chart, processMermaid, mermaidLoaded]);

  // --- Zoom/Pan Handlers ---

  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    // Basic Zoom on wheel
    const sensitivity = 0.001;
    const delta = -e.deltaY * sensitivity;
    setZoom(z => Math.max(0.1, Math.min(5, z + delta)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    setIsDragging(true);
    // Calculate offset relative to current pan to maintain position
    dragStartRef.current = { 
        x: e.clientX - pan.x, 
        y: e.clientY - pan.y 
    };
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    e.preventDefault();
    setPan({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const resetView = () => {
      setZoom(1);
      setPan({ x: 0, y: 0 });
  };

  if (!chart) {
      return (
          <div className="flex flex-col items-center justify-center p-8 text-slate-400 bg-slate-50/50 rounded-lg border border-dashed border-slate-200 h-full min-h-[200px]">
              <p>No chart data available</p>
          </div>
      );
  }

  // ADDED min-h-[500px] to ensure visibility in non-flex/auto containers
  return (
    <div className="w-full h-full min-h-[500px] flex flex-col bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden relative">
      {/* Zoom Toolbar */}
      <div className="absolute bottom-4 right-4 flex gap-1 z-20 bg-white/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-200">
        <button 
            onClick={() => setZoom(z => Math.max(0.1, z - 0.2))}
            className="p-1.5 hover:bg-slate-100 rounded text-slate-600 transition-colors"
            title="Zoom Out"
        >
            <ZoomOut className="w-4 h-4" />
        </button>
        <button 
            onClick={resetView}
            className="p-1.5 hover:bg-slate-100 rounded text-slate-600 transition-colors"
            title="Reset View"
        >
            <RotateCcw className="w-4 h-4" />
        </button>
        <button 
            onClick={() => setZoom(z => Math.min(5, z + 0.2))}
            className="p-1.5 hover:bg-slate-100 rounded text-slate-600 transition-colors"
            title="Zoom In"
        >
            <ZoomIn className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-slate-200 mx-1 self-center"></div>
        <div className="flex items-center justify-center w-8 text-xs font-medium text-slate-500 select-none">
            {Math.round(zoom * 100)}%
        </div>
      </div>

      {/* Loading / Error States Overlay */}
      <div className="absolute top-2 right-2 flex gap-2 z-10 pointer-events-none">
        {!mermaidLoaded && (
            <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full animate-pulse border border-blue-100">
                <Loader2 className="w-3 h-3 animate-spin" /> Engine Loading
            </span>
        )}
        {error && (
            <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-1 rounded-full border border-red-100 max-w-[200px] truncate" title={error}>
                <AlertCircle className="w-3 h-3" /> Error
            </span>
        )}
      </div>

      {/* Interactive Canvas Area */}
      <div 
        className={`flex-1 overflow-hidden relative bg-slate-50/30 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
         <div 
            ref={mermaidRef} 
            className="mermaid-canvas absolute origin-top-left transition-transform duration-75 ease-out"
            style={{ 
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                minWidth: '100%',
                minHeight: '100%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                padding: '2rem'
            }}
         >
            {!mermaidLoaded && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 pt-10">
                    <Loader2 className="w-8 h-8 animate-spin mb-4 text-slate-300" />
                </div>
            )}
         </div>
      </div>
    </div>
  );
}