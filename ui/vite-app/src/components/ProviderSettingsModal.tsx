/**
 * ProviderSettingsModal — BYOK Configuration UI
 *
 * Full-featured, production-quality settings modal for configuring
 * the LLM provider per session. Supports OpenAI, Anthropic, NVIDIA NIM,
 * Ollama (local), and any OpenAI-compatible endpoint.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, Check, Loader2, ChevronDown, Zap, Server, KeyRound, Braces, Eye, EyeOff,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';

/* ── Provider Presets ───────────────────────────────────── */
const PRESETS = [
  {
    id: 'openai',
    label: 'OpenAI',
    model: 'gpt-4o',
    base_url: '',
    hint: 'Works with GPT-4o, GPT-4.1, o3-mini, etc.',
    color: 'text-emerald-400',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    model: 'claude-sonnet-4-20250514',
    base_url: '',
    hint: 'Works with Claude Opus, Sonnet, Haiku.',
    color: 'text-amber-400',
  },
  {
    id: 'nvidia',
    label: 'NVIDIA NIM',
    model: 'nvidia/nemotron-3-super-120b-a12b',
    base_url: 'https://integrate.api.nvidia.com/v1',
    hint: 'NVIDIA Nemotron with optional reasoning.',
    color: 'text-green-400',
  },
  {
    id: 'ollama',
    label: 'Ollama (Local)',
    model: 'ollama/llama3.3',
    base_url: 'http://localhost:11434',
    hint: 'No API key needed. Just run "ollama serve".',
    color: 'text-sky-400',
  },
  {
    id: 'custom',
    label: 'Custom Endpoint',
    model: '',
    base_url: '',
    hint: 'Any OpenAI-compatible API.',
    color: 'text-violet-400',
  },
] as const;

type PresetId = (typeof PRESETS)[number]['id'];

/* ── Types ─────────────────────────────────────────────── */
interface ProviderSettingsModalProps {
  open: boolean;
  onClose: () => void;
  targetSessionId?: string;
}

interface ConfigState {
  model: string;
  api_key: string;
  base_url: string;
  extra_body: string; // JSON string in the textarea
}

/* ── Component ─────────────────────────────────────────── */
export function ProviderSettingsModal({ open, onClose, targetSessionId }: ProviderSettingsModalProps) {
  const storeSessionId = useSessionStore((s) => s.sessionId);
  const sessionId = targetSessionId || storeSessionId;
  const dialogRef = useRef<HTMLDialogElement>(null);

  const [activePreset, setActivePreset] = useState<PresetId>('openai');
  const [config, setConfig] = useState<ConfigState>({
    model: 'gpt-4o',
    api_key: '',
    base_url: '',
    extra_body: '',
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [existingKeyMask, setExistingKeyMask] = useState('');

  /* ── Dialog open/close sync ───────────────────────────── */
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    else if (!open && el.open) el.close();
  }, [open]);

  /* ── Load existing config on mount ────────────────────── */
  const loadConfig = useCallback(async () => {
    if (!sessionId) return;
    const res = await apiClient.get<{
      model: string;
      base_url: string;
      api_key_masked: string;
      extra_body: Record<string, any> | null;
    }>(`/sessions/${sessionId}/config`);

    if (res.data) {
      const d = res.data;
      setExistingKeyMask(d.api_key_masked || '');
      if (d.model) {
        setConfig((c) => ({
          ...c,
          model: d.model || c.model,
          base_url: d.base_url || '',
          extra_body: d.extra_body ? JSON.stringify(d.extra_body, null, 2) : '',
        }));
        // Detect preset
        const match = PRESETS.find((p) => p.model === d.model);
        if (match) setActivePreset(match.id);
        else setActivePreset('custom');
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (open) loadConfig();
  }, [open, loadConfig]);

  /* ── Preset selection handler ─────────────────────────── */
  const selectPreset = (id: PresetId) => {
    const preset = PRESETS.find((p) => p.id === id)!;
    setActivePreset(id);
    setConfig((c) => ({
      ...c,
      model: preset.model || c.model,
      base_url: preset.base_url,
    }));
  };

  /* ── Save ─────────────────────────────────────────────── */
  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSaved(false);

    const payload: Record<string, any> = {
      model: config.model,
      base_url: config.base_url || undefined,
    };

    // Only send api_key if user typed a new one
    if (config.api_key) {
      payload.api_key = config.api_key;
    }

    // Parse extra_body JSON
    if (config.extra_body.trim()) {
      try {
        payload.extra_body = JSON.parse(config.extra_body);
      } catch {
        setError('Invalid JSON in Advanced Config.');
        setSaving(false);
        return;
      }
    }

    const res = await apiClient.patch<{ status: string }>(`/sessions/${sessionId}/config`, payload);

    if (res.status === 'success') {
      setSaved(true);
      setConfig((c) => ({ ...c, api_key: '' })); // Clear plaintext key from state
      await loadConfig(); // Reload masked key
      setTimeout(() => setSaved(false), 2000);
    } else {
      setError(res.error || 'Failed to save configuration.');
    }
    setSaving(false);
  };

  if (!open) return null;

  const currentPreset = PRESETS.find((p) => p.id === activePreset)!;

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      className="fixed inset-0 z-50 m-auto h-auto w-full max-w-xl rounded-2xl border border-slate-700/60 bg-slate-900/95 p-0 text-slate-100 shadow-2xl shadow-black/60 backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <div className="flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-violet-500/20 ring-1 ring-cyan-500/30">
              <Zap className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-tight">LLM Provider Settings</h2>
              <p className="text-[11px] text-slate-500">Configure your AI model for this session</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-800 hover:text-slate-300">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Provider Preset Tabs */}
        <div className="flex gap-1.5 border-b border-slate-800/60 px-6 py-3 overflow-x-auto">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => selectPreset(p.id)}
              className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                activePreset === p.id
                  ? 'bg-slate-700/80 text-white ring-1 ring-slate-600'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-300'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="space-y-4 px-6 py-5">
          {/* Hint */}
          <p className={`text-xs ${currentPreset.color}`}>
            {currentPreset.hint}
          </p>

          {/* Model */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <Server className="h-3 w-3" /> Model
            </label>
            <input
              type="text"
              value={config.model}
              onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
              placeholder="e.g. gpt-4o, claude-sonnet-4-20250514, nvidia/nemotron-..."
              className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <KeyRound className="h-3 w-3" /> API Key
            </label>
            {existingKeyMask && !config.api_key && (
              <div className="mb-1.5 rounded-md bg-emerald-900/20 px-2.5 py-1 text-[11px] text-emerald-400 ring-1 ring-emerald-800/40">
                Current key: <span className="font-mono">{existingKeyMask}</span>
              </div>
            )}
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={config.api_key}
                onChange={(e) => setConfig((c) => ({ ...c, api_key: e.target.value }))}
                placeholder={existingKeyMask ? 'Enter new key to replace...' : 'sk-... or nvapi-...'}
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 pr-10 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-300 transition"
              >
                {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>

          {/* Base URL */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <ChevronDown className="h-3 w-3" /> Base URL
              <span className="ml-auto font-normal normal-case tracking-normal text-slate-600">optional</span>
            </label>
            <input
              type="text"
              value={config.base_url}
              onChange={(e) => setConfig((c) => ({ ...c, base_url: e.target.value }))}
              placeholder="https://integrate.api.nvidia.com/v1"
              className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono"
            />
          </div>

          {/* Advanced: extra_body JSON */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <Braces className="h-3 w-3" /> Advanced Config
              <span className="ml-auto font-normal normal-case tracking-normal text-slate-600">JSON • optional</span>
            </label>
            <textarea
              value={config.extra_body}
              onChange={(e) => setConfig((c) => ({ ...c, extra_body: e.target.value }))}
              placeholder={'{\n  "chat_template_kwargs": {"enable_thinking": true},\n  "reasoning_budget": 16384\n}'}
              rows={4}
              className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-xs text-slate-300 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-red-900/30 px-3 py-2 text-xs text-red-400 ring-1 ring-red-800/40">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 px-6 py-4">
          <p className="text-[10px] text-slate-600">
            Keys stored per-session. Never logged or transmitted externally.
          </p>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-1.5 text-xs font-medium text-slate-400 transition hover:bg-slate-700 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-1.5 text-xs font-semibold text-white shadow-lg shadow-cyan-900/40 transition hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : saved ? (
                <Check className="h-3.5 w-3.5" />
              ) : null}
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Config'}
            </button>
          </div>
        </div>
      </div>
    </dialog>
  );
}
