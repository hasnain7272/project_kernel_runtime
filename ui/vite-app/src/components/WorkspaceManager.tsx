/**
 * WorkspaceManager — Ultra-premium workspace orchestration panel.
 *
 * Glass-morphism design, animated micro-interactions, split local/git views.
 * Integrates with the session's multi-workspace bindings.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useSessionStore, type Workspace } from '@/store/sessionStore';
import { apiClient } from '@/api/client';
import { IconFolder, IconGit, IconPlus, IconX, IconCheck, IconChevron } from '@/features/workspace/WorkspaceIcons';
import { WorkspaceCard } from '@/features/workspace/WorkspaceCard';
import { workspaceStyles } from '@/features/workspace/WorkspaceStyles';

interface WorkspaceManagerProps {
  externalOpen?: boolean;
  onExternalClose?: () => void;
}

export function WorkspaceManager({ externalOpen, onExternalClose }: WorkspaceManagerProps = {}) {
  const workspaces = useSessionStore((s) => s.workspaces);
  const addWorkspace = useSessionStore((s) => s.addWorkspace);
  const removeWorkspace = useSessionStore((s) => s.removeWorkspace);
  const sessionId = useSessionStore((s) => s.sessionId);

  const [expanded, setExpanded] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'local' | 'git'>('local');
  const [localPath, setLocalPath] = useState('');
  const [gitUrl, setGitUrl] = useState('');
  const [gitBranch, setGitBranch] = useState('main');
  const [loading, setLoading] = useState(false);
  const [recentPaths] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('ag-recent-paths') || '[]'); }
    catch { return []; }
  });
  const inputRef = useRef<HTMLInputElement>(null);

  const isModalOpen = showModal || !!externalOpen;
  const closeModal = () => { setShowModal(false); onExternalClose?.(); };

  useEffect(() => {
    if (isModalOpen) setTimeout(() => inputRef.current?.focus(), 100);
  }, [isModalOpen, activeTab]);

  const saveRecent = (path: string) => {
    const paths = [path, ...recentPaths.filter(p => p !== path)].slice(0, 5);
    localStorage.setItem('ag-recent-paths', JSON.stringify(paths));
  };

  const handleAdd = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const ws: Workspace =
        activeTab === 'local'
          ? { type: 'local', path: localPath.trim(), slug: '' }
          : { type: 'git', url: gitUrl.trim(), branch: gitBranch.trim() || 'main', slug: '' };
      if (activeTab === 'local') saveRecent(localPath.trim());
      await addWorkspace(ws);
      setLocalPath(''); setGitUrl(''); setGitBranch('main');
      closeModal();
    } finally { setLoading(false); }
  }, [activeTab, localPath, gitUrl, gitBranch, addWorkspace, loading]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setLoading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const path = (file as any).webkitRelativePath || file.name;
        formData.append('files', file, path);
      }
      const sid = useSessionStore.getState().sessionId;
      const res = await apiClient.post(`/workspace/sessions/${sid}/upload`, formData);
      if (res.data.success) alert(`Successfully uploaded ${res.data.count} files/folders to sandbox.`);
    } catch (err) {
      console.error("[Upload] Failed:", err);
      alert("Upload failed. Check console for details.");
    } finally { setLoading(false); }
  };

  if (!sessionId) return null;

  const localWs = workspaces.filter(w => w.type === 'local');
  const gitWs = workspaces.filter(w => w.type === 'git');
  const isExternalOnly = externalOpen !== undefined;

  return (
    <>
      {!isExternalOnly && (
      <div className="wm-root">
        <button className="wm-header" onClick={() => setExpanded(!expanded)}>
          <div className="wm-header-left">
            <span className={`wm-chevron ${expanded ? 'wm-chevron-open' : ''}`}><IconChevron /></span>
            <span className="wm-header-title">Workspaces</span>
            {workspaces.length > 0 && <span className="wm-count">{workspaces.length}</span>}
          </div>
          <button className="wm-add-trigger" onClick={(e) => { e.stopPropagation(); setShowModal(true); }} title="Attach workspace">
            <IconPlus />
          </button>
        </button>

        {expanded && (
          <div className="wm-list">
            {workspaces.length === 0 ? (
              <button className="wm-empty" onClick={() => setShowModal(true)}>
                <div className="wm-empty-icon"><IconFolder /></div>
                <span>Attach a project folder or repo</span>
              </button>
            ) : (
              <>
                {localWs.length > 0 && (
                  <div className="wm-group">
                    <div className="wm-group-label"><span className="wm-dot wm-dot-local" />Local</div>
                    {localWs.map((ws) => <WorkspaceCard key={ws.slug} ws={ws} onRemove={() => removeWorkspace(ws.slug)} />)}
                  </div>
                )}
                {gitWs.length > 0 && (
                  <div className="wm-group">
                    <div className="wm-group-label"><span className="wm-dot wm-dot-git" />Repositories</div>
                    {gitWs.map((ws) => <WorkspaceCard key={ws.slug} ws={ws} onRemove={() => removeWorkspace(ws.slug)} />)}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
      )}

      {isModalOpen && (
        <div className="wm-overlay" onClick={closeModal}>
          <div className="wm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="wm-modal-header">
              <h3 className="wm-modal-title">Add Workspace</h3>
              <button className="wm-modal-close" onClick={closeModal}><IconX /></button>
            </div>
            <div className="wm-modal-tabs">
              <button className={`wm-modal-tab ${activeTab === 'local' ? 'wm-modal-tab-active' : ''}`} onClick={() => setActiveTab('local')}>
                <div className="flex items-center gap-2"><div className="w-5 h-5 rounded bg-blue-500/10 flex items-center justify-center"><IconFolder /></div><span>Sandbox Workspace</span></div>
              </button>
              <button className={`wm-modal-tab ${activeTab === 'git' ? 'wm-modal-tab-active' : ''}`} onClick={() => setActiveTab('git')}>
                <div className="flex items-center gap-2"><div className="w-5 h-5 rounded bg-emerald-500/10 flex items-center justify-center"><IconGit /></div><span>Git Repository</span></div>
              </button>
            </div>
            <div className="wm-modal-body">
              {activeTab === 'local' ? (
                <div className="wm-form">
                  <div className="p-10 border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center gap-4 bg-slate-900/20 hover:bg-slate-900/40 hover:border-blue-500/30 transition-all cursor-pointer group"
                    onClick={() => document.getElementById('sandbox-upload-input')?.click()}>
                    <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform"><IconPlus /></div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-slate-200">Upload Project Files</p>
                      <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest font-mono">Drag & drop or click to browse</p>
                    </div>
                    <input id="sandbox-upload-input" type="file" multiple webkitdirectory="" directory="" className="hidden" onChange={handleUpload} />
                  </div>
                  <div className="mt-6 flex items-center gap-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl">
                    <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400"><IconCheck /></div>
                    <div>
                      <p className="text-xs font-bold text-blue-300">Isolated Environment</p>
                      <p className="text-[10px] text-blue-500/70 leading-relaxed">Files are uploaded to a secure, session-isolated Docker sandbox.</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="wm-form">
                  <div className="mb-6 p-4 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-slate-400"><IconGit /></div>
                      <div>
                        <p className="text-xs font-bold text-slate-200 uppercase tracking-widest">GitHub Studio</p>
                        <p className="text-[10px] text-slate-500 font-medium">Not connected to account</p>
                      </div>
                    </div>
                    <button onClick={() => {
                      const sid = useSessionStore.getState().sessionId;
                      const origin = window.location.origin;
                      window.location.href = `/api/v1/github/auth?session_id=${sid}&redirect_uri=${origin}/github/callback`;
                    }} className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 transition hover:bg-slate-700 active:scale-95 border border-slate-700/50">Connect GitHub</button>
                  </div>
                  <label className="wm-label">Repository URL</label>
                  <input ref={inputRef} className="wm-input" placeholder="https://github.com/username/repository.git" value={gitUrl} onChange={(e) => setGitUrl(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && gitUrl.trim() && handleAdd()} />
                  <label className="wm-label" style={{ marginTop: 12 }}>Branch / Environment</label>
                  <div className="wm-branch-row">
                    {['main', 'develop', 'production'].map((b) => (
                      <button key={b} className={`wm-branch-chip ${gitBranch === b ? 'wm-branch-chip-active' : ''}`} onClick={() => setGitBranch(b)}>{b}</button>
                    ))}
                    <input className="wm-input wm-branch-input" placeholder="custom..." value={!['main', 'develop', 'production'].includes(gitBranch) ? gitBranch : ''} onChange={(e) => setGitBranch(e.target.value)} />
                  </div>
                  <p className="wm-hint">Choose the branch to mount into your workspace</p>
                </div>
              )}
            </div>
            <div className="wm-modal-footer">
              <button className="wm-btn-cancel" onClick={closeModal}>Cancel</button>
              <button className="wm-btn-submit" onClick={handleAdd} disabled={loading || (activeTab === 'local' ? !localPath.trim() : !gitUrl.trim())}>
                {loading ? <span className="wm-spinner" /> : <><IconCheck /> Attach Workspace</>}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{workspaceStyles}</style>
    </>
  );
}
