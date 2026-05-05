import type { StateCreator } from 'zustand';
import { apiClient } from '@/api/client';
import type { SessionState, Workspace } from './sessionTypes';

export const createSessionActions: StateCreator<SessionState, [], [], Pick<SessionState,
  'setSessionId' | 'setUser' | 'setStatus' | 'setWorkspaces' | 'addPlugin' | 'removePlugin' |
  'toggleSkill' | 'setLlmConfig' | 'setLlmPreset' | 'initLlmFromStorage' | 'ensureSession' |
  'addWorkspace' | 'removeWorkspace' | 'reset'
>> = (set, get) => ({
  setSessionId: (id) => set({ sessionId: id, status: 'active' }),
  setUser: (email, role) => set({ userEmail: email, userRole: role || 'developer' }),
  setStatus: (status) => set({ status }),
  setWorkspaces: (workspaces) => set({ workspaces }),
  addPlugin: (plugin) => set((s) => ({ plugins: [...s.plugins.filter((p) => p.name !== plugin.name), plugin] })),
  removePlugin: (name) => set((s) => ({ plugins: s.plugins.filter((p) => p.name !== name) })),
  toggleSkill: (skillId) => set((s) => ({ activeSkills: s.activeSkills.includes(skillId) ? s.activeSkills.filter((id) => id !== skillId) : [...s.activeSkills, skillId] })),
  setLlmConfig: (config) => set((s) => ({ llmConfig: { ...s.llmConfig, ...config } })),
  setLlmPreset: (preset) => set({ llmPreset: preset }),
  initLlmFromStorage: () => {
    try {
      const parsed = JSON.parse(localStorage.getItem('llm_config') || '{}');
      if (parsed.config) set({ llmConfig: parsed.config, llmPreset: parsed.preset });
    } catch {}
  },
  ensureSession: async (workspaces?: Workspace[]) => {
    if (!localStorage.getItem('auth_token')) return;
    const current = get();
    if (current.status === 'active' && current.sessionId) {
      if (!current.tenantId) set({ tenantId: 'local' });
      return;
    }
    set({ status: 'connecting' });
    try {
      const res = await apiClient.post<{ id: string; tenant_id: string; workspaces: Workspace[] }>('/sessions/', {
        name: 'New Session',
        mode: 'web',
        workspaces: workspaces || current.workspaces || [],
      });
      if (!res.data?.id) return set({ status: 'error' });
      set({ sessionId: res.data.id, tenantId: res.data.tenant_id || '', workspaces: res.data.workspaces || [], status: 'active' });
    } catch {
      set({ status: 'error' });
    }
  },
  addWorkspace: async (ws) => {
    const { sessionId } = get();
    if (!sessionId) return;
    const res = await apiClient.post<{ workspaces: Workspace[] }>(`/sessions/${sessionId}/workspaces`, { workspace: ws });
    if (res.data?.workspaces) set({ workspaces: res.data.workspaces });
  },
  removeWorkspace: async (slug) => {
    const { sessionId } = get();
    if (!sessionId) return;
    const res = await apiClient.delete<{ workspaces: Workspace[] }>(`/sessions/${sessionId}/workspaces/${slug}`);
    if (res.data?.workspaces) set({ workspaces: res.data.workspaces });
  },
  reset: () => set({ sessionId: '', tenantId: '', userEmail: '', userRole: 'developer', workspaces: [], plugins: [], activeSkills: [], status: 'idle' }),
});
