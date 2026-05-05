import { useSessionStore } from '@/store/sessionStore';
import { IconGit } from '@/features/workspace/WorkspaceIcons';

interface Props {
  gitUrl: string;
  gitBranch: string;
  inputRef: React.RefObject<HTMLInputElement>;
  onGitUrl: (value: string) => void;
  onGitBranch: (value: string) => void;
  onSubmit: () => void;
}

const branches = ['main', 'develop', 'production'];

export function GitWorkspaceTab({ gitUrl, gitBranch, inputRef, onGitUrl, onGitBranch, onSubmit }: Props) {
  const connect = () => {
    const sid = useSessionStore.getState().sessionId;
    const origin = window.location.origin;
    window.location.href = `/api/v1/github/auth?session_id=${sid}&redirect_uri=${origin}/github/callback`;
  };

  return (
    <div className="wm-form">
      <div className="mb-6 flex items-center justify-between rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-slate-400"><IconGit /></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-slate-200">GitHub Studio</p>
            <p className="text-[10px] font-medium text-slate-500">Connect account or paste a repository URL</p>
          </div>
        </div>
        <button onClick={connect} className="rounded-lg border border-slate-700/50 bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 transition hover:bg-slate-700">Connect</button>
      </div>
      <label className="wm-label">Repository URL</label>
      <input ref={inputRef} className="wm-input" placeholder="https://github.com/username/repository.git" value={gitUrl} onChange={(event) => onGitUrl(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && gitUrl.trim() && onSubmit()} />
      <label className="wm-label" style={{ marginTop: 12 }}>Branch</label>
      <div className="wm-branch-row">
        {branches.map((branch) => <button key={branch} className={`wm-branch-chip ${gitBranch === branch ? 'wm-branch-chip-active' : ''}`} onClick={() => onGitBranch(branch)}>{branch}</button>)}
        <input className="wm-input wm-branch-input" placeholder="custom..." value={!branches.includes(gitBranch) ? gitBranch : ''} onChange={(event) => onGitBranch(event.target.value)} />
      </div>
      <p className="wm-hint">Choose the branch to mount into your workspace.</p>
    </div>
  );
}
