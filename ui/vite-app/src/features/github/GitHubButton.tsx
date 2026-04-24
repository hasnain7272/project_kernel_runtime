/**
 * GitHub Connect Button
 * 
 * Premium OAuth button with popup flow.
 */
import { useState, useEffect } from 'react';
import { useSessionStore } from '@/store/sessionStore';
import { apiClient } from '@/api/client';

interface GitHubUser {
  login: string;
  name?: string;
  avatar_url?: string;
}

interface Props {
  onConnect?: (user: GitHubUser) => void;
}

export const GitHubButton: React.FC<Props> = ({ onConnect }) => {
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<GitHubUser | null>(null);
  const sessionId = useSessionStore((s) => s.sessionId);

  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data?.type === 'github-connected') {
        setUser(e.data.user);
        onConnect?.(e.data.user);
        setLoading(false);
      }
      if (e.data?.type === 'github-error') {
        setLoading(false);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onConnect]);

  const connect = () => {
    if (!sessionId) return;
    setLoading(true);
    
    const w = 500, h = 600;
    const left = window.screenX + (window.outerWidth - w) / 2;
    const top = window.screenY + (window.outerHeight - h) / 2;
    
    const popup = window.open(
      `/api/v1/github/auth?session_id=${sessionId}&redirect_uri=${encodeURIComponent(window.location.origin + '/github/callback')}`,
      'github-oauth',
      `width=${w},height=${h},left=${left},top=${top},popup`
    );
    
    const check = setInterval(() => {
      if (popup?.closed) {
        clearInterval(check);
        setLoading(false);
      }
    }, 500);
  };

  const disconnect = async () => {
    if (!sessionId) return;
    await apiClient.delete(`/github/disconnect?session_id=${sessionId}`);
    setUser(null);
  };

  if (user) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg border border-slate-700">
        {user.avatar_url && (
          <img src={user.avatar_url} alt={user.login} className="w-6 h-6 rounded-full" />
        )}
        <span className="text-sm text-slate-300">{user.login}</span>
        <button onClick={disconnect} className="text-xs text-slate-500 hover:text-red-400 ml-2">
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={connect}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 
                 text-slate-200 text-sm rounded-lg border border-slate-700
                 transition-all disabled:opacity-50"
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
      ) : (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
      )}
      Connect GitHub
    </button>
  );
};

export default GitHubButton;
