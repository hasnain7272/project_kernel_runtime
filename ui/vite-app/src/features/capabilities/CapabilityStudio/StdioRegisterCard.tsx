import { useState } from 'react';
import { Loader2, Plus, Wand2 } from 'lucide-react';

interface Props {
  onRegister: (form: { name: string; command: string; args: string }) => Promise<void>;
  onError: (message: string) => void;
}

export function StdioRegisterCard({ onRegister, onError }: Props) {
  const [form, setForm] = useState({ name: '', command: 'npx', args: '' });
  const [saving, setSaving] = useState(false);
  const update = (key: keyof typeof form, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async () => {
    if (!form.name || !form.command) return;
    setSaving(true);
    try {
      await onRegister(form);
      setForm({ name: '', command: 'npx', args: '' });
    } catch (error) {
      onError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl border border-dashed border-violet-700/50 bg-violet-900/10 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Plus className="h-4 w-4 text-violet-400" />
        <h3 className="text-sm font-semibold text-slate-200">Add Stdio MCP Server</h3>
      </div>
      <div className="mb-3 flex flex-wrap gap-2">
        <Preset label="Filesystem" onClick={() => setForm({ name: 'filesystem', command: 'npx', args: '-y @modelcontextprotocol/server-filesystem .' })} />
        <Preset label="GitHub" onClick={() => setForm({ name: 'github', command: 'npx', args: '-y @modelcontextprotocol/server-github' })} />
      </div>
      <div className="flex flex-col gap-2 xl:flex-row">
        <input value={form.name} onChange={(e) => update('name', e.target.value)} placeholder="Server name" className="rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-2 text-xs text-slate-100 outline-none transition focus:border-violet-500/40 xl:w-1/4" />
        <input value={form.command} onChange={(e) => update('command', e.target.value)} placeholder="Command" className="rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-2 text-xs text-slate-100 outline-none transition focus:border-violet-500/40 xl:w-1/4" />
        <input value={form.args} onChange={(e) => update('args', e.target.value)} placeholder="Args, space-separated" className="flex-1 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-2 text-xs text-slate-100 outline-none transition focus:border-violet-500/40" />
        <button onClick={submit} disabled={saving || !form.name || !form.command} className="flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50">
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
          Add
        </button>
      </div>
    </div>
  );
}

function Preset({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900/70 px-2.5 py-1 text-[11px] font-semibold text-slate-400 transition hover:border-violet-600/50 hover:text-violet-300">
      <Wand2 className="h-3 w-3" />{label}
    </button>
  );
}
