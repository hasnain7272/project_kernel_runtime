import { useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/api/client';
import { Bot, Boxes, Plug, Search, Server, Sparkles, Wrench, X } from 'lucide-react';

type ToolParameter = {
  name: string;
  type: string;
  description: string;
  required: boolean;
};

type ToolInfo = {
  name: string;
  description: string;
  category: string;
  origin: 'builtin' | 'plugin';
  requires_sandbox: boolean;
  parameters: ToolParameter[];
};

type SkillInfo = {
  id: string;
  name: string;
  description: string;
  prompt: string;
  tools: ToolInfo[];
};

type CatalogResponse = {
  tools: ToolInfo[];
  plugins: ToolInfo[];
  skills: SkillInfo[];
  categories: { id: string; label: string; count: number }[];
};

type Props = {
  open: boolean;
  onClose: () => void;
};

const tabs = [
  { id: 'skills', label: 'Skills', icon: Sparkles },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'plugins', label: 'Plugins', icon: Plug },
] as const;

export function CapabilityStudio({ open, onClose }: Props) {
  const [tab, setTab] = useState<(typeof tabs)[number]['id']>('skills');
  const [query, setQuery] = useState('');
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [pluginName, setPluginName] = useState('');
  const [pluginUrl, setPluginUrl] = useState('');

  const loadCatalog = async () => {
    setLoading(true);
    const res = await apiClient.get<CatalogResponse>('/mcp/catalog');
    setCatalog(res.data || null);
    setLoading(false);
  };

  useEffect(() => {
    if (open) loadCatalog();
  }, [open]);

  const filteredSkills = useMemo(() => {
    const items = catalog?.skills || [];
    return items.filter((item) => `${item.name} ${item.description}`.toLowerCase().includes(query.toLowerCase()));
  }, [catalog, query]);

  const filteredTools = useMemo(() => {
    const items = catalog?.tools || [];
    return items.filter((item) => `${item.name} ${item.description} ${item.category}`.toLowerCase().includes(query.toLowerCase()));
  }, [catalog, query]);

  const filteredPlugins = useMemo(() => {
    const items = catalog?.plugins || [];
    return items.filter((item) => `${item.name} ${item.description}`.toLowerCase().includes(query.toLowerCase()));
  }, [catalog, query]);

  const useSkill = (skill: SkillInfo) => {
    window.dispatchEvent(new CustomEvent('ag-insert-prompt', { detail: { text: skill.prompt } }));
    onClose();
  };

  const registerPlugin = async () => {
    if (!pluginName.trim() || !pluginUrl.trim() || saving) return;
    setSaving(true);
    setMessage('');
    const res = await apiClient.post<{ message: string }>('/mcp/register', {
      name: pluginName.trim(),
      description: `Dynamic plugin for ${pluginName.trim()}`,
      endpoint_url: pluginUrl.trim(),
      parameters: [],
    });
    setSaving(false);
    if (res.data) {
      setPluginName('');
      setPluginUrl('');
      setMessage(res.data.message || 'Plugin registered.');
      loadCatalog();
    } else {
      setMessage(res.error || 'Failed to register plugin.');
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="flex h-[78vh] w-full max-w-6xl flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20">
              <Boxes className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">Capability Studio</h2>
              <p className="text-xs text-slate-500">Skills, MCP plugins, and live tool inventory for the active runtime</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-800 hover:text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-3">
          <div className="flex gap-2">
            {tabs.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setTab(item.id)}
                  className={`flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition ${
                    tab === item.id ? 'bg-slate-800 text-slate-100 ring-1 ring-slate-700' : 'text-slate-500 hover:bg-slate-900 hover:text-slate-300'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              );
            })}
          </div>
          <div className="relative ml-auto w-full max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${tab}...`}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-9 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-600/40"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && <div className="text-sm text-slate-500">Loading capabilities...</div>}
          {!loading && tab === 'skills' && (
            <div className="grid gap-4 lg:grid-cols-2">
              {filteredSkills.map((skill) => (
                <div key={skill.id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4 text-cyan-400" />
                        <h3 className="text-sm font-semibold text-slate-100">{skill.name}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-slate-400">{skill.description}</p>
                    </div>
                    <button onClick={() => useSkill(skill)} className="rounded-xl bg-cyan-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-cyan-500">
                      Use Skill
                    </button>
                  </div>
                  <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                    <div className="mb-2 font-semibold uppercase tracking-wider text-slate-500">Suggested Prompt</div>
                    {skill.prompt}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {skill.tools.map((tool) => (
                      <span key={tool.name} className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300">
                        {tool.name}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && tab === 'tools' && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {(catalog?.categories || []).map((category) => (
                  <span key={category.id} className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-[11px] text-slate-400">
                    {category.label} · {category.count}
                  </span>
                ))}
              </div>
              {filteredTools.map((tool) => (
                <div key={tool.name} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4 text-violet-400" />
                        <span className="text-sm font-semibold text-slate-100">{tool.name}</span>
                        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase tracking-wider text-slate-400">{tool.category}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-400">{tool.description}</p>
                    </div>
                    <div className="text-right text-[11px] text-slate-500">
                      <div>{tool.origin === 'plugin' ? 'Plugin' : 'Built-in'}</div>
                      <div>{tool.requires_sandbox ? 'Sandboxed' : 'Direct'}</div>
                    </div>
                  </div>
                  {tool.parameters.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {tool.parameters.map((param) => (
                        <span key={`${tool.name}-${param.name}`} className="rounded-lg bg-slate-950 px-2.5 py-1 text-[11px] text-slate-400 ring-1 ring-slate-800">
                          {param.name}: {param.type}{param.required ? '' : ' ?'}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {!loading && tab === 'plugins' && (
            <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
              <div className="space-y-3">
                {filteredPlugins.length === 0 && (
                  <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-500">
                    No dynamic plugins are registered yet.
                  </div>
                )}
                {filteredPlugins.map((plugin) => (
                  <div key={plugin.name} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <div className="flex items-center gap-2">
                      <Plug className="h-4 w-4 text-emerald-400" />
                      <span className="text-sm font-semibold text-slate-100">{plugin.name}</span>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{plugin.description}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {plugin.parameters.map((param) => (
                        <span key={`${plugin.name}-${param.name}`} className="rounded-lg bg-slate-950 px-2.5 py-1 text-[11px] text-slate-400 ring-1 ring-slate-800">
                          {param.name}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <h3 className="text-sm font-semibold text-slate-100">Register MCP Plugin</h3>
                <p className="mt-2 text-sm text-slate-400">
                  Hot-load a remote capability into the active runtime by pointing it at an HTTP endpoint.
                </p>
                <div className="mt-4 space-y-3">
                  <input
                    value={pluginName}
                    onChange={(e) => setPluginName(e.target.value)}
                    placeholder="Plugin name"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-violet-600/40"
                  />
                  <input
                    value={pluginUrl}
                    onChange={(e) => setPluginUrl(e.target.value)}
                    placeholder="https://plugin.example.com/run"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-violet-600/40"
                  />
                  <button
                    onClick={registerPlugin}
                    disabled={saving}
                    className="w-full rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
                  >
                    {saving ? 'Registering...' : 'Register Plugin'}
                  </button>
                </div>
                {message && (
                  <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs text-slate-400">
                    {message}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
