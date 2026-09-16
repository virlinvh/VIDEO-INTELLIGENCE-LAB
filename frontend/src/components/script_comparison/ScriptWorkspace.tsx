import { useState, useEffect, useCallback } from 'react';
import type { 
  SegmentRangeRequest, 
  SegmentComparisonResponse 
} from '../../types';
import { RangeControls } from './RangeControls';
import { HorizontalScriptDesk } from './HorizontalScriptDesk';
import { SelectedRangeMetricsSummary } from './SelectedRangeMetricsSummary';
import { useScriptScrollSync } from './useScriptScrollSync';
import type { TranscriptViewMode } from './TranscriptDocument';
import { ErrorBoundary } from '../ErrorBoundary';
import { RefreshCw, Info, AlertCircle } from 'lucide-react';

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

interface ScriptWorkspaceProps {
  selectedVideoIds: string[];
  palette: ColorTheme[];
  onOpenVideoDetail?: (videoId: string) => void;
}

export function ScriptWorkspace({
  selectedVideoIds,
  palette,
  onOpenVideoDetail
}: ScriptWorkspaceProps) {
  const [activeRange, setActiveRange] = useState<SegmentRangeRequest>({ type: 'ENTIRE' });
  const [activePreset, setActivePreset] = useState<string>('entire');
  const [segmentResponse, setSegmentResponse] = useState<SegmentComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Phase 5.3D.1: Workspace View Mode (Document vs Timestamps)
  const [viewMode, setViewMode] = useState<TranscriptViewMode>('document');

  // Phase 5.3C: Pin Reference State
  const [pinnedVideoId, setPinnedVideoId] = useState<string | null>(null);

  // Phase 5.3C: Normalized Relative Scroll Sync Hook
  const {
    scrollMode,
    setScrollMode,
    registerScrollContainer,
    handleScroll,
    resetScrollPositions
  } = useScriptScrollSync();

  // Auto-clear stale pinned reference if video was unselected from comparison
  useEffect(() => {
    if (pinnedVideoId && !selectedVideoIds.includes(pinnedVideoId)) {
      setPinnedVideoId(null);
    }
  }, [selectedVideoIds, pinnedVideoId]);

  const fetchSegments = useCallback(async (
    rangeReq: SegmentRangeRequest, 
    presetKey: string = 'custom'
  ) => {
    if (selectedVideoIds.length < 2) {
      setSegmentResponse(null);
      return;
    }
    setLoading(true);
    setError(null);
    setActivePreset(presetKey);
    setActiveRange(rangeReq);

    try {
      const res = await fetch('/api/v1/comparisons/segments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_ids: selectedVideoIds,
          range: rangeReq
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const rawDetail = errData.detail || errData.error?.message;
        const formattedMsg = rawDetail 
          ? `Unable to load Script Workspace — ${rawDetail}`
          : `Unable to load Script Workspace (HTTP ${res.status}: ${res.statusText || 'Request failed'})`;
        throw new Error(formattedMsg);
      }

      const data: SegmentComparisonResponse = await res.json();
      setSegmentResponse(data);
    } catch (err: any) {
      console.error('Segment query error:', err);
      setError(err.message || 'Failed to load script comparison segments.');
    } finally {
      setLoading(false);
    }
  }, [selectedVideoIds]);

  // Initial load or when selected video IDs change
  useEffect(() => {
    if (selectedVideoIds.length >= 2) {
      fetchSegments(activeRange, activePreset);
    } else {
      setSegmentResponse(null);
    }
  }, [selectedVideoIds]);

  const handleApplyRange = (range: SegmentRangeRequest, presetKey: string) => {
    resetScrollPositions();
    fetchSegments(range, presetKey);
  };

  const handleTogglePin = (videoId: string) => {
    setPinnedVideoId(current => (current === videoId ? null : videoId));
  };

  const handleViewModeChange = (mode: TranscriptViewMode) => {
    resetScrollPositions();
    setViewMode(mode);
  };

  if (selectedVideoIds.length < 2) {
    return (
      <div className="p-8 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
        <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h3 className="text-sm font-bold text-[#0f172a] mb-1">
          Select Videos to Compare
        </h3>
        <p className="text-xs text-[#64748b]">
          Please select at least 2 videos from your library to open the Script Comparison Desk.
        </p>
      </div>
    );
  }

  return (
    <ErrorBoundary fallbackTitle="Script Workspace Error" fallbackMessage="Could not load Script Comparison Workspace.">
      <div className="space-y-4">
        {/* Range Controls Bar */}
        <RangeControls
          onApplyRange={handleApplyRange}
          activePreset={activePreset}
          loading={loading}
        />

        {/* Loading Indicator */}
        {loading && (
          <div className="p-12 text-center bg-white rounded-2xl border-2 border-slate-200 shadow-xs">
            <RefreshCw className="w-7 h-7 text-indigo-600 animate-spin mx-auto mb-3" />
            <h4 className="text-xs font-black text-[#0f172a] uppercase tracking-wider mb-1">
              Extracting Multi-Video Transcripts
            </h4>
            <p className="text-xs text-[#64748b]">
              Resolving exact interval boundaries across {selectedVideoIds.length} video transcripts...
            </p>
          </div>
        )}

        {/* Error Alert */}
        {error && !loading && (
          <div className="p-4 rounded-xl bg-rose-50 border-2 border-rose-300 text-rose-900 text-xs font-medium flex items-center gap-2.5">
            <Info className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Selected Range Metrics Summary (Primary Comparison Analytics Surface) */}
        {segmentResponse && !loading && (
          <SelectedRangeMetricsSummary
            videos={segmentResponse.videos}
            palette={palette}
            hasMixedLanguages={segmentResponse.has_mixed_languages}
          />
        )}

        {/* Horizontal Comparison Desk with Document/Timestamp Views, Pin Reference & Scroll Sync */}
        {segmentResponse && !loading && (
          <HorizontalScriptDesk
            videos={segmentResponse.videos}
            palette={palette}
            pinnedVideoId={pinnedVideoId}
            onTogglePin={handleTogglePin}
            scrollMode={scrollMode}
            onChangeScrollMode={(mode) => setScrollMode(mode, pinnedVideoId)}
            viewMode={viewMode}
            onChangeViewMode={handleViewModeChange}
            registerScrollContainer={registerScrollContainer}
            onScroll={handleScroll}
            onOpenVideoDetail={onOpenVideoDetail}
          />
        )}
      </div>
    </ErrorBoundary>
  );
}
