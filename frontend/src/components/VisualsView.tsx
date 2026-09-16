import { useState, useEffect } from 'react';
import { 
  Video as VideoIcon, 
  Clock, 
  Layers, 
  Activity, 
  RefreshCw, 
  Maximize2, 
  X, 
  Check, 
  Copy, 
  FileText, 
  Zap,
  Sliders
} from 'lucide-react';
import type { VisualMetricsData, FrameData } from '../types';

interface Props {
  videoId: string;
}

export function VisualsView({ videoId }: Props) {
  const [metrics, setMetrics] = useState<VisualMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keepMedia, setKeepMedia] = useState(false);
  const [selectedFrame, setSelectedFrame] = useState<FrameData | null>(null);
  const [segmentSortOrder, setSegmentSortOrder] = useState<'asc' | 'desc'>('asc');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    loadVisualMetrics();
  }, [videoId]);

  async function loadVisualMetrics() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/videos/${videoId}/visual-metrics`);
      if (res.status === 404) {
        // No visual analysis run yet
        setMetrics(null);
      } else if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to load visual metrics');
      } else {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAnalysis() {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/videos/${videoId}/visual-analysis?keep_media=${keepMedia}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Visual analysis execution failed');
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    const millis = Math.floor((secs % 1) * 10);
    return `${mins}:${remainingSecs.toString().padStart(2, '0')}.${millis}`;
  };

  const handleCopy = (text: string, key: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3 rounded-2xl bg-white border-2 border-slate-300 shadow-xs max-w-4xl mx-auto p-8">
        <RefreshCw className="w-8 h-8 text-amber-600 animate-spin mx-auto" />
        <p className="text-sm font-bold text-[#0f172a]">Loading visual intelligence record...</p>
        <p className="text-xs text-[#475569]">Checking boundary detections, frame galleries, and technical video properties.</p>
      </div>
    );
  }

  // Not yet analyzed state
  if (!metrics && !analyzing) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto py-8">
        <div className="p-8 rounded-2xl bg-white border-2 border-slate-300 shadow-sm text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto border border-amber-300 shadow-xs">
            <VideoIcon className="w-7 h-7 text-amber-700" />
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <h3 className="text-base font-black text-[#0f172a] tracking-tight">Deterministic Visual Video Analysis</h3>
            <p className="text-xs text-slate-700 font-semibold leading-relaxed">
              Detect visual boundaries, inspect technical video properties, extract representative frames, and chart visual change activity over time.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200 max-w-lg mx-auto text-left space-y-2 text-xs">
            <div className="flex items-center gap-2 font-bold text-amber-950">
              <Zap className="w-4 h-4 text-amber-700 shrink-0" />
              <span>Strict Bounded Media Lifecycle</span>
            </div>
            <p className="text-amber-900/90 text-[11px] leading-relaxed">
              By default, temporary analysis media is acquired in <code className="font-mono bg-amber-100 px-1 py-0.5 rounded text-amber-950">storage/temp/</code> and completely purged upon completion. Only derived evidence frames are retained.
            </p>

            <label className="flex items-center gap-2 pt-2 text-[#0f172a] font-bold cursor-pointer select-none border-t border-amber-200/60">
              <input
                type="checkbox"
                checked={keepMedia}
                onChange={(e) => setKeepMedia(e.target.checked)}
                className="rounded border-slate-400 text-amber-600 focus:ring-amber-600"
              />
              <span className="text-[11px]">Keep Permanent Video Source Copy in Library (Analyze + Keep)</span>
            </label>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 font-semibold max-w-lg mx-auto">
              {error}
            </div>
          )}

          <button
            onClick={handleStartAnalysis}
            className="px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-black transition-all shadow-md hover:shadow-lg cursor-pointer flex items-center gap-2 mx-auto"
          >
            <VideoIcon className="w-4 h-4" />
            Start Visual Analysis
          </button>
        </div>
      </div>
    );
  }

  // Analyzing in progress
  if (analyzing) {
    return (
      <div className="py-20 text-center space-y-4 rounded-2xl bg-white border-2 border-slate-300 shadow-sm max-w-4xl mx-auto p-8">
        <RefreshCw className="w-10 h-10 text-amber-600 animate-spin mx-auto" />
        <div className="space-y-1">
          <h4 className="text-base font-black text-[#0f172a]">Executing Deterministic Visual Analysis</h4>
          <p className="text-xs text-slate-700 font-semibold max-w-md mx-auto">
            Acquiring analysis stream, running FFprobe technical inspection, detecting visual boundaries with FFmpeg, and extracting representative evidence frames.
          </p>
        </div>
        <div className="inline-block px-3 py-1 rounded-full bg-amber-100 text-amber-950 text-xs font-mono font-bold border border-amber-300">
          Bounded Concurrency: 1 Worker Active
        </div>
      </div>
    );
  }

  if (!metrics) return null;

  const tech = metrics.technical_properties || {};
  const maxActivity = metrics.visual_activity_timeline?.length > 0
    ? Math.max(...metrics.visual_activity_timeline.map(w => w.boundary_count), 1)
    : 1;

  const distEntries = Object.entries(metrics.segment_duration_distribution || {});
  const maxDistVal = distEntries.length > 0 ? Math.max(...distEntries.map(([_, c]) => c)) : 1;

  const sortedSegments = [...(metrics.visual_segments || [])].sort((a, b) => 
    segmentSortOrder === 'asc' ? a.sequence - b.sequence : b.sequence - a.sequence
  );

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Top Action & Version Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-amber-50/80 border-2 border-amber-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-600 text-white flex items-center justify-center font-bold shadow-xs">
            <VideoIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-black text-amber-950 tracking-tight flex items-center gap-2">
              Deterministic Visual Intelligence
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-200/80 text-amber-900 border border-amber-300">
                v{metrics.algorithm_version}
              </span>
            </h3>
            <p className="text-xs text-amber-900/80 font-medium">
              FFmpeg scene threshold: {metrics.scene_threshold} • Analyzed {new Date(metrics.analyzed_at).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <button
          onClick={handleStartAnalysis}
          disabled={analyzing}
          className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-amber-100/60 text-amber-950 border border-amber-300 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-amber-700 ${analyzing ? 'animate-spin' : ''}`} />
          {analyzing ? 'Processing...' : 'Reanalyze Visuals'}
        </button>
      </div>

      {/* 1. VISUAL SNAPSHOT */}
      <section className="space-y-3">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-700" />
          1. Visual Snapshot
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Visual Segments</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.scene_count}</p>
            <p className="text-[11px] text-slate-700 font-semibold">{metrics.scene_timestamps.length} detected boundaries</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Visual Change Rate</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.scene_change_frequency} <span className="text-xs font-bold text-slate-700">/ min</span></p>
            <p className="text-[11px] text-slate-700 font-semibold">Average pacing</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Avg Segment Length</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.avg_scene_duration}s</p>
            <p className="text-[11px] text-slate-700 font-semibold">Median: {metrics.median_scene_duration}s</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Evidence Frames</span>
            <p className="text-2xl font-black text-amber-950">{metrics.frames?.length || 0}</p>
            <p className="text-[11px] text-slate-700 font-semibold">Bounded at max 50</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Shortest Segment</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.shortest_scene_duration}s</p>
            <p className="text-[11px] text-slate-700 font-semibold">Minimum duration</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Longest Segment</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.longest_scene_duration}s</p>
            <p className="text-[11px] text-slate-700 font-semibold">Continuous shot</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Resolution</span>
            <p className="text-lg font-black text-[#0f172a] truncate">{tech.width ? `${tech.width}x${tech.height}` : 'Unavailable'}</p>
            <p className="text-[11px] text-slate-700 font-semibold">DAR: {tech.aspect_ratio || 'N/A'}</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Frame Rate & Codec</span>
            <p className="text-lg font-black text-[#0f172a] truncate">{tech.frame_rate ? `${tech.frame_rate} FPS` : 'Unavailable'}</p>
            <p className="text-[11px] text-slate-700 font-semibold">{tech.video_codec || 'N/A'}</p>
          </div>
        </div>
      </section>

      {/* 2. VISUAL CHANGE ACTIVITY TIMELINE */}
      <section className="space-y-3 bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-700" />
              2. Visual Change Activity Timeline
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Discrete visual boundary frequency over continuous intervals
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-700 font-bold">Total Changes:</span>
            <span className="ml-2 px-2.5 py-1 rounded bg-amber-100 text-amber-950 font-black text-xs border border-amber-300">
              {metrics.scene_timestamps.length}
            </span>
          </div>
        </div>

        {/* Visual Activity Bar Chart */}
        <div className="space-y-2 pt-4">
          <div className="h-36 w-full flex items-end gap-1.5 p-3 bg-slate-50 rounded-xl border border-slate-200 overflow-x-auto">
            {metrics.visual_activity_timeline.map((win) => {
              const heightPct = Math.max(8, Math.round((win.boundary_count / (maxActivity * 1.15)) * 100));
              return (
                <div 
                  key={win.window_index} 
                  className="flex-1 min-w-[36px] flex flex-col items-center gap-1 group relative h-full justify-end"
                >
                  {/* Tooltip */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-2 bg-[#0f172a] text-white text-[10px] p-2 rounded-lg pointer-events-none z-20 whitespace-nowrap shadow-xl border border-slate-700">
                    <p className="font-bold">{formatTime(win.start_time)} - {formatTime(win.end_time)}</p>
                    <p className="text-amber-300 font-bold">{win.boundary_count} visual change(s)</p>
                    <p className="text-slate-300 font-semibold">{win.change_density} changes/min</p>
                  </div>

                  <div 
                    style={{ height: `${heightPct}%` }}
                    className="w-full rounded-t-md bg-amber-500 group-hover:bg-amber-600 transition-all"
                  />
                  <span className="text-[9px] font-mono text-slate-700 font-bold select-none">
                    {Math.round(win.start_time)}s
                  </span>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-700 text-right font-semibold">Hover bars for detailed interval change counts</p>
        </div>
      </section>

      {/* 3. SEGMENT DURATION DISTRIBUTION */}
      <section className="space-y-4 bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm">
        <div>
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-700" />
            3. Segment Duration Distribution
          </h4>
          <p className="text-xs text-slate-700 font-semibold mt-0.5">
            Histogram of continuous visual shot durations across time buckets
          </p>
        </div>

        <div className="space-y-2 pt-2">
          {distEntries.map(([bucket, count]) => {
            const widthPct = Math.max(4, Math.round((count / maxDistVal) * 100));
            return (
              <div key={bucket} className="flex items-center gap-3 text-xs">
                <span className="w-16 font-mono font-bold text-slate-700 text-right">{bucket}</span>
                <div className="flex-1 bg-slate-100 rounded-lg h-6 overflow-hidden p-0.5 border border-slate-200">
                  <div 
                    style={{ width: `${widthPct}%` }}
                    className="bg-amber-600 h-full rounded-md transition-all flex items-center justify-end pr-2 text-white font-bold text-[10px]"
                  >
                    {count > 0 && count}
                  </div>
                </div>
                <span className="w-10 font-mono text-slate-700 font-bold">{count}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. REPRESENTATIVE FRAME EVIDENCE GALLERY */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Maximize2 className="w-4 h-4 text-amber-700" />
              4. Representative Frame Gallery
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Deterministic midpoint frame extractions for visual change segments
            </p>
          </div>
          <span className="px-2.5 py-1 rounded bg-amber-100 text-amber-950 font-bold text-xs border border-amber-300">
            {metrics.frames?.length || 0} Frames
          </span>
        </div>

        {(!metrics.frames || metrics.frames.length === 0) ? (
          <p className="text-xs text-slate-400 italic py-4 text-center">No representative frames extracted.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {metrics.frames.map((frame) => (
              <div
                key={frame.id}
                onClick={() => setSelectedFrame(frame)}
                className="group relative rounded-xl border-2 border-slate-300 overflow-hidden bg-slate-900 cursor-pointer shadow-2xs hover:border-amber-500 hover:shadow-md transition-all"
              >
                <img
                  src={frame.image_url}
                  alt={`Frame at ${frame.timestamp}s`}
                  className="w-full aspect-video object-cover group-hover:scale-105 transition-transform duration-200"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-90 p-2.5 flex flex-col justify-between">
                  <span className="self-end px-1.5 py-0.5 rounded bg-black/60 text-white font-mono text-[10px] font-bold backdrop-blur-xs">
                    #{frame.frame_number}
                  </span>
                  <div className="flex items-center justify-between text-white text-[11px] font-mono font-bold">
                    <span>{formatTime(frame.timestamp)}</span>
                    <Maximize2 className="w-3.5 h-3.5 text-amber-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 5. VISUAL SEGMENT TABLE */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-amber-700" />
              5. Visual Segment Evidence Table
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Exact timestamp intervals of continuous visual shots
            </p>
          </div>
          <button
            onClick={() => setSegmentSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
            className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-bold border border-slate-300 cursor-pointer"
          >
            Sort Sequence: {segmentSortOrder === 'asc' ? 'Ascending (1 → N)' : 'Descending (N → 1)'}
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b-2 border-slate-200 text-slate-700 bg-slate-50 font-bold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Seq</th>
                <th className="py-2.5 px-3">Start Time</th>
                <th className="py-2.5 px-3">End Time</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Segment Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {sortedSegments.map((seg) => (
                <tr key={seg.sequence} className="hover:bg-amber-50/40 transition-colors">
                  <td className="py-2 px-3 font-mono font-bold text-slate-900">#{seg.sequence}</td>
                  <td className="py-2 px-3 font-mono text-cyan-900 font-bold">{formatTime(seg.start_time)}</td>
                  <td className="py-2 px-3 font-mono text-cyan-900 font-bold">{formatTime(seg.end_time)}</td>
                  <td className="py-2 px-3 font-mono text-[#0f172a] font-extrabold">{seg.duration}s</td>
                  <td className="py-2 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200">
                      Continuous Shot
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 6. OCR / ON-SCREEN TEXT EVIDENCE */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <FileText className="w-4 h-4 text-amber-700" />
              6. Detected On-Screen Text (OCR Evidence)
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Deterministic optical character recognition on evidence frames
            </p>
          </div>
          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 font-bold text-xs border border-slate-200">
            {metrics.ocr_available ? 'Active' : 'Optional Capability Unavailable'}
          </span>
        </div>

        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
          <p className="font-bold text-[#0f172a]">OCR Status: No local Tesseract OCR engine configured.</p>
          <p className="text-[11px] leading-relaxed">
            Deterministic on-screen text recognition is an optional capability that operates when local Tesseract is present. In accordance with zero-dependency rules, no models or large OCR engines were silently downloaded.
          </p>
        </div>
      </section>

      {/* LIGHTBOX MODAL FOR ENLARGED EVIDENCE FRAME */}
      {selectedFrame && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-150">
          <div className="bg-white border-2 border-slate-300 rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded bg-amber-600 text-white font-mono text-xs font-bold">
                  Frame #{selectedFrame.frame_number}
                </span>
                <span className="text-xs font-mono font-bold text-[#0f172a]">
                  Timestamp: {formatTime(selectedFrame.timestamp)} ({selectedFrame.timestamp}s)
                </span>
              </div>
              <button
                onClick={() => setSelectedFrame(null)}
                className="p-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-800 cursor-pointer border border-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 bg-black flex items-center justify-center overflow-hidden flex-1">
              <img
                src={selectedFrame.image_url}
                alt={`Frame #${selectedFrame.frame_number}`}
                className="max-h-[65vh] w-auto object-contain rounded"
              />
            </div>

            <div className="p-4 bg-white border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-4 text-slate-700 font-semibold font-mono text-[11px]">
                <span>Dimensions: {selectedFrame.width}x{selectedFrame.height}</span>
                <span>Size: {(selectedFrame.file_size_bytes / 1024).toFixed(1)} KB</span>
                <span>Type: {selectedFrame.frame_type}</span>
              </div>

              <button
                onClick={() => handleCopy(selectedFrame.file_path, 'frame_path')}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg font-bold transition-colors cursor-pointer border border-slate-300"
              >
                {copiedKey === 'frame_path' ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedKey === 'frame_path' ? 'Copied Path' : 'Copy File Path'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
