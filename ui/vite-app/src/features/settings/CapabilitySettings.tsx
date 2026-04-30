import { useState, useEffect } from 'react';
import { Server, Plug, Play, AlertCircle, Bot, Sparkles, Check } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useSessionStore } from '@/store/sessionStore';

export function CapabilitySettings() {
  const [catalog, setCatalog] = useState<any>(null);
  const [pluginName, setPluginName] = useState('');
  const [pluginUrl, setPluginUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState<string | null>(null);
  const [result, setResult] = useState<{ id: string; status: 'success' | 'error'; data: any } | null>(null);

  const { plugins, activeSkills, addPlugin, toggleSkill } = useSessionStore();

  const loadCatalog = async () => {
    const res = await apiClient.get<any>('/mcp/catalog');
    const backendPlugins = res.data?.plugins || [];
    setCatalog(res.data || null);

    // Auto-restore persisted plugins if missing in backend
    for (const p of plugins) {
      if (!backendPlugins.find((bp: any) => bp.name === p.name)) {
        apiClient.post('/mcp/register', { name: p.name, description: `Persisted plugin for ${p.name}`, endpoint_url: p.url })
          .then(() => loadCatalog()); // Reload after restoring
      }
    }
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  const handleRegister = async () => {
    if (!pluginName || !pluginUrl) return;
    setLoading(true);
    try {
      await apiClient.post('/mcp/register', { name: pluginName, description: `Dynamic plugin for ${pluginName}`, endpoint_url: pluginUrl });
      addPlugin({ name: pluginName, url: pluginUrl });
      setPluginName(''); setPluginUrl('');
      loadCatalog();
    } catch (e) {
      alert('Failed to register plugin.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunTool = async (tool: any) => {
    setExecuting(tool.name);
    try {
      const res = await apiClient.post<any>('/mcp/execute', { tool_name: tool.name, parameters: {} });
      setResult({ id: tool.name, status: res.error ? 'error' : 'success', data: res.data || res.error });
    } catch (e: any) {
      setResult({ id: tool.name, status: 'error', data: e.message });
    } finally {
      setExecuting(null);
    }
  };

  const handleApplySkill = (skill: any) => {
    toggleSkill(skill.id);
    window.dispatchEvent(new CustomEvent('ag-insert-prompt', { detail: { text: skill.prompt } }));
  };

  return (
    <div className="p-6 pt-2">
      <label className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500/80">
        <Server className="h-3 w-3" />
        Capabilities & Executions
      </label>

      {/* Live Catalog - Plugins & Tools execution */}
      <div className="space-y-4 mb-6">
        <div className="text-xs font-semibold text-slate-200">Registered Plugins & Tools</div>
        {catalog?.plugins?.length === 0 && <div className="text-xs text-slate-500">No plugins.</div>}
        {catalog?.plugins?.map((plugin: any) => (
          <div key={plugin.name} className="flex flex-col gap-2 rounded-xl border border-slate-700 bg-slate-800/30 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Plug className="h-4 w-4 text-emerald-400" />
                <span className="text-xs font-semibold text-slate-100">{plugin.name}</span>
              </div>
              <button onClick={() => handleRunTool(plugin)} disabled={executing === plugin.name} className="flex items-center gap-1 rounded bg-slate-700 px-2 py-1 text-[10px] text-white hover:bg-slate-600 transition disabled:opacity-50">
                <Play className="h-3 w-3" /> {executing === plugin.name ? 'Running...' : 'Run Tool'}
              </button>
            </div>
            {result?.id === plugin.name && (
              <div className={`mt-2 rounded p-2 text-[10px] font-mono ${result.status === 'error' ? 'bg-red-900/20 text-red-400' : 'bg-slate-900 text-slate-300'}`}>
                {result.status === 'error' && <AlertCircle className="inline h-3 w-3 mr-1" />}
                {JSON.stringify(result.data, null, 2)}
              </div>
            )}
          </div>
        ))}

        <div className="text-xs font-semibold text-slate-200 mt-4">Skills</div>
        {catalog?.skills?.map((skill: any) => (
          <div key={skill.id} className="flex flex-col gap-2 rounded-xl border border-slate-700 bg-slate-800/30 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-cyan-400" />
                <span className="text-xs font-semibold text-slate-100">{skill.name}</span>
              </div>
              <button onClick={() => handleApplySkill(skill)} className={`flex items-center gap-1 rounded px-2 py-1 text-[10px] transition border ${activeSkills.includes(skill.id) ? 'bg-emerald-900/40 text-emerald-400 border-emerald-800' : 'bg-cyan-900/40 text-cyan-400 border-cyan-800 hover:bg-cyan-800/60'}`}>
                {activeSkills.includes(skill.id) ? <Check className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
                {activeSkills.includes(skill.id) ? 'Applied' : 'Apply to Composer'}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-800/30 p-4">
        <div className="flex flex-col gap-3">
          <div>
            <h4 className="text-xs font-semibold text-slate-200">Register Plugin</h4>
            <p className="mt-1 text-[11px] text-slate-500 leading-relaxed">
              Instantly load remote tool endpoints into the active registry.
            </p>
          </div>
          <div className="flex gap-2">
            <input type="text" placeholder="Plugin Name" value={pluginName} onChange={e => setPluginName(e.target.value)} className="w-1/3 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-1.5 text-xs text-slate-100 outline-none" />
            <input type="text" placeholder="Endpoint URL" value={pluginUrl} onChange={e => setPluginUrl(e.target.value)} className="flex-1 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-1.5 text-xs text-slate-100 outline-none" />
            <button onClick={handleRegister} disabled={loading} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition shadow-sm disabled:opacity-50">Hot Load</button>
          </div>
        </div>
      </div>
    </div>
  );
}
