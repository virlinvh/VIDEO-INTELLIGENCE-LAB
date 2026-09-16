import { useState, useEffect } from 'react';
import { 
  Play, 
  RotateCcw, 
  XCircle, 
  CheckCircle2, 
  AlertTriangle, 
  ExternalLink,
  RefreshCw,
  Layers,
  Sparkles
} from 'lucide-react';
import type { Job, JobBatchValidation } from '../types';

interface Props {
  onOpenVideo: (videoId: string) => void;
}

export function AddVideosView({ onOpenVideo }: Props) {
  const [urlInput, setUrlInput] = useState('');
  const [defaultMode, setDefaultMode] = useState<'ANALYZE_ONLY' | 'TRANSCRIPT_ONLY' | 'METADATA_ONLY' | 'ANALYZE_AND_KEEP'>('ANALYZE_ONLY');
  const [defaultLanguage, setDefaultLanguage] = useState<'en' | 'ta' | 'ml' | 'auto'>('en');
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [languageOverrides, setLanguageOverrides] = useState<Record<string, string>>({});
  const [validation, setValidation] = useState<JobBatchValidation | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // Auto-validate on typing debounce
  useEffect(() => {
    if (!urlInput.trim()) {
      setValidation(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsValidating(true);
      try {
        const res = await fetch('/api/v1/jobs/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_text: urlInput })
        });
        if (res.ok) {
          const data = await res.json();
          setValidation(data);
        }
      } catch (err) {
        console.error('Validation error:', err);
      } finally {
        setIsValidating(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [urlInput]);

  // Smart bounded job polling: only poll actively (every 2.5s) if there are in-progress jobs
  useEffect(() => {
    let timer: any = null;

    async function fetchJobs() {
      try {
        const res = await fetch('/api/v1/jobs?limit=20');
        if (res.ok) {
          const data: Job[] = await res.json();
          setJobs(data);

          const hasActive = data.some(j => 
            ['QUEUED', 'VALIDATING', 'EXTRACTING_METADATA', 'GETTING_CAPTIONS', 'PROCESSING_TRANSCRIPT', 'ACQUIRING_AUDIO', 'PREPARING_AUDIO', 'TRANSCRIBING_LOCAL_ASR'].includes(j.state)
          );
          // If active jobs exist, schedule next poll soon; if idle, wait longer (15s)
          timer = setTimeout(fetchJobs, hasActive ? 2500 : 15000);
        }
      } catch (err) {
        console.error('Failed to fetch jobs:', err);
        timer = setTimeout(fetchJobs, 15000);
      }
    }

    fetchJobs();
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, []);

  const handleSubmit = async () => {
    if (!validation || validation.valid_urls === 0) return;
    setIsSubmitting(true);

    const validUrls = validation.items
      .filter(it => it.is_valid)
      .map(it => it.canonical_url || it.raw_url);

    try {
      const res = await fetch('/api/v1/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: validUrls,
          default_mode: defaultMode,
          default_language: defaultLanguage,
          overrides: overrides,
          language_overrides: languageOverrides
        })
      });
      if (res.ok) {
        setUrlInput('');
        setValidation(null);
        setOverrides({});
        setLanguageOverrides({});
        const newJobs = await res.json();
        setJobs(prev => [...newJobs, ...prev]);
      }
    } catch (err) {
      console.error('Submit failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async (jobId: string) => {
    try {
      await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' });
    } catch (err) {
      console.error('Cancel failed:', err);
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await fetch(`/api/v1/jobs/${jobId}/retry`, { method: 'POST' });
    } catch (err) {
      console.error('Retry failed:', err);
    }
  };

  const formatModeName = (mode: string) => {
    switch(mode) {
      case 'ANALYZE_ONLY': return 'Analyze Only';
      case 'TRANSCRIPT_ONLY': return 'Transcript Only';
      case 'METADATA_ONLY': return 'Metadata Only';
      case 'ANALYZE_AND_KEEP': return 'Analyze + Keep';
      case 'RETRANSCRIBE': return 'Retranscribe';
      default: return mode;
    }
  };

  const formatStateLabel = (state: string) => {
    switch(state) {
      case 'COMPLETED': return 'Completed';
      case 'COMPLETED_WITH_WARNINGS': return 'Completed with warnings';
      case 'FAILED': return 'Failed';
      case 'CANCELLED': return 'Cancelled';
      case 'QUEUED': return 'Queued';
      case 'VALIDATING': return 'Validating';
      case 'EXTRACTING_METADATA': return 'Extracting';
      case 'GETTING_CAPTIONS': return 'Getting captions';
      case 'PROCESSING_TRANSCRIPT': return 'Processing';
      case 'ACQUIRING_AUDIO': return 'Acquiring Audio';
      case 'PREPARING_AUDIO': return 'Preparing Audio';
      case 'TRANSCRIBING_LOCAL_ASR': return 'Transcribing ASR';
      default: return state;
    }
  };

  return (
    <div className="space-y-8">
      {/* Input Workspace Card */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-[#0f172a] flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              Batch URL Submission
            </h3>
            <p className="text-xs text-[#475569] mt-1 font-medium">
              Paste one or multiple individual YouTube or Instagram video URLs (one per line).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#334155] font-bold">Transcript Language:</span>
              <select
                value={defaultLanguage}
                onChange={(e: any) => setDefaultLanguage(e.target.value)}
                className="bg-[#f8fafc] border-2 border-indigo-200 text-xs rounded-xl px-3 py-1.5 text-indigo-950 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 font-bold cursor-pointer shadow-2xs"
              >
                <option value="en">English (Default)</option>
                <option value="ta">Tamil (ta)</option>
                <option value="ml">Malayalam (ml)</option>
                <option value="auto">Auto Detect</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-[#334155] font-bold">Batch Default Mode:</span>
              <select
                value={defaultMode}
                onChange={(e: any) => setDefaultMode(e.target.value)}
                className="bg-white border-2 border-slate-300 text-xs rounded-xl px-3 py-1.5 text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 font-bold cursor-pointer"
              >
                <option value="ANALYZE_ONLY">Analyze Only (Default)</option>
                <option value="TRANSCRIPT_ONLY">Transcript Only</option>
                <option value="METADATA_ONLY">Metadata Only</option>
                <option value="ANALYZE_AND_KEEP">Analyze + Keep Video</option>
              </select>
            </div>
          </div>
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            rows={5}
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=...&#10;https://www.instagram.com/reel/...&#10;https://youtu.be/..."
            className="w-full bg-[#f8fafc] border-2 border-slate-300 rounded-xl p-4 text-xs font-mono text-[#0f172a] font-semibold placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all resize-none leading-relaxed"
          />
          {isValidating && (
            <span className="absolute bottom-4 right-4 text-[11px] text-[#334155] font-bold flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-md shadow-xs border border-slate-300">
              <RefreshCw className="w-3 h-3 animate-spin text-indigo-600" /> Validating...
            </span>
          )}
        </div>

        {/* Validation Summary Bar */}
        {validation && (
          <div className="space-y-3 pt-2">
            <div className="flex flex-wrap items-center gap-4 text-xs font-semibold">
              <span className="text-[#334155]">Total: <strong className="text-[#0f172a]">{validation.total_urls}</strong></span>
              <span className="text-[#065f46] bg-[#ecfdf5] px-2.5 py-1 rounded-lg border border-[#a7f3d0] flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Valid: {validation.valid_urls}
              </span>
              {validation.invalid_urls > 0 && (
                <span className="text-[#991b1b] bg-[#fef2f2] px-2.5 py-1 rounded-lg border border-[#fecaca] flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5 text-rose-600" /> Invalid: {validation.invalid_urls}
                </span>
              )}
              {validation.duplicates_in_batch > 0 && (
                <span className="text-[#92400e] bg-[#fffbeb] px-2.5 py-1 rounded-lg border border-[#fde68a] flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Duplicate in input: {validation.duplicates_in_batch}
                </span>
              )}
            </div>

            {/* Validated Items List */}
            <div className="max-h-56 overflow-y-auto space-y-1.5 rounded-xl border border-slate-300 p-2 bg-[#f8fafc]">
              {validation.items.map((item, idx) => (
                <div key={idx} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white border border-slate-300 text-xs shadow-2xs">
                  <div className="flex items-center gap-2 truncate max-w-md">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      item.platform === 'youtube' ? 'bg-red-100 text-red-900 border border-red-300' :
                      item.platform === 'instagram' ? 'bg-pink-100 text-pink-900 border border-pink-300' :
                      'bg-slate-100 text-slate-800 border border-slate-300'
                    }`}>
                      {item.platform}
                    </span>
                    <span className={`font-mono truncate font-semibold ${item.is_valid ? 'text-[#0f172a]' : 'text-rose-700'}`}>
                      {item.raw_url}
                    </span>
                    {item.already_in_library && (
                      <span className="text-[10px] font-bold text-[#92400e] bg-[#fffbeb] px-2 py-0.5 rounded border border-[#fde68a]">
                        In Library (Reprocess)
                      </span>
                    )}
                    {item.error && (
                      <span className="text-[11px] text-rose-700 font-medium truncate">({item.error})</span>
                    )}
                  </div>

                  {item.is_valid && (
                    <div className="flex items-center gap-2">
                      <select
                        value={languageOverrides[item.raw_url] || defaultLanguage}
                        onChange={(e) => setLanguageOverrides({ ...languageOverrides, [item.raw_url]: e.target.value })}
                        className="bg-indigo-50/60 border border-indigo-200 text-[11px] rounded-lg px-2 py-1 text-indigo-950 font-bold focus:outline-none focus:border-indigo-600 cursor-pointer"
                        title="Per-video transcript language override"
                      >
                        <option value="en">English (en)</option>
                        <option value="ta">Tamil (ta)</option>
                        <option value="ml">Malayalam (ml)</option>
                        <option value="auto">Auto</option>
                      </select>

                      <select
                        value={overrides[item.raw_url] || defaultMode}
                        onChange={(e) => setOverrides({ ...overrides, [item.raw_url]: e.target.value })}
                        className="bg-white border border-slate-300 text-[11px] rounded-lg px-2 py-1 text-[#0f172a] font-semibold focus:outline-none focus:border-indigo-600 cursor-pointer"
                      >
                        <option value="ANALYZE_ONLY">Analyze Only</option>
                        <option value="TRANSCRIPT_ONLY">Transcript Only</option>
                        <option value="METADATA_ONLY">Metadata Only</option>
                        <option value="ANALYZE_AND_KEEP">Analyze + Keep</option>
                      </select>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleSubmit}
            disabled={!validation || validation.valid_urls === 0 || isSubmitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs shadow-md shadow-indigo-600/30 transition-all cursor-pointer disabled:cursor-not-allowed border border-indigo-700"
          >
            {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            Process {validation?.valid_urls ? `${validation.valid_urls} Video${validation.valid_urls > 1 ? 's' : ''}` : 'Videos'}
          </button>
        </div>
      </div>

      {/* Execution Queue Table */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-[#0f172a] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            Extraction Pipeline & Job Queue
          </h3>
          <span className="text-xs text-[#334155] font-bold">{jobs.length} total jobs</span>
        </div>

        {jobs.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#64748b] font-medium">
            No extraction jobs enqueued yet. Submit URLs above to start processing.
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-300">
            <table className="w-full text-left text-xs text-[#0f172a]">
              <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                <tr>
                  <th className="py-3 px-4">URL / Source</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4">State</th>
                  <th className="py-3 px-4">Progress / Step</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4 font-mono truncate max-w-xs text-[#0f172a] font-bold">
                      {j.url}
                    </td>
                    <td className="py-3.5 px-4 space-x-1.5">
                      <span className="px-2.5 py-1 rounded text-[11px] bg-slate-100 text-[#0f172a] font-bold border border-slate-300">
                        {formatModeName(j.processing_mode)}
                      </span>
                      <span 
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-black uppercase border ${
                          j.requested_transcript_language === 'ta' ? 'bg-amber-100 text-amber-900 border-amber-300' :
                          j.requested_transcript_language === 'ml' ? 'bg-purple-100 text-purple-900 border-purple-300' :
                          'bg-indigo-100 text-indigo-900 border-indigo-300'
                        }`}
                        title={`Transcript language: ${j.requested_transcript_language || 'en'}`}
                      >
                        {j.requested_transcript_language || 'en'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {j.state === 'FAILED' && (j.error_details?.code === 'UPSTREAM_RATE_LIMIT' || j.error_details?.code === 'CIRCUIT_BREAKER_OPEN') ? (
                        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                          Rate Limited
                        </span>
                      ) : (
                        <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                          j.state === 'COMPLETED' ? 'bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0]' :
                          j.state === 'COMPLETED_WITH_WARNINGS' ? 'bg-[#fffbeb] text-[#92400e] border border-[#fde68a]' :
                          j.state === 'FAILED' ? 'bg-[#fef2f2] text-[#991b1b] border border-[#fecaca]' :
                          j.state === 'CANCELLED' ? 'bg-slate-100 text-slate-700 border border-slate-300' :
                          'bg-[#eff6ff] text-[#1e40af] border border-[#bfdbfe] animate-pulse'
                        }`}>
                          {formatStateLabel(j.state)}
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] text-[#334155] font-semibold">
                          <span className="truncate max-w-xs text-[#0f172a]">{j.current_step}</span>
                          <span className="font-bold">{j.progress_percent}%</span>
                        </div>
                        <div className="w-48 h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-300">
                          <div 
                            className={`h-full transition-all duration-300 ${
                              j.state === 'COMPLETED' ? 'bg-emerald-600' :
                              j.state === 'COMPLETED_WITH_WARNINGS' ? 'bg-amber-600' :
                              j.state === 'FAILED' ? ((j.error_details?.code === 'UPSTREAM_RATE_LIMIT' || j.error_details?.code === 'CIRCUIT_BREAKER_OPEN') ? 'bg-amber-500' : 'bg-rose-600') : 'bg-indigo-600'
                            }`}
                            style={{ width: `${j.progress_percent}%` }}
                          />
                        </div>
                        {j.error_details && (
                          <div className={`p-2 rounded-lg text-[11px] font-medium mt-1 ${
                            j.error_details.code === 'UPSTREAM_RATE_LIMIT' || j.error_details.code === 'CIRCUIT_BREAKER_OPEN'
                              ? 'bg-amber-50 border border-amber-200 text-amber-900'
                              : 'bg-[#fef2f2] border border-[#fecaca] text-[#991b1b]'
                          }`}>
                            <div className="font-bold">
                              {j.error_details.code === 'UPSTREAM_RATE_LIMIT' ? 'Upstream Rate Limit (HTTP 429)' :
                               j.error_details.code === 'CIRCUIT_BREAKER_OPEN' ? 'Circuit Breaker Cooldown Active' :
                               j.error_details.code}
                            </div>
                            <div className="text-[10px] mt-0.5">{j.error_details.message}</div>
                          </div>
                        )}
                        {j.warnings && j.warnings.length > 0 && (
                          <div className="p-2 rounded-lg bg-[#fffbeb] border border-[#fde68a] text-[11px] text-[#92400e] font-medium mt-1">
                            {j.warnings[0].includes('UNAVAILABLE_NO_CAPTIONS') ? 'No native or automatic captions found for this video.' : j.warnings[0]}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      {j.video_id && (j.state === 'COMPLETED' || j.state === 'COMPLETED_WITH_WARNINGS') && (
                        <button
                          onClick={() => onOpenVideo(j.video_id!)}
                          className="px-3.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-bold text-xs border border-indigo-300 cursor-pointer inline-flex items-center gap-1.5 shadow-2xs transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5 text-indigo-700" /> View Video
                        </button>
                      )}
                      {(j.state === 'FAILED' || j.state === 'CANCELLED') && (
                        <button
                          onClick={() => handleRetry(j.id)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-[#0f172a] font-bold text-xs border border-slate-300 cursor-pointer inline-flex items-center gap-1 shadow-2xs transition-colors"
                        >
                          <RotateCcw className="w-3.5 h-3.5 text-slate-700" /> Retry
                        </button>
                      )}
                      {(j.state === 'QUEUED' || j.state.startsWith('EXTRACT') || j.state.startsWith('GETTING')) && (
                        <button
                          onClick={() => handleCancel(j.id)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-800 font-bold text-xs border border-slate-300 hover:border-rose-300 cursor-pointer inline-flex items-center gap-1 shadow-2xs transition-colors"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
