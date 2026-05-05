import { useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import { ChatComposer } from '@/features/chat/ChatComposer';
import { MessageBubble } from '@/features/chat/MessageBubble';
import { useChatController } from '@/features/chat/useChatController';

export function ChatPane() {
  const endRef = useRef<HTMLDivElement>(null);
  const chat = useChatController();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.msgs]);

  useEffect(() => {
    const insert = (event: Event) => {
      const detail = (event as CustomEvent<{ text?: string }>).detail;
      if (!detail?.text) return;
      chat.setInput(chat.input ? `${chat.input}\n${detail.text}` : detail.text);
      chat.inputRef.current?.focus();
    };
    window.addEventListener('ag-insert-prompt', insert as EventListener);
    return () => window.removeEventListener('ag-insert-prompt', insert as EventListener);
  }, [chat]);

  return (
    <div className="flex h-full flex-col bg-slate-950/20">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 lg:px-14 xl:px-20">
        {chat.msgs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="rounded-2xl bg-cyan-500/10 p-5 ring-1 ring-cyan-400/20">
              <Sparkles className="h-9 w-9 text-cyan-300/70" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-200">Ready for the next move</h3>
              <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">
                Ask the agent to inspect, edit, run, connect tools, or reason across the workspace.
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {chat.msgs.map((m, i) => <MessageBubble key={i} {...m} />)}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="border-t border-slate-800/60 bg-slate-900/40 px-4 py-3 md:px-8 lg:px-14 xl:px-20">
        <div className="mx-auto max-w-3xl">
          <ChatComposer
            input={chat.input}
            streaming={chat.streaming}
            shadowMode={chat.shadowMode}
            inputRef={chat.inputRef}
            onInput={chat.setInput}
            onSend={chat.send}
            onUpload={chat.upload}
            onToggleShadow={() => chat.setShadowMode(!chat.shadowMode)}
          />
          <p className="mt-1.5 text-center text-[10px] text-slate-600">Live workspace actions use your configured provider and sandbox.</p>
        </div>
      </div>
    </div>
  );
}
