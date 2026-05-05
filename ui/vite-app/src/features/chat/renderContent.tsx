export function renderContent(content: string) {
  if (!content) return null;
  return content.split(/(`[^`]+`)/g).map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="rounded bg-slate-950/80 px-1.5 py-0.5 font-mono text-[0.8em] text-cyan-300 ring-1 ring-slate-700/50">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part.split(/(\*\*[^*]+\*\*)/g).map((bp, j) => {
      if (bp.startsWith('**') && bp.endsWith('**')) {
        return <strong key={`${i}-${j}`} className="font-semibold text-white">{bp.slice(2, -2)}</strong>;
      }
      return bp.split('\n').map((line, k, arr) => (
        <span key={`${i}-${j}-${k}`}>
          {line}
          {k < arr.length - 1 && <br />}
        </span>
      ));
    });
  });
}
