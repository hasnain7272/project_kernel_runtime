import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';
import { Badge } from '@/components/ui/badge';
import { TerminalSquare } from 'lucide-react';

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [sending, setSending] = useState(false);
  const sessionId = useSessionStore((s) => s.sessionId);
  const upsertTask = useTaskStore((s) => s.upsertTask);
  const setActiveTask = useTaskStore((s) => s.setActiveTask);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((o) => !o);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || sending) return;
    setSending(true);

    // Actually dispatch to FastAPI
    const res = await apiClient.post<{ task_id: string }>('/tasks/', {
      session_id: sessionId,
      description: query.trim(),
    });

    if (res.data?.task_id) {
      upsertTask({ id: res.data.task_id, description: query, status: 'pending' });
      setActiveTask(res.data.task_id);
    }

    setSending(false);
    setIsOpen(false);
    setQuery('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[20vh] backdrop-blur-sm" onClick={() => setIsOpen(false)}>
      <div className="w-full max-w-2xl overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit} className="flex items-center border-b border-slate-800 px-4">
          <TerminalSquare className="mr-3 h-5 w-5 text-slate-500" />
          <input
            autoFocus
            type="text"
            className="flex h-16 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-slate-500"
            placeholder="Type a command or ask the agent..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={sending}
          />
          <Badge variant="outline">{sending ? '...' : 'Enter ↵'}</Badge>
        </form>
        <div className="p-4 text-xs text-slate-500">
          Press <kbd className="px-1 py-0.5 rounded bg-slate-800 font-mono">ESC</kbd> to close.
        </div>
      </div>
    </div>
  );
}
