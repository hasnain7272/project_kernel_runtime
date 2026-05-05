import { Loader2, Paperclip, Send } from 'lucide-react';

interface Props {
  input: string;
  streaming: boolean;
  shadowMode: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement>;
  onInput: (value: string) => void;
  onSend: () => void;
  onUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onToggleShadow: () => void;
}

export function ChatComposer({ input, streaming, shadowMode, inputRef, onInput, onSend, onUpload, onToggleShadow }: Props) {
  const submit = (event: React.FormEvent) => { event.preventDefault(); onSend(); };
  const keyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); onSend(); }
  };

  return (
    <form onSubmit={submit} className="flex items-end gap-2 rounded-2xl border border-slate-700/60 bg-slate-900/85 px-4 py-2 ring-1 ring-slate-800/50 transition focus-within:border-cyan-600/50 focus-within:ring-cyan-600/20">
      <textarea ref={inputRef} rows={1} value={input} onChange={(event) => onInput(event.target.value)} onKeyDown={keyDown} placeholder="Ask, edit, build..." disabled={streaming} className="max-h-[120px] flex-1 resize-none bg-transparent py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 disabled:opacity-50" />
      <label className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-800 hover:text-slate-200" title="Attach file">
        <input type="file" className="hidden" onChange={onUpload} />
        <Paperclip className="h-3.5 w-3.5" />
      </label>
      <button type="button" onClick={onToggleShadow} title="Shadow mode" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition ${shadowMode ? 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/50' : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'}`}>
        <span className={`h-2.5 w-2.5 rounded-full ${shadowMode ? 'animate-pulse bg-amber-400' : 'bg-slate-600'}`} />
      </button>
      <button type="submit" disabled={streaming || !input.trim()} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-600 text-white transition hover:bg-cyan-500 disabled:opacity-30">
        {streaming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
      </button>
    </form>
  );
}
