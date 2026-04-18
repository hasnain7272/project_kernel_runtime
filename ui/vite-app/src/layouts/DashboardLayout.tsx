/**
 * DashboardLayout — SaaS-grade chat-centric layout
 *
 * Clean, premium interface focused entirely on the conversation.
 * No source code exposure — this is a SaaS product.
 */
import { useState } from 'react';

import { ChatPane } from '@/features/chat/ChatPane';
import { ProviderSettingsModal } from '@/components/ProviderSettingsModal';
import { SessionDrawer } from '@/components/SessionDrawer';
import { Badge } from '@/components/ui/badge';
import { Settings, Layers, Cpu, Sparkles } from 'lucide-react';
import { useSessionStore } from '@/store/sessionStore';

export function DashboardLayout() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [settingsTargetSession, setSettingsTargetSession] = useState<string | undefined>(undefined);
  const sessionId = useSessionStore((s) => s.sessionId);

  const handleOpenSettings = (targetId?: string) => {
    setSettingsTargetSession(targetId);
    setSettingsOpen(true);
    setDrawerOpen(false);
  };

  const handleCloseSettings = () => {
    setSettingsOpen(false);
    setSettingsTargetSession(undefined);
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 overflow-hidden">
      {/* Top Bar */}
      <header className="flex h-12 items-center justify-between border-b border-slate-800/60 px-4 bg-slate-900/40 shrink-0 backdrop-blur-sm">
        {/* Left */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setDrawerOpen(true)}
            className="group flex items-center gap-2 rounded-lg px-2.5 py-1.5 transition hover:bg-slate-800/70"
          >
            <Layers className="h-4 w-4 text-emerald-500 transition group-hover:scale-110" />
            <span className="text-sm font-bold tracking-tight text-slate-200">Antigravity</span>
          </button>
          <Badge variant="secondary" className="text-[10px]">v3.0</Badge>

          <div className="h-4 w-px bg-slate-800" />

          {sessionId && (
            <div className="flex items-center gap-1.5 rounded-lg bg-slate-800/50 px-2.5 py-1 ring-1 ring-slate-700/40">
              <Cpu className="h-3 w-3 text-cyan-500" />
              <span className="font-mono text-[10px] text-slate-500">{sessionId.slice(0, 8)}</span>
            </div>
          )}
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenSettings()}
            className="group flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 transition hover:bg-slate-800/80 hover:text-slate-200"
          >
            <Settings className="h-3.5 w-3.5 transition group-hover:rotate-90" />
            <span>Provider</span>
          </button>
          <kbd className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">⌘K</kbd>
        </div>
      </header>

      {/* Session Drawer */}
      <SessionDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onOpenSettings={(id) => handleOpenSettings(id)}
      />

      {/* Provider Settings Modal */}
      <ProviderSettingsModal
        open={settingsOpen}
        onClose={handleCloseSettings}
        targetSessionId={settingsTargetSession}
      />

      {/* Main — Chat-centric */}
      <main className="flex-1 overflow-hidden">
        <ChatPane />
      </main>
    </div>
  );
}
