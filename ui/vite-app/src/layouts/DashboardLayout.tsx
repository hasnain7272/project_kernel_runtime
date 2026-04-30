/**
 * DashboardLayout — SaaS-grade Agentic IDE Layout
 *
 * Implements a bifurcated Antigravity/Codex style layout:
 * [File Explorer] | [Command Center / Terminal] | [Mission Control / Chat]
 */
import { useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { DashboardHeader } from '@/layouts/DashboardHeader';
import { ChatPane } from '@/features/chat/ChatPane';
import { ProviderSettingsModal } from '@/components/ProviderSettingsModal';
import { SessionDrawer } from '@/components/SessionDrawer';
import { FileExplorer } from '@/features/workspace/FileExplorer';
import { ConsoleWindow } from '@/features/terminal/ConsoleWindow';
import { WorkspaceManager } from '@/components/WorkspaceManager';
import { CapabilityStudio } from '@/features/capabilities/CapabilityStudio';

export function DashboardLayout() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [showCapabilityStudio, setShowCapabilityStudio] = useState(false);
  const [settingsTargetSession, setSettingsTargetSession] = useState<string | undefined>();

  const handleOpenSettings = (targetId?: string) => {
    setSettingsTargetSession(targetId);
    setSettingsOpen(true);
    setDrawerOpen(false);
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 overflow-hidden font-sans">
      <DashboardHeader
        onOpenDrawer={() => setDrawerOpen(true)}
        onOpenWorkspaceModal={() => setShowWorkspaceModal(true)}
        showFileExplorer={showFileExplorer}
        onToggleFileExplorer={() => setShowFileExplorer(!showFileExplorer)}
        onOpenCapabilityStudio={() => setShowCapabilityStudio(true)}
        onOpenSettings={() => handleOpenSettings()}
      />

      <SessionDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onOpenSettings={handleOpenSettings}
      />

      <ProviderSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        targetSessionId={settingsTargetSession}
      />

      {/* Main — Bifurcated Agentic Interface */}
      <main className="flex-1 overflow-hidden flex bg-slate-950">
        <PanelGroup direction="horizontal">
          
          {showFileExplorer && (
            <>
              <Panel defaultSize={20} minSize={15} maxSize={30} className="bg-slate-900/20 backdrop-blur-sm border-r border-slate-800 flex flex-col">
                <FileExplorer />
              </Panel>
              <PanelResizeHandle className="w-1 bg-slate-800/50 hover:bg-cyan-500/50 transition-colors cursor-col-resize" />
            </>
          )}

          {/* System Editor / Terminal Center */}
          <Panel defaultSize={45} minSize={30} className="flex flex-col bg-[#020617] border-r border-slate-800">
            <div className="h-8 border-b border-slate-800 flex items-center px-3 bg-slate-900/50">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">System Console</span>
            </div>
            <div className="flex-1 overflow-hidden relative">
              <ConsoleWindow />
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-slate-800/50 hover:bg-cyan-500/50 transition-colors cursor-col-resize shadow-md" />

          {/* Mission Control / Chat */}
          <Panel defaultSize={35} minSize={25} className="flex flex-col bg-slate-900/30">
            <ChatPane />
          </Panel>

        </PanelGroup>
      </main>

      <WorkspaceManager externalOpen={showWorkspaceModal} onExternalClose={() => setShowWorkspaceModal(false)} />
      <CapabilityStudio open={showCapabilityStudio} onClose={() => setShowCapabilityStudio(false)} />
    </div>
  );
}
