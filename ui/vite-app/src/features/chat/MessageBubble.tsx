import { Bot, User, Wrench } from 'lucide-react';
import { renderContent } from '@/features/chat/renderContent';
import { ToolCallCard } from '@/features/chat/ToolCallCard';
import type { ChatRole, ToolCall } from '@/features/chat/types';

interface MessageBubbleProps {
  role: ChatRole;
  content: string;
  streaming?: boolean;
  tool_calls?: ToolCall[];
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

export function MessageBubble({ role, content, streaming, tool_calls }: MessageBubbleProps) {
  const config = ROLE_CONFIG[role] || ROLE_CONFIG.assistant;
  const Icon = config.icon;

  return (
    <div className={`group flex max-w-[85%] gap-2.5 ${config.align}`}>
      {role !== 'user' && (
        <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${config.iconColor}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      )}
      <div className={`rounded-2xl px-4 py-2.5 ${config.bg} ${config.ring} ${config.text}`}>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-50">{config.label}</div>
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {renderContent(content)}
          {streaming && <StreamingDots />}
        </div>
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
    </div>
  );
}
