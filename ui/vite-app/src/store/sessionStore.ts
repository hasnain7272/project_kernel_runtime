import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

// ── Types ──

export interface Workspace {
  type: 'local' | 'git';
  slug: string;
  path?: string;
  url?: string;
  branch?: string;
}

interface SessionState {
  sessionId: string;
  tenantId: string;
  userEmail: string;
  userRole: string;
  workspaces: Workspace[];
  status: 'idle' | 'connecting' | 'active' | 'error';

  // Actions
  setSessionId: (id: string) => void;
  setUser: (email: string, role?: string) => void;
  setStatus: (s: SessionState['status']) => void;
  setWorkspaces: (w: Workspace[]) => void;
  ensureSession: (workspaces?: Workspace[]) => Promise<void>;
  addWorkspace: (ws: Workspace) => Promise<void>;
  removeWorkspace: (slug: string) => Promise<void>;
  reset: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessionId: '',
      tenantId: '',
      userEmail: '',
      userRole: 'developer',
      workspaces: [],
      status: 'idle',

      setSessionId: (id) => set({ sessionId: id, status: 'active' }),
      setUser: (email, role) => set({ userEmail: email, userRole: role || 'developer' }),
      setStatus: (status) => set({ status }),
      setWorkspaces: (workspaces) => set({ workspaces }),

      ensureSession: async (workspaces?: Workspace[]) => {
        const token = localStorage.getItem('auth_token');
        if (!token) return;

        const current = get();
        if (current.sessionId) {
          if (!current.tenantId) set({ tenantId: 'local' });
          return;
        }
        set({ status: 'connecting' });

        try {
          const payload = {
            name: 'New Session',
            mode: 'web',
            workspaces: workspaces || current.workspaces || [],
          };

          const res = await apiClient.post<{
            id: string;
            tenant_id: string;
            workspaces: Workspace[];
          }>('/sessions/', payload);

          if (res.data?.id) {
            const ws = res.data.workspaces || [];
            set({
              sessionId: res.data.id,
              tenantId: res.data.tenant_id || '',
              workspaces: ws,
              status: 'active',
            });
          } else {
            set({ status: 'error' });
          }
        } catch (err) {
          console.error('[Session] Failed to create session:', err);
          set({ status: 'error' });
        }
      },

      addWorkspace: async (ws: Workspace) => {
        const { sessionId } = get();
        if (!sessionId) return;

        try {
          const res = await apiClient.post<{
            workspaces: Workspace[];
          }>(`/sessions/${sessionId}/workspaces`, { workspace: ws });

          if (res.data?.workspaces) {
            set({ workspaces: res.data.workspaces });
          }
        } catch (err) {
          console.error('[Session] Failed to add workspace:', err);
        }
      },

      removeWorkspace: async (slug: string) => {
        const { sessionId } = get();
        if (!sessionId) return;

        try {
          const res = await apiClient.delete<{
            workspaces: Workspace[];
          }>(`/sessions/${sessionId}/workspaces/${slug}`);

          if (res.data?.workspaces) {
            set({ workspaces: res.data.workspaces });
          }
        } catch (err) {
          console.error('[Session] Failed to remove workspace:', err);
        }
      },

      reset: () =>
        set({
          sessionId: '',
          tenantId: '',
          userEmail: '',
          userRole: 'developer',
          workspaces: [],
          status: 'idle',
        }),
    }),
    { name: 'ag-session' },
  ),
);