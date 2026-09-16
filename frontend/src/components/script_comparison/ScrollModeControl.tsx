import { Layers, Link2 } from 'lucide-react';
import type { ScrollMode } from './useScriptScrollSync';

interface ScrollModeControlProps {
  scrollMode: ScrollMode;
  onChangeScrollMode: (mode: ScrollMode) => void;
}

export function ScrollModeControl({
  scrollMode,
  onChangeScrollMode
}: ScrollModeControlProps) {
  return (
    <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-300">
      <span className="text-[11px] font-bold text-slate-500 px-1.5 flex items-center gap-1">
        Scroll:
      </span>
      <button
        type="button"
        onClick={() => onChangeScrollMode('independent')}
        aria-pressed={scrollMode === 'independent'}
        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
          scrollMode === 'independent'
            ? 'bg-white text-[#0f172a] shadow-xs border border-slate-200'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
        }`}
        title="Independent vertical scrolling per script column"
      >
        <Layers className="w-3.5 h-3.5" />
        <span>Independent</span>
      </button>

      <button
        type="button"
        onClick={() => onChangeScrollMode('sync')}
        aria-pressed={scrollMode === 'sync'}
        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
          scrollMode === 'sync'
            ? 'bg-indigo-600 text-white shadow-xs'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
        }`}
        title="Synchronize vertical reading progress (0–100%) across all visible script columns"
      >
        <Link2 className="w-3.5 h-3.5" />
        <span>Sync (Relative)</span>
      </button>
    </div>
  );
}
