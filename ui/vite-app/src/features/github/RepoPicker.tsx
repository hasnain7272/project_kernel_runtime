/**
 * Repository Picker
 * 
 * Browse and select GitHub repositories for the session.
 */
import { useState, useEffect, useCallback } from 'react';
import { useSessionStore } from '@/store/sessionStore';
import { apiClient } from '@/api/client';

interface Repo {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  private: boolean;
  updated_at: string;
}

interface RepoPickerProps {
  onSelect: (repo: Repo) => void;
  onCancel?: () => void;
}

export const RepoPicker: React.FC<RepoPickerProps> = ({ onSelect, onCancel }) => {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [search, setSearch] = useState('');
  const sessionId = useSessionStore((s) => s.sessionId);

  const fetchRepos = useCallback(async () => {
    if (!sessionId) return;
    
    setLoading(true);
    try {
      const res = await apiClient.get<{ repos: Repo[] }>(`/github/repos?session_id=${sessionId}&page=${page}`);
      const newRepos = res.data?.repos || [];
      
      if (page === 1) {
        setRepos(newRepos);
      } else {
        setRepos((prev) => [...prev, ...newRepos]);
      }
      
      setHasMore(newRepos.length === 30);
    } catch (err) {
      console.error('Failed to fetch repos:', err);
    } finally {
      setLoading(false);
    }
  }, [page, sessionId]);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  const filteredRepos = repos.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.full_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="w-full max-w-md bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-white">Select Repository</h3>
        <p className="text-sm text-slate-400 mt-1">
          Choose a repository to work with in this session
        </p>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-slate-700">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search repositories..."
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg 
                     text-slate-200 placeholder-slate-500 text-sm
                     focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Repo List */}
      <div className="max-h-96 overflow-y-auto">
        {loading && page === 1 ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-slate-500 text-sm mt-3">Loading repositories...</p>
          </div>
        ) : filteredRepos.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>No repositories found</p>
          </div>
        ) : (
          <>
            {filteredRepos.map((repo) => (
              <button
                key={repo.id}
                onClick={() => onSelect(repo)}
                className="w-full px-4 py-3 flex items-start gap-3 hover:bg-slate-800 
                           border-b border-slate-800/50 transition-colors text-left"
              >
                <div className="mt-0.5">
                  {repo.private ? (
                    <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {repo.full_name}
                  </p>
                  {repo.description && (
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                      {repo.description}
                    </p>
                  )}
                </div>
              </button>
            ))}
            
            {hasMore && (
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={loading}
                className="w-full py-3 text-sm text-slate-400 hover:text-slate-200 
                           hover:bg-slate-800 transition-colors"
              >
                {loading ? 'Loading...' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-700 bg-slate-800/50 flex justify-end">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default RepoPicker;
