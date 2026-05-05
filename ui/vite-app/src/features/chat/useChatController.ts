import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient, getAuthToken } from '@/api/client';
import { useToastStore } from '@/components/Toast';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';
import type { Msg } from '@/features/chat/types';

const CHAT_STORAGE_KEY = 'ag-chat-messages';
const fromStorage = () => {
  try { return JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '[]') as Msg[]; }
  catch { return []; }
};

export function useChatController() {
  const [input, setInput] = useState('');
  const [msgs, setMsgs] = useState<Msg[]>(fromStorage);
  const [streaming, setStreaming] = useState(false);
  const [shadowMode, setShadowMode] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sid = useSessionStore((s) => s.sessionId);
  const tenantId = useSessionStore((s) => s.tenantId);
  const upsertTask = useTaskStore((s) => s.upsertTask);
  const setActive = useTaskStore((s) => s.setActiveTask);
  const addToast = useToastStore((s) => s.addToast);

  const loadHistory = useCallback(async () => {
    if (!sid) return;
    const res = await apiClient.get<{ messages: Msg[] }>(`/chat/${sid}/history`);
    if (res.data?.messages?.length) {
      setMsgs(res.data.messages);
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(res.data.messages));
    } else if (!localStorage.getItem(CHAT_STORAGE_KEY)) setMsgs([]);
  }, [sid]);

  const streamTask = useCallback((taskId: string) => {
    wsRef.current?.close();
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const params = new URLSearchParams({ tenant_id: tenantId || localStorage.getItem('tenant_id') || 'local' });
    const token = getAuthToken();
    if (token) params.set('token', token);
    const ws = new WebSocket(`${proto}//${window.location.host}/api/v1/tasks/${taskId}/stream?${params}`);
    wsRef.current = ws;
    let buffer = '';
    ws.onopen = () => { setStreaming(true); setMsgs((p) => [...p, { role: 'assistant', content: '', streaming: true }]); };
    ws.onmessage = (event) => {
      const raw = String(event.data);
      try {
        const data = JSON.parse(raw);
        if (data.event_type === 'TASK_RESOLVED' || data.event === 'TASK_RESOLVED') return ws.close();
        if (data.event === 'token') buffer += data.text;
        if (data.event === 'tool_start' || data.event === 'tool_executing') {
          setMsgs((p) => p.map((m, i) => i === p.length - 1 ? { ...m, tool_calls: [...(m.tool_calls || []), { function: { name: data.name, arguments: data.args || '' }, status: 'running' }] } : m));
        }
      } catch {
        buffer += raw.replace(/\x1b\[[0-9;]*m/g, '');
      }
      if (buffer.trim()) setMsgs((p) => p.map((m, i) => i === p.length - 1 && m.streaming ? { ...m, content: buffer } : m));
    };
    ws.onerror = () => { setStreaming(false); addToast('error', 'Live stream disconnected.'); };
    ws.onclose = () => { wsRef.current = null; setStreaming(false); loadHistory(); };
  }, [addToast, loadHistory, tenantId]);

  const send = async () => {
    if (!input.trim() || streaming) return;
    const text = input.trim();
    setInput('');
    setMsgs((p) => [...p, { role: 'user', content: text }]);
    const res = await apiClient.post<{ task_id: string }>('/chat/', { session_id: sid, message: text, shadow_mode: shadowMode });
    if (!res.data?.task_id) return addToast('error', res.error || 'Failed to start task.');
    upsertTask({ id: res.data.task_id, description: text, status: 'running' });
    setActive(res.data.task_id);
    streamTask(res.data.task_id);
  };

  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !sid) return;
    const body = new FormData();
    body.append('files', file);
    addToast('info', 'Uploading...');
    const res = await apiClient.post(`/workspace/sessions/${sid}/upload`, body);
    if (!res.data) return addToast('error', res.error || 'Upload failed');
    addToast('success', 'File uploaded');
    setMsgs((p) => [...p, { role: 'system', content: `Attached: ${file.name}` }]);
    window.dispatchEvent(new Event('refresh-workspace'));
  };

  useEffect(() => { if (msgs.length) localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(msgs)); }, [msgs]);
  useEffect(() => { loadHistory(); }, [loadHistory]);
  useEffect(() => () => wsRef.current?.close(), []);

  return { input, msgs, streaming, shadowMode, inputRef, setInput, send, upload, setShadowMode };
}
