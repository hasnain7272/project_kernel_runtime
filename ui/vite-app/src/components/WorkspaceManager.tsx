/**
 * WorkspaceManager — Ultra-premium workspace orchestration panel.
 *
 * Glass-morphism design, animated micro-interactions, split local/git views.
 * Integrates with the session's multi-workspace bindings.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useSessionStore, type Workspace } from '@/store/sessionStore';

// ── Icons (inline SVG for zero dependency) ──

const IconFolder = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const IconGit = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" />
    <path d="M13 6h3a2 2 0 0 1 2 2v7" /><line x1="6" y1="9" x2="6" y2="21" />
  </svg>
);

const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconX = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconChevron = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

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
    try {
      return JSON.parse(localStorage.getItem('ag-recent-paths') || '[]');
    } catch { return []; }
  });

  const inputRef = useRef<HTMLInputElement>(null);

  // Sync external modal trigger
  const isModalOpen = showModal || !!externalOpen;
  const closeModal = () => {
    setShowModal(false);
    onExternalClose?.();
  };

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
      setLocalPath('');
      setGitUrl('');
      setGitBranch('main');
      closeModal();
    } finally {
      setLoading(false);
    }
  }, [activeTab, localPath, gitUrl, gitBranch, addWorkspace, loading]);

  if (!sessionId) return null;

  const localWs = workspaces.filter(w => w.type === 'local');
  const gitWs = workspaces.filter(w => w.type === 'git');
  // When used as external-only modal (from header), skip sidebar rendering
  const isExternalOnly = externalOpen !== undefined;

  return (
    <>
      {!isExternalOnly && (
      <div className="wm-root">
        {/* ── Header ── */}
        <button className="wm-header" onClick={() => setExpanded(!expanded)}>
          <div className="wm-header-left">
            <span className={`wm-chevron ${expanded ? 'wm-chevron-open' : ''}`}><IconChevron /></span>
            <span className="wm-header-title">Workspaces</span>
            {workspaces.length > 0 && (
              <span className="wm-count">{workspaces.length}</span>
            )}
          </div>
          <button
            className="wm-add-trigger"
            onClick={(e) => { e.stopPropagation(); setShowModal(true); }}
            title="Attach workspace"
          >
            <IconPlus />
          </button>
        </button>

        {/* ── Workspace List ── */}
        {expanded && (
          <div className="wm-list">
            {workspaces.length === 0 ? (
              <button className="wm-empty" onClick={() => setShowModal(true)}>
                <div className="wm-empty-icon">
                  <IconFolder />
                </div>
                <span>Attach a project folder or repo</span>
              </button>
            ) : (
              <>
                {localWs.length > 0 && (
                  <div className="wm-group">
                    <div className="wm-group-label">
                      <span className="wm-dot wm-dot-local" />Local
                    </div>
                    {localWs.map((ws) => (
                      <WorkspaceCard key={ws.slug} ws={ws} onRemove={() => removeWorkspace(ws.slug)} />
                    ))}
                  </div>
                )}
                {gitWs.length > 0 && (
                  <div className="wm-group">
                    <div className="wm-group-label">
                      <span className="wm-dot wm-dot-git" />Repositories
                    </div>
                    {gitWs.map((ws) => (
                      <WorkspaceCard key={ws.slug} ws={ws} onRemove={() => removeWorkspace(ws.slug)} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
      )}

      {/* ── Add Workspace Modal ── */}
      {isModalOpen && (
        <div className="wm-overlay" onClick={closeModal}>
          <div className="wm-modal" onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div className="wm-modal-header">
              <h3 className="wm-modal-title">Add Workspace</h3>
              <button className="wm-modal-close" onClick={closeModal}>
                <IconX />
              </button>
            </div>

            {/* Tabs */}
            <div className="wm-modal-tabs">
              <button
                className={`wm-modal-tab ${activeTab === 'local' ? 'wm-modal-tab-active' : ''}`}
                onClick={() => setActiveTab('local')}
              >
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-blue-500/10 flex items-center justify-center">
                    <IconFolder />
                  </div>
                  <span>Sandbox Workspace</span>
                </div>
              </button>
              <button
                className={`wm-modal-tab ${activeTab === 'git' ? 'wm-modal-tab-active' : ''}`}
                onClick={() => setActiveTab('git')}
              >
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded bg-emerald-500/10 flex items-center justify-center">
                    <IconGit />
                  </div>
                  <span>Git Repository</span>
                </div>
              </button>
            </div>

            {/* Content */}
            <div className="wm-modal-body">
              {activeTab === 'local' ? (
                <div className="wm-form">
                  <div 
                    className="p-10 border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center gap-4 bg-slate-900/20 hover:bg-slate-900/40 hover:border-blue-500/30 transition-all cursor-pointer group"
                    onClick={() => document.getElementById('sandbox-upload-input')?.click()}
                  >
                    <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform">
                      <IconPlus />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-slate-200">Upload Project Files</p>
                      <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest font-mono">Drag & drop or click to browse</p>
                    </div>
                    <input 
                      id="sandbox-upload-input"
                      type="file" 
                      multiple 
                      /* @ts-ignore */
                      webkitdirectory=""
                      /* @ts-ignore */
                      directory=""
                      className="hidden" 
                      onChange={async (e) => {
                        const files = e.target.files;
                        if (!files?.length) return;
                        
                        setLoading(true);
                        try {
                          const formData = new FormData();
                          for (let i = 0; i < files.length; i++) {
                            // Use webkitRelativePath for folder structure preservation
                            const file = files[i];
                            const path = (file as any).webkitRelativePath || file.name;
                            formData.append('files', file, path);
                          }
                          
                          const sid = useSessionStore.getState().sessionId;
                          const res = await (await import('@/api/client')).apiClient.post(
                            `/workspace/sessions/${sid}/upload`, 
                            formData
                          );
                          
                          if (res.data.success) {
                            alert(`Successfully uploaded ${res.data.count} files/folders to sandbox.`);
                          }
                        } catch (err) {
                          console.error("[Upload] Failed:", err);
                          alert("Upload failed. Check console for details.");
                        } finally {
                          setLoading(false);
                        }
                      }}
                    />
                  </div>
                  
                  <div className="mt-6 flex items-center gap-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl">
                    <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
                      <IconCheck />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-blue-300">Isolated Environment</p>
                      <p className="text-[10px] text-blue-500/70 leading-relaxed">Files are uploaded to a secure, session-isolated Docker sandbox.</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="wm-form">
                  {/* GitHub Connection State */}
                  <div className="mb-6 p-4 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-slate-400">
                        <IconGit />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-200 uppercase tracking-widest">GitHub Studio</p>
                        <p className="text-[10px] text-slate-500 font-medium">Not connected to account</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => {
                        const sid = useSessionStore.getState().sessionId;
                        const origin = window.location.origin;
                        window.location.href = `/api/v1/github/auth?session_id=${sid}&redirect_uri=${origin}/github/callback`;
                      }}
                      className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 transition hover:bg-slate-700 active:scale-95 border border-slate-700/50"
                    >
                      Connect GitHub
                    </button>
                  </div>

                  <label className="wm-label">Repository URL</label>
                  <input
                    ref={inputRef}
                    className="wm-input"
                    placeholder="https://github.com/username/repository.git"
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && gitUrl.trim() && handleAdd()}
                  />

                  <label className="wm-label" style={{ marginTop: 12 }}>Branch / Environment</label>
                  <div className="wm-branch-row">
                    {['main', 'develop', 'production'].map((b) => (
                      <button
                        key={b}
                        className={`wm-branch-chip ${gitBranch === b ? 'wm-branch-chip-active' : ''}`}
                        onClick={() => setGitBranch(b)}
                      >
                        {b}
                      </button>
                    ))}
                    <input
                      className="wm-input wm-branch-input"
                      placeholder="custom..."
                      value={!['main', 'develop', 'production'].includes(gitBranch) ? gitBranch : ''}
                      onChange={(e) => setGitBranch(e.target.value)}
                    />
                  </div>
                  <p className="wm-hint">Choose the branch to mount into your workspace</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="wm-modal-footer">
              <button className="wm-btn-cancel" onClick={closeModal}>Cancel</button>
              <button
                className="wm-btn-submit"
                onClick={handleAdd}
                disabled={loading || (activeTab === 'local' ? !localPath.trim() : !gitUrl.trim())}
              >
                {loading ? (
                  <span className="wm-spinner" />
                ) : (
                  <><IconCheck /> Attach Workspace</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{styles}</style>
    </>
  );
}

// ── Workspace Card ──

function WorkspaceCard({ ws, onRemove }: { ws: Workspace; onRemove: () => void }) {
  const isGit = ws.type === 'git';
  return (
    <div className="wm-card">
      <div className={`wm-card-icon ${isGit ? 'wm-card-icon-git' : 'wm-card-icon-local'}`}>
        {isGit ? <IconGit /> : <IconFolder />}
      </div>
      <div className="wm-card-info">
        <span className="wm-card-name">{ws.slug}</span>
        <span className="wm-card-detail">
          {isGit ? `${ws.url?.replace('https://github.com/', '')} · ${ws.branch || 'main'}` : ws.path}
        </span>
      </div>
      <button className="wm-card-remove" onClick={onRemove} title="Remove">
        <IconX />
      </button>
    </div>
  );
}

// ── Styles ──

const styles = `
  .wm-root {
    border-bottom: 1px solid rgba(148,163,184,0.06);
  }

  /* Header */
  .wm-header {
    display: flex; align-items: center; justify-content: space-between;
    width: 100%; padding: 10px 14px; border: none; background: none;
    cursor: pointer; transition: background 0.15s;
  }
  .wm-header:hover { background: rgba(30,41,59,0.4); }
  .wm-header-left { display: flex; align-items: center; gap: 6px; }
  .wm-chevron {
    color: #475569; transition: transform 0.2s; display: flex;
  }
  .wm-chevron-open { transform: rotate(90deg); }
  .wm-header-title {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #94a3b8;
  }
  .wm-count {
    font-size: 10px; font-weight: 700; color: #06b6d4;
    background: rgba(6,182,212,0.1); border-radius: 10px;
    padding: 1px 7px; min-width: 18px; text-align: center;
  }
  .wm-add-trigger {
    width: 24px; height: 24px; border-radius: 6px;
    border: 1px dashed rgba(6,182,212,0.25); background: transparent;
    color: #06b6d4; cursor: pointer; display: flex;
    align-items: center; justify-content: center; transition: all 0.15s;
  }
  .wm-add-trigger:hover {
    background: rgba(6,182,212,0.1); border-color: #06b6d4;
    transform: scale(1.1);
  }

  /* Workspace list */
  .wm-list { padding: 0 8px 10px; }
  .wm-empty {
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    width: 100%; padding: 20px 12px; border-radius: 12px;
    border: 1.5px dashed rgba(148,163,184,0.1); background: rgba(15,23,42,0.3);
    cursor: pointer; transition: all 0.2s; color: #475569; font-size: 11px;
  }
  .wm-empty:hover {
    border-color: rgba(6,182,212,0.25); background: rgba(6,182,212,0.03);
    color: #64748b;
  }
  .wm-empty-icon {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, rgba(6,182,212,0.08), rgba(139,92,246,0.08));
    display: flex; align-items: center; justify-content: center;
    color: #475569;
  }

  /* Groups */
  .wm-group { margin-top: 6px; }
  .wm-group-label {
    display: flex; align-items: center; gap: 5px;
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #475569; padding: 4px 6px;
  }
  .wm-dot {
    width: 6px; height: 6px; border-radius: 50%;
  }
  .wm-dot-local { background: #a855f7; box-shadow: 0 0 6px rgba(168,85,247,0.4); }
  .wm-dot-git { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.4); }

  /* Cards */
  .wm-card {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 8px; border-radius: 8px; margin-top: 2px;
    transition: all 0.15s; cursor: default;
  }
  .wm-card:hover { background: rgba(30,41,59,0.6); }
  .wm-card-icon {
    width: 28px; height: 28px; border-radius: 7px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  .wm-card-icon-local { background: rgba(168,85,247,0.1); color: #a855f7; }
  .wm-card-icon-git { background: rgba(34,197,94,0.1); color: #22c55e; }
  .wm-card-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .wm-card-name {
    font-size: 12px; font-weight: 500; color: #e2e8f0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .wm-card-detail {
    font-size: 10px; color: #475569;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .wm-card-remove {
    width: 20px; height: 20px; border-radius: 5px; border: none;
    background: transparent; color: #334155; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    opacity: 0; transition: all 0.15s;
  }
  .wm-card:hover .wm-card-remove { opacity: 1; }
  .wm-card-remove:hover { background: rgba(239,68,68,0.12); color: #ef4444; }

  /* Modal overlay */
  .wm-overlay {
    position: fixed; inset: 0; z-index: 100;
    background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);
    display: flex; align-items: center; justify-content: center;
    animation: wm-fade-in 0.15s ease-out;
  }
  @keyframes wm-fade-in { from { opacity: 0; } to { opacity: 1; } }

  /* Modal */
  .wm-modal {
    width: 480px; max-width: 90vw;
    background: linear-gradient(165deg, rgba(15,23,42,0.98) 0%, rgba(2,6,23,0.98) 100%);
    border: 1px solid rgba(148,163,184,0.08);
    border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.6);
    animation: wm-scale-in 0.2s cubic-bezier(0.16,1,0.3,1);
    overflow: hidden;
  }
  @keyframes wm-scale-in {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }
  .wm-modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 20px 14px;
  }
  .wm-modal-title {
    font-size: 15px; font-weight: 700; color: #f1f5f9;
    letter-spacing: -0.01em;
  }
  .wm-modal-close {
    width: 28px; height: 28px; border-radius: 8px;
    border: 1px solid rgba(148,163,184,0.08); background: rgba(30,41,59,0.5);
    color: #64748b; cursor: pointer; display: flex;
    align-items: center; justify-content: center; transition: all 0.15s;
  }
  .wm-modal-close:hover { background: rgba(51,65,85,0.7); color: #94a3b8; }

  /* Tabs */
  .wm-modal-tabs {
    display: flex; gap: 4px; padding: 0 16px; margin-bottom: 4px;
  }
  .wm-modal-tab {
    flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 10px 14px; border-radius: 10px; border: 1px solid transparent;
    background: transparent; color: #64748b; font-size: 13px; font-weight: 500;
    cursor: pointer; transition: all 0.2s;
  }
  .wm-modal-tab:hover { background: rgba(30,41,59,0.5); color: #94a3b8; }
  .wm-modal-tab-active {
    background: rgba(6,182,212,0.06) !important;
    border-color: rgba(6,182,212,0.2) !important;
    color: #06b6d4 !important;
  }

  /* Form */
  .wm-modal-body { padding: 12px 20px 8px; }
  .wm-form { display: flex; flex-direction: column; }
  .wm-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #64748b; margin-bottom: 6px;
  }
  .wm-input {
    width: 100%; padding: 10px 14px; border-radius: 10px;
    border: 1px solid rgba(148,163,184,0.08);
    background: rgba(2,6,23,0.6); color: #e2e8f0;
    font-size: 13px; outline: none; transition: all 0.2s;
    box-sizing: border-box; font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .wm-input:focus {
    border-color: rgba(6,182,212,0.35);
    box-shadow: 0 0 0 3px rgba(6,182,212,0.08);
  }
  .wm-input::placeholder { color: #334155; }
  .wm-hint {
    font-size: 11px; color: #475569; margin-top: 6px;
  }

  /* Branch row */
  .wm-branch-row {
    display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  }
  .wm-branch-chip {
    padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 500;
    border: 1px solid rgba(148,163,184,0.08); background: rgba(15,23,42,0.6);
    color: #64748b; cursor: pointer; transition: all 0.15s;
  }
  .wm-branch-chip:hover { border-color: rgba(148,163,184,0.15); color: #94a3b8; }
  .wm-branch-chip-active {
    background: rgba(34,197,94,0.08) !important;
    border-color: rgba(34,197,94,0.25) !important;
    color: #22c55e !important;
  }
  .wm-branch-input {
    flex: 1; min-width: 100px; padding: 6px 10px !important;
    font-size: 12px !important;
  }

  /* Recent paths */
  .wm-recent { margin-top: 14px; }
  .wm-recent-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #334155; display: block; margin-bottom: 6px;
  }
  .wm-recent-item {
    display: flex; align-items: center; gap: 8px; width: 100%;
    padding: 7px 10px; border-radius: 8px; border: none;
    background: transparent; color: #64748b; font-size: 12px;
    cursor: pointer; transition: all 0.15s; text-align: left;
  }
  .wm-recent-item:hover { background: rgba(30,41,59,0.5); color: #94a3b8; }
  .wm-recent-item svg { flex-shrink: 0; width: 14px; height: 14px; }
  .wm-recent-path {
    flex: 1; font-size: 10px; color: #334155; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; text-align: right;
  }

  /* Footer */
  .wm-modal-footer {
    display: flex; justify-content: flex-end; gap: 8px;
    padding: 14px 20px 18px; border-top: 1px solid rgba(148,163,184,0.06);
  }
  .wm-btn-cancel {
    padding: 9px 18px; border-radius: 10px; font-size: 13px; font-weight: 500;
    border: 1px solid rgba(148,163,184,0.08); background: transparent;
    color: #64748b; cursor: pointer; transition: all 0.15s;
  }
  .wm-btn-cancel:hover { background: rgba(30,41,59,0.5); color: #94a3b8; }
  .wm-btn-submit {
    display: flex; align-items: center; gap: 6px;
    padding: 9px 20px; border-radius: 10px; font-size: 13px; font-weight: 600;
    border: none; cursor: pointer; transition: all 0.2s;
    background: linear-gradient(135deg, #06b6d4 0%, #8b5cf6 100%);
    color: white; box-shadow: 0 4px 16px rgba(6,182,212,0.2);
  }
  .wm-btn-submit:hover {
    box-shadow: 0 6px 24px rgba(6,182,212,0.3);
    transform: translateY(-1px);
  }
  .wm-btn-submit:disabled { opacity: 0.35; cursor: not-allowed; transform: none; box-shadow: none; }
  .wm-spinner {
    width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.2);
    border-top-color: white; border-radius: 50%;
    animation: wm-spin 0.5s linear infinite;
  }
  @keyframes wm-spin { to { transform: rotate(360deg); } }
`;
