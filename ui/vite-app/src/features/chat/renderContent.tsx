export function renderContent(content: string, sessionId?: string) {
  if (!content) return null;

  // 1. Detect absolute image paths (Tool Artifacts)
  const imageRegex = /([a-zA-Z]:\\[^*|"<>?\n]+\.(?:png|jpg|jpeg|webp|gif))/gi;
  
  // 2. Detect "Attached: filename.ext" (User Uploads)
  const attachmentRegex = /Attached: ([^\n]+\.(?:png|jpg|jpeg|webp|gif|mp4|mov|webm))/gi;

  const combinedRegex = new RegExp(`(${imageRegex.source}|${attachmentRegex.source})`, 'gi');
  
  const parts = content.split(combinedRegex);
  return parts.map((part, i) => {
    if (!part) return null;

    // Check for absolute path artifact
    if (part.match(imageRegex)) {
      return (
        <div key={i} className="my-3 overflow-hidden rounded-xl border border-slate-700/50 bg-slate-950/40 shadow-2xl">
          <img 
            src={`/api/v1/workspace/artifacts?path=${encodeURIComponent(part)}`} 
            alt="Tool Artifact" 
            className="max-h-96 w-full object-contain"
          />
          <div className="bg-slate-900/60 px-3 py-1.5 text-[10px] font-mono text-slate-500 truncate">
            {part}
          </div>
        </div>
      );
    }

    // Check for "Attached: filename.ext"
    const attachmentMatch = part.match(/Attached: ([^\n]+\.(?:png|jpg|jpeg|webp|gif|mp4|mov|webm))/i);
    if (attachmentMatch && sessionId) {
      const filename = attachmentMatch[1];
      const isVideo = /\.(mp4|mov|webm)$/i.test(filename);
      const url = `/api/v1/workspace/sessions/${sessionId}/file/${encodeURIComponent(filename)}`;

      return (
        <div key={i} className="my-3 overflow-hidden rounded-xl border border-cyan-800/30 bg-slate-950/40 shadow-xl">
          {isVideo ? (
            <video src={url} controls className="max-h-96 w-full" />
          ) : (
            <img src={url} alt={filename} className="max-h-96 w-full object-contain" />
          )}
          <div className="bg-cyan-950/20 px-3 py-1.5 text-[10px] font-medium text-cyan-500/70 truncate flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-cyan-500" />
            {filename}
          </div>
        </div>
      );
    }

    // Standard text rendering with backticks and bold
    return part.split(/(`[^`]+`)/g).map((subpart, j) => {
      if (subpart.startsWith('`') && subpart.endsWith('`')) {
        return (
          <code key={`${i}-${j}`} className="rounded bg-slate-950/80 px-1.5 py-0.5 font-mono text-[0.8em] text-cyan-300 ring-1 ring-slate-700/50">
            {subpart.slice(1, -1)}
          </code>
        );
      }
      return subpart.split(/(\*\*[^*]+\*\*)/g).map((bp, k) => {
        if (bp.startsWith('**') && bp.endsWith('**')) {
          return <strong key={`${i}-${j}-${k}`} className="font-semibold text-white">{bp.slice(2, -2)}</strong>;
        }
        return bp.split('\n').map((line, l, arr) => (
          <span key={`${i}-${j}-${k}-${l}`}>
            {line}
            {l < arr.length - 1 && <br />}
          </span>
        ));
      });
    });
  });
}
