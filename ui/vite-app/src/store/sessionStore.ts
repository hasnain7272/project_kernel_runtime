import { create } from 'zustand';
import { apiClient } from '@/api/client';

interface SessionState {
  sessionId: string;
  userRole: string;
  workspacePath: string;
  status: 'idle' | 'connecting' | 'active' | 'error';
  setSessionId: (id: string) => void;
  setStatus: (s: SessionState['status']) => void;
  setWorkspacePath: (p: string) => void;
  ensureSession: () => Promise<void>;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessionId: '',
  userRole: 'developer',
  workspacePath: '.',
  status: 'idle',
  setSessionId: (id) => set({ sessionId: id, status: 'active' }),
  setStatus: (status) => set({ status }),
  setWorkspacePath: (p) => set({ workspacePath: p }),

  ensureSession: async () => {
    if (get().sessionId) return;
    set({ status: 'connecting' });

    const res = await apiClient.post<{ session_id: string }>('/sessions/', {
      user_id: 'local',
      workspace_path: '.',
      mode: 'web',
    });

    if (res.data?.session_id) {
      set({ sessionId: res.data.session_id, status: 'active' });
    } else {
      set({ status: 'error' });
    }
  },

  reset: () => set({
    sessionId: '',
    userRole: 'developer',
    workspacePath: '.',
    status: 'idle',
  }),
}));
