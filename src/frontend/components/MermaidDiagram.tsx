import React, { useRef, useState, useEffect } from 'react';

const MermaidDiagram: React.FC<{ chart: string }> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!chart) return;

    const renderChart = async () => {
      try {
        // @ts-ignore - mermaid loaded from CDN
        if (window.mermaid) {
          // @ts-ignore
          window.mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose',
            fontFamily: 'Inter',
          });

          const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
          // @ts-ignore
          const { svg } = await window.mermaid.render(id, chart);
          setSvg(svg);
          setError(null);
        }
      } catch (err) {
        console.error("Mermaid error:", err);
        setError("Failed to render diagram syntax.");
      }
    };

    renderChart();
  }, [chart]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-400 p-4 border border-red-900/50 bg-red-900/10 rounded">
        <span className="text-sm font-mono">{error}</span>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-auto flex flex-col items-center justify-center p-8 bg-[#0B1120] rounded-lg border border-slate-800">
      {svg ? (
        <div 
          ref={containerRef}
          dangerouslySetInnerHTML={{ __html: svg }}
          className="w-full flex justify-center mermaid-svg-container"
        />
      ) : (
        <div className="flex items-center gap-2 text-slate-500 animate-pulse">
           <div className="w-2 h-2 rounded-full bg-blue-500"></div>
           <span className="text-xs font-mono">Rendering topology...</span>
        </div>
      )}
    </div>
  );
};

export default MermaidDiagram;
