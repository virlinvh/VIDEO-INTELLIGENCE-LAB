import { useState } from 'react';
import { 
  Clock, 
  Sparkles, 
  Scissors, 
  Layers, 
  RotateCcw,
  SlidersHorizontal 
} from 'lucide-react';
import type { SegmentRangeRequest } from '../../types';

interface RangeControlsProps {
  onApplyRange: (range: SegmentRangeRequest, presetKey: string) => void;
  activePreset: string;
  loading: boolean;
}

function parseTimeInput(input: string): number | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  if (/^\d+(\.\d+)?$/.test(trimmed)) {
    return parseFloat(trimmed);
  }
  const parts = trimmed.split(':');
  if (parts.length === 2) {
    const mins = parseFloat(parts[0]);
    const secs = parseFloat(parts[1]);
    if (!isNaN(mins) && !isNaN(secs)) {
      return mins * 60 + secs;
    }
  } else if (parts.length === 3) {
    const hrs = parseFloat(parts[0]);
    const mins = parseFloat(parts[1]);
    const secs = parseFloat(parts[2]);
    if (!isNaN(hrs) && !isNaN(mins) && !isNaN(secs)) {
      return hrs * 3600 + mins * 60 + secs;
    }
  }
  return null;
}

export function RangeControls({ onApplyRange, activePreset, loading }: RangeControlsProps) {
  const [customStart, setCustomStart] = useState<string>('00:00');
  const [customEnd, setCustomEnd] = useState<string>('00:30');
  const [customError, setCustomError] = useState<string | null>(null);

  const handleApplyCustom = () => {
    const s = parseTimeInput(customStart);
    const e = parseTimeInput(customEnd);
    if (s === null || e === null || s >= e) {
      setCustomError('Start time must be strictly less than end time (e.g. 00:00 to 00:30).');
      return;
    }
    setCustomError(null);
    onApplyRange({ type: 'ABSOLUTE', start_seconds: s, end_seconds: e }, 'custom');
  };

  return (
    <div className="p-5 rounded-2xl bg-white border-2 border-slate-200 shadow-xs space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-indigo-600" />
          <h3 className="text-sm font-black text-[#0f172a] uppercase tracking-wide">
            Transcript Range Scope
          </h3>
        </div>
        <span className="text-xs text-[#64748b]">
          Select an opening hook, relative slice, closing outro, or custom interval across all videos
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Full Script Preset */}
        <div className="lg:col-span-2 flex flex-col justify-center">
          <button
            type="button"
            disabled={loading}
            onClick={() => onApplyRange({ type: 'ENTIRE' }, 'entire')}
            className={`w-full py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activePreset === 'entire'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-[#0f172a] border border-slate-300'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0" />
            <span>Entire Script</span>
          </button>
        </div>

        {/* Opening Hooks Presets */}
        <div className="lg:col-span-3 space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569]">
            <Clock className="w-3 h-3 text-emerald-600" />
            <span>Opening Hooks</span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {[
              { label: '3s', sec: 3.0, key: 'op-3' },
              { label: '5s', sec: 5.0, key: 'op-5' },
              { label: '10s', sec: 10.0, key: 'op-10' },
              { label: '30s', sec: 30.0, key: 'op-30' }
            ].map(p => (
              <button
                key={p.key}
                type="button"
                disabled={loading}
                onClick={() => onApplyRange({ type: 'OPENING', duration_seconds: p.sec }, p.key)}
                className={`py-1.5 px-1 rounded-lg text-xs font-bold transition-all text-center cursor-pointer ${
                  activePreset === p.key
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Relative Scale (0-100%) */}
        <div className="lg:col-span-4 space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569]">
            <Layers className="w-3 h-3 text-cyan-600" />
            <span>Relative Duration Scale (0–100%)</span>
          </div>
          <div className="grid grid-cols-5 gap-1.5">
            {[
              { label: '0–10%', s: 0, e: 10, key: 'rel-0-10', sub: 'Hook' },
              { label: '10–25%', s: 10, e: 25, key: 'rel-10-25', sub: 'Intro' },
              { label: '25–50%', s: 25, e: 50, key: 'rel-25-50', sub: 'Core' },
              { label: '50–75%', s: 50, e: 75, key: 'rel-50-75', sub: 'Climax' },
              { label: '75–100%', s: 75, e: 100, key: 'rel-75-100', sub: 'Outro' }
            ].map(p => (
              <button
                key={p.key}
                type="button"
                disabled={loading}
                onClick={() => onApplyRange({ type: 'RELATIVE', start_percent: p.s, end_percent: p.e }, p.key)}
                className={`py-1.5 px-1 rounded-lg text-xs font-bold transition-all text-center cursor-pointer flex flex-col items-center justify-center ${
                  activePreset === p.key
                    ? 'bg-cyan-700 text-white shadow-xs'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200'
                }`}
                title={`${p.label} (${p.sub})`}
              >
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Closing Outros */}
        <div className="lg:col-span-3 space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569]">
            <RotateCcw className="w-3 h-3 text-rose-600" />
            <span>Closing Outros</span>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {[
              { label: 'Last 5s', sec: 5.0, key: 'cl-5' },
              { label: 'Last 10s', sec: 10.0, key: 'cl-10' },
              { label: 'Last 30s', sec: 30.0, key: 'cl-30' }
            ].map(p => (
              <button
                key={p.key}
                type="button"
                disabled={loading}
                onClick={() => onApplyRange({ type: 'CLOSING', duration_seconds: p.sec }, p.key)}
                className={`py-1.5 px-1 rounded-lg text-xs font-bold transition-all text-center cursor-pointer ${
                  activePreset === p.key
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Custom Absolute Range Bar */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-xs">
          <Scissors className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
          <span className="font-bold text-[#475569]">Custom Interval:</span>
          <div className="flex items-center gap-1.5 font-mono">
            <input
              type="text"
              value={customStart}
              onChange={e => setCustomStart(e.target.value)}
              placeholder="00:00"
              className="w-16 px-2 py-1 text-center bg-slate-50 border border-slate-300 rounded-lg text-xs font-bold text-[#0f172a] focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
            <span className="text-slate-400 font-bold">to</span>
            <input
              type="text"
              value={customEnd}
              onChange={e => setCustomEnd(e.target.value)}
              placeholder="00:30"
              className="w-16 px-2 py-1 text-center bg-slate-50 border border-slate-300 rounded-lg text-xs font-bold text-[#0f172a] focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={handleApplyCustom}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activePreset === 'custom'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-indigo-50 text-indigo-900 border border-indigo-200 hover:bg-indigo-100'
            }`}
          >
            Apply
          </button>
        </div>

        {customError && (
          <span className="text-xs text-rose-600 font-semibold">{customError}</span>
        )}
      </div>
    </div>
  );
}
