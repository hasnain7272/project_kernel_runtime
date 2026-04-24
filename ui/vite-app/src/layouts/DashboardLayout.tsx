/**
 * DashboardLayout — SaaS-grade chat-centric layout
 *
 * Clean, premium interface focused entirely on the conversation.
 * No source code exposure — this is a SaaS product.
 * Workspace management via the new ultra-premium WorkspaceManager modal.
 */
import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';

import { ChatPane } from '@/features/chat/ChatPane';
import { ProviderSettingsModal } from '@/components/ProviderSettingsModal';
import { SessionDrawer } from '@/components/SessionDrawer';
import { WorkspaceManager } from '@/components/WorkspaceManager';
import { FileExplorer } from '@/features/workspace/FileExplorer';
import { CapabilityStudio } from '@/features/capabilities/CapabilityStudio';
import { Badge } from '@/components/ui/badge';
import { Settings, Layers, FolderOpen, FileCode, Sparkles } from 'lucide-react';
import { useSessionStore } from '@/store/sessionStore';

export function DashboardLayout() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showFileExplorer, setShowFileExplorer] = useState(false);
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [showCapabilityStudio, setShowCapabilityStudio] = useState(false);
  const [settingsTargetSession, setSettingsTargetSession] = useState<string | undefined>(undefined);
  const [tenantInfo, setTenantInfo] = useState<any>(null);
  const sessionId = useSessionStore((s) => s.sessionId);
  const workspaces = useSessionStore((s) => s.workspaces);

  useEffect(() => {
    const fetchMe = async () => {
      const res = await apiClient.get<any>('/auth/me');
      if (res.data) setTenantInfo(res.data);
    };
    fetchMe();
  }, []);

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
    <div className="flex h-screen w-full flex-col bg-slate-950 overflow-hidden font-sans">
      {/* Top Bar */}
      <header className="flex h-12 items-center justify-between border-b border-slate-800/60 px-4 bg-slate-900/40 shrink-0 backdrop-blur-md z-40 relative shadow-sm shadow-black/20">
        {/* Left */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setDrawerOpen(true)}
            className="group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 transition hover:bg-slate-800/70 active:scale-95"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-900/20">
              <Layers className="h-3.5 w-3.5 text-white transition group-hover:scale-110" />
            </div>
            <span className="text-sm font-bold tracking-tight text-slate-100 italic">Antigravity</span>
          </button>
          
          <Badge variant="outline" className="text-[9px] h-4 px-1.5 border-emerald-500/30 bg-emerald-500/5 text-emerald-400 font-mono tracking-tighter">v4.0.0-PROD</Badge>

          <div className="h-4 w-[1px] bg-slate-800/80 mx-1" />

          {/* Unified Project Explorer */}
          <button
            onClick={() => setShowWorkspaceModal(true)}
            className="group flex items-center gap-2.5 rounded-lg px-3 py-1.5 transition-all hover:bg-slate-800/70 border border-transparent hover:border-slate-700/50 bg-slate-800/40"
          >
            <FolderOpen className="h-4 w-4 text-blue-400 transition group-hover:scale-110" />
            <span className="text-[11px] font-bold text-slate-100 uppercase tracking-wider">
              {workspaces.length > 0 ? `Project: ${workspaces[0].name}${workspaces.length > 1 ? ` (+${workspaces.length - 1})` : ''}` : 'Connect Project'}
            </span>
          </button>

          <div className="h-4 w-[1px] bg-slate-800/80 mx-1" />

          {/* Quick Toggle for Side-Explorer */}
          <button
            onClick={() => setShowFileExplorer(!showFileExplorer)}
            className={`flex h-8 w-8 items-center justify-center rounded-lg transition-all ${
              showFileExplorer ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-slate-500 hover:bg-slate-800/70'
            }`}
            title="Toggle Sidebar Explorer"
          >
            <FileCode className="h-4 w-4" />
          </button>

          <button
            onClick={() => setShowCapabilityStudio(true)}
            className="group flex items-center gap-2 rounded-lg border border-transparent bg-slate-800/40 px-3 py-1.5 transition-all hover:border-slate-700/50 hover:bg-slate-800/70"
            title="Skills, MCPs, and plugins"
          >
            <Sparkles className="h-4 w-4 text-cyan-400 transition group-hover:scale-110" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-100">Capabilities</span>
          </button>
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          {/* Spend vs Quota Dashboard */}
          {tenantInfo && (
            <div className="flex flex-col gap-1 px-3 py-1.5 rounded-xl bg-slate-800/30 border border-slate-700/30 w-32" title="API Budget">
              <div className="flex justify-between items-center text-[9px] font-bold tracking-wider uppercase text-slate-400">
                <span>Spend</span>
                <span className={`${tenantInfo.cost_cents / 100 >= tenantInfo.quota_usd * 0.9 ? 'text-red-400' : 'text-slate-300'}`}>
                  ${(tenantInfo.cost_cents / 100).toFixed(2)} / ${tenantInfo.quota_usd}
                </span>
              </div>
              <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${tenantInfo.cost_cents / 100 >= tenantInfo.quota_usd * 0.9 ? 'bg-red-500' : 'bg-cyan-500'} transition-all`} 
                  style={{ width: `${Math.min(100, (tenantInfo.cost_cents / 100 / tenantInfo.quota_usd) * 100)}%` }} 
                />
              </div>
            </div>
          )}

          {/* User Profile */}
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-800/30 border border-slate-700/30">
            <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
              {useSessionStore.getState().userEmail?.[0].toUpperCase() || 'U'}
            </div>
            <span className="text-[11px] text-slate-300 font-medium tracking-tight">
              {useSessionStore.getState().userEmail || 'User'}
            </span>
            <div className="h-4 w-[1px] bg-slate-800/40 mx-0.5" />
            <button 
              onClick={() => {
                localStorage.removeItem('auth_token');
                useSessionStore.getState().reset();
                window.location.href = '/login';
              }}
              className="text-[10px] text-slate-500 hover:text-red-400 font-bold uppercase transition-colors"
            >
              Logout
            </button>
          </div>
          
          <button
            onClick={() => handleOpenSettings()}
            className="group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-400 transition-all hover:bg-slate-800/80 hover:text-slate-200"
          >
            <Settings className="h-3.5 w-3.5 text-slate-500 transition group-hover:rotate-45" />
          </button>
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

      {/* Main — Chat-centric with optional File Explorer */}
      <main className="flex-1 overflow-hidden flex">
        {showFileExplorer && (
          <div className="w-72 shrink-0 border-r border-slate-800 flex flex-col overflow-hidden bg-slate-900/20 backdrop-blur-sm">
            <div className="flex-1 overflow-hidden">
              <FileExplorer />
            </div>
          </div>
        )}
        <div className="flex-1">
          <ChatPane />
        </div>
      </main>

      {/* Workspace Modal — triggered from header or sidebar */}
      <WorkspaceManager externalOpen={showWorkspaceModal} onExternalClose={() => setShowWorkspaceModal(false)} />
      <CapabilityStudio open={showCapabilityStudio} onClose={() => setShowCapabilityStudio(false)} />
    </div>
  );
}
