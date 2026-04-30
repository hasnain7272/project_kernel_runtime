import { Cpu, Server, KeyRound, EyeOff, Eye } from 'lucide-react';

export const PRESETS = [
  { id: 'openai', label: 'OpenAI', model: 'gpt-4o', hint: 'Works with GPT-4o, GPT-4.1, o3-mini.', color: 'text-emerald-400' },
  { id: 'anthropic', label: 'Anthropic', model: 'claude-sonnet-4-20250514', hint: 'Works with Claude Opus, Sonnet, Haiku.', color: 'text-amber-400' },
  { id: 'nvidia', label: 'NVIDIA', model: 'nvidia/nemotron-3-super-120b-a12b', base_url: 'https://integrate.api.nvidia.com/v1', hint: 'NVIDIA Nemotron.', color: 'text-green-400' },
  { id: 'ollama', label: 'Ollama', model: 'ollama/llama3.3', base_url: 'http://localhost:11434', hint: 'Local Ollama.', color: 'text-sky-400' },
  { id: 'custom', label: 'Custom', model: '', hint: 'Any OpenAI-compatible API.', color: 'text-violet-400' },
];

export function LLMSettings({ preset, setPreset, config, setConfig, existingKey, showKey, setShowKey }: any) {
  const currentPreset = PRESETS.find(p => p.id === preset) || PRESETS[0];

  return (
    <div className="p-6 pb-2">
      <label className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500/80">
        <Cpu className="h-3 w-3" /> Intelligence Provider
      </label>
      
      <div className="flex gap-1.5 mb-4 overflow-x-auto pb-1">
        {PRESETS.map(p => (
          <button key={p.id} onClick={() => { setPreset(p.id); setConfig((c: any) => ({ ...c, model: p.model, base_url: p.base_url || '' })); }}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition ${preset === p.id ? 'bg-slate-700/80 text-white ring-1 ring-slate-600' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-300'}`}>
            {p.label}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        <p className={`text-[11px] ${currentPreset.color} px-1`}>{currentPreset.hint}</p>
        <div>
          <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><Server className="h-3 w-3" />Model name</label>
          <input value={config.model} onChange={e => setConfig((c: any) => ({ ...c, model: e.target.value }))}
            className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
        </div>
        <div>
          <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><KeyRound className="h-3 w-3" />API Key</label>
          {existingKey && !config.api_key && <div className="mb-1.5 rounded-md bg-emerald-900/20 px-2.5 py-1 text-[11px] text-emerald-400 ring-1 ring-emerald-800/40">Current: <span className="font-mono">{existingKey}</span></div>}
          <div className="relative">
            <input type={showKey ? 'text' : 'password'} value={config.api_key} onChange={e => setConfig((c: any) => ({ ...c, api_key: e.target.value }))}
              placeholder={existingKey ? 'Enter new key to replace...' : 'sk-...'}
              className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 pr-10 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
            <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-300 transition">
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
        <div>
          <label className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Base URL <span className="ml-auto font-normal normal-case text-slate-600">optional</span></label>
          <input value={config.base_url} onChange={e => setConfig((c: any) => ({ ...c, base_url: e.target.value }))}
            placeholder="Defaults to provider auto-detection"
            className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/30 transition font-mono" />
        </div>
      </div>
    </div>
  );
}
