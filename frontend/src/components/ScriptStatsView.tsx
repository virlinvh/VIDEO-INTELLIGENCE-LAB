import { useState, useEffect } from 'react';
import { 
  Clock, 
  FileText, 
  HelpCircle, 
  AlertCircle, 
  Sparkles, 
  Copy, 
  Check, 
  RefreshCw, 
  Layers, 
  ListOrdered, 
  Hash, 
  Activity, 
  Info
} from 'lucide-react';
import type { ScriptMetricsData } from '../types';

interface Props {
  videoId: string;
  hasTranscript: boolean;
}

export function ScriptStatsView({ videoId, hasTranscript }: Props) {
  const [metrics, setMetrics] = useState<ScriptMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Controls
  const [wordFreqMode, setWordFreqMode] = useState<'filtered' | 'all'>('filtered');
  const [wordFreqLimit, setWordFreqLimit] = useState<number>(15);
  const [ngramTab, setNgramTab] = useState<'2' | '3' | '4'>('2');
  const [activeOpeningTab, setActiveOpeningTab] = useState<'first_sentence' | 'first_3s' | 'first_5s' | 'first_10s' | 'first_15s' | 'first_30s'>('first_sentence');
  const [activeClosingTab, setActiveClosingTab] = useState<'final_sentence' | 'last_5s' | 'last_10s' | 'last_15s' | 'last_30s'>('final_sentence');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Expanded evidence sections
  const [expandedSection, setExpandedSection] = useState<'questions' | 'exclamations' | 'fillers' | 'transitions' | 'repeated' | null>(null);

  useEffect(() => {
    if (!hasTranscript) {
      setLoading(false);
      return;
    }
    loadMetrics();
  }, [videoId, hasTranscript]);

  async function loadMetrics() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/videos/${videoId}/script-metrics`);
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to load script metrics');
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecalculate() {
    setRecalculating(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/videos/${videoId}/script-metrics/recalculate`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Recalculation failed');
      }
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRecalculating(false);
    }
  }

  const handleCopy = (text: string, key: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs.toString().padStart(2, '0')}`;
  };

  if (!hasTranscript) {
    return (
      <div className="py-20 text-center space-y-3 rounded-2xl bg-white border-2 border-slate-300 shadow-xs max-w-4xl mx-auto p-8">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center mx-auto border border-slate-300">
          <FileText className="w-6 h-6 text-slate-600" />
        </div>
        <h4 className="text-base font-bold text-[#0f172a]">Script Statistics Unavailable</h4>
        <p className="text-xs text-[#334155] max-w-md mx-auto leading-relaxed font-semibold">
          Script statistics require a transcript. No transcript is currently available for this video.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3 rounded-2xl bg-white border-2 border-slate-300 shadow-xs max-w-4xl mx-auto p-8">
        <RefreshCw className="w-8 h-8 text-purple-600 animate-spin mx-auto" />
        <p className="text-sm font-bold text-[#0f172a]">Calculating deterministic script metrics...</p>
        <p className="text-xs text-[#475569]">Parsing lexical diversity, speaking pace, temporal windows, and n-grams.</p>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="py-16 text-center space-y-3 rounded-2xl bg-white border-2 border-red-300 shadow-xs max-w-4xl mx-auto p-8">
        <AlertCircle className="w-8 h-8 text-red-600 mx-auto" />
        <h4 className="text-base font-bold text-red-950">Script Intelligence Error</h4>
        <p className="text-xs text-red-800 max-w-md mx-auto">{error || 'Unknown error occurred'}</p>
        <button
          onClick={handleRecalculate}
          className="mt-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
        >
          Retry Calculation
        </button>
      </div>
    );
  }

  // Pre-calculate frequencies for rendering
  const activeFreqs = wordFreqMode === 'filtered' ? metrics.word_frequencies_filtered : metrics.word_frequencies;
  const freqEntries = Object.entries(activeFreqs || {}).slice(0, wordFreqLimit);
  const maxFreq = freqEntries.length > 0 ? Math.max(...freqEntries.map(([_, count]) => count)) : 1;

  const activeNgrams = Object.entries(metrics.phrase_frequencies?.[ngramTab] || {}).slice(0, 12);
  const maxNgramCount = activeNgrams.length > 0 ? Math.max(...activeNgrams.map(([_, count]) => count)) : 1;

  // Max sentence bucket
  const distEntries = Object.entries(metrics.sentence_length_distribution || {});
  const maxDistVal = distEntries.length > 0 ? Math.max(...distEntries.map(([_, count]) => count)) : 1;

  // Max timeline WPM
  const maxTimelineWpm = metrics.pace_timeline.length > 0 
    ? Math.max(...metrics.pace_timeline.map(w => w.estimated_wpm), 1) 
    : 1;

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Top Header & Version Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-purple-50/80 border-2 border-purple-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-600 text-white flex items-center justify-center font-bold shadow-xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-black text-purple-950 tracking-tight flex items-center gap-2">
              Deterministic Script Intelligence
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-200/80 text-purple-900 border border-purple-300">
                v{metrics.calculation_version}
              </span>
            </h3>
            <p className="text-xs text-purple-900/80 font-medium">
              Pure mathematical analysis • Calculated {new Date(metrics.calculated_at).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-purple-100/60 text-purple-950 border border-purple-300 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-purple-700 ${recalculating ? 'animate-spin' : ''}`} />
          {recalculating ? 'Recalculating...' : 'Recalculate Metrics'}
        </button>
      </div>

      {/* 1. SCRIPT SNAPSHOT */}
      <section className="space-y-3">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
          <Activity className="w-4 h-4 text-purple-700" />
          1. Script Snapshot
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Spoken Words</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.word_count.toLocaleString()}</p>
            <p className="text-[11px] text-slate-700 font-semibold">{metrics.unique_words.toLocaleString()} unique tokens</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Speaking Rate</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.estimated_wpm} <span className="text-xs font-bold text-slate-700">WPM</span></p>
            <p className="text-[11px] text-slate-700 font-semibold">{formatTime(metrics.total_spoken_duration)} spoken duration</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Sentences</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.sentence_count}</p>
            <p className="text-[11px] text-slate-700 font-semibold">{metrics.avg_sentence_length} words / avg sentence</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Lexical Diversity</span>
            <p className="text-2xl font-black text-purple-950">{metrics.lexical_diversity_ttr}%</p>
            <p className="text-[11px] text-slate-700 font-semibold">TTR (Root TTR: {metrics.root_ttr})</p>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Questions</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.question_count}</p>
            <button 
              onClick={() => setExpandedSection(expandedSection === 'questions' ? null : 'questions')}
              className="text-[11px] font-bold text-purple-700 hover:text-purple-900 underline cursor-pointer"
            >
              {expandedSection === 'questions' ? 'Hide evidence' : 'Inspect questions'}
            </button>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Exclamations</span>
            <p className="text-2xl font-black text-[#0f172a]">{metrics.exclamation_count}</p>
            <button 
              onClick={() => setExpandedSection(expandedSection === 'exclamations' ? null : 'exclamations')}
              className="text-[11px] font-bold text-purple-700 hover:text-purple-900 underline cursor-pointer"
            >
              {expandedSection === 'exclamations' ? 'Hide evidence' : 'Inspect exclamations'}
            </button>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Potential Fillers</span>
            <p className="text-2xl font-black text-amber-900">
              {Object.values(metrics.filler_word_counts || {}).reduce((a, b) => a + b, 0)}
            </p>
            <button 
              onClick={() => setExpandedSection(expandedSection === 'fillers' ? null : 'fillers')}
              className="text-[11px] font-bold text-amber-700 hover:text-amber-900 underline cursor-pointer"
            >
              {expandedSection === 'fillers' ? 'Hide evidence' : 'Inspect fillers'}
            </button>
          </div>

          <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs space-y-1">
            <span className="text-[11px] font-bold text-slate-700 uppercase">Detected Transitions</span>
            <p className="text-2xl font-black text-emerald-950">
              {Object.values(metrics.transition_phrase_counts || {}).reduce((a, b) => a + b, 0)}
            </p>
            <button 
              onClick={() => setExpandedSection(expandedSection === 'transitions' ? null : 'transitions')}
              className="text-[11px] font-bold text-emerald-700 hover:text-emerald-900 underline cursor-pointer"
            >
              {expandedSection === 'transitions' ? 'Hide evidence' : 'Inspect transitions'}
            </button>
          </div>
        </div>
      </section>

      {/* 2. SPEAKING PACE OVER TIME */}
      <section className="space-y-3 bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-700" />
              2. Speaking Pace Timeline
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Estimated WPM calculated over discrete continuous time intervals
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-700 font-bold">Overall Average:</span>
            <span className="ml-2 px-2.5 py-1 rounded bg-purple-100 text-purple-950 font-black text-xs border border-purple-200">
              {metrics.estimated_wpm} WPM
            </span>
          </div>
        </div>

        {/* Visual Pace Histogram / Timeline */}
        <div className="space-y-2 pt-4">
          <div className="h-36 w-full flex items-end gap-1.5 p-3 bg-slate-50 rounded-xl border border-slate-200 overflow-x-auto">
            {metrics.pace_timeline.map((win) => {
              const heightPct = Math.max(8, Math.round((win.estimated_wpm / (maxTimelineWpm * 1.15)) * 100));
              return (
                <div 
                  key={win.window_index} 
                  className="flex-1 min-w-[36px] flex flex-col items-center gap-1 group relative h-full justify-end"
                >
                  {/* Tooltip */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-2 bg-[#0f172a] text-white text-[10px] p-2 rounded-lg pointer-events-none z-20 whitespace-nowrap shadow-xl border border-slate-700">
                    <p className="font-bold">{formatTime(win.start_time)} - {formatTime(win.end_time)}</p>
                    <p className="text-purple-300 font-bold">{win.estimated_wpm} WPM ({win.word_count} words)</p>
                    {win.question_count > 0 && <p className="text-cyan-300">❓ {win.question_count} question(s)</p>}
                    {win.exclamation_count > 0 && <p className="text-amber-300">❗ {win.exclamation_count} exclamation(s)</p>}
                  </div>

                  <div 
                    style={{ height: `${heightPct}%` }}
                    className={`w-full rounded-t-md transition-all ${
                      win.estimated_wpm > 180 
                        ? 'bg-rose-500 group-hover:bg-rose-600' 
                        : win.estimated_wpm < 100 
                        ? 'bg-amber-500 group-hover:bg-amber-600' 
                        : 'bg-purple-600 group-hover:bg-purple-700'
                    }`}
                  />
                  <span className="text-[9px] font-mono text-slate-700 font-bold select-none">
                    {Math.round(win.start_time)}s
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-700 px-1 font-semibold">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block"/> Slow (&lt;100 WPM)</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-purple-600 inline-block"/> Normal (100–180 WPM)</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block"/> Fast (&gt;180 WPM)</span>
            </div>
            <span>Hover bars for window details</span>
          </div>
        </div>
      </section>

      {/* 3. SENTENCE STRUCTURE & DISTRIBUTION */}
      <section className="space-y-4 bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm">
        <div>
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <ListOrdered className="w-4 h-4 text-purple-700" />
            3. Sentence Structure & Length Distribution
          </h4>
          <p className="text-xs text-slate-700 font-semibold mt-0.5">
            Deterministic segmentation based on punctuation boundaries
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-purple-50/50 p-4 rounded-xl border border-purple-200">
          <div>
            <span className="text-[10px] font-bold text-slate-700 uppercase">Shortest Sentence</span>
            <p className="text-base font-extrabold text-[#0f172a]">{metrics.min_sentence_length} <span className="text-xs font-normal">words</span></p>
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-700 uppercase">Median Length</span>
            <p className="text-base font-extrabold text-[#0f172a]">{metrics.median_sentence_length} <span className="text-xs font-normal">words</span></p>
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-700 uppercase">Average Length</span>
            <p className="text-base font-extrabold text-[#0f172a]">{metrics.avg_sentence_length} <span className="text-xs font-normal">words</span></p>
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-700 uppercase">Longest Sentence</span>
            <p className="text-base font-extrabold text-[#0f172a]">{metrics.max_sentence_length} <span className="text-xs font-normal">words</span></p>
          </div>
        </div>

        {/* Bucket Bar Chart */}
        <div className="space-y-2 pt-2">
          <span className="text-xs font-bold text-[#0f172a]">Sentence Length Buckets (Words per Sentence):</span>
          <div className="space-y-2">
            {distEntries.map(([bucket, count]) => {
              const widthPct = Math.max(4, Math.round((count / maxDistVal) * 100));
              return (
                <div key={bucket} className="flex items-center gap-3 text-xs">
                  <span className="w-14 font-mono font-bold text-slate-700 text-right">{bucket}</span>
                  <div className="flex-1 bg-slate-100 rounded-lg h-6 overflow-hidden p-0.5 border border-slate-200">
                    <div 
                      style={{ width: `${widthPct}%` }}
                      className="bg-purple-600 h-full rounded-md transition-all flex items-center justify-end pr-2 text-white font-bold text-[10px]"
                    >
                      {count > 0 && count}
                    </div>
                  </div>
                  <span className="w-10 font-mono text-slate-700 font-bold">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. OPENING & CLOSING EVIDENCE */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Opening Card */}
        <div className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div>
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-700" />
                Opening Evidence
              </h4>
              <p className="text-[11px] text-slate-700 font-semibold">Exact words spoken during start</p>
            </div>
            <button
              onClick={() => handleCopy(metrics.opening_extracts?.[activeOpeningTab] || '', 'opening')}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-colors cursor-pointer"
              title="Copy text"
            >
              {copiedKey === 'opening' ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {[
              { id: 'first_sentence', label: '1st Sentence' },
              { id: 'first_3s', label: 'First 3s' },
              { id: 'first_5s', label: 'First 5s' },
              { id: 'first_10s', label: 'First 10s' },
              { id: 'first_15s', label: 'First 15s' },
              { id: 'first_30s', label: 'First 30s' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveOpeningTab(tab.id as any)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap transition-all cursor-pointer ${
                  activeOpeningTab === tab.id
                    ? 'bg-cyan-700 text-white shadow-2xs'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 p-4 bg-cyan-50/40 rounded-xl border border-cyan-200 font-mono text-xs text-[#0f172a] leading-relaxed select-text min-h-[100px]">
            {metrics.opening_extracts?.[activeOpeningTab] ? (
              `"${metrics.opening_extracts[activeOpeningTab]}"`
            ) : (
              <span className="text-slate-400 italic font-sans">No speech detected within this time window.</span>
            )}
          </div>
        </div>

        {/* Closing Card */}
        <div className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div>
              <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-purple-700" />
                Closing Evidence
              </h4>
              <p className="text-[11px] text-slate-700 font-semibold">Exact words spoken prior to video conclusion</p>
            </div>
            <button
              onClick={() => handleCopy(metrics.closing_extracts?.[activeClosingTab] || '', 'closing')}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-colors cursor-pointer"
              title="Copy text"
            >
              {copiedKey === 'closing' ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {[
              { id: 'final_sentence', label: 'Final Sentence' },
              { id: 'last_5s', label: 'Last 5s' },
              { id: 'last_10s', label: 'Last 10s' },
              { id: 'last_15s', label: 'Last 15s' },
              { id: 'last_30s', label: 'Last 30s' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveClosingTab(tab.id as any)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap transition-all cursor-pointer ${
                  activeClosingTab === tab.id
                    ? 'bg-purple-700 text-white shadow-2xs'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 p-4 bg-purple-50/40 rounded-xl border border-purple-200 font-mono text-xs text-[#0f172a] leading-relaxed select-text min-h-[100px]">
            {metrics.closing_extracts?.[activeClosingTab] ? (
              `"${metrics.closing_extracts[activeClosingTab]}"`
            ) : (
              <span className="text-slate-400 italic font-sans">No speech detected within this time window.</span>
            )}
          </div>
        </div>
      </section>

      {/* 5. WORD FREQUENCY */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Hash className="w-4 h-4 text-purple-700" />
              5. Word Frequency
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Ranked frequency of token occurrences
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center gap-2">
            <div className="bg-slate-100 p-1 rounded-xl border border-slate-200 flex gap-1 text-xs">
              <button
                onClick={() => setWordFreqMode('filtered')}
                className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  wordFreqMode === 'filtered' 
                    ? 'bg-white text-purple-950 shadow-2xs border border-slate-200' 
                    : 'text-slate-700 hover:text-[#0f172a]'
                }`}
              >
                Meaningful Words (Stopwords Removed)
              </button>
              <button
                onClick={() => setWordFreqMode('all')}
                className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  wordFreqMode === 'all' 
                    ? 'bg-white text-purple-950 shadow-2xs border border-slate-200' 
                    : 'text-slate-700 hover:text-[#0f172a]'
                }`}
              >
                All Words
              </button>
            </div>
          </div>
        </div>

        {/* Word Frequency Bars */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 pt-2">
          {freqEntries.map(([word, count]) => {
            const widthPct = Math.max(5, Math.round((count / maxFreq) * 100));
            return (
              <div key={word} className="flex items-center gap-3 text-xs">
                <span className="w-24 font-bold text-[#0f172a] truncate">{word}</span>
                <div className="flex-1 bg-slate-100 rounded-md h-5 overflow-hidden border border-slate-200">
                  <div 
                    style={{ width: `${widthPct}%` }}
                    className="bg-indigo-600 h-full rounded-xs transition-all"
                  />
                </div>
                <span className="w-8 font-mono text-slate-700 font-extrabold text-right">{count}</span>
              </div>
            );
          })}
        </div>

        {Object.keys(activeFreqs || {}).length > wordFreqLimit && (
          <div className="text-center pt-2">
            <button
              onClick={() => setWordFreqLimit(prev => prev + 15)}
              className="text-xs font-bold text-purple-700 hover:text-purple-950 underline cursor-pointer"
            >
              Show More Words ({Object.keys(activeFreqs || {}).length - wordFreqLimit} remaining)
            </button>
          </div>
        )}
      </section>

      {/* 6. PHRASE FREQUENCY (N-GRAMS) */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-700" />
              6. Phrase Frequency (N-Grams)
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Sliding window multi-word sequence counts
            </p>
          </div>

          <div className="flex gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
            <button
              onClick={() => setNgramTab('2')}
              className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                ngramTab === '2' ? 'bg-white text-purple-950 shadow-2xs border border-slate-200' : 'text-slate-700'
              }`}
            >
              2-Word Phrases
            </button>
            <button
              onClick={() => setNgramTab('3')}
              className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                ngramTab === '3' ? 'bg-white text-purple-950 shadow-2xs border border-slate-200' : 'text-slate-700'
              }`}
            >
              3-Word Phrases
            </button>
            <button
              onClick={() => setNgramTab('4')}
              className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                ngramTab === '4' ? 'bg-white text-purple-950 shadow-2xs border border-slate-200' : 'text-slate-700'
              }`}
            >
              4-Word Phrases
            </button>
          </div>
        </div>

        {activeNgrams.length === 0 ? (
          <p className="text-xs text-slate-400 italic py-4 text-center">No repeating {ngramTab}-word phrases detected.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2.5 pt-2">
            {activeNgrams.map(([phrase, count]) => {
              const widthPct = Math.max(5, Math.round((count / maxNgramCount) * 100));
              return (
                <div key={phrase} className="flex items-center gap-3 text-xs">
                  <span className="w-36 font-bold text-[#0f172a] truncate" title={phrase}>"{phrase}"</span>
                  <div className="flex-1 bg-slate-100 rounded-md h-5 overflow-hidden border border-slate-200">
                    <div 
                      style={{ width: `${widthPct}%` }}
                      className="bg-purple-700 h-full rounded-xs transition-all"
                    />
                  </div>
                  <span className="w-8 font-mono text-slate-700 font-extrabold text-right">{count}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 7. REPEATED LANGUAGE */}
      <section className="bg-white p-6 rounded-2xl border-2 border-slate-300 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-purple-700" />
              7. Repeated Phrases (&ge; 2 Occurrences)
            </h4>
            <p className="text-xs text-slate-700 font-semibold mt-0.5">
              Meaningful multi-word phrases repeated across the video
            </p>
          </div>
          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-800 font-bold text-xs border border-slate-200">
            {metrics.repeated_phrases.length} Phrases
          </span>
        </div>

        {metrics.repeated_phrases.length === 0 ? (
          <p className="text-xs text-slate-400 italic py-4 text-center">No significant repeated multi-word phrases detected.</p>
        ) : (
          <div className="divide-y divide-slate-200">
            {metrics.repeated_phrases.slice(0, 8).map((item, idx) => (
              <div key={idx} className="py-3 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-[#0f172a]">"{item.phrase}"</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-purple-100 text-purple-900 border border-purple-200">
                      {item.count}&times;
                    </span>
                    <span className="text-[10px] text-slate-700 font-semibold">{item.word_count} words</span>
                  </div>

                  {item.occurrences.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {item.occurrences.map((occ, oIdx) => (
                        <span key={oIdx} className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 rounded text-[10px] font-mono text-slate-800 border border-slate-200">
                          <Clock className="w-2.5 h-2.5 text-slate-700" />
                          {formatTime(occ.timestamp)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 8. DETECTED EVIDENCE DRILL-DOWNS */}
      <section className="space-y-4">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-purple-700" />
          8. Rule-Based Punctuation & Expression Evidence
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Questions Drilldown */}
          <div className="bg-white p-5 rounded-2xl border-2 border-slate-300 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-[#0f172a] flex items-center gap-1.5">
                Questions Detected ({metrics.question_count})
              </span>
              <span className="text-[10px] font-bold text-slate-700">Rule: Punctuation "?"</span>
            </div>

            {metrics.question_evidence.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No question sentences found.</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {metrics.question_evidence.map((q, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-cyan-50/50 border border-cyan-200 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-cyan-900 bg-cyan-100 px-1.5 py-0.5 rounded border border-cyan-300">
                        {formatTime(q.timestamp)}
                      </span>
                    </div>
                    <p className="text-[#0f172a] font-medium select-text">"{q.text}"</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Exclamations Drilldown */}
          <div className="bg-white p-5 rounded-2xl border-2 border-slate-300 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-[#0f172a] flex items-center gap-1.5">
                Exclamations Detected ({metrics.exclamation_count})
              </span>
              <span className="text-[10px] font-bold text-slate-700">Rule: Punctuation "!"</span>
            </div>

            {metrics.exclamation_evidence.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No exclamation sentences found.</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {metrics.exclamation_evidence.map((ex, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-amber-50/50 border border-amber-200 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-amber-900 bg-amber-100 px-1.5 py-0.5 rounded border border-amber-300">
                        {formatTime(ex.timestamp)}
                      </span>
                    </div>
                    <p className="text-[#0f172a] font-medium select-text">"{ex.text}"</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 9 & 10. Potential Fillers & Transitions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Potential Fillers */}
          <div className="bg-white p-5 rounded-2xl border-2 border-slate-300 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-amber-950">
                Potential Filler Expressions ({metrics.filler_evidence.length})
              </span>
              <span className="text-[10px] font-bold text-slate-700">Dictionary Match</span>
            </div>

            <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-[11px] text-amber-900 font-semibold flex items-start gap-2">
              <Info className="w-4 h-4 shrink-0 text-amber-700 mt-0.5" />
              <span>These are rule-based dictionary matches and may not represent filler usage in every context.</span>
            </div>

            {metrics.filler_evidence.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No dictionary filler expressions matched.</p>
            ) : (
              <div className="max-h-52 overflow-y-auto space-y-2 pr-1">
                {metrics.filler_evidence.map((f, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                    <div className="flex items-center justify-between font-bold">
                      <span className="text-amber-950 uppercase">"{f.expression}"</span>
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 text-[10px] border border-amber-300">
                        {f.count}&times;
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {f.occurrences.map((occ, oIdx) => (
                        <span key={oIdx} className="px-1.5 py-0.5 bg-white text-[10px] font-mono text-slate-800 rounded border border-slate-300">
                          {formatTime(occ.timestamp)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Detected Transitions */}
          <div className="bg-white p-5 rounded-2xl border-2 border-slate-300 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-emerald-950">
                Detected Transition Expressions ({metrics.transition_evidence.length})
              </span>
              <span className="text-[10px] font-bold text-slate-700">Dictionary Match</span>
            </div>

            <div className="p-2.5 bg-emerald-50 rounded-lg border border-emerald-200 text-[11px] text-emerald-900 font-semibold flex items-start gap-2">
              <Info className="w-4 h-4 shrink-0 text-emerald-700 mt-0.5" />
              <span>Dictionary-matched transition cues. Does not imply rhetorical classification.</span>
            </div>

            {metrics.transition_evidence.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">No transition expressions matched.</p>
            ) : (
              <div className="max-h-52 overflow-y-auto space-y-2 pr-1">
                {metrics.transition_evidence.map((t, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                    <div className="flex items-center justify-between font-bold">
                      <span className="text-emerald-950 capitalize">"{t.expression}"</span>
                      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 text-[10px] border border-emerald-300">
                        {t.count}&times;
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {t.occurrences.map((occ, oIdx) => (
                        <span key={oIdx} className="px-1.5 py-0.5 bg-white text-[10px] font-mono text-slate-800 rounded border border-slate-300">
                          {formatTime(occ.timestamp)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
