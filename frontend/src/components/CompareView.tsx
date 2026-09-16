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
  SlidersHorizontal,
  AlertTriangle,
  Image,
  Type,
  Edit2,
  MessageSquare,
  ThumbsUp,
  Eye,
  AlignLeft
} from 'lucide-react';
import type { 
  VideoSummary, 
  MultiVideoComparisonResult, 
  ComparisonSavedItem
} from '../types';
import { ErrorBoundary } from './ErrorBoundary';
import { ScriptWorkspace } from './script_comparison/ScriptWorkspace';

interface CompareViewProps {
  initialVideoIds?: string[];
  onOpenVideoDetail?: (videoId: string) => void;
}

const VIDEO_PALETTE = [
  { name: 'Indigo', border: 'border-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-950', badge: 'bg-indigo-600 text-white', bar: 'bg-indigo-600', dot: 'bg-indigo-600', fill: '#4f46e5', ring: 'ring-indigo-300' },
  { name: 'Emerald', border: 'border-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-950', badge: 'bg-emerald-600 text-white', bar: 'bg-emerald-600', dot: 'bg-emerald-600', fill: '#059669', ring: 'ring-emerald-300' },
  { name: 'Amber', border: 'border-amber-500', bg: 'bg-amber-50', text: 'text-amber-950', badge: 'bg-amber-600 text-white', bar: 'bg-amber-600', dot: 'bg-amber-600', fill: '#d97706', ring: 'ring-amber-300' },
  { name: 'Rose', border: 'border-rose-500', bg: 'bg-rose-50', text: 'text-rose-950', badge: 'bg-rose-600 text-white', bar: 'bg-rose-600', dot: 'bg-rose-600', fill: '#e11d48', ring: 'ring-rose-300' },
  { name: 'Cyan', border: 'border-cyan-500', bg: 'bg-cyan-50', text: 'text-cyan-950', badge: 'bg-cyan-600 text-white', bar: 'bg-cyan-600', dot: 'bg-cyan-600', fill: '#0891b2', ring: 'ring-cyan-300' },
  { name: 'Violet', border: 'border-violet-500', bg: 'bg-violet-50', text: 'text-violet-950', badge: 'bg-violet-600 text-white', bar: 'bg-violet-600', dot: 'bg-violet-600', fill: '#7c3aed', ring: 'ring-violet-300' },
  { name: 'Blue', border: 'border-blue-500', bg: 'bg-blue-50', text: 'text-blue-950', badge: 'bg-blue-600 text-white', bar: 'bg-blue-600', dot: 'bg-blue-600', fill: '#2563eb', ring: 'ring-blue-300' },
  { name: 'Orange', border: 'border-orange-500', bg: 'bg-orange-50', text: 'text-orange-950', badge: 'bg-orange-600 text-white', bar: 'bg-orange-600', dot: 'bg-orange-600', fill: '#ea580c', ring: 'ring-orange-300' },
  { name: 'Fuchsia', border: 'border-fuchsia-500', bg: 'bg-fuchsia-50', text: 'text-fuchsia-950', badge: 'bg-fuchsia-600 text-white', bar: 'bg-fuchsia-600', dot: 'bg-fuchsia-600', fill: '#c026d3', ring: 'ring-fuchsia-300' },
  { name: 'Slate', border: 'border-slate-500', bg: 'bg-slate-100', text: 'text-slate-950', badge: 'bg-slate-700 text-white', bar: 'bg-slate-700', dot: 'bg-slate-700', fill: '#334155', ring: 'ring-slate-300' },
];

export function CompareView({ initialVideoIds = [], onOpenVideoDetail }: CompareViewProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialVideoIds);
  const [libraryVideos, setLibraryVideos] = useState<VideoSummary[]>([]);
  const [savedComparisons, setSavedComparisons] = useState<ComparisonSavedItem[]>([]);
  const [result, setResult] = useState<MultiVideoComparisonResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sub-tab Navigation
  const [activeSubTab, setActiveSubTab] = useState<
    'matrix' | 'script_workspace' | 'engagement' | 'script' | 'openings' | 'language' | 'visuals' | 'timeline' | 'keyframes' | 'ocr' | 'creators'
  >('matrix');

  // Modals & Controls
  const [showPickerModal, setShowPickerModal] = useState<boolean>(false);
  const [showSaveModal, setShowSaveModal] = useState<boolean>(false);
  const [saveTitle, setSaveTitle] = useState<string>('');
  const [saveNotes, setSaveNotes] = useState<string>('');
  const [pickerSearch, setPickerSearch] = useState<string>('');
  const [matrixMode, setMatrixMode] = useState<'raw' | 'normalized'>('raw');
  const [matrixCategoryFilter, setMatrixCategoryFilter] = useState<string>('all');
  const [timelineMetric, setTimelineMetric] = useState<'wpm' | 'words' | 'cuts_per_minute' | 'scene_changes'>('wpm');
  const [editingSavedId, setEditingSavedId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState<string>('');

  useEffect(() => {
    fetchLibrary();
    fetchSavedComparisons();
  }, []);

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
      console.error('Failed to fetch library:', err);
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
      setError('Maximum 10 videos can be compared simultaneously.');
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
      setError(err.message || 'Comparison calculation failed.');
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
        body: JSON.stringify({
          title: saveTitle.trim(),
          notes: saveNotes.trim() || null,
          video_ids: selectedIds
        })
      });
      if (res.ok) {
        setSaveTitle('');
        setSaveNotes('');
        setShowSaveModal(false);
        fetchSavedComparisons();
      }
    } catch (err) {
      console.error('Failed to save comparison:', err);
    }
  };

  const handleUpdateSavedTitle = async (id: string) => {
    if (!editTitle.trim()) return;
    try {
      const res = await fetch(`/api/v1/comparisons/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle.trim() })
      });
      if (res.ok) {
        setEditingSavedId(null);
        setEditTitle('');
        fetchSavedComparisons();
      }
    } catch (err) {
      console.error('Failed to rename comparison:', err);
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

  const categories = result ? Array.from(new Set(result.matrix.map(r => r.category))) : [];
  const filteredMatrix = result ? result.matrix.filter(r => 
    matrixCategoryFilter === 'all' || r.category === matrixCategoryFilter
  ) : [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-20">
      {/* Top Header & Comparison Controls */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
              <Scale className="w-4 h-4" />
              <span>Phase 5 Comparison Intelligence</span>
            </div>
            <h2 className="text-2xl font-black text-[#0f172a] mt-1 tracking-tight">Cross-Video Research Workspace</h2>
            <p className="text-xs text-[#475569] mt-0.5 font-medium">
              Deterministic comparison across 2 to 10 stored library videos using persisted analysis records.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => setShowPickerModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Select Videos ({selectedIds.length}/10)</span>
            </button>

            {selectedIds.length >= 2 && (
              <button
                onClick={() => setShowSaveModal(true)}
                className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Bookmark className="w-3.5 h-3.5 text-slate-700" />
                <span>Save Set</span>
              </button>
            )}

            {savedComparisons.length > 0 && (
              <div className="relative group">
                <button className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5 cursor-pointer">
                  <BookmarkCheck className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Saved Sets ({savedComparisons.length})</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                </button>
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-300 py-2 z-30 hidden group-hover:block divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {savedComparisons.map(sc => (
                    <div
                      key={sc.id}
                      onClick={() => handleLoadSaved(sc)}
                      className="px-4 py-2.5 hover:bg-indigo-50 cursor-pointer flex items-center justify-between group/item transition-colors"
                    >
                      <div className="truncate pr-2">
                        {editingSavedId === sc.id ? (
                          <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <input
                              type="text"
                              value={editTitle}
                              onChange={e => setEditTitle(e.target.value)}
                              className="text-xs px-1.5 py-0.5 border rounded border-indigo-400 w-36"
                              autoFocus
                            />
                            <button
                              onClick={() => handleUpdateSavedTitle(sc.id)}
                              className="text-[10px] bg-indigo-600 text-white px-1.5 py-0.5 rounded font-bold"
                            >
                              Save
                            </button>
                          </div>
                        ) : (
                          <>
                            <p className="text-xs font-bold text-[#0f172a] truncate">{sc.title}</p>
                            <p className="text-[11px] text-[#475569]">{sc.videos.length} videos</p>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingSavedId(sc.id);
                            setEditTitle(sc.title);
                          }}
                          className="text-slate-400 hover:text-indigo-600 p-1 transition-colors"
                          title="Rename saved comparison"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteSavedComparison(sc.id, e)}
                          className="text-slate-400 hover:text-rose-600 p-1 transition-colors"
                          title="Delete saved comparison"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
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
                    className="text-slate-400 hover:text-rose-600 transition-colors ml-0.5 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
            <button
              onClick={() => { setSelectedIds([]); setResult(null); setError(null); }}
              className="text-xs font-bold text-rose-600 hover:text-rose-700 underline underline-offset-2 ml-2 cursor-pointer"
            >
              Clear All
            </button>
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center">
            <Scale className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-bold text-[#0f172a]">No videos selected for comparison</p>
            <p className="text-xs text-[#475569] mt-1 max-w-md mx-auto">
              Select 2 to 10 videos from your Library to compare metadata, transcripts, speech pacing, visual cuts, and timelines side-by-side.
            </p>
            <button
              onClick={() => setShowPickerModal(true)}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm inline-flex items-center gap-1.5 cursor-pointer"
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
          <p className="text-xs text-[#475569]">Analyzing duration-normalized speech rates, visual cut density, and multilingual vocabulary overlap.</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-800 text-xs font-medium flex items-center gap-2">
          <Info className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Comparison Workspace */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Cross-Language Warning Banner */}
          {result.has_mixed_languages && (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3 shadow-2xs">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-amber-950">Cross-Language Comparison Notice</h4>
                <p className="text-xs text-amber-800 mt-0.5">
                  Transcripts in this comparison set use multiple languages ({result.detected_languages.join(', ')}). Lexical overlap is limited to direct loanwords or cognates, while pacing (WPM), scene cuts, and engagement metrics remain fully comparable.
                </p>
              </div>
            </div>
          )}

          {/* Sub-Navigation Tabs */}
          <div className="flex items-center gap-1.5 bg-white p-1.5 rounded-2xl border border-slate-300 shadow-sm overflow-x-auto">
            {[
              { id: 'matrix', label: 'Comparison Matrix', icon: SlidersHorizontal },
              { id: 'script_workspace', label: 'Script Workspace', icon: AlignLeft },
              { id: 'engagement', label: 'Engagement', icon: Eye },
              { id: 'script', label: 'Script Intelligence', icon: FileText },
              { id: 'openings', label: 'Openings & Closings', icon: BookOpen },
              { id: 'language', label: 'Vocabulary & Phrases', icon: TrendingUp },
              { id: 'visuals', label: 'Visual Pacing', icon: Film },
              { id: 'keyframes', label: 'Keyframe Gallery', icon: Image },
              { id: 'timeline', label: '0–100% Timeline Overlay', icon: Activity },
              { id: 'ocr', label: 'OCR Evidence', icon: Type },
              { id: 'creators', label: 'Creator Benchmarks', icon: Users },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeSubTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveSubTab(tab.id as any)}
                  className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
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
                    Side-by-side metric inspection with highest (MAX) and lowest (MIN) badges across numerical properties.
                  </p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  {/* Category Filter */}
                  <div className="flex items-center gap-1.5 text-xs font-bold text-[#475569]">
                    <span>Category:</span>
                    <select
                      value={matrixCategoryFilter}
                      onChange={e => setMatrixCategoryFilter(e.target.value)}
                      className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-300 text-xs font-bold text-[#0f172a] focus:outline-none"
                    >
                      <option value="all">All Categories ({result.matrix.length})</option>
                      {categories.map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>

                  {/* Raw vs Normalized Toggle */}
                  <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-300">
                    <button
                      onClick={() => setMatrixMode('raw')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        matrixMode === 'raw' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      Raw Values
                    </button>
                    <button
                      onClick={() => setMatrixMode('normalized')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        matrixMode === 'normalized' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      Duration Normalized (/min)
                    </button>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-300 max-h-[70vh]">
                <table className="w-full text-left text-xs text-[#0f172a] border-collapse">
                  <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300 sticky top-0 z-20">
                    <tr>
                      <th className="py-3.5 px-4 w-64 bg-slate-100 border-r border-slate-300 sticky left-0 z-30 shadow-r">Metric Category</th>
                      {result.videos.map((v, idx) => {
                        const color = getColor(idx);
                        return (
                          <th key={v.id} className="py-3.5 px-4 min-w-[200px] border-r border-slate-200 last:border-r-0 bg-[#f8fafc]">
                            <div className="flex items-center gap-2">
                              <span className={`w-2.5 h-2.5 rounded-full ${color.dot} shrink-0`} />
                              <div className="truncate">
                                <p 
                                  onClick={() => onOpenVideoDetail && onOpenVideoDetail(v.id)}
                                  className="font-bold text-[#0f172a] truncate hover:text-indigo-600 hover:underline cursor-pointer"
                                >
                                  {v.title}
                                </p>
                                <p className="text-[10px] text-[#475569] font-normal">{v.creator_name || v.platform}</p>
                              </div>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {filteredMatrix.map((row) => (
                      <tr key={row.key} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-bold text-[#0f172a] bg-slate-50 border-r border-slate-300 sticky left-0 z-10 shadow-r">
                          <div className="flex items-center justify-between gap-2">
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
                                    ? 'text-amber-800 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-semibold border border-amber-200' 
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

          {/* Script Workspace Sub-Tab (Phase 5.3B Horizontal Script Comparison Desk) */}
          {activeSubTab === 'script_workspace' && (
            <ScriptWorkspace
              selectedVideoIds={selectedIds}
              palette={VIDEO_PALETTE}
              onOpenVideoDetail={onOpenVideoDetail}
            />
          )}

          {/* 2. Engagement Sub-Tab */}
          {activeSubTab === 'engagement' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {result.videos.map((v, idx) => {
                  const color = getColor(idx);
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
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569] uppercase">
                            <Eye className="w-3.5 h-3.5 text-indigo-600" />
                            <span>Total Views</span>
                          </div>
                          <p className="text-xl font-black text-[#0f172a] mt-1">
                            {v.views !== null && v.views !== undefined ? Number(v.views).toLocaleString() : 'Unavailable'}
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569] uppercase">
                            <ThumbsUp className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Total Likes</span>
                          </div>
                          <p className="text-xl font-black text-[#0f172a] mt-1">
                            {v.likes !== null && v.likes !== undefined ? Number(v.likes).toLocaleString() : 'Unavailable'}
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569] uppercase">
                            <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                            <span>Comments</span>
                          </div>
                          <p className="text-xl font-black text-[#0f172a] mt-1">
                            {v.comments !== null && v.comments !== undefined ? Number(v.comments).toLocaleString() : 'Unavailable'}
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#475569] uppercase">
                            <Activity className="w-3.5 h-3.5 text-purple-600" />
                            <span>Like/View %</span>
                          </div>
                          <p className="text-xl font-black text-[#0f172a] mt-1">
                            {v.like_view_ratio !== null && v.like_view_ratio !== undefined ? `${v.like_view_ratio}%` : 'Unavailable'}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 3. Script Intelligence Sub-Tab */}
          {activeSubTab === 'script' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {result.videos.map((v, idx) => {
                  const color = getColor(idx);
                  const vocab = result.video_vocabularies[v.id];
                  const wpmCell = result.matrix.find(r => r.key === 'wpm')?.values[v.id];
                  const wordsCell = result.matrix.find(r => r.key === 'word_count')?.values[v.id];
                  const ttrCell = result.matrix.find(r => r.key === 'vocabulary_richness')?.values[v.id];
                  const qCell = result.matrix.find(r => r.key === 'questions')?.values[v.id];
                  const exCell = result.matrix.find(r => r.key === 'exclamations')?.values[v.id];
                  const fillCell = result.matrix.find(r => r.key === 'fillers')?.values[v.id];

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
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Exclamations</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{exCell?.display_value || '—'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Filler Words</p>
                          <p className="text-xl font-black text-[#0f172a] mt-1">{fillCell?.display_value || '—'}</p>
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

          {/* 4. Openings & Closings Sub-Tab */}
          {activeSubTab === 'openings' && (
            <div className="space-y-6">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Opening Hook vs Closing Structure</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Deterministic extraction of the opening hook (first 10% / 15s) and closing outro (last 10% / 15s) with speaking rates and question counts.
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
                                <span className="text-xs font-bold text-indigo-950 uppercase tracking-wide">
                                  Opening Hook (First {oc.opening_duration_sec}s)
                                </span>
                                <span className="px-2 py-0.5 rounded bg-indigo-600 text-white text-[10px] font-bold">
                                  {oc.opening_wpm} WPM
                                </span>
                              </div>
                              <p className="text-xs text-[#1e293b] leading-relaxed italic bg-white p-2.5 rounded-lg border border-indigo-100">
                                "{oc.opening_text || 'No spoken words in opening window.'}"
                              </p>
                              <div className="flex items-center justify-between text-[11px] text-[#475569]">
                                <span>Words in first 5s: <strong>{oc.words_in_first_5s}</strong></span>
                                <span>Opening questions: <strong>{oc.opening_questions}</strong></span>
                              </div>
                            </div>

                            {/* Closing Outro */}
                            <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-amber-950 uppercase tracking-wide">
                                  Closing Outro (Last {oc.closing_duration_sec}s)
                                </span>
                                <span className="px-2 py-0.5 rounded bg-amber-600 text-white text-[10px] font-bold">
                                  {oc.closing_wpm} WPM
                                </span>
                              </div>
                              <p className="text-xs text-[#1e293b] leading-relaxed italic bg-white p-2.5 rounded-lg border border-amber-100">
                                "{oc.closing_text || 'No spoken words in closing window.'}"
                              </p>
                              {oc.final_sentence && (
                                <p className="text-[11px] text-[#475569]">
                                  Final sentence: <span className="italic font-medium">"{oc.final_sentence}"</span>
                                </p>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="p-6 text-center text-xs text-amber-800 bg-amber-50 rounded-xl border border-amber-200">
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

          {/* 5. Vocabulary & Phrases Sub-Tab */}
          {activeSubTab === 'language' && (
            <div className="space-y-6">
              {/* Shared Vocabulary Table */}
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">Shared Vocabulary Matrix</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Keywords appearing across multiple videos in the comparison set with average occurrences per 1,000 words.
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
                          <th className="py-3 px-4">Avg / 1k Words</th>
                          {result.videos.map((v) => (
                            <th key={v.id} className="py-3 px-4 font-bold text-[#0f172a]">
                              {v.title.slice(0, 15)}...
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {result.shared_vocabulary.slice(0, 25).map(item => (
                          <tr key={item.word} className="hover:bg-slate-50 transition-colors">
                            <td className="py-2.5 px-4 font-bold font-mono text-indigo-700">{item.word}</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{item.video_count} / {result.videos.length}</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{item.total_count}</td>
                            <td className="py-2.5 px-4 font-mono text-slate-700">{item.occurrences_per_thousand_avg}</td>
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

              {/* Shared Multi-word Phrases */}
              {result.shared_phrases && result.shared_phrases.length > 0 && (
                <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-[#0f172a]">Shared Multi-Word Phrases</h3>
                    <p className="text-xs text-[#475569] mt-0.5">
                      Exact 2 to 4-word phrase matches appearing in more than one video transcript.
                    </p>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-slate-300">
                    <table className="w-full text-left text-xs text-[#0f172a]">
                      <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                        <tr>
                          <th className="py-3 px-4">Shared Phrase</th>
                          <th className="py-3 px-4">Videos</th>
                          <th className="py-3 px-4">Total Count</th>
                          {result.videos.map(v => (
                            <th key={v.id} className="py-3 px-4 font-bold text-[#0f172a]">
                              {v.title.slice(0, 15)}...
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 bg-white">
                        {result.shared_phrases.map(sp => (
                          <tr key={sp.phrase} className="hover:bg-slate-50 transition-colors">
                            <td className="py-2.5 px-4 font-bold text-indigo-900">"{sp.phrase}"</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{sp.video_count} / {result.videos.length}</td>
                            <td className="py-2.5 px-4 font-bold text-[#0f172a]">{sp.total_count}</td>
                            {result.videos.map(v => (
                              <td key={v.id} className="py-2.5 px-4 font-medium text-[#334155]">
                                {sp.counts[v.id] || 0}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

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

          {/* 6. Visual Pacing Sub-Tab */}
          {activeSubTab === 'visuals' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div>
                <h3 className="text-base font-bold text-[#0f172a]">Visual Pacing & Technical Properties</h3>
                <p className="text-xs text-[#475569] mt-0.5">
                  Side-by-side scene cut rates, average shot durations, resolution, and frame rates.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
                        <div className="p-6 text-center text-xs text-amber-800 bg-amber-50 rounded-xl border border-amber-200">
                          Visual metrics not yet analyzed for this video.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 7. Keyframe Gallery Sub-Tab */}
          {activeSubTab === 'keyframes' && (
            <ErrorBoundary fallbackTitle="Keyframe Gallery Error" fallbackMessage="Could not render Keyframe Gallery for the selected videos.">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-6">
                <div>
                  <h3 className="text-base font-bold text-[#0f172a]">0% to 100% Milestone Keyframe Gallery</h3>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Synchronized visual snapshots across videos at 0%, 25%, 50%, 75%, and 100% video progress.
                  </p>
                </div>

                <div className="space-y-6">
                  {(result.videos || []).map((v, idx) => {
                    const color = getColor(idx);
                    const frames = (result.keyframe_gallery && result.keyframe_gallery[v.id]) || [];

                    return (
                      <div key={v.id} className={`p-5 rounded-2xl bg-white border-2 ${color.border} shadow-sm space-y-3`}>
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                          <div className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full ${color.dot}`} />
                            <h4 className="text-sm font-black text-[#0f172a] truncate">{v.title}</h4>
                          </div>
                          <span className="text-xs text-[#475569] font-bold">{Math.round(v.duration_seconds || 0)}s duration</span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                          {frames.map((f, fIdx) => (
                            <div key={f.position_pct ?? fIdx} className="rounded-xl border border-slate-200 bg-slate-50 overflow-hidden space-y-1.5 p-2">
                              <div className="flex items-center justify-between text-[11px] font-bold text-[#475569]">
                                <span>{f.label || `Frame ${f.position_pct}%`} ({f.position_pct ?? 0}%)</span>
                                <span className="font-mono">{f.timestamp !== null && f.timestamp !== undefined ? `${Math.round(f.timestamp || 0)}s` : '—'}</span>
                              </div>
                              <div className="aspect-video bg-slate-200 rounded-lg overflow-hidden flex items-center justify-center border border-slate-300">
                                {f.image_url ? (
                                  <img
                                    src={f.image_url}
                                    alt={f.label || 'Video keyframe'}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                      (e.target as HTMLElement).style.display = 'none';
                                    }}
                                  />
                                ) : (
                                  <div className="flex flex-col items-center gap-1 text-slate-400">
                                    <Image className="w-5 h-5" />
                                    <span className="text-[10px]">{f.status === 'AVAILABLE' ? 'Frame' : 'Not Extracted'}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </ErrorBoundary>
          )}

          {/* 8. Normalized 0–100% Timeline Overlay Sub-Tab */}
          {activeSubTab === 'timeline' && (
            <ErrorBoundary fallbackTitle="Timeline Overlay Error" fallbackMessage="Could not render 0-100% Timeline Overlay for the selected videos.">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
                  <div>
                    <h3 className="text-base font-bold text-[#0f172a]">Normalized 0–100% Video Progress Curves</h3>
                    <p className="text-xs text-[#475569] mt-0.5">
                      Resampled across 10 uniform progress deciles for fair structural comparison between short and long videos.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl border border-slate-300 self-start">
                    <button
                      type="button"
                      onClick={() => setTimelineMetric('wpm')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        timelineMetric === 'wpm' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      Speaking Rate (WPM)
                    </button>
                    <button
                      type="button"
                      onClick={() => setTimelineMetric('cuts_per_minute')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        timelineMetric === 'cuts_per_minute' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      Cut Density (cuts/min)
                    </button>
                    <button
                      type="button"
                      onClick={() => setTimelineMetric('words')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        timelineMetric === 'words' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      Words per Decile
                    </button>
                  </div>
                </div>

                {/* Stacked Visual Cut Density Bar Overlay */}
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-black uppercase tracking-wider text-[#0f172a]">Normalized Visual Cut Strip (0% to 100%)</h4>
                    <span className="text-[11px] text-[#64748b]">Ticks represent scene transition events</span>
                  </div>

                  <div className="space-y-3">
                    {(result.videos || []).map((v, idx) => {
                      const color = getColor(idx);
                      const events = (result.timeline_events && result.timeline_events[v.id]) || [];

                      return (
                        <div key={v.id} className="space-y-1">
                          <div className="flex justify-between text-xs font-bold">
                            <span className={color.text}>{v.title}</span>
                            <span className="text-[#64748b]">{events.length} cut{events.length !== 1 ? 's' : ''}</span>
                          </div>
                          <div className="relative w-full h-5 bg-slate-200 rounded-lg overflow-hidden border border-slate-300">
                            {events.map((ev, i) => {
                              const leftPos = Math.min(Math.max(Number(ev.normalized_position_pct) || 0, 0), 100);
                              return (
                                <div
                                  key={i}
                                  title={`Cut at ${ev.formatted_time || ''} (${leftPos}%)`}
                                  className="absolute top-0 bottom-0 w-1 bg-indigo-600 hover:bg-rose-500 transition-colors cursor-pointer"
                                  style={{ left: `${leftPos}%` }}
                                />
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Deciles Comparison Chart Table */}
                <div className="space-y-3">
                  {(result.timeline_deciles || []).map(pt => (
                    <div key={pt.decile} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-[#0f172a] font-mono tracking-wider bg-white px-2 py-0.5 rounded border border-slate-300">
                          {pt.decile_label} Progress
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
                        {(result.videos || []).map((v, idx) => {
                          const color = getColor(idx);
                          const s = (pt.series && pt.series[v.id]) ? pt.series[v.id] : null;
                          const rawVal = s ? (s as any)[timelineMetric] : 0;
                          const val = typeof rawVal === 'number' && !isNaN(rawVal) && isFinite(rawVal) ? rawVal : 0;
                          
                          const seriesVals = (result.timeline_deciles || []).map(d => {
                            const dSeries = (d.series && d.series[v.id]) ? d.series[v.id] : null;
                            const vVal = dSeries ? (dSeries as any)[timelineMetric] : 0;
                            return typeof vVal === 'number' && !isNaN(vVal) && isFinite(vVal) ? vVal : 0;
                          });
                          const maxVal = Math.max(...seriesVals, 1);
                          const pct = maxVal > 0 ? Math.min(Math.max(Math.round((val / maxVal) * 100), 0), 100) : 0;

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
            </ErrorBoundary>
          )}

          {/* 9. OCR Evidence Sub-Tab */}
          {activeSubTab === 'ocr' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div>
                <h3 className="text-base font-bold text-[#0f172a]">Cross-Video OCR Evidence</h3>
                <p className="text-xs text-[#475569] mt-0.5">
                  Extracted on-screen text detections across the compared videos.
                </p>
              </div>

              {result.ocr_evidence && result.ocr_evidence.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-slate-300">
                  <table className="w-full text-left text-xs text-[#0f172a]">
                    <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                      <tr>
                        <th className="py-3 px-4">Timestamp</th>
                        <th className="py-3 px-4">Video Title</th>
                        <th className="py-3 px-4">Detected On-Screen Text</th>
                        <th className="py-3 px-4">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {result.ocr_evidence.map((item, i) => (
                        <tr key={i} className="hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-4 font-mono font-bold text-indigo-700">{item.formatted_time}</td>
                          <td className="py-2.5 px-4 font-bold text-[#0f172a] max-w-[200px] truncate">{item.video_title}</td>
                          <td className="py-2.5 px-4 font-medium text-[#1e293b]">{item.detected_text}</td>
                          <td className="py-2.5 px-4 font-mono font-bold text-slate-700">{Math.round(item.confidence * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 text-slate-500 text-xs">
                  No OCR text detections recorded for the selected videos.
                </div>
              )}
            </div>
          )}

          {/* 10. Creator Benchmarks Sub-Tab */}
          {activeSubTab === 'creators' && (
            <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
              <div>
                <h3 className="text-base font-bold text-[#0f172a]">Creator Aggregate Benchmarks</h3>
                <p className="text-xs text-[#475569] mt-0.5">
                  Factual aggregates across all stored Library videos for creators represented in this comparison set.
                </p>
                <div className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs font-semibold">
                  <Info className="w-3.5 h-3.5 text-amber-600" />
                  <span>Based on videos in your Library</span>
                </div>
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
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Speech Rate</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_wpm ? `${ca.mean_wpm} WPM` : 'Not Analyzed'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Cut Rate</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_cut_rate_per_min ? `${ca.mean_cut_rate_per_min} /min` : 'Not Analyzed'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Views</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_views ? Number(ca.mean_views).toLocaleString() : 'Unavailable'}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-[11px] font-bold text-[#475569] uppercase">Mean Likes</p>
                          <p className="text-lg font-black text-[#0f172a] mt-1">{ca.mean_likes ? Number(ca.mean_likes).toLocaleString() : 'Unavailable'}</p>
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
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors cursor-pointer"
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
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors cursor-pointer"
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

            <textarea
              placeholder="Optional notes or context..."
              value={saveNotes}
              onChange={(e) => setSaveNotes(e.target.value)}
              rows={3}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs font-medium text-[#0f172a] focus:bg-white focus:outline-none focus:border-indigo-500"
            />

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowSaveModal(false)}
                className="px-4 py-2 text-xs font-bold text-[#475569] hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveComparison}
                disabled={!saveTitle.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm transition-colors cursor-pointer"
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
