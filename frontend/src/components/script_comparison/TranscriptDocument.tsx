import { useMemo } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { FileText, AlertCircle, Clock } from 'lucide-react';

export type TranscriptViewMode = 'document' | 'timestamps';

interface TranscriptDocumentProps {
  video: VideoSegmentComparisonItem;
  viewMode?: TranscriptViewMode;
  containerRef?: (el: HTMLDivElement | null) => void;
  onScroll?: (e: React.UIEvent<HTMLDivElement>) => void;
}

export function TranscriptDocument({
  video,
  viewMode = 'document',
  containerRef,
  onScroll
}: TranscriptDocumentProps) {
  if (video.availability === 'NO_TRANSCRIPT' || !video.has_transcript) {
    return (
      <div 
        ref={containerRef}
        className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/50 rounded-xl border border-dashed border-slate-200 min-h-[300px]"
      >
        <FileText className="w-8 h-8 text-slate-300 mb-2" />
        <h4 className="text-xs font-bold text-[#0f172a] mb-1">Transcript Unavailable</h4>
        <p className="text-[11px] text-[#64748b] max-w-[240px]">
          No transcript or caption record was found for this video in the Library.
        </p>
      </div>
    );
  }

  if (video.availability === 'EMPTY_RANGE' || video.segments.length === 0) {
    return (
      <div 
        ref={containerRef}
        className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/50 rounded-xl border border-dashed border-slate-200 min-h-[300px]"
      >
        <Clock className="w-8 h-8 text-slate-300 mb-2" />
        <h4 className="text-xs font-bold text-[#0f172a] mb-1">No Spoken Segments</h4>
        <p className="text-[11px] text-[#64748b] max-w-[240px]">
          {video.warning || 'No spoken words recorded in this specific time interval for this video.'}
        </p>
      </div>
    );
  }

  if (video.availability === 'NOT_AVAILABLE') {
    return (
      <div 
        ref={containerRef}
        className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-rose-50/50 rounded-xl border border-dashed border-rose-200 min-h-[300px]"
      >
        <AlertCircle className="w-8 h-8 text-rose-400 mb-2" />
        <h4 className="text-xs font-bold text-rose-900 mb-1">Range Unavailable</h4>
        <p className="text-[11px] text-rose-700 max-w-[240px]">
          {video.warning || 'Could not compute the requested range for this video.'}
        </p>
      </div>
    );
  }

  // Memoize naturally grouped paragraph blocks for Document Mode
  const documentParagraphs = useMemo(() => {
    if (!video.segments || video.segments.length === 0) return [];
    const paras: string[] = [];
    let currentGroup: string[] = [];
    let currentWords = 0;

    for (const seg of video.segments) {
      const text = seg.text?.trim();
      if (!text) continue;
      currentGroup.push(text);
      currentWords += seg.word_count || text.split(/\s+/).length;

      // Group paragraphs naturally around terminal punctuation or segment groups
      const endsWithPunct = /[.!?]$/.test(text) || /[.!?]["']$/.test(text);
      if ((endsWithPunct && currentWords >= 30) || currentGroup.length >= 5) {
        paras.push(currentGroup.join(' '));
        currentGroup = [];
        currentWords = 0;
      }
    }

    if (currentGroup.length > 0) {
      paras.push(currentGroup.join(' '));
    }

    return paras;
  }, [video.segments]);

  return (
    <div 
      ref={containerRef}
      onScroll={onScroll}
      className="flex-1 overflow-y-auto px-4 py-3.5 bg-white select-text font-sans scrollbar-thin"
    >
      {viewMode === 'document' ? (
        /* Document Reading Mode: Natural flowing paragraphs without timestamp clutter */
        <div className="space-y-3.5 text-[13px] text-slate-800 leading-relaxed font-sans">
          {documentParagraphs.map((paragraph, pIdx) => (
            <p key={pIdx} className="leading-relaxed text-slate-800 break-words whitespace-pre-wrap">
              {paragraph}
            </p>
          ))}
        </div>
      ) : (
        /* Timestamps Mode: Evidence-oriented segment rows with start time and duration */
        <div className="space-y-2.5 font-sans">
          {video.segments.map((seg) => (
            <div 
              key={seg.id || `${seg.sequence_index}-${seg.start_time}`} 
              className="group flex flex-col space-y-1 transition-colors hover:bg-slate-50/90 -mx-1.5 px-2 py-1.5 rounded-lg border border-transparent hover:border-slate-200"
            >
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span className="font-bold text-indigo-700 bg-indigo-50/80 px-1.5 py-0.5 rounded border border-indigo-100">
                  {seg.formatted_start_time}
                </span>
                <span className="text-slate-400 group-hover:text-slate-600 font-medium">
                  {seg.duration}s
                </span>
              </div>
              <p className="text-xs text-[#0f172a] leading-relaxed font-normal break-words whitespace-pre-wrap">
                {seg.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

