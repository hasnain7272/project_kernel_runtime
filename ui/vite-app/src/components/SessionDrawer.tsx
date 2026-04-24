/**
 * SessionDrawer — Slack-style session manager
 *
 * Full lifecycle: create, switch, rename, configure, and archive sessions.
 * Each session isolates its own LLM provider, API key, and conversation.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  X, Plus, Trash2, Settings, Cpu, Zap, Clock, Loader2, Radio, Pencil, Check,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { useTaskStore } from '@/store/taskStore';

/* ── Types ─────────────────────────────────────────────── */
interface SessionInfo {
  id: string;
  name: string;
  user_id: string;
  mode: string;
  created_at: string;
  model?: string;
  has_key?: boolean;
}

interface SessionDrawerProps {
  open: boolean;
  onClose: () => void;
  onOpenSettings: (sessionId: string) => void;
}

/* ── Editable Session Name ─────────────────────────────── */
function EditableName({ sessionId, name, onRename }: { sessionId: string; name: string; onRename: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const save = async () => {
    if (value.trim() && value.trim() !== name) {
      await apiClient.patch(`/sessions/${sessionId}/name`, { name: value.trim() });
      onRename();
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false); }}
          className="w-full rounded bg-slate-800 px-1.5 py-0.5 text-[11px] font-medium text-slate-200 outline-none ring-1 ring-cyan-500/40"
          maxLength={64}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 group/name">
      <span className="truncate text-[11px] font-medium text-slate-200">{name}</span>
      <button
        onClick={(e) => { e.stopPropagation(); setEditing(true); }}
        className="shrink-0 rounded p-0.5 text-slate-600 opacity-0 transition hover:text-cyan-400 group-hover/name:opacity-100"
      >
        <Pencil className="h-2.5 w-2.5" />
      </button>
    </div>
  );
}

/* ── Component ─────────────────────────────────────────── */
export function SessionDrawer({ open, onClose, onOpenSettings }: SessionDrawerProps) {
  const currentSessionId = useSessionStore((s) => s.sessionId);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const clearTasks = useTaskStore((s) => s.clearTasks);

  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  /* ── Load sessions ─────────────────────────────────────── */
  const loadSessions = useCallback(async () => {
    setLoading(true);
    const res = await apiClient.get<{ sessions: SessionInfo[] }>('/sessions/');
    if (res.data?.sessions) {
      const enriched = await Promise.all(
        res.data.sessions.map(async (s) => {
          const cfg = await apiClient.get<{ model: string; api_key_masked: string }>(
            `/sessions/${s.id}/config`,
          );
          return { ...s, model: cfg.data?.model || '', has_key: !!cfg.data?.api_key_masked };
        }),
      );
      setSessions(enriched);
    }
    setLoading(false);
  }, []);

  useEffect(() => { if (open) loadSessions(); }, [open, loadSessions]);

  /* ── Create ────────────────────────────────────────────── */
  const handleCreate = async () => {
    setCreating(true);
    const res = await apiClient.post<{ id: string }>('/sessions/', {
      name: 'New Session', mode: 'web',
    });
    if (res.data?.id) {
      setSessionId(res.data.id);
      clearTasks();
      await loadSessions();
      onOpenSettings(res.data.id);
    }
    setCreating(false);
  };

  /* ── Switch ────────────────────────────────────────────── */
  const handleSwitch = (id: string) => {
    if (id === currentSessionId) return;
    setSessionId(id);
    clearTasks();
    onClose();
  };

  /* ── End ────────────────────────────────────────────────── */
  const handleEnd = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await apiClient.delete(`/sessions/${id}`);
    if (id === currentSessionId) {
      const remaining = sessions.filter((s) => s.id !== id);
      if (remaining.length > 0) setSessionId(remaining[0].id);
    }
    await loadSessions();
  };

  /* ── Time ──────────────────────────────────────────────── */
  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />}
      <div
        className={`fixed left-0 top-0 z-50 flex h-full w-80 flex-col border-r border-slate-800/80 bg-slate-950/98 shadow-2xl shadow-black/40 transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 ring-1 ring-emerald-500/30">
              <Radio className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <h2 className="text-sm font-semibold text-slate-200">Sessions</h2>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-800 hover:text-slate-300">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Create */}
        <div className="border-b border-slate-800/60 p-3">
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600/90 to-blue-600/90 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-cyan-900/30 transition hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50"
          >
            {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            New Session
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-xs text-slate-600">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : sessions.length === 0 ? (
            <div className="px-5 py-12 text-center text-xs text-slate-600">No sessions yet.</div>
          ) : (
            <div className="space-y-1 p-2">
              {sessions.map((s) => {
                const isActive = s.id === currentSessionId;
                return (
                  <button
                    key={s.id}
                    onClick={() => handleSwitch(s.id)}
                    className={`group relative flex w-full items-start gap-3 rounded-xl px-3.5 py-3 text-left transition ${
                      isActive ? 'bg-slate-800/80 ring-1 ring-cyan-500/30' : 'hover:bg-slate-800/40'
                    }`}
                  >
                    {isActive && <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-cyan-500" />}

                    <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                      isActive ? 'bg-cyan-500/15 ring-1 ring-cyan-500/30' : 'bg-slate-800/60 ring-1 ring-slate-700/40'
                    }`}>
                      <Cpu className={`h-3.5 w-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                    </div>

                    <div className="min-w-0 flex-1">
                      {/* Editable name */}
                      <EditableName sessionId={s.id} name={s.name || s.id.slice(0, 8)} onRename={loadSessions} />

                      {/* Provider */}
                      <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-slate-500">
                        {s.model ? (
                          <><Zap className="h-2.5 w-2.5 text-amber-500" /><span className="truncate">{s.model.split('/').pop()}</span></>
                        ) : (
                          <span className="italic text-slate-600">No provider</span>
                        )}
                      </div>

                      {/* Meta */}
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-600">
                        <Clock className="h-2.5 w-2.5" />
                        <span>{timeAgo(s.created_at)}</span>
                        {s.has_key ? (
                          <span className="rounded bg-emerald-900/30 px-1 py-0.5 text-[9px] text-emerald-500">Key ✓</span>
                        ) : (
                          <span className="rounded bg-amber-900/30 px-1 py-0.5 text-[9px] text-amber-500">No Key</span>
                        )}
                      </div>
                    </div>

                    {/* Hover actions */}
                    <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition group-hover:opacity-100">
                      <button
                        onClick={(e) => { e.stopPropagation(); onOpenSettings(s.id); }}
                        className="rounded-md p-1 text-slate-500 transition hover:bg-slate-700 hover:text-cyan-400"
                        title="Provider settings"
                      >
                        <Settings className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleEnd(s.id, e)}
                        className="rounded-md p-1 text-slate-500 transition hover:bg-red-900/40 hover:text-red-400"
                        title="End session"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-slate-800/60 px-5 py-3">
          <p className="text-[10px] text-slate-600">
            Each session isolates its own LLM provider, API key, and conversation history.
          </p>
        </div>
      </div>
    </>
  );
}
