import type { VideoSegmentComparisonItem } from '../../types';
import { ScriptColumnHeader } from './ScriptColumnHeader';
import { TranscriptDocument, type TranscriptViewMode } from './TranscriptDocument';
import { ErrorBoundary } from '../ErrorBoundary';

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

interface ScriptColumnProps {
  video: VideoSegmentComparisonItem;
  index: number;
  totalVideos: number;
  color: ColorTheme;
  viewMode?: TranscriptViewMode;
  isPinned?: boolean;
  isTwoColumn?: boolean;
  onTogglePin?: (videoId: string) => void;
  onOpenVideoDetail?: (videoId: string) => void;
  registerScrollContainer?: (videoId: string, el: HTMLElement | null) => void;
  onScroll?: (videoId: string) => void;
}

export function ScriptColumn({
  video,
  index,
  totalVideos,
  color,
  viewMode = 'document',
  isPinned = false,
  isTwoColumn = false,
  onTogglePin,
  onOpenVideoDetail,
  registerScrollContainer,
  onScroll
}: ScriptColumnProps) {
  return (
    <ErrorBoundary>
      <div 
        className={`flex flex-col bg-white rounded-2xl shadow-xs h-[720px] max-h-[calc(100vh-270px)] overflow-hidden transition-all snap-start ${
          isPinned 
            ? 'border-2 border-amber-400 ring-2 ring-amber-200/60 w-[380px] lg:w-[410px] shrink-0' 
            : isTwoColumn 
            ? `border-2 ${color.border} flex-1 min-w-[380px] max-w-[650px]` 
            : `border-2 ${color.border} w-[400px] min-w-[380px] max-w-[440px] shrink-0`
        }`}
      >
        {/* Sticky Top Header */}
        <ScriptColumnHeader
          video={video}
          index={index}
          totalVideos={totalVideos}
          color={color}
          isPinned={isPinned}
          onTogglePin={onTogglePin}
          onOpenVideoDetail={onOpenVideoDetail}
        />

        {/* Scrollable Document Area with Ref and Scroll Listener */}
        <TranscriptDocument 
          video={video} 
          viewMode={viewMode}
          containerRef={(el) => {
            if (registerScrollContainer) {
              registerScrollContainer(video.video_id, el);
            }
          }}
          onScroll={() => {
            if (onScroll) {
              onScroll(video.video_id);
            }
          }}
        />

        {/* Compact Column Bottom Bar */}
        <div className={`shrink-0 px-3.5 py-1.5 border-t flex items-center justify-between text-[10px] ${
          isPinned 
            ? 'bg-amber-50/70 border-amber-200 text-amber-950 font-semibold' 
            : 'bg-slate-50 border-slate-200 text-[#64748b]'
        }`}>
          <span className="truncate max-w-[180px] font-medium">
            {isPinned ? '★ Reference Scope' : video.requested_range_label}
          </span>
          <span className="font-mono">
            {video.segments.length} segments
          </span>
        </div>
      </div>
    </ErrorBoundary>
  );
}
