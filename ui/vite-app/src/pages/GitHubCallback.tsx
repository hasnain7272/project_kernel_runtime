/**
 * GitHub OAuth Callback Page
 * 
 * Handles the OAuth redirect and communicates with parent window.
 */
import { useEffect } from 'react';
import { getAuthToken } from '@/api/client';

export default function GitHubCallback() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (error) {
      window.opener?.postMessage({ type: 'github-error', error }, '*');
      setTimeout(() => window.close(), 100);
      return;
    }

    if (code && state) {
      const redirectUri = `${window.location.origin}/github/callback`;
      const query = new URLSearchParams({ code, state, redirect_uri: redirectUri });
      fetch(`/api/v1/github/connect?${query.toString()}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            window.opener?.postMessage({ type: 'github-connected', user: data.user }, '*');
          } else {
            window.opener?.postMessage({ type: 'github-error', error: data.message }, '*');
          }
        })
        .catch(err => {
          window.opener?.postMessage({ type: 'github-error', error: err.message }, '*');
        })
        .finally(() => {
          setTimeout(() => window.close(), 100);
        });
    }
  }, []);

  return (
    <div className="flex h-screen items-center justify-center bg-slate-950">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-slate-400 text-sm mt-4">Connecting to GitHub...</p>
      </div>
    </div>
  );
}
