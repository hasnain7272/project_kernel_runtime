import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';
import { Badge } from '@/components/ui/badge';
import { TerminalSquare, FolderOpen, Settings, Zap } from 'lucide-react';

interface Folder {
  id: string;
  name: string;
  slug: string;
  color: string;
}

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState<'command' | 'folders'>('command');
  const [query, setQuery] = useState('');
  const [sending, setSending] = useState(false);
  const [folders, setFolders] = useState<Folder[]>([]);
  const sessionId = useSessionStore((s) => s.sessionId);
  const mountedFolders = useSessionStore((s) => s.mountedFolders);
  const ensureSession = useSessionStore((s) => s.ensureSession);
  const upsertTask = useTaskStore((s) => s.upsertTask);
  const setActiveTask = useTaskStore((s) => s.setActiveTask);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const handleOpen = async () => {
    setIsOpen(true);
    setMode('command');
    const res = await apiClient.get<{ folders: Folder[] }>('/folders/');
    if (res.data?.folders) setFolders(res.data.folders);
  };

  const handleSelectFolder = async (folder: Folder) => {
    await ensureSession([folder.slug]);
    setIsOpen(false);
    setQuery('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || sending) return;
    setSending(true);

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

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-[15vh] backdrop-blur-sm fade-in" 
      onClick={() => setIsOpen(false)}
    >
      <div className="w-full max-w-2xl overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl scale-in" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit} className="flex items-center border-b border-slate-800 px-4">
          <TerminalSquare className="mr-3 h-5 w-5 text-slate-500" />
          <input
            ref={inputRef}
            autoFocus
            type="text"
            className="flex h-14 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-slate-500"
            placeholder="Ask the agent or switch projects..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={sending}
          />
          <Badge variant="outline" className={sending ? 'animate-pulse' : ''}>
            {sending ? '...' : 'Enter ↵'}
          </Badge>
        </form>

        {/* Folder shortcuts */}
        {folders.length > 0 && (
          <div className="border-b border-slate-800/60">
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
              Recent Projects
            </div>
            <div className="max-h-40 overflow-y-auto pb-2">
              {folders.slice(0, 5).map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => handleSelectFolder(folder)}
                  className={`flex w-full items-center gap-3 px-4 py-2 text-left transition hover:bg-slate-800/60 ${
                    mountedFolders.includes(folder.slug) ? 'bg-slate-800/60' : ''
                  }`}
                >
                  <FolderOpen className="h-4 w-4 text-violet-400" />
                  <span className="flex-1 text-sm text-slate-300 truncate">{folder.name}</span>
                  <span className="text-xs text-slate-600">{folder.slug.split('-').slice(0, 2).join('-')}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="border-b border-slate-800/60">
          <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
            Quick Actions
          </div>
          <div className="pb-2">
            <button className="flex w-full items-center gap-3 px-4 py-2 text-left transition hover:bg-slate-800/60" onClick={(e) => { e.preventDefault(); setQuery('/search '); inputRef.current?.focus(); }}>
              <span className="flex h-5 w-5 items-center justify-center rounded bg-cyan-900/40 text-cyan-400">?</span>
              <span className="flex-1 text-sm text-slate-300">Global Search</span>
              <span className="text-xs text-slate-600">Type /search</span>
            </button>
            <button className="flex w-full items-center gap-3 px-4 py-2 text-left transition hover:bg-slate-800/60" onClick={(e) => { e.preventDefault(); setQuery('/tools '); inputRef.current?.focus(); }}>
              <Zap className="h-4 w-4 text-emerald-400" />
              <span className="flex-1 text-sm text-slate-300">Tool Registry</span>
              <span className="text-xs text-slate-600">Type /tools</span>
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-2.5 text-xs text-slate-600">
          <div className="flex gap-3">
            <span><kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono">⌘K</kbd> Command</span>
            <span><kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono">ESC</kbd> Close</span>
          </div>
          <span className="flex items-center gap-1 text-slate-500">
            <Zap className="h-3 w-3" /> AI-powered
          </span>
        </div>
      </div>
    </div>
  );
}
