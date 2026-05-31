import { useState } from 'react';
import { Bot, Brain, ChevronDown, ChevronRight, User, Wrench } from 'lucide-react';
import { renderContent } from '@/features/chat/renderContent';
import { ToolCallCard } from '@/features/chat/ToolCallCard';
import type { ChatRole, ToolCall } from '@/features/chat/types';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';

interface MessageBubbleProps {
  id?: string;
  role: ChatRole;
  content: string;
  streaming?: boolean;
  reasoning?: string;
  tool_calls?: ToolCall[];
  metadata?: Record<string, any>;
  sessionId?: string;
  onApprove?: (id: string, decision: 'approved' | 'denied') => void;
}

const ROLE_CONFIG = {
  user: {
    align: 'ml-auto',
    bg: 'bg-gradient-to-br from-cyan-900/55 to-cyan-800/30',
    ring: 'ring-1 ring-cyan-700/30',
    text: 'text-cyan-50',
    icon: User,
    iconColor: 'text-cyan-300 bg-cyan-900/40',
    label: 'You',
  },
  assistant: {
    align: 'mr-auto',
    bg: 'bg-slate-800/55',
    ring: 'ring-1 ring-slate-700/30',
    text: 'text-slate-200',
    icon: Bot,
    iconColor: 'text-violet-300 bg-violet-900/30',
    label: 'Agent',
  },
  tool: {
    align: 'mr-auto',
    bg: 'bg-amber-950/30',
    ring: 'ring-1 ring-amber-800/30',
    text: 'text-amber-200',
    icon: Wrench,
    iconColor: 'text-amber-300 bg-amber-900/30',
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

function StreamingDots() {
  return (
    <span className="ml-1 inline-flex items-center">
      <span className="mr-0.5 inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
      <span className="mr-0.5 inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400 [animation-delay:150ms]" />
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400 [animation-delay:300ms]" />
    </span>
  );
}

function ReasoningBlock({ text, streaming }: { text: string; streaming?: boolean }) {
  const [open, setOpen] = useState(streaming || false);
  if (!text) return null;

  return (
    <div className="mb-2 rounded-lg border border-violet-800/30 bg-violet-950/20">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-violet-400/80 transition hover:text-violet-300"
      >
        <Brain className="h-3 w-3" />
        Reasoning
        {streaming && <span className="ml-1 h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />}
        {open ? <ChevronDown className="ml-auto h-3 w-3" /> : <ChevronRight className="ml-auto h-3 w-3" />}
      </button>
      {open && (
        <div className="border-t border-violet-800/20 px-3 py-2 text-xs leading-relaxed text-violet-300/70 whitespace-pre-wrap">
          {text}
        </div>
      )}
    </div>
  );
}

export function MessageBubble({ id, role, content, streaming, reasoning, tool_calls, metadata, sessionId, onApprove }: MessageBubbleProps) {
  const config = ROLE_CONFIG[role] || ROLE_CONFIG.assistant;
  const Icon = config.icon;
  const setSessionId = useSessionStore((s) => s.setSessionId);

  return (
    <div className={`group flex max-w-[85%] gap-2.5 relative ${config.align}`}>
      {role !== 'user' && (
        <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${config.iconColor}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      )}
      <div className={`rounded-2xl px-4 py-2.5 ${config.bg} ${config.ring} ${config.text}`}>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-50">{config.label}</div>
        {reasoning && <ReasoningBlock text={reasoning} streaming={streaming} />}
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {renderContent(content, sessionId)}
          {streaming && !content && !reasoning && <StreamingDots />}
          {streaming && (content || reasoning) && <StreamingDots />}
        </div>
        
        {metadata?.status === 'NEEDS_APPROVAL' && id && onApprove && (
          <div className="mt-3 flex flex-col gap-2 rounded-xl bg-slate-900/40 p-3 ring-1 ring-amber-500/30">
            <div className="flex items-center gap-2 text-xs font-medium text-amber-300">
              <Wrench className="h-3 w-3" />
              <span>Permission Required: {metadata.tool_name}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onApprove(id, 'approved')}
                className="flex-1 rounded-md bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-cyan-500 active:scale-95"
              >
                Approve
              </button>
              <button
                onClick={() => onApprove(id, 'denied')}
                className="flex-1 rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-slate-600 active:scale-95"
              >
                Deny
              </button>
            </div>
          </div>
        )}

        {metadata?.status === 'APPROVED' && (
          <div className="mt-2 flex items-center gap-1.5 text-[10px] font-medium text-cyan-400 opacity-80">
            <div className="h-1 w-1 rounded-full bg-cyan-400" />
            Approved
          </div>
        )}

        {metadata?.status === 'DENIED' && (
          <div className="mt-2 flex items-center gap-1.5 text-[10px] font-medium text-rose-400 opacity-80">
            <div className="h-1 w-1 rounded-full bg-rose-400" />
            Denied
          </div>
        )}

        {!!tool_calls?.length && (
          <div className="mt-3 space-y-2">
            {tool_calls.map((tc, i) => <ToolCallCard key={i} call={tc} />)}
          </div>
        )}
      </div>
      {role === 'user' && (
        <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${config.iconColor}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      )}
      
      {/* Branch Button (visible on hover) */}
      <div className={`absolute top-0 opacity-0 group-hover:opacity-100 transition flex ${role === 'user' ? '-left-8' : '-right-8'}`}>
        <button 
          onClick={async () => {
             if (!id || !sessionId) return;
             try {
                const res = await apiClient.post<{ id: string }>(`/sessions/${sessionId}/fork`, { message_id: id });
                if (!res.data?.id) throw new Error(res.error || 'Fork failed');
                setSessionId(res.data.id);
                window.location.reload(); // simplest: re-init full session-bound state
             } catch {
                console.error("Fork failed");
             }
          }}
          className="p-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-cyan-400 hover:bg-slate-700 shadow-lg"
          title="Branch from here"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/></svg>
        </button>
      </div>
    </div>
  );
}
