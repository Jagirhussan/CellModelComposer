import tikzjax from 'node-tikzjax';

// Robustly handle the export whether it's CJS or ESM
let tex2svg = tikzjax;
if (typeof tex2svg !== 'function') {
    if (tex2svg.default && typeof tex2svg.default === 'function') {
        tex2svg = tex2svg.default;
    } else if (tex2svg.default && typeof tex2svg.default.default === 'function') {
        tex2svg = tex2svg.default.default;
    }
}

const chunks = [];
process.stdin.on('data', chunk => chunks.push(chunk));
process.stdin.on('end', async () => {
  const input = Buffer.concat(chunks).toString().trim(); // Trim input first
  
  if (!input) {
    console.error("Error: No TikZ input provided.");
    process.exit(1);
  }

  // --- FIX: Robust Preamble Detection ---
  // If the input ALREADY has a document class, use it as is.
  // We use a regex to be insensitive to whitespace/comments at the start.
  let source = input;
  const hasDocumentClass = /^\s*\\documentclass/m.test(input);

  if (!hasDocumentClass) {
      source = `\\documentclass[margin=10pt]{standalone}
\\usepackage{tikz}
\\usetikzlibrary{arrows.meta, positioning, calc, shapes}
\\begin{document}
${source}
\\end{document}`;
  }

  // Capture stdout/console.log to prevent polluting the pipe with TeX logs
  // and to report them on stderr if failure occurs.
  const originalLog = console.log;
  const logBuffer = [];
  console.log = (...args) => {
      logBuffer.push(args.join(' '));
  };

  try {
    // Render with console logs enabled to capture LaTeX errors
    const svg = await tex2svg(source, {
      embedFontCss: true, 
      showConsole: true // Logs are now captured in logBuffer
    });

    // Restore console.log before writing output
    console.log = originalLog;
    process.stdout.write(svg);
  } catch (err) {
    console.log = originalLog;
    
    console.error("---------------------------------------------------");
    console.error("[TikZ Renderer] Fatal Error");
    console.error("---------------------------------------------------");
    console.error(err);
    console.error("---------------------------------------------------");
    console.error("[TeX Logs]");
    console.error(logBuffer.join('\n'));
    console.error("---------------------------------------------------");
    console.error("[TikZ Renderer] Failed Source Code:");
    console.error(source);
    console.error("---------------------------------------------------");
    process.exit(1);
  }
});