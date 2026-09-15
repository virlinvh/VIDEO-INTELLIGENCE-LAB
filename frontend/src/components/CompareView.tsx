import React, { useState, useEffect } from 'react';
import { 
  Scale, 
  Plus, 
  Trash2, 
  Bookmark, 
  BookmarkCheck, 
  Check, 
  X, 
  Search, 
  FileText, 
  Film, 
  Activity, 
  Users, 
  BookOpen, 
  TrendingUp, 
  Info,
  ChevronDown,
  RefreshCw,
  SlidersHorizontal
} from 'lucide-react';
import type { 
  VideoSummary, 
  MultiVideoComparisonResult, 
  ComparisonSavedItem
} from '../types';

interface CompareViewProps {
  initialVideoIds?: string[];
  onOpenVideoDetail?: (videoId: string) => void;
}

const VIDEO_PALETTE = [
  { name: 'Indigo', border: 'border-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-900', badge: 'bg-indigo-600 text-white', bar: 'bg-indigo-600', dot: 'bg-indigo-600', fill: '#4f46e5' },
  { name: 'Emerald', border: 'border-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-900', badge: 'bg-emerald-600 text-white', bar: 'bg-emerald-600', dot: 'bg-emerald-600', fill: '#059669' },
  { name: 'Amber', border: 'border-amber-500', bg: 'bg-amber-50', text: 'text-amber-900', badge: 'bg-amber-600 text-white', bar: 'bg-amber-600', dot: 'bg-amber-600', fill: '#d97706' },
  { name: 'Rose', border: 'border-rose-500', bg: 'bg-rose-50', text: 'text-rose-900', badge: 'bg-rose-600 text-white', bar: 'bg-rose-600', dot: 'bg-rose-600', fill: '#e11d48' },
  { name: 'Cyan', border: 'border-cyan-500', bg: 'bg-cyan-50', text: 'text-cyan-900', badge: 'bg-cyan-600 text-white', bar: 'bg-cyan-600', dot: 'bg-cyan-600', fill: '#0891b2' },
  { name: 'Violet', border: 'border-violet-500', bg: 'bg-violet-50', text: 'text-violet-900', badge: 'bg-violet-600 text-white', bar: 'bg-violet-600', dot: 'bg-violet-600', fill: '#7c3aed' },
  { name: 'Blue', border: 'border-blue-500', bg: 'bg-blue-50', text: 'text-blue-900', badge: 'bg-blue-600 text-white', bar: 'bg-blue-600', dot: 'bg-blue-600', fill: '#2563eb' },
  { name: 'Orange', border: 'border-orange-500', bg: 'bg-orange-50', text: 'text-orange-900', badge: 'bg-orange-600 text-white', bar: 'bg-orange-600', dot: 'bg-orange-600', fill: '#ea580c' },
  { name: 'Fuchsia', border: 'border-fuchsia-500', bg: 'bg-fuchsia-50', text: 'text-fuchsia-900', badge: 'bg-fuchsia-600 text-white', bar: 'bg-fuchsia-600', dot: 'bg-fuchsia-600', fill: '#c026d3' },
  { name: 'Slate', border: 'border-slate-500', bg: 'bg-slate-100', text: 'text-slate-900', badge: 'bg-slate-700 text-white', bar: 'bg-slate-700', dot: 'bg-slate-700', fill: '#334155' },
];

export function CompareView({ initialVideoIds = [], onOpenVideoDetail }: CompareViewProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialVideoIds);
  const [libraryVideos, setLibraryVideos] = useState<VideoSummary[]>([]);
  const [savedComparisons, setSavedComparisons] = useState<ComparisonSavedItem[]>([]);
  const [result, setResult] = useState<MultiVideoComparisonResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // UI States
  const [activeSubTab, setActiveSubTab] = useState<'matrix' | 'script' | 'openings' | 'language' | 'visuals' | 'timeline' | 'creators'>('matrix');
  const [showPickerModal, setShowPickerModal] = useState<boolean>(false);
  const [showSaveModal, setShowSaveModal] = useState<boolean>(false);
  const [saveTitle, setSaveTitle] = useState<string>('');
  const [pickerSearch, setPickerSearch] = useState<string>('');
  const [matrixMode, setMatrixMode] = useState<'raw' | 'normalized'>('raw');
  const [timelineMetric, setTimelineMetric] = useState<'wpm' | 'words' | 'cuts_per_minute' | 'scene_changes'>('wpm');

  // Fetch Library Videos & Saved Comparisons
  useEffect(() => {
    fetchLibrary();
    fetchSavedComparisons();
  }, []);

  // When initialVideoIds changes
  useEffect(() => {
    if (initialVideoIds.length >= 2) {
      setSelectedIds(initialVideoIds);
      runComparison(initialVideoIds);
    }
  }, [initialVideoIds]);

  const fetchLibrary = async () => {
    try {
      const res = await fetch('/api/v1/videos');
      if (res.ok) {
        const data = await res.json();
        setLibraryVideos(data);
      }
    } catch (err) {
      console.error('Failed to fetch library for comparison:', err);
    }
  };

  const fetchSavedComparisons = async () => {
    try {
      const res = await fetch('/api/v1/comparisons');
      if (res.ok) {
        const data = await res.json();
        setSavedComparisons(data);
      }
    } catch (err) {
      console.error('Failed to fetch saved comparisons:', err);
    }
  };

  const runComparison = async (ids: string[]) => {
    if (ids.length < 2) {
      setResult(null);
      setError('Please select at least 2 videos to compare.');
      return;
    }
    if (ids.length > 10) {
      setError('Maximum 10 videos can be compared at once.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/comparisons/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_ids: ids })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to analyze comparison.');
      }
      const data: MultiVideoComparisonResult = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Comparison failed.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelectVideo = (id: string) => {
    let next: string[];
    if (selectedIds.includes(id)) {
      next = selectedIds.filter(x => x !== id);
    } else {
      if (selectedIds.length >= 10) return;
      next = [...selectedIds, id];
    }
    setSelectedIds(next);
    if (next.length >= 2) {
      runComparison(next);
    } else {
      setResult(null);
      setError('Please select at least 2 videos to compare.');
    }
  };

  const handleSaveComparison = async () => {
    if (!saveTitle.trim() || selectedIds.length < 2) return;
    try {
      const res = await fetch('/api/v1/comparisons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: saveTitle.trim(), video_ids: selectedIds })
      });
      if (res.ok) {
        setSaveTitle('');
        setShowSaveModal(false);
        fetchSavedComparisons();
      }
    } catch (err) {
      console.error('Failed to save comparison:', err);
    }
  };

  const handleDeleteSavedComparison = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/v1/comparisons/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchSavedComparisons();
      }
    } catch (err) {
      console.error('Failed to delete saved comparison:', err);
    }
  };

  const handleLoadSaved = (item: ComparisonSavedItem) => {
    const ids = item.videos.map(v => v.video_id);
    setSelectedIds(ids);
    runComparison(ids);
  };

  const getColor = (index: number) => VIDEO_PALETTE[index % VIDEO_PALETTE.length];

  const filteredLibrary = libraryVideos.filter(v => 
    v.title.toLowerCase().includes(pickerSearch.toLowerCase()) ||
    (v.creator?.name && v.creator.name.toLowerCase().includes(pickerSearch.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header & Comparison Controls */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-rose-700 font-bold text-xs uppercase tracking-wider">
              <Scale className="w-4 h-4" />
              <span>Phase 5 Comparison Intelligence</span>
            </div>
            <h2 className="text-2xl font-black text-[#0f172a] mt-1 tracking-tight">Cross-Video Research Workspace</h2>
            <p className="text-xs text-[#475569] mt-0.5 font-medium">
              Deterministic, mathematical comparison across scripts, pacing, visual density, and creator benchmarks.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => setShowPickerModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Select Videos ({selectedIds.length}/10)</span>
            </button>

            {selectedIds.length >= 2 && (
              <button
                onClick={() => setShowSaveModal(true)}
                className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5"
              >
                <Bookmark className="w-3.5 h-3.5 text-slate-700" />
                <span>Save Set</span>
              </button>
            )}

            {savedComparisons.length > 0 && (
              <div className="relative group">
                <button className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5">
                  <BookmarkCheck className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Saved Sets ({savedComparisons.length})</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                </button>
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-300 py-2 z-30 hidden group-hover:block divide-y divide-slate-100">
                  {savedComparisons.map(sc => (
                    <div
                      key={sc.id}
                      onClick={() => handleLoadSaved(sc)}
                      className="px-4 py-2.5 hover:bg-indigo-50 cursor-pointer flex items-center justify-between group/item transition-colors"
                    >
                      <div className="truncate pr-2">
                        <p className="text-xs font-bold text-[#0f172a] truncate">{sc.title}</p>
                        <p className="text-[11px] text-[#475569]">{sc.videos.length} videos</p>
                      </div>
                      <button
                        onClick={(e) => handleDeleteSavedComparison(sc.id, e)}
                        className="text-slate-400 hover:text-rose-600 p-1 transition-colors"
                        title="Delete saved comparison"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Selected Video Chips */}
        {selectedIds.length > 0 ? (
          <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-slate-200">
            <span className="text-xs font-bold text-[#475569] mr-1">Active Set:</span>
            {selectedIds.map((vid, idx) => {
              const vSummary = result?.videos.find(v => v.id === vid) || libraryVideos.find(v => v.id === vid);
              const color = getColor(idx);
              return (
                <div
                  key={vid}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border ${color.border} ${color.bg} shadow-2xs`}
                >
                  <span className={`w-2.5 h-2.5 rounded-full ${color.dot}`} />
                  <span 
                    onClick={() => onOpenVideoDetail && onOpenVideoDetail(vid)}
                    className={`text-xs font-bold ${color.text} max-w-[200px] truncate cursor-pointer hover:underline`}
                  >
                    {vSummary ? vSummary.title : vid.slice(0, 8)}
                  </span>
                  <button
                    onClick={() => toggleSelectVideo(vid)}
                    className="text-slate-400 hover:text-rose-600 transition-colors ml-0.5"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
            <button
              onClick={() => { setSelectedIds([]); setResult(null); setError(null); }}
              className="text-xs font-bold text-rose-600 hover:text-rose-700 underline underline-offset-2 ml-2"
            >
              Clear All
            </button>
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center">
            <Scale className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-bold text-[#0f172a]">No videos selected for comparison</p>
            <p className="text-xs text-[#475569] mt-1 max-w-md mx-auto">
              Select 2 to 10 videos from your Library to compare metadata, transcript vocabulary, pacing rate, visual cuts, and timeline progression.
            </p>
            <button
              onClick={() => setShowPickerModal(true)}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm inline-flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Browse Library Videos</span>
            </button>
          </div>
        )}
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="p-12 rounded-2xl bg-white border border-slate-300 shadow-sm text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
          <p className="text-sm font-bold text-[#0f172a]">Computing Cross-Video Intelligence...</p>
          <p className="text-xs text-[#475569]">Calculating duration-normalized speech rates, visual cut density, and vocabulary overlap.</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-800 text-xs font-medium flex items-center gap-2">
          <Info className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Comparison Dashboard */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Sub-Navigation Tabs */}
          <div className="flex items-center gap-1.5 bg-white p-1.5 rounded-2xl border border-slate-300 shadow-sm overflow-x-auto">
            {[
              { id: 'matrix', label: 'Overview Matrix', icon: SlidersHorizontal },
              { id: 'script', label: 'Script Intelligence', icon: FileText },
              { id: 'openings', label: 'Openings & Closings', icon: BookOpen },
              { id: 'language', label: 'Language & N-Grams', icon: TrendingUp },
              { id: 'visuals', label: 'Visual Pacing', icon: Film },
              { id: 'timeline', label: '0–100% Timeline Overlay', icon: Activity },
              { id: 'creators', label: 'Creator Benchmarks', icon: Users },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeSubTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveSubTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-[#334155] hover:text-[#0f172a] hover:bg-slate-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* 1. Overview Matrix Sub-Tab */}
          {activeSubTab === 'matrix' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Multi-Video Comparison Matrix</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Direct side-by-side metric inspection with highest/lowest badges across available properties.
                  </p>
                </div>
                <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl border border-slate-300 self-start">
                  <button
                    onClick={() => setMatrixMode('raw')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                      matrixMode === 'raw' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                    }`}
                  >
                    Raw Values
                  </button>
                  <button
                    onClick={() => setMatrixMode('normalized')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                      matrixMode === 'normalized' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                    }`}
                  >
                    Duration Normalized (/min)
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-300">
                <table className="w-full text-left text-xs text-[#0f172a]">
                  <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                    <tr>
                      <th className="py-3.5 px-4 w-64 bg-slate-100/70 border-r border-slate-300">Metric Category</th>
                      {result.videos.map((v, idx) => {
                        const color = getColor(idx);
                        return (
                          <th key={v.id} className="py-3.5 px-4 min-w-[200px] border-r border-slate-200 last:border-r-0">
                            <div className="flex items-center gap-2">
                              <span className={`w-2.5 h-2.5 rounded-full ${color.dot} shrink-0`} />
                              <div className="truncate">
                                <p className="font-bold text-[#0f172a] truncate">{v.title}</p>
                                <p className="text-[10px] text-[#475569] font-normal">{v.creator_name || v.platform}</p>
                              </div>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {result.matrix.map((row) => (
                      <tr key={row.key} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-bold text-[#0f172a] bg-slate-50/50 border-r border-slate-300">
                          <div className="flex items-center justify-between">
                            <span>{row.label}</span>
                            <span className="text-[10px] font-mono text-[#64748b] uppercase font-normal">{row.category}</span>
                          </div>
                        </td>
                        {result.videos.map((v) => {
                          const cell = row.values[v.id];
                          if (!cell) return <td key={v.id} className="py-3 px-4 text-slate-400 font-mono">—</td>;

                          const isNormalized = matrixMode === 'normalized' && cell.normalized_per_min !== null && cell.normalized_per_min !== undefined;
                          const display = isNormalized ? `${cell.normalized_per_min} /min` : cell.display_value;

                          return (
                            <td key={v.id} className="py-3 px-4 font-medium border-r border-slate-200 last:border-r-0">
                              <div className="flex items-center justify-between gap-2">
                                <span className={`${
                                  cell.status === 'NOT_ANALYZED' 
                                    ? 'text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-semibold border border-amber-200' 
                                    : cell.status === 'UNAVAILABLE' 
                                      ? 'text-slate-400 italic text-[11px]' 
                                      : 'text-[#0f172a] font-bold'
                                }`}>
                                  {display}
                                </span>

                                {cell.status === 'AVAILABLE' && (cell.is_max || cell.is_min) && (
                                  <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded shrink-0 ${
                                    cell.is_max 
                                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                                  }`}>
                                    {cell.is_max ? 'MAX' : 'MIN'}
                                  </span>
                                )}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 2. Script Intelligence Sub-Tab */}
          {activeSubTab === 'script' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {result.videos.map((v, idx) => {
                  const color = getColor(idx);
                  const vocab = result.video_vocabularies[v.id];
                  const wpmCell = result.matrix.find(r => r.key === 'wpm')?.values[v.id];
                  const wordsCell = result.matrix.find(r => r.key === 'word_count')?.values[v.id];
                  const ttrCell = result.matrix.find(r => r.key === 'vocabulary_richness')?.values[v.id];
                  const qCell = result.matrix.find(r => r.key === 'questions')?.values[v.id];

                  return (
                    <div key={v.id} className={`p-5 rounded-2xl bg-white border-2 ${color.border} shadow-sm space-y-4`}>
                      <div className="flex items-center gap-2.5 pb-2 border-b border-slate-200">
                        <span className={`w-3.5 h-3.5 rounded-full ${color.dot} shrink-0`} />
                        <div className="truncate">
                          <h4 className="text-sm font-black text-[#0f172a] truncate">{v.title}</h4>
                          <p className="text-xs text-[#475569] font-medium">{v.creator_name || v.platform}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Speech Rate</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{wpmCell?.display_value || '—'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Total Words</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{wordsCell?.display_value || '—'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Vocab Richness (TTR)</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{ttrCell?.display_value || '—'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Questions Asked</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{qCell?.display_value || '—'}</p>
                        </div>
                      </div>

                      {vocab && vocab.signature_words.length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-[#334155] uppercase tracking-wider mb-2">Distinct Key Terms</p>
                          <div className="flex flex-wrap gap-1.5">
                            {vocab.signature_words.slice(0, 8).map(sw => (
                              <span key={sw.word} className={`px-2 py-0.5 rounded text-[11px] font-bold border ${color.border} ${color.bg} ${color.text}`}>
                                {sw.word} ({sw.count})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 3. Openings & Closings Sub-Tab */}
          {activeSubTab === 'openings' && (
            <div className="space-y-6">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Opening Hook vs Closing Structure</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Side-by-side extracts of the first 10% (Hook) and last 10% (Call-to-Action) of each video with pacing rates.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {result.openings_closings.map((oc, idx) => {
                    const color = getColor(idx);
                    return (
                      <div key={oc.video_id} className={`p-5 rounded-2xl bg-white border-2 ${color.border} shadow-sm space-y-4`}>
                        <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
                          <span className={`w-3 h-3 rounded-full ${color.dot} shrink-0`} />
                          <h4 className="text-sm font-black text-[#0f172a] truncate">{oc.title}</h4>
                        </div>

                        {oc.status === 'AVAILABLE' ? (
                          <div className="space-y-4">
                            {/* Opening Hook */}
                            <div className="p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-indigo-950 uppercase tracking-wide">Opening Hook (First {oc.opening_duration_sec}s)</span>
                                <span className="px-2 py-0.5 rounded bg-indigo-600 text-white text-[10px] font-bold">{oc.opening_wpm} WPM</span>
                              </div>
                              <p className="text-xs text-[#1e293b] leading-relaxed italic bg-white p-2.5 rounded-lg border border-indigo-100">
                                "{oc.opening_text || 'No spoken words in opening window.'}"
                              </p>
                            </div>

                            {/* Closing Outro */}
                            <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-amber-950 uppercase tracking-wide">Closing Outro (Last {oc.closing_duration_sec}s)</span>
                                <span className="px-2 py-0.5 rounded bg-amber-600 text-white text-[10px] font-bold">{oc.closing_wpm} WPM</span>
                              </div>
                              <p className="text-xs text-[#1e293b] leading-relaxed italic bg-white p-2.5 rounded-lg border border-amber-100">
                                "{oc.closing_text || 'No spoken words in closing window.'}"
                              </p>
                            </div>
                          </div>
                        ) : (
                          <div className="p-6 text-center text-xs text-amber-700 bg-amber-50 rounded-xl border border-amber-200">
                            Transcript not analyzed for this video.
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* 4. Language & N-Grams Sub-Tab */}
          {activeSubTab === 'language' && (
            <div className="space-y-6">
              {/* Shared Vocabulary Table */}
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Shared Vocabulary Matrix</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Keywords appearing across multiple videos in the comparison set (stop words removed).
                  </p>
                </div>

                {result.shared_vocabulary.length > 0 ? (
                  <div className="overflow-x-auto rounded-xl border border-slate-300">
                    <table className="w-full text-left text-xs text-[#0f172a]">
                      <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                        <tr>
                          <th className="py-3 px-4">Shared Term</th>
                          <th className="py-3 px-4">In # Videos</th>
                          <th className="py-3 px-4">Total Frequency</th>
                          {result.videos.map((v) => (
                            <th key={v.id} className="py-3 px-4 font-bold text-[#0f172a]">
                              {v.title.slice(0, 15)}...
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {result.shared_vocabulary.slice(0, 20).map(item => (
                          <tr key={item.word} className="hover:bg-slate-50 transition-colors">
                            <td className="py-2.5 px-4 font-bold font-mono text-indigo-700 capitalize">{item.word}</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{item.video_count} / {result.videos.length}</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{item.total_count}</td>
                            {result.videos.map(v => (
                              <td key={v.id} className="py-2.5 px-4 font-medium text-[#334155]">
                                {item.counts[v.id] || 0}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic p-4 bg-slate-50 rounded-xl border border-slate-200">
                    No significant shared vocabulary found across these transcripts.
                  </p>
                )}
              </div>

              {/* Side-by-Side N-Grams */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {result.videos.map((v, idx) => {
                  const color = getColor(idx);
                  const vocab = result.video_vocabularies[v.id];
                  if (!vocab) return null;

                  return (
                    <div key={v.id} className={`p-5 rounded-2xl bg-white border-2 ${color.border} shadow-sm space-y-4`}>
                      <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
                        <span className={`w-3 h-3 rounded-full ${color.dot} shrink-0`} />
                        <h4 className="text-sm font-black text-[#0f172a] truncate">{v.title}</h4>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs font-bold text-[#334155] uppercase tracking-wider mb-2">Top 2-Word Phrases</p>
                          <div className="space-y-1.5">
                            {vocab.top_bigrams.length > 0 ? (
                              vocab.top_bigrams.slice(0, 5).map(bg => (
                                <div key={bg.ngram} className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                                  <span className="font-medium text-[#0f172a] truncate">{bg.ngram}</span>
                                  <span className="font-bold text-indigo-700 shrink-0 ml-2">×{bg.count}</span>
                                </div>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400 italic">None</span>
                            )}
                          </div>
                        </div>

                        <div>
                          <p className="text-xs font-bold text-[#334155] uppercase tracking-wider mb-2">Top 3-Word Phrases</p>
                          <div className="space-y-1.5">
                            {vocab.top_trigrams.length > 0 ? (
                              vocab.top_trigrams.slice(0, 5).map(tg => (
                                <div key={tg.ngram} className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                                  <span className="font-medium text-[#0f172a] truncate">{tg.ngram}</span>
                                  <span className="font-bold text-indigo-700 shrink-0 ml-2">×{tg.count}</span>
                                </div>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400 italic">None</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 5. Visual Pacing Sub-Tab */}
          {activeSubTab === 'visuals' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div>
                <h3 className="text-base font-bold text-[#0f172a]">Visual Pacing & Scene Change Comparison</h3>
                <p className="text-xs text-[#475569] mt-0.5">
                  Side-by-side scene cut rates, average shot durations, and technical properties.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {result.videos.map((v, idx) => {
                  const color = getColor(idx);
                  const cutsCell = result.matrix.find(r => r.key === 'scene_changes')?.values[v.id];
                  const cutRateCell = result.matrix.find(r => r.key === 'cut_rate')?.values[v.id];
                  const avgShotCell = result.matrix.find(r => r.key === 'avg_shot_duration')?.values[v.id];
                  const resCell = result.matrix.find(r => r.key === 'resolution')?.values[v.id];
                  const fpsCell = result.matrix.find(r => r.key === 'fps')?.values[v.id];

                  return (
                    <div key={v.id} className={`p-5 rounded-2xl bg-white border-2 ${color.border} shadow-sm space-y-4`}>
                      <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
                        <span className={`w-3 h-3 rounded-full ${color.dot} shrink-0`} />
                        <div className="truncate">
                          <h4 className="text-sm font-black text-[#0f172a] truncate">{v.title}</h4>
                          <p className="text-xs text-[#475569] font-medium">{v.creator_name || v.platform}</p>
                        </div>
                      </div>

                      {v.has_visual_metrics ? (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-3">
                            <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200">
                              <p className="text-[11px] font-bold text-amber-900 uppercase">Cut Rate</p>
                              <p className="text-xl font-black text-[#0f172a] mt-1">{cutRateCell?.display_value || '—'}</p>
                            </div>
                            <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200">
                              <p className="text-[11px] font-bold text-amber-900 uppercase">Avg Shot Length</p>
                              <p className="text-xl font-black text-[#0f172a] mt-1">{avgShotCell?.display_value || '—'}</p>
                            </div>
                          </div>

                          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
                            <div className="flex justify-between">
                              <span className="text-[#475569] font-medium">Total Scene Cuts:</span>
                              <span className="font-bold text-[#0f172a]">{cutsCell?.display_value}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#475569] font-medium">Resolution:</span>
                              <span className="font-bold text-[#0f172a]">{resCell?.display_value}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#475569] font-medium">Frame Rate:</span>
                              <span className="font-bold text-[#0f172a]">{fpsCell?.display_value}</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="p-6 text-center text-xs text-amber-700 bg-amber-50 rounded-xl border border-amber-200">
                          Visual metrics not yet analyzed for this video.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 6. Normalized 0–100% Timeline Overlay Sub-Tab */}
          {activeSubTab === 'timeline' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Normalized 0–100% Video Progress Curve</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Resampled across 10 uniform progress deciles for fair comparison between short reels and long videos.
                  </p>
                </div>
                <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl border border-slate-300 self-start">
                  <button
                    onClick={() => setTimelineMetric('wpm')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                      timelineMetric === 'wpm' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                    }`}
                  >
                    Speaking Rate (WPM)
                  </button>
                  <button
                    onClick={() => setTimelineMetric('cuts_per_minute')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                      timelineMetric === 'cuts_per_minute' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                    }`}
                  >
                    Cut Density (cuts/min)
                  </button>
                  <button
                    onClick={() => setTimelineMetric('words')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                      timelineMetric === 'words' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                    }`}
                  >
                    Words per Decile
                  </button>
                </div>
              </div>

              {/* Deciles Comparison Chart Table */}
              <div className="space-y-3">
                {result.timeline_deciles.map(pt => (
                  <div key={pt.decile} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-[#0f172a] font-mono tracking-wider bg-white px-2 py-0.5 rounded border border-slate-300">
                        {pt.decile_label} Video Progress
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
                      {result.videos.map((v, idx) => {
                        const color = getColor(idx);
                        const s = pt.series[v.id];
                        const val = s ? (s as any)[timelineMetric] : 0;
                        const maxVal = Math.max(...result.timeline_deciles.map(d => (d.series[v.id] as any)?.[timelineMetric] || 0), 1);
                        const pct = Math.min(Math.round((val / maxVal) * 100), 100);

                        return (
                          <div key={v.id} className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className={`font-bold ${color.text} truncate max-w-[140px]`}>{v.title}</span>
                              <span className="font-mono font-black text-[#0f172a]">
                                {val} {timelineMetric === 'wpm' ? 'wpm' : timelineMetric === 'cuts_per_minute' ? '/min' : 'w'}
                              </span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                              <div
                                className={`h-full ${color.bar} transition-all duration-300`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7. Creator Benchmarks Sub-Tab */}
          {activeSubTab === 'creators' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div>
                <h3 className="text-base font-bold text-[#0f172a]">Creator Aggregate Benchmarks (Library-Bounded)</h3>
                <p className="text-xs text-[#475569] mt-0.5">
                  Mathematical aggregates across all stored Library videos for creators represented in this comparison set.
                </p>
              </div>

              {result.creator_aggregates.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {result.creator_aggregates.map(ca => (
                    <div key={ca.creator_id || ca.creator_name} className="p-5 rounded-2xl bg-white border-2 border-indigo-200 shadow-sm space-y-4">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                        <div>
                          <h4 className="text-base font-black text-[#0f172a]">{ca.creator_name}</h4>
                          <span className="text-[11px] font-bold text-indigo-700 capitalize">{ca.platform} Creator</span>
                        </div>
                        <span className="px-3 py-1 rounded-full bg-indigo-100 text-indigo-900 border border-indigo-300 text-xs font-bold">
                          Sample Size N = {ca.sample_size_n}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Duration</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{Math.round(ca.mean_duration_seconds)}s</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Median Duration</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{Math.round(ca.median_duration_seconds)}s</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Speaking Rate</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_wpm ? `${ca.mean_wpm} WPM` : 'Not Analyzed'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Cut Rate</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_cut_rate_per_min ? `${ca.mean_cut_rate_per_min} /min` : 'Not Analyzed'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic p-4 bg-slate-50 rounded-xl border border-slate-200">
                  No recognized creators associated with the selected videos.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Video Picker Modal */}
      {showPickerModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-300 shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="text-base font-black text-[#0f172a]">Select Videos to Compare</h3>
                <p className="text-xs text-[#475569] mt-0.5 font-medium">Choose between 2 and 10 videos from your Library.</p>
              </div>
              <button
                onClick={() => setShowPickerModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Input */}
            <div className="p-4 border-b border-slate-200 bg-white">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search library by title or creator..."
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs font-medium text-[#0f172a] focus:bg-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Video List */}
            <div className="overflow-y-auto p-4 space-y-2 flex-1 divide-y divide-slate-100">
              {filteredLibrary.map((v) => {
                const isSelected = selectedIds.includes(v.id);
                return (
                  <div
                    key={v.id}
                    onClick={() => toggleSelectVideo(v.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-indigo-50/80 border-indigo-400 shadow-2xs'
                        : 'bg-white hover:bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-4">
                      <div className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-slate-300 bg-white'
                      }`}>
                        {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-[#0f172a] truncate">{v.title}</p>
                        <div className="flex items-center gap-2 text-[11px] text-[#475569] mt-0.5">
                          <span className="capitalize font-semibold">{v.platform}</span>
                          <span>•</span>
                          <span>{Math.round(v.duration_seconds)}s</span>
                          {v.creator?.name && (
                            <>
                              <span>•</span>
                              <span className="font-medium">{v.creator.name}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {v.has_transcript && (
                        <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-800 text-[10px] font-bold border border-purple-200">
                          Transcript
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <span className="text-xs font-bold text-[#0f172a]">
                {selectedIds.length} of 10 selected
              </span>
              <button
                onClick={() => setShowPickerModal(false)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Set Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-300 shadow-2xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-black text-[#0f172a]">Save Comparison Set</h3>
            <p className="text-xs text-[#475569]">Save this {selectedIds.length}-video comparison group for fast recall.</p>
            
            <input
              type="text"
              placeholder="e.g. YouTube Tech Explainers Benchmark"
              value={saveTitle}
              onChange={(e) => setSaveTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-300 text-xs font-medium text-[#0f172a] focus:bg-white focus:outline-none focus:border-indigo-500"
            />

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowSaveModal(false)}
                className="px-4 py-2 text-xs font-bold text-[#475569] hover:bg-slate-100 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveComparison}
                disabled={!saveTitle.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm transition-colors"
              >
                Save Group
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
