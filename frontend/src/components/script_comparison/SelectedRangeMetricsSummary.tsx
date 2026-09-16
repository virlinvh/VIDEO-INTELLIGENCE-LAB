import { useState } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { Table, ChevronDown, ChevronUp, Languages, Sparkles, Copy, Check } from 'lucide-react';
import { formatMetricsSummaryTable } from './scriptCopyFormatters';

interface ColorTheme {
  name: string;
  border: string;
  bg: string;
  text: string;
  badge: string;
  bar: string;
  dot: string;
  fill: string;
  ring: string;
}

interface SelectedRangeMetricsSummaryProps {
  videos: VideoSegmentComparisonItem[];
  palette: ColorTheme[];
  hasMixedLanguages?: boolean;
}

export function SelectedRangeMetricsSummary({
  videos,
  palette,
  hasMixedLanguages = false
}: SelectedRangeMetricsSummaryProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const [showAllMetrics, setShowAllMetrics] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopyMetrics = async () => {
    try {
      const textTable = formatMetricsSummaryTable(videos, showAllMetrics);
      await navigator.clipboard.writeText(textTable);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy metrics:', err);
    }
  };

  if (!videos || videos.length < 2) return null;

  const coreMetricKeys: { key: string; label: string; suffix?: string; tooltip?: string }[] = [
    { key: 'word_count', label: 'Words' },
    { key: 'range_wpm', label: 'Range WPM', tooltip: 'Words per minute over effective selected range' },
    { key: 'sentence_count', label: 'Sentences' },
    { key: 'unique_words', label: 'Unique Words' },
    { key: 'question_count', label: 'Questions' }
  ];

  const extendedMetricKeys: { key: string; label: string; suffix?: string; tooltip?: string }[] = [
    { key: 'segment_count', label: 'Segments' },
    { key: 'lexical_diversity', label: 'Lexical Diversity', suffix: '%' },
    { key: 'average_sentence_length', label: 'Avg Sentence Length', suffix: ' w/s' },
    { key: 'exclamation_count', label: 'Exclamations' },
    { key: 'filler_count', label: 'Fillers' },
    { key: 'transition_count', label: 'Transitions' },
    { key: 'repeated_phrase_count', label: 'Repeated Phrases' }
  ];

  const displayedKeys = showAllMetrics 
    ? [...coreMetricKeys, ...extendedMetricKeys] 
    : coreMetricKeys;

  return (
    <div className="bg-white rounded-2xl border-2 border-slate-200/90 shadow-xs overflow-hidden transition-all">
      {/* Header Bar */}
      <div className="px-4 py-3 bg-slate-50/90 border-b border-slate-200 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center shrink-0">
            <Table className="w-3.5 h-3.5 text-indigo-600" />
          </div>
          <div>
            <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <span>Selected Range Metrics Summary</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-200/80 text-slate-700">
                {videos[0]?.requested_range_label || 'Active Range'}
              </span>
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isOpen && (
            <>
              <button
                type="button"
                onClick={handleCopyMetrics}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold inline-flex items-center gap-1 transition-colors cursor-pointer shadow-2xs ${
                  copied
                    ? 'bg-emerald-600 text-white'
                    : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
                }`}
                title="Copy metrics table to clipboard"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 stroke-[3]" />
                    <span>Copied Metrics</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3 text-slate-500" />
                    <span>Copy Metrics</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => setShowAllMetrics(!showAllMetrics)}
                className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 shadow-2xs inline-flex items-center gap-1 transition-colors cursor-pointer"
              >
                <Sparkles className="w-3 h-3 text-indigo-500" />
                <span>{showAllMetrics ? 'Show Core Metrics' : 'Show All 12 Metrics'}</span>
              </button>
            </>
          )}

          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="p-1 rounded-lg hover:bg-slate-200 text-slate-600 transition-colors cursor-pointer"
            aria-label={isOpen ? 'Collapse metrics summary' : 'Expand metrics summary'}
          >
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="p-4 space-y-3">
          {/* Mixed-Language Callout */}
          {hasMixedLanguages && (
            <div className="p-2.5 rounded-xl bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900 flex items-center gap-2 font-medium">
              <Languages className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                Scripts contain multiple languages. Lexical metrics are calculated independently from each transcript.
              </span>
            </div>
          )}

          {/* Horizontally Scrollable Summary Table */}
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/90 border-b border-slate-200 text-slate-600 text-[11px] font-bold">
                  <th className="py-2.5 px-3.5 sticky left-0 bg-slate-50/95 z-10 border-r border-slate-200 min-w-[160px]">
                    Metric
                  </th>
                  {videos.map((v, idx) => {
                    const theme = palette[idx % palette.length];
                    return (
                      <th key={v.video_id} className="py-2.5 px-3.5 min-w-[140px] font-semibold">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${theme.dot} shrink-0`} />
                          <span className="truncate max-w-[120px] text-slate-800" title={v.title}>
                            {v.title}
                          </span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {displayedKeys.map((item) => (
                  <tr key={item.key} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-2 px-3.5 font-medium text-slate-700 sticky left-0 bg-white/95 z-10 border-r border-slate-200" title={item.tooltip}>
                      <span className="flex items-center gap-1">
                        <span>{item.label}</span>
                        {item.tooltip && (
                          <span className="text-[10px] text-slate-400 font-normal">ⓘ</span>
                        )}
                      </span>
                    </td>
                    {videos.map((v) => {
                      const m = v.metrics;
                      if (v.availability === 'NO_TRANSCRIPT') {
                        return (
                          <td key={v.video_id} className="py-2 px-3.5 font-mono text-slate-400 text-[11px]">
                            — (no transcript)
                          </td>
                        );
                      }
                      if (v.availability === 'NOT_AVAILABLE') {
                        return (
                          <td key={v.video_id} className="py-2 px-3.5 font-mono text-slate-400 text-[11px]">
                            — (unavailable)
                          </td>
                        );
                      }
                      if (!m) {
                        return (
                          <td key={v.video_id} className="py-2 px-3.5 font-mono text-slate-400">
                            —
                          </td>
                        );
                      }

                      const val = (m as any)[item.key];
                      const displayVal = val === null || val === undefined 
                        ? '—' 
                        : `${typeof val === 'number' ? val.toLocaleString() : val}${item.suffix || ''}`;

                      return (
                        <td key={v.video_id} className="py-2 px-3.5 font-mono font-bold text-slate-900">
                          {displayVal}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
