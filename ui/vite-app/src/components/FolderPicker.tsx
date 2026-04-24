/**
 * FolderPicker — SaaS project selector modal.
 * Ultra-premium, sub-150 line implementation.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Plus, Folder, FolderOpen, Loader2, Check, Trash2 } from 'lucide-react';
import { apiClient } from '@/api/client';

const COLORS = [
  { id: 'cyan', bg: 'bg-cyan-500/20', ring: 'ring-cyan-500/50', text: 'text-cyan-400' },
  { id: 'violet', bg: 'bg-violet-500/20', ring: 'ring-violet-500/50', text: 'text-violet-400' },
  { id: 'amber', bg: 'bg-amber-500/20', ring: 'ring-amber-500/50', text: 'text-amber-400' },
  { id: 'emerald', bg: 'bg-emerald-500/20', ring: 'ring-emerald-500/50', text: 'text-emerald-400' },
  { id: 'rose', bg: 'bg-rose-500/20', ring: 'ring-rose-500/50', text: 'text-rose-400' },
  { id: 'sky', bg: 'bg-sky-500/20', ring: 'ring-sky-500/50', text: 'text-sky-400' },
];

interface Folder { id: string; name: string; slug: string; color: string; description: string; permission: string; }

interface Props { open: boolean; onClose: () => void; onSelect: (f: Folder) => void; }

function FolderItem({ f, onSelect, onDelete }: { f: Folder; onSelect: () => void; onDelete: () => void }) {
  const c = COLORS.find(x => x.id === f.color) || COLORS[0];
  return (
    <div className={`group flex items-center gap-3 rounded-lg p-3 transition hover:bg-slate-800/60 ${c.bg}`}>
      <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${c.bg} ${c.ring} ring-1`}>
        <Folder className={`h-5 w-5 ${c.text}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-slate-200">{f.name}</span>
          {f.permission !== 'viewer' && (
            <span className="rounded bg-slate-800/80 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">{f.permission}</span>
          )}
        </div>
        {f.description && <p className="mt-0.5 truncate text-xs text-slate-500">{f.description}</p>}
      </div>
      <div className="flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
        {f.permission === 'owner' && (
          <button onClick={onDelete} className="rounded p-1.5 text-slate-500 hover:bg-red-900/30 hover:text-red-400">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
        <button onClick={onSelect} className="rounded p-1.5 text-slate-500 hover:bg-slate-700 hover:text-slate-300">
          <FolderOpen className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}export function FolderPicker({ open, onClose, onSelect }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [load, setLoad] = useState(false);
  const [mode, setMode] = useState<'list' | 'create' | 'import' | 'clone'>('list');
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [branch, setBranch] = useState('main');
  const [desc, setDesc] = useState('');
  const [color, setColor] = useState('cyan');

  const loadFolders = useCallback(async () => {
    setLoad(true);
    try {
      const res = await apiClient.get<{ folders: Folder[] }>('/folders/');
      if (res.data?.folders) setFolders(res.data.folders);
    } catch (e) {
      console.error('Folder load failed', e);
    } finally {
      setLoad(false);
    }
  }, []);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open) {
      if (!el.open) el.showModal();
      loadFolders();
    } else {
      if (el.open) el.close();
      setMode('list');
    }
  }, [open, loadFolders]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setLoad(true);
    try {
      await apiClient.post('/folders/', { name: name.trim(), description: desc.trim(), color });
      await loadFolders();
      setMode('list');
      setName(''); setDesc(''); setColor('cyan');
    } catch (e: any) {
      alert(e.message || 'Create failed');
    } finally {
      setLoad(false);
    }
  };

  const handleImportLocal = async () => {
    if (!name.trim() || !path.trim()) return;
    setLoad(true);
    try {
      const res = await apiClient.post<any>('/folders/import-local', { 
        name: name.trim(), 
        local_path: path.trim(), 
        color, 
        description: 'Linked local directory' 
      });
      if (res.data) {
        await loadFolders();
        setMode('list');
        setName(''); setPath('');
      } else {
        alert(res.error || 'Import failed');
      }
    } catch (e: any) {
      alert(e.message || 'Import failed');
    } finally {
      setLoad(false);
    }
  };

  const handleCloneRepo = async () => {
    if (!name.trim() || !path.trim()) return; // path is repo_url here
    setLoad(true);
    try {
      const res = await apiClient.post<any>('/folders/clone', { 
        name: name.trim(), 
        repo_url: path.trim(), 
        branch,
        color: 'violet', 
      });
      if (res.data) {
        await loadFolders();
        setMode('list');
        setName(''); setPath(''); setBranch('main');
      } else {
        alert(res.error || 'Clone failed');
      }
    } catch (e: any) {
      alert(e.message || 'Clone failed');
    } finally {
      setLoad(false);
    }
  };

  const handleDel = async (id: string) => {
    if (!confirm('This will unlink or delete the project workspace. Proceed?')) return;
    await apiClient.delete(`/folders/${id}`);
    await loadFolders();
  };

  if (!open) return null;

  return (
    <dialog ref={dialogRef} onCancel={onClose}
      className="fixed inset-0 z-50 m-auto h-auto w-full max-w-md rounded-2xl border border-slate-700/60 bg-slate-900/95 p-0 text-slate-100 shadow-2xl shadow-black/60 backdrop:bg-black/70 backdrop:backdrop-blur-sm scale-in">
      <div className="flex flex-col">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/20 to-indigo-500/20 ring-1 ring-blue-500/30">
              <Folder className="h-4 w-4 text-blue-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-tight">Project Manager</h2>
              <p className="text-[11px] text-slate-500">Initialize or switch your active project</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-3 border-b border-slate-800/60 bg-slate-800/10 flex gap-1.5">
           <button onClick={() => setMode('create')} className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition ${mode === 'create' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'}`}><Plus className="h-3 w-3"/> Cloud</button>
           <button onClick={() => setMode('import')} className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition ${mode === 'import' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'}`}>
             <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M2 20h20M2 14V5a2 2 0 012-2h16a2 2 0 012 2v9M9 21v-3m6 3v-3"/></svg> Local
           </button>
           <button onClick={() => setMode('clone')} className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider transition ${mode === 'clone' ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'}`}>
             <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg> Git
           </button>
        </div>

        {mode === 'create' && (
          <div className="space-y-4 px-5 py-6">
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Project Name</label>
              <input value={name} onChange={e => setName(e.target.value)} autoFocus placeholder="e.g. My Next.js Blog"
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-violet-600/60 focus:ring-1 focus:ring-violet-600/30 transition" />
            </div>
            <div className="flex gap-2 justify-center">
              {COLORS.map(col => (
                <button key={col.id} onClick={() => setColor(col.id)}
                  className={`h-7 w-7 rounded-full ${col.bg} transition-all ${color === col.id ? `${col.ring} ring-2 scale-110` : 'opacity-40 hover:opacity-100'}`} />
              ))}
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={() => setMode('list')} className="flex-1 rounded-lg border border-slate-700 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 transition">Cancel</button>
              <button onClick={handleCreate} disabled={load || !name.trim()}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 py-2 text-xs font-bold text-white shadow-lg hover:bg-violet-500 transition disabled:opacity-50">
                {load ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Create Workspace'}
              </button>
            </div>
          </div>
        )}

        {mode === 'import' && (
          <div className="space-y-4 px-5 py-6">
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Workspace Name</label>
              <input value={name} onChange={e => setName(e.target.value)} autoFocus placeholder="e.g. Local Frontend"
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition" />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Absolute Host Path</label>
              <input value={path} onChange={e => setPath(e.target.value)} placeholder="C:\Users\...\my-project"
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={() => setMode('list')} className="flex-1 rounded-lg border border-slate-700 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 transition">Cancel</button>
              <button onClick={handleImportLocal} disabled={load || !name.trim() || !path.trim()}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-cyan-600 py-2 text-xs font-bold text-white shadow-lg hover:bg-cyan-500 transition disabled:opacity-50">
                {load ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Link Local Directory'}
              </button>
            </div>
          </div>
        )}

        {mode === 'clone' && (
          <div className="space-y-4 px-5 py-6">
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Workspace Name</label>
              <input value={name} onChange={e => setName(e.target.value)} autoFocus placeholder="e.g. NextJS UI"
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-600/60 focus:ring-1 focus:ring-indigo-600/30 transition" />
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Repo URL (HTTPS)</label>
                <input value={path} onChange={e => setPath(e.target.value)} placeholder="https://github.com/..."
                  className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-600/60 focus:ring-1 focus:ring-indigo-600/30 transition font-mono" />
              </div>
              <div className="w-24">
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Branch</label>
                <input value={branch} onChange={e => setBranch(e.target.value)} placeholder="main"
                  className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-600/60 focus:ring-1 focus:ring-indigo-600/30 transition font-mono" />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={() => setMode('list')} className="flex-1 rounded-lg border border-slate-700 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 transition">Cancel</button>
              <button onClick={handleCloneRepo} disabled={load || !name.trim() || !path.trim()}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 py-2 text-xs font-bold text-white shadow-lg hover:bg-indigo-500 transition disabled:opacity-50">
                {load ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : (
                  <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                )}
                {load ? 'Cloning...' : 'Clone Repository'}
              </button>
            </div>
          </div>
        )}

        {mode === 'list' && (
          <div className="max-h-72 overflow-y-auto custom-scrollbar">
            {load ? <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-500" /></div>
              : folders.length === 0 ? <div className="py-12 text-center"><FolderOpen className="mx-auto h-10 w-10 text-slate-700" /><p className="mt-3 text-sm text-slate-500">No projects yet</p></div>
              : <div className="space-y-1 px-3 py-2">{folders.map(f => <FolderItem key={f.id} f={f} onSelect={() => { onSelect(f); onClose(); }} onDelete={() => handleDel(f.id)} />)}</div>}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3">
          <p className="text-[10px] text-slate-600 uppercase tracking-widest font-bold font-mono">{folders.length.toString().padStart(2, '0')} // WORKSPACES</p>
          <button onClick={onClose} className="rounded-lg text-xs text-slate-500 transition hover:text-slate-300">Close</button>
        </div>
      </div>
    </dialog>
  );
}