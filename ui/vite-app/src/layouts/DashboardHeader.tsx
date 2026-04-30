import { useState, useEffect } from 'react';
import { Layers, FolderOpen, FileCode, Sparkles, Settings } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useSessionStore } from '@/store/sessionStore';
import { apiClient } from '@/api/client';

interface DashboardHeaderProps {
  onOpenDrawer: () => void;
  onOpenWorkspaceModal: () => void;
  showFileExplorer: boolean;
  onToggleFileExplorer: () => void;
  onOpenCapabilityStudio: () => void;
  onOpenSettings: () => void;
}

export function DashboardHeader({
  onOpenDrawer,
  onOpenWorkspaceModal,
  showFileExplorer,
  onToggleFileExplorer,
  onOpenCapabilityStudio,
  onOpenSettings
}: DashboardHeaderProps) {
  const [tenantInfo, setTenantInfo] = useState<any>(null);
  const workspaces = useSessionStore((s) => s.workspaces);
  const userEmail = useSessionStore((s) => s.userEmail);

  useEffect(() => {
    const fetchMe = async () => {
      try {
        const res = await apiClient.get<any>('/auth/me');
        if (res.data) setTenantInfo(res.data);
      } catch (e) {
        // Ignored
      }
    };
    fetchMe();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    useSessionStore.getState().reset();
    window.location.href = '/login';
  };

  return (
    <header className="flex h-12 items-center justify-between border-b border-slate-800/60 px-4 bg-slate-900/40 shrink-0 backdrop-blur-md z-40 relative shadow-sm shadow-black/20">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenDrawer}
          className="group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 transition hover:bg-slate-800/70 active:scale-95"
        >
          <div className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-900/20">
            <Layers className="h-3.5 w-3.5 text-white transition group-hover:scale-110" />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-100 italic">Antigravity</span>
        </button>
        
        <Badge variant="outline" className="text-[9px] h-4 px-1.5 border-emerald-500/30 bg-emerald-500/5 text-emerald-400 font-mono tracking-tighter">v4.0.0-PROD</Badge>
        <div className="h-4 w-[1px] bg-slate-800/80 mx-1" />

        <button
          onClick={onOpenWorkspaceModal}
          className="group flex items-center gap-2.5 rounded-lg px-3 py-1.5 transition-all hover:bg-slate-800/70 border border-transparent hover:border-slate-700/50 bg-slate-800/40"
        >
          <FolderOpen className="h-4 w-4 text-blue-400 transition group-hover:scale-110" />
          <span className="text-[11px] font-bold text-slate-100 uppercase tracking-wider">
            {workspaces.length > 0 ? `Project: ${workspaces[0].slug || workspaces[0].path?.split('/').pop() || 'Workspace'}${workspaces.length > 1 ? ` (+${workspaces.length - 1})` : ''}` : 'Connect Project'}
          </span>
        </button>

        <div className="h-4 w-[1px] bg-slate-800/80 mx-1" />

        <button
          onClick={onToggleFileExplorer}
          className={`flex h-8 w-8 items-center justify-center rounded-lg transition-all ${
            showFileExplorer ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-slate-500 hover:bg-slate-800/70'
          }`}
          title="Toggle Sidebar Explorer"
        >
          <FileCode className="h-4 w-4" />
        </button>

        <button
          onClick={onOpenCapabilityStudio}
          className="group flex items-center gap-2 rounded-lg border border-transparent bg-slate-800/40 px-3 py-1.5 transition-all hover:border-slate-700/50 hover:bg-slate-800/70"
        >
          <Sparkles className="h-4 w-4 text-cyan-400 transition group-hover:scale-110" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-100">Capabilities</span>
        </button>
      </div>

      <div className="flex items-center gap-3">
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

        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-800/30 border border-slate-700/30">
          <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
            {userEmail?.[0]?.toUpperCase() || 'U'}
          </div>
          <span className="text-[11px] text-slate-300 font-medium tracking-tight">
            {userEmail || 'User'}
          </span>
          <div className="h-4 w-[1px] bg-slate-800/40 mx-0.5" />
          <button onClick={handleLogout} className="text-[10px] text-slate-500 hover:text-red-400 font-bold uppercase transition-colors">Logout</button>
        </div>
        
        <button
          onClick={onOpenSettings}
          className="group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-400 transition-all hover:bg-slate-800/80 hover:text-slate-200"
        >
          <Settings className="h-3.5 w-3.5 text-slate-500 transition group-hover:rotate-45" />
        </button>
      </div>
    </header>
  );
}
