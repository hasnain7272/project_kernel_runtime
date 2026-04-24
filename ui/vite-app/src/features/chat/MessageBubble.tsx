/**
 * MessageBubble — Premium chat message rendering
 * Supports markdown-style formatting, status indicators, and streaming state.
 */
import { Bot, User, Wrench, Loader2 } from 'lucide-react';

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  streaming?: boolean;
  tool_calls?: any[];
}

const ROLE_CONFIG = {
  user: {
    align: 'ml-auto',
    bg: 'bg-gradient-to-br from-cyan-900/50 to-cyan-800/30',
    ring: 'ring-1 ring-cyan-700/30',
    text: 'text-cyan-50',
    icon: User,
    iconColor: 'text-cyan-400 bg-cyan-900/40',
    label: 'You',
  },
  assistant: {
    align: 'mr-auto',
    bg: 'bg-slate-800/50',
    ring: 'ring-1 ring-slate-700/30',
    text: 'text-slate-200',
    icon: Bot,
    iconColor: 'text-violet-400 bg-violet-900/30',
    label: 'Agent',
  },
  tool: {
    align: 'mr-auto',
    bg: 'bg-amber-950/30',
    ring: 'ring-1 ring-amber-800/30',
    text: 'text-amber-200',
    icon: Wrench,
    iconColor: 'text-amber-400 bg-amber-900/30',
    label: 'Tool',
  },
  system: {
    align: 'mx-auto',
    bg: 'bg-slate-800/30',
    ring: 'ring-1 ring-slate-700/20',
    text: 'text-slate-400',
    icon: Bot,
    iconColor: 'text-slate-500 bg-slate-800/40',
    label: 'System',
  },
};

/** Simple inline markdown: **bold**, `code`, and newlines */
function renderContent(content: string) {
  if (!content) return null;

  // Split by code blocks first
  const parts = content.split(/(`[^`]+`)/g);

  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="rounded bg-slate-900/80 px-1.5 py-0.5 font-mono text-[0.8em] text-cyan-300 ring-1 ring-slate-700/50">
          {part.slice(1, -1)}
        </code>
      );
    }
    // Bold
    const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
    return boldParts.map((bp, j) => {
      if (bp.startsWith('**') && bp.endsWith('**')) {
        return <strong key={`${i}-${j}`} className="font-semibold text-white">{bp.slice(2, -2)}</strong>;
      }
      // Preserve newlines
      return bp.split('\n').map((line, k, arr) => (
        <span key={`${i}-${j}-${k}`}>
          {line}
          {k < arr.length - 1 && <br />}
        </span>
      ));
    });
  });
}

export function MessageBubble({ role, content, streaming, tool_calls }: MessageBubbleProps) {
  const config = ROLE_CONFIG[role] || ROLE_CONFIG.assistant;
  const Icon = config.icon;

  return (
    <div className={`flex gap-2.5 ${config.align} max-w-[85%] group`}>
      {/* Avatar */}
      {role !== 'user' && (
        <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${config.iconColor} mt-0.5`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      )}

      {/* Bubble */}
      <div className={`rounded-2xl px-4 py-2.5 ${config.bg} ${config.ring} ${config.text}`}>
        {/* Role label */}
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-50">
          {config.label}
        </div>

        {/* Content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {renderContent(content)}
          {streaming && (
            <span className="inline-flex items-center ml-1">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400 mr-0.5" />
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400 mr-0.5" style={{ animationDelay: '150ms' }} />
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400" style={{ animationDelay: '300ms' }} />
            </span>
          )}
        </div>

        {/* Tool Calls Polish */}
        {tool_calls && tool_calls.length > 0 && (
          <div className="mt-3 space-y-2">
            {tool_calls.map((tc, i) => {
              const tName = tc.function?.name || 'tool_execution';
              const isSwarm = tName === 'delegate_task';
              const isMemory = tName === 'search_past_decisions';
              
              let headerColor = "text-cyan-400";
              let dotColor = "bg-cyan-400";
              let label = "Execution";
              let bgClass = "bg-slate-900/60 border-slate-700/50";
              let headBg = "bg-slate-800/80";

              if (isSwarm) {
                headerColor = "text-violet-400";
                dotColor = "bg-violet-400";
                label = "Sub-Agent Spawned";
                bgClass = "bg-violet-950/20 border-violet-800/30 ring-1 ring-violet-500/20 shadow-lg shadow-violet-900/10";
                headBg = "bg-violet-900/20";
              } else if (isMemory) {
                headerColor = "text-amber-400";
                dotColor = "bg-amber-400";
                label = "Accessing Cortex Memory";
                bgClass = "bg-amber-950/20 border-amber-800/30 ring-1 ring-amber-500/20 shadow-lg shadow-amber-900/10";
                headBg = "bg-amber-900/20";
              }

              return (
                <div key={i} className={`flex flex-col border rounded-lg overflow-hidden transition-all ${bgClass}`}>
                  <div className={`flex items-center gap-2 px-3 py-2 border-b border-slate-700/50 ${headBg}`}>
                    <div className={`w-2 h-2 rounded-full animate-pulse ${dotColor}`} />
                    <span className={`text-xs font-semibold font-mono ${headerColor}`}>
                      {tName}
                    </span>
                    <span className="text-[10px] text-slate-500 ml-auto uppercase tracking-wider">{label}</span>
                  </div>
                  <div className="px-3 py-2 text-xs text-slate-400 font-mono overflow-x-auto whitespace-pre-wrap">
                    {tc.function?.arguments || '{}'}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* User avatar on right */}
      {role === 'user' && (
        <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${config.iconColor} mt-0.5`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      )}
    </div>
  );
}
