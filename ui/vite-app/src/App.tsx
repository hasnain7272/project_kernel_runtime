import { useEffect } from 'react';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { CommandPalette } from '@/features/commander/CommandPalette';
import { ToastContainer } from '@/components/Toast';
import { useSessionStore } from '@/store/sessionStore';

export default function App() {
  const ensureSession = useSessionStore((s) => s.ensureSession);
  const status = useSessionStore((s) => s.status);

  useEffect(() => {
    ensureSession();
  }, [ensureSession]);

  if (status === 'connecting') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-500 text-sm">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500/30 border-t-cyan-500" />
          <span>Initializing session...</span>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="rounded-2xl bg-red-900/20 p-4 ring-1 ring-red-500/30">
            <span className="text-2xl">⚠️</span>
          </div>
          <p className="text-sm text-red-400">Failed to connect to backend.</p>
          <p className="text-xs text-slate-500">Is the server running on :8089?</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 font-sans">
      <DashboardLayout />
      <CommandPalette />
      <ToastContainer />
    </div>
  );
}
