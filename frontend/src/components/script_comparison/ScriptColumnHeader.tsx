import { useState, useRef, useEffect } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { 
  formatSingleVideoScript, 
  formatTime 
} from './scriptCopyFormatters';
import { Copy, Check, Film, Clock, Pin, PinOff, ChevronDown, FileText } from 'lucide-react';

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

interface ScriptColumnHeaderProps {
  video: VideoSegmentComparisonItem;
  index: number;
  totalVideos: number;
  color: ColorTheme;
  isPinned?: boolean;
  onTogglePin?: (videoId: string) => void;
  onOpenVideoDetail?: (videoId: string) => void;
}

export function ScriptColumnHeader({
  video,
  index,
  totalVideos,
  color,
  isPinned = false,
  onTogglePin,
  onOpenVideoDetail
}: ScriptColumnHeaderProps) {
  const [menuOpen, setMenuOpen] = useState<boolean>(false);
  const [copiedMode, setCopiedMode] = useState<string | null>(null);
  const [loadingFull, setLoadingFull] = useState<boolean>(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  const handleCopy = async (targetScope: 'current' | 'full', includeTimestamps: boolean) => {
    try {
      let targetItem = video;

      if (targetScope === 'full' && video.requested_range_label !== 'Entire Video') {
        setLoadingFull(true);
        const res = await fetch('/api/v1/comparisons/segments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_ids: [video.video_id],
            range: { type: 'ENTIRE' }
          })
        });
        if (res.ok) {
          const data = await res.json();
          if (data && data.videos && data.videos.length > 0) {
            targetItem = data.videos[0];
          }
        }
      }

      const formatted = formatSingleVideoScript(targetItem, { includeTimestamps });
      await navigator.clipboard.writeText(formatted);

      const label = targetScope === 'full' ? 'Full Script' : 'Range';
      setCopiedMode(`${label}${includeTimestamps ? ' + Time' : ''}`);
      setTimeout(() => {
        setCopiedMode(null);
        setMenuOpen(false);
      }, 1800);
    } catch (err) {
      console.error('Failed to copy single script:', err);
    } finally {
      setLoadingFull(false);
    }
  };

  const effectiveRangeText = video.effective_start_seconds !== null && video.effective_start_seconds !== undefined &&
    video.effective_end_seconds !== null && video.effective_end_seconds !== undefined
      ? `${formatTime(video.effective_start_seconds)} – ${formatTime(video.effective_end_seconds)}`
      : '—';

  return (
    <div className={`shrink-0 p-3 border-b space-y-2 ${
      isPinned 
        ? 'bg-amber-50/95 border-amber-300' 
        : 'bg-slate-50/95 border-slate-200'
    }`}>
      {/* ROW 1: Position/Reference Badge + Title (2 lines) + Actions (Pin, Copy) */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-1.5 min-w-0 flex-1">
          {isPinned ? (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-black tracking-wider bg-amber-500 text-slate-950 flex items-center gap-0.5 shrink-0 mt-0.5 shadow-2xs">
              <Pin className="w-2.5 h-2.5 fill-current" />
              <span>REF</span>
            </span>
          ) : (
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-black tracking-wider ${color.badge} shrink-0 mt-0.5`}>
              {index + 1}/{totalVideos}
            </span>
          )}
          <h4
            onClick={() => onOpenVideoDetail && onOpenVideoDetail(video.video_id)}
            className="text-xs font-bold text-[#0f172a] line-clamp-2 leading-snug cursor-pointer hover:underline hover:text-indigo-600 transition-colors"
            title={video.title}
          >
            {video.title}
          </h4>
        </div>

        {/* Action Controls: Pin & Copy Menu */}
        <div className="flex items-center gap-1 shrink-0 mt-0.5">
          {onTogglePin && (
            <button
              type="button"
              onClick={() => onTogglePin(video.video_id)}
              className={`px-1.5 py-1 rounded-md text-[10px] font-bold inline-flex items-center gap-1 transition-all cursor-pointer ${
                isPinned
                  ? 'bg-amber-500 hover:bg-amber-600 text-slate-950 shadow-2xs'
                  : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 shadow-2xs'
              }`}
              title={isPinned ? 'Unpin reference script' : 'Pin as reference script (Lock on Left)'}
              aria-label={isPinned ? 'Unpin reference script' : 'Pin as reference script'}
            >
              {isPinned ? (
                <>
                  <PinOff className="w-2.5 h-2.5" />
                  <span>Unpin</span>
                </>
              ) : (
                <>
                  <Pin className="w-2.5 h-2.5 text-slate-500" />
                  <span>Pin</span>
                </>
              )}
            </button>
          )}

          {/* Individual Video Copy Menu Popover */}
          <div className="relative inline-block" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              disabled={video.availability === 'NO_TRANSCRIPT'}
              className={`px-1.5 py-1 rounded-md text-[10px] font-bold inline-flex items-center gap-1 transition-all cursor-pointer ${
                copiedMode
                  ? 'bg-emerald-600 text-white shadow-2xs'
                  : video.availability === 'NO_TRANSCRIPT'
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                  : menuOpen
                  ? 'bg-indigo-700 text-white shadow-2xs'
                  : 'bg-white hover:bg-slate-100 text-[#0f172a] border border-slate-300 shadow-2xs'
              }`}
              title="Copy script options (Current Range / Full Script / Timestamps)"
              aria-label="Open script copy options"
            >
              {copiedMode ? (
                <>
                  <Check className="w-2.5 h-2.5 stroke-[3]" />
                  <span>{copiedMode}</span>
                </>
              ) : (
                <>
                  <Copy className="w-2.5 h-2.5 text-slate-600" />
                  <span>Copy</span>
                  <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
                </>
              )}
            </button>

            {/* Dropdown Menu */}
            {menuOpen && (
              <div className="absolute right-0 mt-1.5 w-56 bg-white rounded-xl border border-slate-200 shadow-xl z-50 py-1.5 text-left animate-in fade-in duration-100">
                <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Copy Options
                </div>

                <div className="py-1">
                  <button
                    type="button"
                    onClick={() => handleCopy('current', false)}
                    className="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 flex items-center justify-between cursor-pointer"
                  >
                    <span className="font-semibold text-slate-800">Current Range</span>
                    <span className="text-[10px] text-slate-400">Clean</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleCopy('current', true)}
                    className="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 flex items-center justify-between cursor-pointer"
                  >
                    <span className="font-semibold text-slate-800">Current Range</span>
                    <span className="text-[10px] text-indigo-600 font-mono">+ Timestamps</span>
                  </button>
                </div>

                <div className="border-t border-slate-100 py-1">
                  <button
                    type="button"
                    onClick={() => handleCopy('full', false)}
                    disabled={loadingFull}
                    className="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 flex items-center justify-between cursor-pointer"
                  >
                    <span className="font-semibold text-slate-800 flex items-center gap-1">
                      <FileText className="w-3 h-3 text-slate-400" />
                      <span>Full Script</span>
                    </span>
                    <span className="text-[10px] text-slate-400">Canonical</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleCopy('full', true)}
                    disabled={loadingFull}
                    className="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 flex items-center justify-between cursor-pointer"
                  >
                    <span className="font-semibold text-slate-800 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>Full Script</span>
                    </span>
                    <span className="text-[10px] text-indigo-600 font-mono">+ Timestamps</span>
                  </button>
                </div>

                {loadingFull && (
                  <div className="px-3 py-1 text-[10px] text-indigo-600 bg-indigo-50 font-medium text-center">
                    Fetching full script...
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ROW 2: Thumbnail + Creator + Language + Source + Total Duration on Right */}
      <div className="flex items-center justify-between gap-2 text-[10px] text-slate-600">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {video.thumbnail_url ? (
            <img 
              src={video.thumbnail_url} 
              alt="" 
              className="w-7 h-5 object-cover rounded border border-slate-200 shrink-0 bg-slate-200"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          ) : (
            <div className="w-7 h-5 rounded bg-slate-200 border border-slate-300 flex items-center justify-center shrink-0">
              <Film className="w-3 h-3 text-slate-500" />
            </div>
          )}

          <span className="font-semibold text-slate-700 truncate max-w-[110px]" title={video.creator_name || video.platform}>
            {video.creator_name || video.platform}
          </span>

          {video.actual_transcript_language && (
            <span className="px-1 py-0.2 rounded bg-indigo-50 text-indigo-900 font-bold border border-indigo-200 uppercase tracking-wider text-[9px] shrink-0">
              {video.actual_transcript_language}
            </span>
          )}

          {video.transcript_source && (
            <span className="text-slate-400 truncate max-w-[90px] text-[9px]" title={video.asr_model || video.transcript_source}>
              · {video.asr_model || video.transcript_source}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 font-mono text-[10px] text-slate-500 shrink-0">
          <Clock className="w-3 h-3 text-slate-400" />
          <span>{formatTime(video.duration_seconds)}</span>
        </div>
      </div>

      {/* ROW 3: Compact Effective Range Context */}
      <div className="px-2 py-1 rounded-lg bg-white/90 border border-slate-200 flex items-center justify-between text-[10px] shadow-2xs">
        <span className="text-slate-500 font-medium truncate max-w-[190px]" title={video.requested_range_label}>
          {video.requested_range_label}
        </span>
        <span className="font-mono font-bold text-slate-900 shrink-0">
          {effectiveRangeText}
        </span>
      </div>
    </div>
  );
}
