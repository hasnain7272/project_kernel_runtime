/**
 * ChatPane — Ultra-premium SaaS chat interface.
 * Sub-150 line implementation with full functionality.
 */
import { useRef, useState, useEffect, useCallback } from 'react';
import { Send, Sparkles, Loader2, Paperclip } from 'lucide-react';
import { apiClient, getAuthToken } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';
import { useToastStore } from '@/components/Toast';
import { MessageBubble } from '@/features/chat/MessageBubble';

interface Msg { role: 'user' | 'assistant' | 'tool' | 'system'; content: string; streaming?: boolean; tool_calls?: any[]; }

export function ChatPane() {
  const [input, setInput] = useState('');
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [stream, setStream] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sid = useSessionStore(s => s.sessionId);
  const tenantId = useSessionStore(s => s.tenantId);
  const upsertTask = useTaskStore(s => s.upsertTask);
  const setActive = useTaskStore(s => s.setActiveTask);
  const addToast = useToastStore(s => s.addToast);

  const loadHistory = useCallback(async () => {
    if (!sid) return;
    const res = await apiClient.get<{messages: Msg[]}>(`/chat/${sid}/history`);
    if (res.data?.messages) {
      setMsgs(res.data.messages);
    } else {
      setMsgs([]);
    }
  }, [sid]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  useEffect(() => {
    const handleInsert = (event: Event) => {
      const detail = (event as CustomEvent<{ text?: string }>).detail;
      if (detail?.text) {
        setInput((prev) => (prev ? `${prev}\n${detail.text}` : detail.text));
        inputRef.current?.focus();
      }
    };
    window.addEventListener('ag-insert-prompt', handleInsert as EventListener);
    return () => window.removeEventListener('ag-insert-prompt', handleInsert as EventListener);
  }, []);

  const streamResponse = useCallback((taskId: string) => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const tid = tenantId || localStorage.getItem('tenant_id') || 'local';
    const params = new URLSearchParams({ tenant_id: tid });
    const token = getAuthToken();
    if (token) params.set('token', token);
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/tasks/${taskId}/stream?${params.toString()}`);
    wsRef.current = ws; let buf = '';
    ws.onopen = () => { setStream(true); setMsgs(p => [...p, { role: 'assistant', content: '', streaming: true }]); };
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        
        // Final resolution
        if (d.event_type === 'TASK_RESOLVED' || d.event === 'TASK_RESOLVED') {
          setStream(false);
          ws.close();
          loadHistory();
          return;
        }

        // Structured Events (Token, Reasoning, Tool)
        if (d.event === 'token') {
          buf += d.text;
          setMsgs(p => {
            const u = [...p];
            const l = u[u.length - 1];
            if (l?.streaming) l.content = buf;
            return [...u];
          });
        } else if (d.event === 'tool_start' || d.event === 'tool_executing') {
          setMsgs(p => {
            const u = [...p];
            const l = u[u.length - 1];
            if (l?.role === 'assistant') {
              const tc = { function: { name: d.name, arguments: d.args || '' }, status: 'running' };
              l.tool_calls = [...(l.tool_calls || []), tc];
            }
            return [...u];
          });
        }
      } catch {
        // Fallback for raw text tokens (legacy or unformatted)
        const txt = e.data.replace(/\x1b\[[0-9;]*m/g, '');
        if (txt.trim()) {
          buf += txt;
          setMsgs(p => {
            const u = [...p];
            const l = u[u.length - 1];
            if (l?.streaming) l.content = buf;
            return [...u];
          });
        }
      }
    };
    ws.onerror = () => { setStream(false); addToast('error', 'WS failed.'); };
    ws.onclose = () => { wsRef.current = null; setStream(false); loadHistory(); };
  }, [addToast, tenantId, loadHistory]);

  const send = async () => {
    if (!input.trim() || stream) return;
    const txt = input.trim(); setInput('');
    setMsgs(p => [...p, { role: 'user', content: txt }]);
    const res = await apiClient.post<{ task_id: string }>('/chat/', { session_id: sid, message: txt, shadow_mode: shadowMode });
    if (res.data?.task_id) { upsertTask({ id: res.data.task_id, description: txt, status: 'running' }); setActive(res.data.task_id); streamResponse(res.data.task_id); }
    else { setMsgs(p => [...p, { role: 'system', content: res.error || 'Failed' }]); addToast('error', res.error || 'Failed'); }
  };

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f || !sid) return;
    const formData = new FormData();
    formData.append('files', f);
    
    addToast('info', 'Uploading...');
    const res = await apiClient.post(`/workspace/sessions/${sid}/upload`, formData);
    
    if (res.data) {
      addToast('success', 'File uploaded to sandbox!');
      setMsgs(p => [...p, { role: 'system', content: `📎 Uploaded: ${f.name}` }]);
      window.dispatchEvent(new Event('refresh-workspace'));
    } else {
      addToast('error', res.error || 'Upload failed');
    }
  };

  const handleKey = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };
  useEffect(() => () => { if (wsRef.current) wsRef.current.close(); }, []);

  const [shadowMode, setShadowMode] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-6 md:px-8 lg:px-16 xl:px-24">
        {msgs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <div className="rounded-3xl bg-gradient-to-br from-cyan-500/10 via-violet-500/5 to-transparent p-6 ring-1 ring-cyan-500/20">
              <Sparkles className="h-10 w-10 text-cyan-500/50" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-slate-300">Start a conversation</h3>
              <p className="mt-1 max-w-xs text-xs text-slate-500">Configure your LLM provider in Settings, then ask the agent anything.</p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">{msgs.map((m, i) => <MessageBubble key={i} role={m.role} content={m.content} streaming={m.streaming} tool_calls={m.tool_calls} />)}</div>
        )}
        <div ref={endRef} />
      </div>
      <div className="border-t border-slate-800/60 bg-slate-900/30 px-4 py-3 md:px-8 lg:px-16 xl:px-24">
        <div className="mx-auto max-w-3xl">
          <form onSubmit={e => { e.preventDefault(); send(); }}
            className="flex items-end gap-2 rounded-2xl border border-slate-700/60 bg-slate-900/80 px-4 py-2 ring-1 ring-slate-800/50 transition focus-within:border-cyan-600/50 focus-within:ring-cyan-600/20">
            <textarea ref={inputRef} rows={1} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey} placeholder="Ask anything... (Enter to send)" disabled={stream}
              className="flex-1 resize-none bg-transparent py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 disabled:opacity-50" style={{ maxHeight: '120px' }} />
            
            <label className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-800 hover:text-slate-200">
              <input type="file" className="hidden" onChange={upload} />
              <Paperclip className="h-3.5 w-3.5" />
            </label>

            <button type="button" onClick={() => setShadowMode(!shadowMode)} className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition ${shadowMode ? 'bg-amber-500/20 text-amber-500 ring-1 ring-amber-500/50' : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'}`} title="Toggle Shadow Mode (Dry Run)">
              <div className={`h-2.5 w-2.5 rounded-full ${shadowMode ? 'bg-amber-400 animate-pulse' : 'bg-slate-600'}`} />
            </button>

            <button type="submit" disabled={stream || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-600 text-white transition hover:bg-cyan-500 disabled:opacity-30">
              {stream ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </form>
          <p className="mt-1.5 text-center text-[10px] text-slate-600">Responses are generated by your configured LLM provider.</p>
        </div>
      </div>
    </div>
  );
}
