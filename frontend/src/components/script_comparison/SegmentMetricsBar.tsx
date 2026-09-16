import { useState } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { ChevronDown, ChevronUp, BarChart2 } from 'lucide-react';

interface SegmentMetricsBarProps {
  video: VideoSegmentComparisonItem;
  isPinned?: boolean;
}

export function SegmentMetricsBar({ video, isPinned = false }: SegmentMetricsBarProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const metrics = video.metrics;

  if (video.availability === 'NO_TRANSCRIPT') {
    return (
      <div className="px-3 py-2 rounded-xl bg-slate-100/80 border border-slate-200 text-center text-[11px] text-slate-500 font-medium">
        Transcript unavailable for this video
      </div>
    );
  }

  if (video.availability === 'NOT_AVAILABLE') {
    return (
      <div className="px-3 py-2 rounded-xl bg-amber-50/90 border border-amber-200 text-center text-[11px] text-amber-800 font-medium">
        {video.warning || 'Range metrics unavailable'}
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <div className={`rounded-xl border transition-all ${
      isPinned 
        ? 'bg-amber-100/60 border-amber-300/80 shadow-2xs' 
        : 'bg-white border-slate-200 shadow-2xs'
    }`}>
      {/* Compact Quick Stats Grid */}
      <div className="p-2.5 space-y-2">
        <div className="grid grid-cols-4 gap-1.5 text-center">
          <div className="p-1 rounded-lg bg-slate-50/90 border border-slate-200/80">
            <span className="block text-[9px] font-semibold text-slate-500 uppercase tracking-wider">Words</span>
            <span className="font-mono text-xs font-bold text-slate-900">{metrics.word_count.toLocaleString()}</span>
          </div>

          <div className="p-1 rounded-lg bg-slate-50/90 border border-slate-200/80" title="Words per minute over effective selected range">
            <span className="block text-[9px] font-semibold text-slate-500 uppercase tracking-wider">Range WPM</span>
            <span className="font-mono text-xs font-bold text-slate-900">
              {metrics.range_wpm !== null && metrics.range_wpm !== undefined ? metrics.range_wpm : '—'}
            </span>
          </div>

          <div className="p-1 rounded-lg bg-slate-50/90 border border-slate-200/80">
            <span className="block text-[9px] font-semibold text-slate-500 uppercase tracking-wider">Sents</span>
            <span className="font-mono text-xs font-bold text-slate-900">{metrics.sentence_count}</span>
          </div>

          <div className="p-1 rounded-lg bg-slate-50/90 border border-slate-200/80">
            <span className="block text-[9px] font-semibold text-slate-500 uppercase tracking-wider">Unique</span>
            <span className="font-mono text-xs font-bold text-slate-900">{metrics.unique_words}</span>
          </div>
        </div>

        {/* Expand / Collapse Button */}
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className={`w-full py-1 px-2 rounded-lg text-[10px] font-bold inline-flex items-center justify-center gap-1 transition-colors cursor-pointer ${
            isExpanded 
              ? 'bg-slate-200/70 text-slate-800' 
              : 'hover:bg-slate-100 text-slate-600'
          }`}
          aria-expanded={isExpanded}
          aria-label={isExpanded ? 'Hide segment metrics' : 'View full segment metrics'}
        >
          <BarChart2 className="w-3 h-3 text-slate-500" />
          <span>{isExpanded ? 'Hide Segment Metrics' : 'View Segment Metrics'}</span>
          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {/* Expanded Metrics Table */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-slate-200/80 space-y-1.5 animate-fadeIn">
          <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
            Segment Metrics ({video.requested_range_label})
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Words</span>
              <span className="font-mono font-bold text-slate-900">{metrics.word_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Segments</span>
              <span className="font-mono font-bold text-slate-900">{metrics.segment_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Sentences</span>
              <span className="font-mono font-bold text-slate-900">{metrics.sentence_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Unique Words</span>
              <span className="font-mono font-bold text-slate-900">{metrics.unique_words}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Lexical Diversity</span>
              <span className="font-mono font-bold text-slate-900">{metrics.lexical_diversity}%</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Avg Sentence Length</span>
              <span className="font-mono font-bold text-slate-900">{metrics.average_sentence_length} w/s</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100" title="Words per minute over effective selected range">
              <span className="text-slate-500">Range WPM</span>
              <span className="font-mono font-bold text-slate-900">
                {metrics.range_wpm !== null && metrics.range_wpm !== undefined ? metrics.range_wpm : '—'}
              </span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Questions</span>
              <span className="font-mono font-bold text-slate-900">{metrics.question_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Exclamations</span>
              <span className="font-mono font-bold text-slate-900">{metrics.exclamation_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Fillers</span>
              <span className="font-mono font-bold text-slate-900">{metrics.filler_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Transitions</span>
              <span className="font-mono font-bold text-slate-900">{metrics.transition_count}</span>
            </div>

            <div className="flex items-center justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">Repeated Phrases</span>
              <span className="font-mono font-bold text-slate-900">{metrics.repeated_phrase_count}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
