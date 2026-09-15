import { useState, useEffect } from 'react';
import { 
  X, 
  FileText, 
  BarChart2, 
  Video as VideoIcon, 
  Info, 
  Code, 
  Copy, 
  Check, 
  Search, 
  Clock, 
  Eye, 
  ThumbsUp, 
  MessageSquare,
  RefreshCw,
  Headphones
} from 'lucide-react';
import type { VideoDetail, TranscriptData } from '../types';
import { ScriptStatsView } from './ScriptStatsView';
import { VisualsView } from './VisualsView';

interface Props {
  videoId: string;
  onClose: () => void;
}

export function VideoDetailModal({ videoId, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'transcript' | 'stats' | 'visuals' | 'metadata' | 'raw'>('overview');
  const [video, setVideo] = useState<VideoDetail | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [rawData, setRawData] = useState<any>(null);
  const [transcriptSearch, setTranscriptSearch] = useState('');
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retranscribing, setRetranscribing] = useState(false);
  const [retranscribeStep, setRetranscribeStep] = useState<string>('');
  const [retranscribeLang, setRetranscribeLang] = useState('en');
  const [retranscribeError, setRetranscribeError] = useState<{ code: string; message: string; retryable?: boolean; details?: any } | null>(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);

  const loadData = async () => {
    try {
      const [vRes, tRes, rRes] = await Promise.all([
        fetch(`/api/v1/videos/${videoId}`).then(r => r.ok ? r.json() : null),
        fetch(`/api/v1/videos/${videoId}/transcript`).then(r => r.ok ? r.json() : null),
        fetch(`/api/v1/videos/${videoId}/raw`).then(r => r.ok ? r.json() : null),
      ]);
      setVideo(vRes);
      setTranscript(tRes);
      setRawData(rRes);
    } catch (err) {
      console.error('Failed to load video details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [videoId]);

  const handleRetranscribe = async () => {
    setRetranscribing(true);
    setRetranscribeError(null);
    setRetranscribeStep('Enqueuing retranscription job...');

    try {
      const initRes = await fetch(`/api/v1/videos/${videoId}/retranscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: retranscribeLang })
      });

      if (!initRes.ok) {
        let errJson: any = null;
        try { errJson = await initRes.json(); } catch {}
        const errObj = errJson?.error || {};
        throw {
          code: errObj.code || 'RETRANSCRIBE_INIT_FAILED',
          message: errObj.message || errJson?.detail || 'Failed to start retranscription job',
          retryable: true,
          details: errObj.details
        };
      }

      const jobInit = await initRes.json();
      const jobId = jobInit.job_id;

      // Poll background job until complete or failed
      let done = false;
      while (!done) {
        await new Promise(r => setTimeout(r, 1200));
        const jobRes = await fetch(`/api/v1/jobs/${jobId}`);
        if (!jobRes.ok) continue;
        const jobData = await jobRes.json();

        setRetranscribeStep(jobData.current_step || 'Processing...');

        if (jobData.state === 'COMPLETED' || jobData.state === 'COMPLETED_WITH_WARNINGS') {
          done = true;
          await loadData();
          break;
        } else if (jobData.state === 'FAILED' || jobData.state === 'CANCELLED') {
          done = true;
          const errObj = jobData.error_details || {};
          throw {
            code: errObj.code || 'RETRANSCRIBE_FAILED',
            message: errObj.message || 'Retranscription job failed',
            retryable: errObj.retryable !== false,
            details: errObj.details
          };
        }
      }
    } catch (e: any) {
      setRetranscribeError({
        code: e.code || 'ERROR',
        message: e.message || 'An unexpected error occurred during retranscription.',
        retryable: e.retryable !== false,
        details: e.details
      });
    } finally {
      setRetranscribing(false);
      setRetranscribeStep('');
    }
  };

  const handleCopyTranscript = () => {
    if (!transcript) return;
    navigator.clipboard.writeText(transcript.full_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs.toString().padStart(2, '0')}`;
  };

  const filteredSegments = transcript?.segments.filter(s => 
    s.text.toLowerCase().includes(transcriptSearch.toLowerCase())
  ) || [];

  if (loading) {
    return (
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-white p-6 rounded-2xl shadow-xl text-[#0f172a] text-sm font-bold border border-slate-300">
          Loading video intelligence record...
        </div>
      </div>
    );
  }

  if (!video) return null;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Info, color: 'text-indigo-600' },
    { id: 'transcript', label: `Transcript ${transcript ? `(${transcript.segment_count})` : ''}`, icon: FileText, color: 'text-cyan-700' },
    { id: 'stats', label: 'Script Stats', icon: BarChart2, color: 'text-purple-600' },
    { id: 'visuals', label: 'Visuals', icon: VideoIcon, color: 'text-amber-600' },
    { id: 'metadata', label: 'Metadata', icon: Info, color: 'text-blue-600' },
    { id: 'raw', label: 'Raw Data', icon: Code, color: 'text-slate-700' },
  ] as const;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 sm:p-6 md:p-8 animate-in fade-in duration-150">
      <div className="w-full max-w-5xl h-[92vh] bg-white border-2 border-slate-300 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-200 flex items-start justify-between gap-4 bg-[#f8fafc]">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                video.platform === 'youtube' ? 'bg-red-600 text-white' : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
              }`}>
                {video.platform}
              </span>
              <span className="text-xs text-[#334155] font-mono font-bold">{video.platform_video_id}</span>
            </div>
            <h2 className="text-lg font-black text-[#0f172a] line-clamp-1 tracking-tight">{video.title}</h2>
            <p className="text-xs text-[#334155] font-semibold">
              by <strong className="text-[#0f172a] font-bold">{video.creator?.name || 'Unknown Creator'}</strong> • Duration: {formatTime(video.duration_seconds)}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-200 hover:bg-slate-300 text-[#0f172a] transition-colors cursor-pointer border border-slate-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 border-b border-slate-300 bg-white flex gap-2 overflow-x-auto">
          {tabs.map(t => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3.5 text-xs font-bold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                  isActive 
                    ? 'border-indigo-600 text-indigo-900 bg-indigo-50/70' 
                    : 'border-transparent text-[#475569] hover:text-[#0f172a] hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? t.color : 'text-slate-500'}`} />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#f1f5f9]">
          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              {/* Metric Highlights */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-2xs">
                  <p className="text-[11px] uppercase font-bold text-[#475569]">Views</p>
                  <p className="text-2xl font-black text-[#0f172a] mt-1 flex items-center gap-2">
                    <Eye className="w-5 h-5 text-blue-600" />
                    {video.view_count ? Number(video.view_count).toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-2xs">
                  <p className="text-[11px] uppercase font-bold text-[#475569]">Likes</p>
                  <p className="text-2xl font-black text-[#0f172a] mt-1 flex items-center gap-2">
                    <ThumbsUp className="w-5 h-5 text-rose-600" />
                    {video.like_count ? Number(video.like_count).toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-2xs">
                  <p className="text-[11px] uppercase font-bold text-[#475569]">Comments</p>
                  <p className="text-2xl font-black text-[#0f172a] mt-1 flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-purple-600" />
                    {video.comment_count ? Number(video.comment_count).toLocaleString() : 'N/A'}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-2xs">
                  <p className="text-[11px] uppercase font-bold text-[#475569]">Duration</p>
                  <p className="text-2xl font-black text-[#0f172a] mt-1 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-amber-600" />
                    {formatTime(video.duration_seconds)}
                  </p>
                </div>
              </div>

              {/* Description */}
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-2xs space-y-3">
                <h3 className="text-xs font-black text-[#0f172a] uppercase tracking-wider">Video Description</h3>
                <p className="text-sm text-[#1e293b] whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto font-normal">
                  {video.description || 'No description provided.'}
                </p>
              </div>

              {/* Chapters */}
              {video.chapters && video.chapters.length > 0 && (
                <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-2xs space-y-3">
                  <h3 className="text-xs font-black text-[#0f172a] uppercase tracking-wider">Chapters</h3>
                  <div className="space-y-2">
                    {video.chapters.map((ch, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs py-2.5 px-4 rounded-lg bg-[#f8fafc] border border-slate-300 font-semibold">
                        <span className="text-[#0f172a]">{ch.title}</span>
                        <span className="font-mono text-indigo-700 font-bold">{formatTime(ch.start_time)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TRANSCRIPT TAB (16px High-Contrast Document Reader) */}
          {activeTab === 'transcript' && (
            <div className="space-y-4 max-w-4xl mx-auto">
              {/* Provenance & Retranscribe Header */}
              {transcript && (
                <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-cyan-50 border border-cyan-200 text-cyan-800">
                      <Headphones className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold text-[#0f172a] uppercase">Language:</span>
                        <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-indigo-100 text-indigo-950 border border-indigo-300">
                          {transcript.language === 'ta' ? 'Tamil (ta)' : transcript.language === 'ml' ? 'Malayalam (ml)' : 'English (en)'}
                        </span>
                        <span className="text-xs font-bold text-[#0f172a] uppercase ml-1">Source:</span>
                        <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-cyan-100 text-cyan-950 border border-cyan-300">
                          {transcript.caption_source || (transcript.source_type === 'local_asr' ? 'Local ASR' : transcript.source_type)}
                        </span>
                        {transcript.asr_model && (
                          <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold bg-purple-50 text-purple-900 border border-purple-200">
                            Model: {transcript.asr_model}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#475569] mt-1 font-medium">
                        {transcript.segment_count} segments · {transcript.full_text.split(/\s+/).filter(Boolean).length} words
                        {transcript.requested_language && (
                          <span className="ml-2 text-slate-500 font-normal">
                            (Requested: {transcript.requested_language.toUpperCase()})
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Retranscribe Control */}
                  <div className="flex items-center gap-2 self-start md:self-auto">
                    <select
                      value={retranscribeLang}
                      onChange={(e) => setRetranscribeLang(e.target.value)}
                      disabled={retranscribing}
                      className="px-2.5 py-1.5 rounded-lg bg-[#f8fafc] border border-slate-300 text-xs font-bold text-[#0f172a] cursor-pointer"
                    >
                      <option value="en">English (en)</option>
                      <option value="ta">Tamil (ta)</option>
                      <option value="ml">Malayalam (ml)</option>
                      <option value="auto">Auto Detect</option>
                    </select>

                    <button
                      onClick={handleRetranscribe}
                      disabled={retranscribing}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${retranscribing ? 'animate-spin' : ''}`} />
                      <span>{retranscribing ? (retranscribeStep || 'Transcribing...') : 'Retranscribe'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Live Retranscribing Progress Banner */}
              {retranscribing && (
                <div className="p-3.5 rounded-xl bg-cyan-50 border border-cyan-300 text-cyan-950 text-xs font-semibold flex items-center gap-2 shadow-2xs animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin text-cyan-700 shrink-0" />
                  <span>{retranscribeStep || 'Processing background retranscription...'}</span>
                </div>
              )}

              {/* Structured Error Banner */}
              {retranscribeError && (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-950 text-xs space-y-2 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-rose-900">Retranscription Failed:</span>
                      <span>{retranscribeError.message}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowErrorDetails(!showErrorDetails)}
                        className="text-[11px] font-bold text-rose-800 underline hover:text-rose-950 cursor-pointer"
                      >
                        {showErrorDetails ? 'Hide Details' : 'Technical Details'}
                      </button>
                      <button
                        onClick={handleRetranscribe}
                        className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-700 text-white font-bold text-[11px] cursor-pointer"
                      >
                        Retry
                      </button>
                    </div>
                  </div>

                  {showErrorDetails && (
                    <div className="p-3 rounded-lg bg-white border border-rose-200 text-slate-800 font-mono text-[11px] space-y-1">
                      <div><strong className="text-slate-600">Code:</strong> {retranscribeError.code}</div>
                      <div><strong className="text-slate-600">Retryable:</strong> {retranscribeError.retryable ? 'Yes' : 'No'}</div>
                      {retranscribeError.details && (
                        <div><strong className="text-slate-600">Details:</strong> {JSON.stringify(retranscribeError.details)}</div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {!transcript ? (
                <div className="py-16 text-center text-xs text-[#334155] space-y-4 bg-white rounded-2xl border border-slate-300 p-8 shadow-xs">
                  <FileText className="w-10 h-10 text-slate-400 mx-auto" />
                  <div>
                    <p className="text-sm font-bold text-[#0f172a]">No platform captions found</p>
                    <p className="text-xs text-[#475569] mt-1">You can generate a local transcript using the local transcription engine.</p>
                  </div>

                  <div className="flex items-center justify-center gap-2 pt-2">
                    <select
                      value={retranscribeLang}
                      onChange={(e) => setRetranscribeLang(e.target.value)}
                      disabled={retranscribing}
                      className="px-3 py-2 rounded-lg bg-[#f8fafc] border border-slate-300 text-xs font-bold text-[#0f172a] cursor-pointer"
                    >
                      <option value="en">English (en)</option>
                      <option value="ta">Tamil (ta)</option>
                      <option value="ml">Malayalam (ml)</option>
                      <option value="auto">Auto Detect</option>
                    </select>

                    <button
                      onClick={handleRetranscribe}
                      disabled={retranscribing}
                      className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${retranscribing ? 'animate-spin' : ''}`} />
                      <span>{retranscribing ? (retranscribeStep || 'Transcribing...') : 'Transcribe Video'}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Controls Toolbar */}
                  <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-xl bg-white border border-slate-300 shadow-2xs">
                    <div className="relative flex-1 min-w-[220px]">
                      <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                      <input
                        type="text"
                        value={transcriptSearch}
                        onChange={(e) => setTranscriptSearch(e.target.value)}
                        placeholder="Search transcript text..."
                        className="w-full bg-[#f8fafc] border border-slate-300 rounded-lg pl-9 pr-3 py-1.5 text-xs font-semibold text-[#0f172a] placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-indigo-600"
                      />
                    </div>

                    <div className="flex items-center gap-3.5 text-xs">
                      <label className="flex items-center gap-2 text-[#0f172a] font-bold cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={showTimestamps}
                          onChange={(e) => setShowTimestamps(e.target.checked)}
                          className="rounded border-slate-400 text-indigo-600 focus:ring-indigo-600"
                        />
                        <span>Show Timestamps</span>
                      </label>

                      <button
                        onClick={handleCopyTranscript}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-950 border border-indigo-300 text-xs font-bold cursor-pointer transition-colors shadow-2xs"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5 text-indigo-700" />}
                        {copied ? 'Copied Full Text' : 'Copy Clean Transcript'}
                      </button>
                    </div>
                  </div>

                  {/* High-Contrast Document Reading Paper */}
                  <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-sm p-8 divide-y divide-slate-200 space-y-4">
                    {filteredSegments.map((seg) => (
                      <div 
                        key={seg.sequence_index} 
                        className="pt-4 first:pt-0 flex items-start gap-4 hover:bg-indigo-50/40 p-2.5 -mx-2.5 rounded-xl transition-colors"
                      >
                        {showTimestamps && (
                          <div className="font-mono text-xs text-cyan-900 font-extrabold shrink-0 pt-0.5 select-none bg-cyan-50 px-2.5 py-1 rounded border border-cyan-200">
                            {formatTime(seg.start_time)}
                          </div>
                        )}
                        <p className="text-[16px] text-[#0f172a] leading-[1.7] font-normal tracking-normal">
                          {seg.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* SCRIPT STATS TAB */}
          {activeTab === 'stats' && (
            <ScriptStatsView 
              videoId={videoId} 
              hasTranscript={Boolean(video.has_transcript && transcript)} 
            />
          )}

          {/* VISUALS TAB */}
          {activeTab === 'visuals' && (
            <VisualsView 
              videoId={videoId} 
            />
          )}

          {/* METADATA TAB */}
          {activeTab === 'metadata' && (
            <div className="space-y-4 max-w-4xl mx-auto">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-2xs space-y-4">
                <h3 className="text-xs font-black text-[#0f172a] uppercase tracking-wider">Technical Video Details</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                  {Object.entries(video.technical_details || {}).map(([k, val]) => (
                    <div key={k} className="p-3.5 rounded-xl bg-[#f8fafc] border border-slate-300">
                      <p className="text-[11px] text-[#475569] uppercase font-bold">{k}</p>
                      <p className="font-mono text-[#0f172a] font-bold text-xs mt-1">{String(val || 'N/A')}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* RAW DATA TAB */}
          {activeTab === 'raw' && (
            <div className="space-y-3 max-w-4xl mx-auto">
              <div className="flex justify-between items-center">
                <span className="text-xs text-[#0f172a] font-bold">Raw yt-dlp Extraction JSON</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(rawData, null, 2));
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-xs text-indigo-950 font-bold cursor-pointer border border-indigo-300 shadow-2xs transition-colors"
                >
                  Copy JSON
                </button>
              </div>
              <pre className="p-5 rounded-2xl bg-[#0f172a] text-slate-100 text-xs font-mono overflow-x-auto max-h-[60vh] leading-relaxed border border-slate-700 shadow-md">
                {JSON.stringify(rawData, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
