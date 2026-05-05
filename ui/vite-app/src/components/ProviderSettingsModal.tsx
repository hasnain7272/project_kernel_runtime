/**
 * ProviderSettingsModal — BYOK Configuration UI.
 * Ultra-premium, sub-100 line implementation utilizing modular settings panes.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Check, Loader2, Zap } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { PRESETS, LLMSettings } from '@/features/settings/LLMSettings';
import { GitSettings } from '@/features/settings/GitSettings';
import { CapabilitySettings } from '@/features/settings/CapabilitySettings';

interface Props { open: boolean; onClose: () => void; targetSessionId?: string; }

export function ProviderSettingsModal({ open, onClose, targetSessionId }: Props) {
  const activeSessionId = useSessionStore(s => s.sessionId);
  const llmConfig = useSessionStore(s => s.llmConfig);
  const llmPreset = useSessionStore(s => s.llmPreset);
  const setLlmConfig = useSessionStore(s => s.setLlmConfig);
  const setLlmPreset = useSessionStore(s => s.setLlmPreset);
  const sessionId = targetSessionId || activeSessionId;

  const dialogRef = useRef<HTMLDialogElement>(null);
  const [preset, setPreset] = useState(llmPreset || PRESETS[0].id);
  const [config, setConfig] = useState(llmConfig);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [existingKey, setExistingKey] = useState('');

  useEffect(() => {
    setConfig(llmConfig);
    setPreset(llmPreset || PRESETS[0].id);
  }, [llmConfig, llmPreset]);

  const loadConfig = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await apiClient.get<any>(`/sessions/${sessionId}/config`);
      if (res.data) {
        setExistingKey(res.data.api_key_masked || '');
        if (res.data.model) {
          setConfig(c => ({
            ...c,
            model: res.data.model || c.model,
            base_url: res.data.base_url || c.base_url || '',
            api_key: '',
          }));
          const match = PRESETS.find(p => p.model === res.data.model);
          if (match) setPreset(match.id); else setPreset('custom');
        }
      }
    } catch (e) {
      console.error('Failed to load session config', e);
    }
  }, [sessionId]);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open) {
      if (!el.open) { el.showModal(); loadConfig(); }
    } else {
      if (el.open) el.close();
    }
  }, [open, loadConfig]);

  const handleSave = async () => {
    if (!sessionId) return;
    setSaving(true); setError('');
    try {
      const payload: Record<string, any> = { model: config.model, base_url: config.base_url || undefined };
      if (config.api_key) payload.api_key = config.api_key;

      const res = await apiClient.patch<any>(`/sessions/${sessionId}/config`, payload);
      if (res.status === 'success' || res.data?.status === 'config_updated') {
        setSaved(true);
        setLlmConfig({ ...config, api_key: config.api_key ? config.api_key : llmConfig.api_key });
        setLlmPreset(preset);
        localStorage.setItem('llm_config', JSON.stringify({ config, preset }));
        setConfig(c => ({ ...c, api_key: '' }));
        setTimeout(() => setSaved(false), 2000);
        loadConfig();
      } else {
        setError(res.error || 'Failed to save.');
      }
    } catch (e: any) { setError(e.message || 'Network error.'); } finally { setSaving(false); }
  };

  if (!open) return null;

  return (
    <dialog ref={dialogRef} onCancel={onClose}
      className="fixed inset-0 z-50 m-auto h-auto w-full max-w-xl rounded-2xl border border-slate-700/60 bg-slate-900/95 p-0 text-slate-100 shadow-2xl shadow-black/60 backdrop:bg-black/70 backdrop:backdrop-blur-sm scale-in">
      <div className="flex flex-col">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-violet-500/20 ring-1 ring-cyan-500/30">
              <Zap className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-tight">Project Settings</h2>
              <p className="text-[11px] text-slate-500">Configure Intelligence & Resources</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto max-h-[70vh] custom-scrollbar">
          <LLMSettings
            preset={preset}
            setPreset={setPreset}
            config={config}
            setConfig={setConfig}
            existingKey={existingKey}
            showKey={showKey}
            setShowKey={setShowKey}
          />
          <div className="mx-6 my-4 h-px bg-slate-800/60" />
          <GitSettings />
          <div className="mx-6 my-4 h-px bg-slate-800/60" />
          <CapabilitySettings />
        </div>

        {error && <div className="mx-6 mb-4 rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-400 ring-1 ring-red-800/40">{error}</div>}

        <div className="flex items-center justify-between border-t border-slate-800 px-6 py-4">
          <p className="text-[10px] text-slate-600 italic">BYOK: Bring Your Own Key. Configuration is session-isolated.</p>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-1.5 text-xs font-medium text-slate-400 transition hover:bg-slate-700 hover:text-slate-200">Cancel</button>
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-1.5 text-xs font-semibold text-white shadow-lg shadow-cyan-900/40 transition hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : saved ? <Check className="h-3.5 w-3.5" /> : null}
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Apply Settings'}
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}