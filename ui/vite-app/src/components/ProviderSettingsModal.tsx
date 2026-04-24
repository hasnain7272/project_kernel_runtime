/**
 * ProviderSettingsModal — BYOK Configuration UI.
 * Ultra-premium, sub-150 line implementation.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Check, Loader2, KeyRound, Server, Eye, EyeOff, Zap, Cpu } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';
import { GitHubConnectButton } from '@/features/github/GitHubConnectButton';


const PRESETS = [
  { id: 'openai', label: 'OpenAI', model: 'gpt-4o', hint: 'Works with GPT-4o, GPT-4.1, o3-mini.', color: 'text-emerald-400' },
  { id: 'anthropic', label: 'Anthropic', model: 'claude-sonnet-4-20250514', hint: 'Works with Claude Opus, Sonnet, Haiku.', color: 'text-amber-400' },
  { id: 'nvidia', label: 'NVIDIA', model: 'nvidia/nemotron-3-super-120b-a12b', base_url: 'https://integrate.api.nvidia.com/v1', hint: 'NVIDIA Nemotron.', color: 'text-green-400' },
  { id: 'ollama', label: 'Ollama', model: 'ollama/llama3.3', base_url: 'http://localhost:11434', hint: 'Local Ollama.', color: 'text-sky-400' },
  { id: 'custom', label: 'Custom', model: '', hint: 'Any OpenAI-compatible API.', color: 'text-violet-400' },
];

interface Props { open: boolean; onClose: () => void; targetSessionId?: string; }

export function ProviderSettingsModal({ open, onClose, targetSessionId }: Props) {
  const activeSessionId = useSessionStore(s => s.sessionId);
  const sessionId = targetSessionId || activeSessionId;
  
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [preset, setPreset] = useState(PRESETS[0].id);
  const [config, setConfig] = useState({ model: 'gpt-4o', api_key: '', base_url: '', extra_body: '' });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [existingKey, setExistingKey] = useState('');

  const loadConfig = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await apiClient.get<any>(`/sessions/${sessionId}/config`);
      if (res.data) {
        setExistingKey(res.data.api_key_masked || '');
        if (res.data.model) {
          setConfig(c => ({ ...c, model: res.data.model || c.model, base_url: res.data.base_url || '' }));
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
      if (!el.open) {
        el.showModal();
        loadConfig();
      }
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
        setConfig(c => ({ ...c, api_key: '' })); 
        setTimeout(() => setSaved(false), 2000); 
        loadConfig();
      } else {
        setError(res.error || 'Failed to save.');
      }
    } catch (e: any) {
      setError(e.message || 'Network error.');
    } finally {
      setSaving(false);
    }
  };

  const currentPreset = PRESETS.find(p => p.id === preset) || PRESETS[0];

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
          {/* LLM Section */}
          <div className="p-6 pb-2">
            <label className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500/80">
              <Cpu className="h-3 w-3" />
              Intelligence Provider
            </label>
            
            <div className="flex gap-1.5 mb-4 overflow-x-auto pb-1">
              {PRESETS.map(p => (
                <button key={p.id} onClick={() => { setPreset(p.id); setConfig(c => ({ ...c, model: p.model, base_url: p.base_url || '' })); }}
                  className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition ${preset === p.id ? 'bg-slate-700/80 text-white ring-1 ring-slate-600' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-300'}`}>
                  {p.label}
                </button>
              ))}
            </div>

            <div className="space-y-4">
              <p className={`text-[11px] ${currentPreset.color} px-1`}>{currentPreset.hint}</p>
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><Server className="h-3 w-3" />Model name</label>
                <input value={config.model} onChange={e => setConfig(c => ({ ...c, model: e.target.value }))}
                  className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
              </div>
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><KeyRound className="h-3 w-3" />API Key</label>
                {existingKey && !config.api_key && <div className="mb-1.5 rounded-md bg-emerald-900/20 px-2.5 py-1 text-[11px] text-emerald-400 ring-1 ring-emerald-800/40">Current: <span className="font-mono">{existingKey}</span></div>}
                <div className="relative">
                  <input type={showKey ? 'text' : 'password'} value={config.api_key} onChange={e => setConfig(c => ({ ...c, api_key: e.target.value }))}
                    placeholder={existingKey ? 'Enter new key to replace...' : 'sk-...'}
                    className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 pr-10 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
                  <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-300 transition">
                    {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Base URL <span className="ml-auto font-normal normal-case text-slate-600">optional</span></label>
                <input value={config.base_url} onChange={e => setConfig(c => ({ ...c, base_url: e.target.value }))}
                  placeholder="Defaults to provider auto-detection"
                  className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
              </div>
            </div>
          </div>

          <div className="mx-6 my-4 h-px bg-slate-800/60" />

          {/* Git Section */}
          <div className="p-6 pt-2">
            <label className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500/80">
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              GitHub Integration
            </label>
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-800/30 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">Connect GitHub</h4>
                  <p className="mt-1 text-[11px] text-slate-500 leading-relaxed">
                    Allow Antigravity to clone repositories and push changes on your behalf.
                  </p>
                </div>
                <GitHubConnectButton />
              </div>
            </div>
          </div>

          <div className="mx-6 my-4 h-px bg-slate-800/60" />

          {/* MCP Plugins Section */}
          <div className="p-6 pt-2">
            <label className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500/80">
              <Server className="h-3 w-3" />
              Dynamic MCP Plugins
            </label>
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-800/30 p-4">
              <div className="flex flex-col gap-3">
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">Register Plugin</h4>
                  <p className="mt-1 text-[11px] text-slate-500 leading-relaxed">
                    Instantly load remote tool endpoints into the active registry.
                  </p>
                </div>
                <div className="flex gap-2">
                  <input type="text" placeholder="Plugin Name" id="mcp_name" className="w-1/3 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-1.5 text-xs text-slate-100 outline-none" />
                  <input type="text" placeholder="Endpoint URL" id="mcp_url" className="flex-1 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-1.5 text-xs text-slate-100 outline-none" />
                  <button type="button" onClick={() => {
                    const name = (document.getElementById('mcp_name') as HTMLInputElement).value;
                    const url = (document.getElementById('mcp_url') as HTMLInputElement).value;
                    if(name && url) {
                      apiClient.post('/mcp/register', { name, description: `Dynamic plugin for ${name}`, endpoint_url: url }).then(() => {
                        alert('Plugin Registered!');
                        (document.getElementById('mcp_name') as HTMLInputElement).value = '';
                        (document.getElementById('mcp_url') as HTMLInputElement).value = '';
                      }).catch(e => alert(e.message || 'Failed'));
                    }
                  }} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition shadow-sm">Hot Load</button>
                </div>
              </div>
            </div>
          </div>
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