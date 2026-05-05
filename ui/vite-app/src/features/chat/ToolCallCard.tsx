import type { ToolCall } from '@/features/chat/types';

function tone(name: string) {
  if (name === 'delegate_task') return ['Sub-agent', 'bg-violet-400', 'text-violet-300', 'bg-violet-950/20 border-violet-800/30 ring-1 ring-violet-500/20', 'bg-violet-900/20'];
  if (name === 'search_past_decisions') return ['Memory', 'bg-amber-400', 'text-amber-300', 'bg-amber-950/20 border-amber-800/30 ring-1 ring-amber-500/20', 'bg-amber-900/20'];
  return ['Execution', 'bg-cyan-400', 'text-cyan-300', 'bg-slate-950/60 border-slate-700/50', 'bg-slate-800/70'];
}

export function ToolCallCard({ call }: { call: ToolCall }) {
  const name = call.function?.name || 'tool_execution';
  const [label, dot, title, shell, head] = tone(name);
  return (
    <div className={`overflow-hidden rounded-lg border ${shell}`}>
      <div className={`flex items-center gap-2 border-b border-slate-700/50 px-3 py-2 ${head}`}>
        <span className={`h-2 w-2 rounded-full ${dot}`} />
        <span className={`font-mono text-xs font-semibold ${title}`}>{name}</span>
        <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      <pre className="max-h-40 overflow-auto whitespace-pre-wrap px-3 py-2 font-mono text-xs text-slate-400">
        {call.function?.arguments || '{}'}
      </pre>
    </div>
  );
}
