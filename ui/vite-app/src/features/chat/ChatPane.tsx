/**
 * ChatPane — Primary SaaS chat interface
 *
 * Dispatches user messages via REST, then opens a WebSocket to stream
 * the LLM response tokens directly into the chat in real-time.
 * No terminal needed — everything is inline.
 */
import { useRef, useState, useEffect, useCallback } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { apiClient, getTenantId } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';
import { useToastStore } from '@/components/Toast';
import { MessageBubble } from './MessageBubble';

interface Message {
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  streaming?: boolean;
}

export function ChatPane() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionId = useSessionStore((s) => s.sessionId);
  const setActiveTask = useTaskStore((s) => s.setActiveTask);
  const upsertTask = useTaskStore((s) => s.upsertTask);
  const addToast = useToastStore((s) => s.addToast);

  /* ── Load history on session change ──────────────────── */
  const loadHistory = useCallback(async () => {
    if (!sessionId) return;
    const res = await apiClient.get<{ messages: Message[] }>(`/chat/${sessionId}/history`);
    if (res.data?.messages) {
      setMessages(res.data.messages);
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  useEffect(() => {
    setMessages([]);
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ── WebSocket streaming of LLM response ─────────────── */
  const streamResponse = useCallback((taskId: string) => {
    // Close any existing WS
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/tasks/${taskId}/stream?tenant_id=${encodeURIComponent(getTenantId())}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    let buffer = '';
    let hasContent = false;

    ws.onopen = () => {
      setStreaming(true);
      // Add a placeholder streaming message
      setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true }]);
    };

    ws.onmessage = (event) => {
      try {
        // Check if it's a JSON control message
        const data = JSON.parse(event.data);
        if (data.event_type === 'TASK_RESOLVED') {
          // Stream complete — finalize the message
          setStreaming(false);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.streaming) {
              last.streaming = false;
              if (!last.content.trim()) {
                last.content = buffer || 'Task completed.';
              }
            }
            return [...updated];
          });
          ws.close();
          // Reload history to sync with DB
          loadHistory();
          return;
        }
        if (data.event_type === 'TIMEOUT') {
          addToast('error', 'Agent timed out waiting for LLM response.');
          setStreaming(false);
          ws.close();
          return;
        }
      } catch {
        // Not JSON — it's a text stream chunk (reasoning/content tokens)
      }

      // Text chunk — append to the streaming message
      const text = event.data;
      // Strip ANSI escape codes for clean display
      const clean = text.replace(/\x1b\[[0-9;]*m/g, '');
      if (clean.trim()) {
        hasContent = true;
        buffer += clean;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.streaming) {
            last.content = buffer;
          }
          return [...updated];
        });
      }
    };

    ws.onerror = () => {
      setStreaming(false);
      addToast('error', 'WebSocket connection failed.');
    };

    ws.onclose = () => {
      wsRef.current = null;
      setStreaming(false);
      // Finalize any streaming message
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.streaming) {
          last.streaming = false;
        }
        return [...updated];
      });
    };
  }, [addToast, loadHistory]);

  /* ── Send message ────────────────────────────────────── */
  const send = async () => {
    if (!input.trim() || streaming) return;
    const text = input.trim();
    setInput('');

    // Add user message
    setMessages((p) => [...p, { role: 'user', content: text }]);

    // Dispatch to backend
    const res = await apiClient.post<{ task_id: string }>('/chat/', {
      session_id: sessionId,
      message: text,
    });

    if (res.data?.task_id) {
      upsertTask({ id: res.data.task_id, description: text, status: 'running' });
      setActiveTask(res.data.task_id);
      // Start WebSocket stream
      streamResponse(res.data.task_id);
    } else {
      setMessages((p) => [...p, { role: 'system', content: res.error || 'Failed to dispatch message.' }]);
      addToast('error', res.error || 'Failed to send message.');
    }
  };

  /* ── Textarea auto-resize + Enter to send ────────────── */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  /* ── Cleanup WS on unmount ───────────────────────────── */
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-6 md:px-8 lg:px-16 xl:px-24">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <div className="rounded-3xl bg-gradient-to-br from-cyan-500/10 via-violet-500/5 to-transparent p-6 ring-1 ring-cyan-500/20">
              <Sparkles className="h-10 w-10 text-cyan-500/50" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-slate-300">Start a conversation</h3>
              <p className="mt-1 max-w-xs text-xs text-slate-500">
                Configure your LLM provider in Settings, then ask the agent anything.
                Responses stream in real-time.
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} content={m.content} streaming={m.streaming} />
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-800/60 bg-slate-900/30 px-4 py-3 md:px-8 lg:px-16 xl:px-24">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="flex items-end gap-2 rounded-2xl border border-slate-700/60 bg-slate-900/80 px-4 py-2 ring-1 ring-slate-800/50 transition focus-within:border-cyan-600/50 focus-within:ring-cyan-600/20"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything... (Enter to send, Shift+Enter for newline)"
              disabled={streaming}
              className="flex-1 resize-none bg-transparent py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 disabled:opacity-50"
              style={{ maxHeight: '120px' }}
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-600 text-white transition hover:bg-cyan-500 disabled:opacity-30"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
          <p className="mt-1.5 text-center text-[10px] text-slate-600">
            Responses are generated by your configured LLM provider. Keys are stored per-session.
          </p>
        </div>
      </div>
    </div>
  );
}
