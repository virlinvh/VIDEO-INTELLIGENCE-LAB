import { useRef } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { ScriptColumn } from './ScriptColumn';
import { ScrollModeControl } from './ScrollModeControl';
import type { ScrollMode } from './useScriptScrollSync';
import type { TranscriptViewMode } from './TranscriptDocument';
import { CopyComparisonPopover } from './CopyComparisonPopover';
import { ChevronLeft, ChevronRight, AlignLeft, Pin, FileText } from 'lucide-react';

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

interface HorizontalScriptDeskProps {
  videos: VideoSegmentComparisonItem[];
  palette: ColorTheme[];
  pinnedVideoId: string | null;
  onTogglePin: (videoId: string) => void;
  scrollMode: ScrollMode;
  onChangeScrollMode: (mode: ScrollMode) => void;
  viewMode: TranscriptViewMode;
  onChangeViewMode: (mode: TranscriptViewMode) => void;
  registerScrollContainer: (videoId: string, el: HTMLElement | null) => void;
  onScroll: (videoId: string) => void;
  onOpenVideoDetail?: (videoId: string) => void;
}

export function HorizontalScriptDesk({
  videos,
  palette,
  pinnedVideoId,
  onTogglePin,
  scrollMode,
  onChangeScrollMode,
  viewMode,
  onChangeViewMode,
  registerScrollContainer,
  onScroll,
  onOpenVideoDetail
}: HorizontalScriptDeskProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const handleScrollLeft = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: -420, behavior: 'smooth' });
    }
  };

  const handleScrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 420, behavior: 'smooth' });
    }
  };

  const pinnedVideo = pinnedVideoId ? videos.find(v => v.video_id === pinnedVideoId) : null;
  const comparisonVideos = pinnedVideoId ? videos.filter(v => v.video_id !== pinnedVideoId) : videos;

  const isTwoColumnUnpinned = !pinnedVideo && videos.length === 2;

  // Map original indices for stable palette colors
  const videoColorMap = new Map<string, { color: ColorTheme; originalIndex: number }>();
  videos.forEach((v, idx) => {
    videoColorMap.set(v.video_id, {
      color: palette[idx % palette.length],
      originalIndex: idx
    });
  });

  return (
    <div className="space-y-3">
      {/* Desk Control Bar & Overview */}
      <div className="flex items-center justify-between flex-wrap gap-3 px-1 text-xs text-[#475569] bg-slate-50 p-2.5 rounded-2xl border border-slate-200">
        <div className="flex items-center gap-2 flex-wrap">
          <AlignLeft className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="font-black text-[#0f172a]">
            {videos.length} Video Scripts
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-[#64748b]">
            Scope: <strong className="text-slate-800 font-semibold">{videos[0]?.requested_range_label || 'Selected Range'}</strong>
          </span>
          {pinnedVideo && (
            <>
              <span className="text-slate-300">|</span>
              <span className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold flex items-center gap-1">
                <Pin className="w-3 h-3 fill-current" />
                <span>Reference: {pinnedVideo.title.slice(0, 20)}...</span>
              </span>
            </>
          )}
        </div>

        {/* Right Controls: Copy Comparison + View Mode Switcher + Scroll Mode Switcher + Horizontal Navigation Arrows */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Workspace Multi-Video Copy Comparison Popover */}
          <CopyComparisonPopover
            videos={videos}
            pinnedVideoId={pinnedVideoId}
          />

          {/* Workspace-level View Mode Switcher (Document vs Timestamps) */}
          <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-300 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-500 uppercase px-1.5 flex items-center gap-1">
              <FileText className="w-3 h-3 text-slate-400" />
              <span>View:</span>
            </span>
            <button
              type="button"
              onClick={() => onChangeViewMode('document')}
              className={`px-2 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'document'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Document reading view (natural prose without timestamp clutter)"
            >
              Document
            </button>
            <button
              type="button"
              onClick={() => onChangeViewMode('timestamps')}
              className={`px-2 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'timestamps'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Timestamps evidence view (time-aligned segments)"
            >
              Timestamps
            </button>
          </div>

          {/* Scroll Mode Switcher */}
          <ScrollModeControl
            scrollMode={scrollMode}
            onChangeScrollMode={onChangeScrollMode}
          />

          {/* Horizontal Navigation Arrows */}
          <div className="flex items-center gap-1 border-l border-slate-300 pl-2.5">
            <button
              type="button"
              onClick={handleScrollLeft}
              className="p-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 shadow-2xs transition-colors cursor-pointer"
              title="Scroll Comparison Track Left (←)"
              aria-label="Scroll left"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-[11px] font-mono text-slate-500 px-1 font-semibold">
              {comparisonVideos.length} {pinnedVideo ? 'compared' : 'columns'}
            </span>
            <button
              type="button"
              onClick={handleScrollRight}
              className="p-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 shadow-2xs transition-colors cursor-pointer"
              title="Scroll Comparison Track Right (→)"
              aria-label="Scroll right"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Desk Content Area: Split Pinned Layout vs Standard Horizontal Layout */}
      {pinnedVideo ? (
        <div className="flex flex-row gap-5 items-stretch">
          {/* Pinned Reference Column (Fixed on the Left) */}
          <div className="shrink-0">
            <ScriptColumn
              key={`pinned-${pinnedVideo.video_id}`}
              video={pinnedVideo}
              index={videoColorMap.get(pinnedVideo.video_id)?.originalIndex ?? 0}
              totalVideos={videos.length}
              color={videoColorMap.get(pinnedVideo.video_id)?.color ?? palette[0]}
              viewMode={viewMode}
              isPinned={true}
              onTogglePin={onTogglePin}
              onOpenVideoDetail={onOpenVideoDetail}
              registerScrollContainer={registerScrollContainer}
              onScroll={onScroll}
            />
          </div>

          {/* Vertical Divider Line */}
          <div className="w-px bg-slate-300 self-stretch shrink-0 mx-1 hidden sm:block" />

          {/* Horizontally Scrollable Comparison Track */}
          <div
            ref={scrollContainerRef}
            className="flex-1 flex flex-row gap-5 overflow-x-auto pb-4 pt-1 px-1 scroll-smooth snap-x snap-mandatory focus:outline-none"
            style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#cbd5e1 #f1f5f9'
            }}
          >
            {comparisonVideos.map((video) => {
              const info = videoColorMap.get(video.video_id);
              return (
                <ScriptColumn
                  key={video.video_id}
                  video={video}
                  index={info?.originalIndex ?? 0}
                  totalVideos={videos.length}
                  color={info?.color ?? palette[0]}
                  viewMode={viewMode}
                  isPinned={false}
                  isTwoColumn={comparisonVideos.length === 1}
                  onTogglePin={onTogglePin}
                  onOpenVideoDetail={onOpenVideoDetail}
                  registerScrollContainer={registerScrollContainer}
                  onScroll={onScroll}
                />
              );
            })}
          </div>
        </div>
      ) : (
        /* Normal Unpinned Horizontal Scroll Container */
        <div
          ref={scrollContainerRef}
          className="flex flex-row gap-5 overflow-x-auto pb-4 pt-1 px-1 scroll-smooth snap-x snap-mandatory focus:outline-none"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: '#cbd5e1 #f1f5f9'
          }}
        >
          {videos.map((video, idx) => {
            const color = palette[idx % palette.length];
            return (
              <ScriptColumn
                key={video.video_id}
                video={video}
                index={idx}
                totalVideos={videos.length}
                color={color}
                viewMode={viewMode}
                isPinned={false}
                isTwoColumn={isTwoColumnUnpinned}
                onTogglePin={onTogglePin}
                onOpenVideoDetail={onOpenVideoDetail}
                registerScrollContainer={registerScrollContainer}
                onScroll={onScroll}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
