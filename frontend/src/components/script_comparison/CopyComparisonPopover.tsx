import { useState, useRef, useEffect } from 'react';
import type { VideoSegmentComparisonItem } from '../../types';
import { 
  formatMultiVideoClean, 
  formatMultiVideoResearch, 
  type ComparisonCopyOptions 
} from './scriptCopyFormatters';
import { Copy, Check, ChevronDown, FileText, Sparkles, Sliders, Clock, Info } from 'lucide-react';

interface CopyComparisonPopoverProps {
  videos: VideoSegmentComparisonItem[];
  pinnedVideoId?: string | null;
}

export function CopyComparisonPopover({
  videos,
  pinnedVideoId
}: CopyComparisonPopoverProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [loadingFull, setLoadingFull] = useState<boolean>(false);
  const [copiedSummary, setCopiedSummary] = useState<string | null>(null);

  // Configuration state
  const [scope, setScope] = useState<'current_range' | 'full_scripts'>('current_range');
  const [format, setFormat] = useState<'clean' | 'research'>('clean');
  const [includeTimestamps, setIncludeTimestamps] = useState<boolean>(false);
  const [includeMetrics, setIncludeMetrics] = useState<boolean>(true);
  const [showAll12Metrics, setShowAll12Metrics] = useState<boolean>(false);

  const popoverRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [popoverStyle, setPopoverStyle] = useState<React.CSSProperties>({});

  // Viewport-aware position calculation
  useEffect(() => {
    if (!isOpen) return;

    const updatePosition = () => {
      if (!popoverRef.current) return;
      const triggerRect = popoverRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const desiredWidth = Math.min(380, viewportWidth - 32);

      // Anchor left edge of popover to left edge of trigger button (left: 0)
      let offsetLeft = 0;

      // If expanding rightward would overflow the viewport, shift left
      if (triggerRect.left + desiredWidth > viewportWidth - 16) {
        const overflow = (triggerRect.left + desiredWidth) - (viewportWidth - 16);
        offsetLeft = -overflow;
      }

      // Ensure left edge never goes offscreen or behind fixed sidebar
      if (triggerRect.left + offsetLeft < 16) {
        offsetLeft = 16 - triggerRect.left;
      }

      setPopoverStyle({
        left: `${offsetLeft}px`,
        width: `${desiredWidth}px`,
        maxWidth: `calc(100vw - 32px)`,
        maxHeight: `min(560px, calc(100vh - 120px))`
      });
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    return () => window.removeEventListener('resize', updatePosition);
  }, [isOpen]);

  // Close on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleCopy = async () => {
    try {
      let targetVideos = videos;

      // If full_scripts is requested and current range is not entire
      if (scope === 'full_scripts') {
        const isAlreadyEntire = videos.every(v => v.requested_range_label === 'Entire Video');
        if (!isAlreadyEntire) {
          setLoadingFull(true);
          const res = await fetch('/api/v1/comparisons/segments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              video_ids: videos.map(v => v.video_id),
              range: { type: 'ENTIRE' }
            })
          });
          if (res.ok) {
            const data = await res.json();
            if (data && data.videos) {
              targetVideos = data.videos;
            }
          }
        }
      }

      const options: ComparisonCopyOptions = {
        scope,
        format,
        includeTimestamps,
        includeMetrics: scope === 'current_range' ? includeMetrics : false,
        pinnedVideoId,
        showAll12Metrics
      };

      let formattedText = '';
      if (format === 'clean') {
        formattedText = formatMultiVideoClean(targetVideos, {
          includeTimestamps,
          pinnedVideoId
        });
      } else {
        formattedText = formatMultiVideoResearch(targetVideos, options);
      }

      await navigator.clipboard.writeText(formattedText);
      setCopied(true);
      const lines = formattedText.split('\n').length;
      setCopiedSummary(`${targetVideos.length} scripts (${lines} lines, ${formattedText.length.toLocaleString()} chars) copied`);
      
      setTimeout(() => {
        setCopied(false);
        setCopiedSummary(null);
        setIsOpen(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy comparison:', err);
    } finally {
      setLoadingFull(false);
    }
  };

  return (
    <div className="relative inline-block" ref={popoverRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`px-3 py-1.5 rounded-xl text-xs font-bold inline-flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs ${
          isOpen
            ? 'bg-indigo-700 text-white'
            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
        }`}
        title="Copy multiple video scripts or research report"
        aria-label="Open comparison export options"
      >
        <Copy className="w-3.5 h-3.5" />
        <span>Copy Comparison</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div 
          ref={dropdownRef}
          style={popoverStyle}
          className="absolute top-full mt-2 bg-white rounded-2xl border-2 border-slate-200 shadow-2xl z-50 p-4 space-y-3.5 animate-in fade-in zoom-in-95 duration-100 overflow-y-auto"
        >
          {/* Header Row */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-indigo-600" />
              <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider">
                Copy Comparison Scripts
              </h4>
            </div>
            <span className="text-[10px] font-mono text-slate-500 font-semibold bg-slate-100 px-2 py-0.5 rounded-md">
              {videos.length} Videos
            </span>
          </div>

          {/* Scope Selector */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-700 block">
              Comparison Scope
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setScope('current_range')}
                className={`px-2.5 py-2 rounded-xl text-xs font-semibold border text-left transition-all cursor-pointer ${
                  scope === 'current_range'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-bold shadow-2xs'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                  <span className="truncate">Current Range</span>
                </div>
                <div className="text-[10px] text-slate-500 truncate mt-0.5" title={videos[0]?.requested_range_label || 'Selected interval'}>
                  {videos[0]?.requested_range_label || 'Selected interval'}
                </div>
              </button>

              <button
                type="button"
                onClick={() => setScope('full_scripts')}
                className={`px-2.5 py-2 rounded-xl text-xs font-semibold border text-left transition-all cursor-pointer ${
                  scope === 'full_scripts'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-bold shadow-2xs'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                  <span>Full Scripts</span>
                </div>
                <div className="text-[10px] text-slate-500 truncate mt-0.5">
                  Entire transcripts
                </div>
              </button>
            </div>
          </div>

          {/* Format Selector */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-700 block">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setFormat('clean')}
                className={`px-2.5 py-2 rounded-xl text-xs font-semibold border text-left transition-all cursor-pointer ${
                  format === 'clean'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-bold shadow-2xs'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <span className="block font-bold">Clean Scripts</span>
                <span className="text-[10px] text-slate-500 block leading-tight mt-0.5">
                  Separated readable scripts
                </span>
              </button>

              <button
                type="button"
                onClick={() => setFormat('research')}
                className={`px-2.5 py-2 rounded-xl text-xs font-semibold border text-left transition-all cursor-pointer ${
                  format === 'research'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-bold shadow-2xs'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <span className="block font-bold">Research Report</span>
                <span className="text-[10px] text-slate-500 block leading-tight mt-0.5">
                  Structured metadata & report
                </span>
              </button>
            </div>
          </div>

          {/* Options Toggles */}
          <div className="space-y-2 pt-1 border-t border-slate-100">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeTimestamps}
                onChange={(e) => setIncludeTimestamps(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
              />
              <span>Include Segment Timestamps (<code className="text-[10px] font-mono text-slate-500">[MM:SS]</code>)</span>
            </label>

            {format === 'research' && (
              <div className="space-y-1.5 pl-0.5">
                <label className={`flex items-center gap-2 text-xs font-medium select-none ${
                  scope === 'full_scripts' ? 'text-slate-400 cursor-not-allowed' : 'text-slate-700 cursor-pointer'
                }`}>
                  <input
                    type="checkbox"
                    disabled={scope === 'full_scripts'}
                    checked={scope === 'current_range' && includeMetrics}
                    onChange={(e) => setIncludeMetrics(e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer disabled:cursor-not-allowed"
                  />
                  <span>Include Selected Range Metrics Summary</span>
                </label>

                {scope === 'full_scripts' && (
                  <p className="text-[10px] text-slate-400 pl-6 flex items-center gap-1">
                    <Info className="w-3 h-3 shrink-0" />
                    <span>Range metrics are omitted for full script exports.</span>
                  </p>
                )}

                {scope === 'current_range' && includeMetrics && (
                  <div className="pl-6 pt-1">
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-600 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={showAll12Metrics}
                        onChange={(e) => setShowAll12Metrics(e.target.checked)}
                        className="w-3.5 h-3.5 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
                      />
                      <span className="flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-indigo-500" />
                        <span>Include All 12 Metrics (vs Core 5)</span>
                      </span>
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Button & Feedback */}
          <div className="pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={handleCopy}
              disabled={loadingFull || copied}
              className={`w-full py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 transition-all cursor-pointer shadow-xs ${
                copied
                  ? 'bg-emerald-600 text-white'
                  : loadingFull
                  ? 'bg-indigo-400 text-white cursor-wait'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white active:scale-[0.99]'
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 stroke-[3]" />
                  <span>Copied to Clipboard!</span>
                </>
              ) : loadingFull ? (
                <span>Fetching Full Transcripts...</span>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copy {videos.length} Scripts ({scope === 'full_scripts' ? 'Full' : 'Range'})</span>
                </>
              )}
            </button>

            {copiedSummary && (
              <p className="text-[10px] text-emerald-700 font-semibold text-center mt-1.5">
                ✓ {copiedSummary}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
