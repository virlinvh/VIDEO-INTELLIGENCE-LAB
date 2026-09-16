import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Film, 
  Clock, 
  Eye, 
  FileText, 
  Trash2, 
  ExternalLink,
  SlidersHorizontal,
  Scale,
  Check,
  X
} from 'lucide-react';
import type { VideoSummary } from '../types';

interface Props {
  onOpenVideo: (videoId: string) => void;
  onNavigateToCompare?: (videoIds: string[]) => void;
}

export function LibraryView({ onOpenVideo, onNavigateToCompare }: Props) {
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [transcriptFilter, setTranscriptFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<string>('desc');
  const [loading, setLoading] = useState(true);

  const fetchVideos = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (platformFilter !== 'all') params.append('platform', platformFilter);
      if (transcriptFilter !== 'all') params.append('has_transcript', transcriptFilter === 'true' ? 'true' : 'false');
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);

      const res = await fetch(`/api/v1/videos?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setVideos(data);
      }
    } catch (err) {
      console.error('Failed to load videos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, [search, platformFilter, transcriptFilter, sortBy, sortOrder]);

  const handleDelete = async (e: React.MouseEvent, videoId: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this video research record?')) return;
    try {
      await fetch(`/api/v1/videos/${videoId}`, { method: 'DELETE' });
      setVideos(prev => prev.filter(v => v.id !== videoId));
      setSelectedForCompare(prev => prev.filter(id => id !== videoId));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const toggleSelect = (e: React.MouseEvent, videoId: string) => {
    e.stopPropagation();
    setSelectedForCompare(prev => 
      prev.includes(videoId) ? prev.filter(id => id !== videoId) : [...prev, videoId]
    );
  };

  const formatDuration = (seconds: number) => {
    if (seconds <= 0) return '0s';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}h ${mins}m`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24">
      {/* Header Area */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-slate-300 shadow-sm">
        <div>
          <h2 className="text-2xl font-black text-[#0f172a] tracking-tight">Research Library</h2>
          <p className="text-xs text-[#475569] mt-0.5 font-medium">
            Locally stored video transcripts, factual metadata, and computed intelligence.
          </p>
        </div>

        {/* Global Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-[#475569] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search titles, transcripts, creators..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 border border-slate-300 text-xs font-medium text-[#0f172a] placeholder-[#64748b] focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 transition-all shadow-2xs"
          />
        </div>
      </div>

      {/* Filters & Sorting Bar */}
      <div className="p-4 rounded-xl bg-white border border-slate-300 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-[#334155] font-bold">
            <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-600" />
            <span>Filters:</span>
          </div>

          {/* Platform Filter */}
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-300 text-xs font-semibold text-[#0f172a] focus:bg-white focus:outline-none cursor-pointer"
          >
            <option value="all">All Platforms</option>
            <option value="youtube">YouTube</option>
            <option value="instagram">Instagram</option>
          </select>

          {/* Caption Filter */}
          <select
            value={transcriptFilter}
            onChange={(e) => setTranscriptFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-300 text-xs font-semibold text-[#0f172a] focus:bg-white focus:outline-none cursor-pointer"
          >
            <option value="all">All Captions Status</option>
            <option value="true">Has Captions</option>
            <option value="false">No Captions</option>
          </select>
        </div>

        {/* Sorting */}
        <div className="flex items-center gap-2">
          <span className="text-[#475569] font-semibold">Sort by:</span>
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(':');
              setSortBy(sb);
              setSortOrder(so);
            }}
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-300 text-xs font-semibold text-[#0f172a] focus:bg-white focus:outline-none cursor-pointer"
          >
            <option value="created_at:desc">Recently Added</option>
            <option value="duration_seconds:desc">Longest Duration</option>
            <option value="duration_seconds:asc">Shortest Duration</option>
            <option value="title:asc">Title (A-Z)</option>
          </select>
        </div>
      </div>

      {/* Video Grid */}
      {loading ? (
        <div className="p-16 rounded-2xl bg-white border border-slate-300 shadow-sm text-center">
          <Film className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
          <p className="text-xs font-bold text-[#475569]">Loading library records...</p>
        </div>
      ) : videos.length === 0 ? (
        <div className="p-16 rounded-2xl bg-white border border-slate-300 shadow-sm text-center space-y-2">
          <Film className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-base font-black text-[#0f172a]">No Videos in Library</h3>
          <p className="text-xs text-[#475569] max-w-sm mx-auto font-medium">
            Submit video URLs from YouTube or Instagram in the Add Videos tab to start researching.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map((v) => {
            const isSelected = selectedForCompare.includes(v.id);
            return (
              <div
                key={v.id}
                onClick={() => onOpenVideo(v.id)}
                className={`group rounded-2xl bg-white border transition-all duration-200 overflow-hidden shadow-sm cursor-pointer flex flex-col justify-between ${
                  isSelected ? 'border-2 border-indigo-600 ring-2 ring-indigo-100 shadow-md' : 'border-slate-300 hover:border-indigo-600 hover:shadow-md'
                }`}
              >
                <div>
                  {/* Thumbnail Area */}
                  <div className="relative aspect-video bg-slate-200 overflow-hidden border-b border-slate-200">
                    {v.thumbnail_url ? (
                      <img 
                        src={v.thumbnail_url} 
                        alt={v.title} 
                        className="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300" 
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <Film className="w-10 h-10" />
                      </div>
                    )}

                    {/* Compare Selection Checkbox */}
                    <button
                      onClick={(e) => toggleSelect(e, v.id)}
                      className={`absolute top-2.5 right-2.5 w-6 h-6 rounded-lg border flex items-center justify-center shadow-md transition-transform ${
                        isSelected 
                          ? 'bg-indigo-600 border-indigo-600 text-white scale-105' 
                          : 'bg-white/90 border-slate-300 text-slate-400 hover:text-slate-800'
                      }`}
                      title={isSelected ? 'Deselect for comparison' : 'Select for comparison'}
                    >
                      {isSelected && <Check className="w-4 h-4 stroke-[3]" />}
                    </button>

                    {/* Duration Badge */}
                    <div className="absolute bottom-2.5 right-2.5 px-2.5 py-0.5 rounded-md bg-slate-900/90 backdrop-blur-sm text-[11px] font-mono font-bold text-white flex items-center gap-1 shadow-sm">
                      <Clock className="w-3 h-3 text-slate-300" />
                      {formatDuration(v.duration_seconds)}
                    </div>

                    {/* Platform Badge */}
                    <div className="absolute top-2.5 left-2.5">
                      <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider shadow-sm ${
                        v.platform === 'youtube' 
                          ? 'bg-red-600 text-white' 
                          : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                      }`}>
                        {v.platform}
                      </span>
                    </div>
                  </div>

                  {/* Body Details */}
                  <div className="p-4 space-y-2">
                    <h4 className="text-sm font-bold text-[#0f172a] line-clamp-2 group-hover:text-indigo-600 transition-colors leading-snug">
                      {v.title}
                    </h4>

                    <div className="flex items-center justify-between text-xs text-[#334155] font-semibold">
                      <span className="truncate max-w-[150px] text-[#0f172a]">
                        {v.creator?.name || 'Unknown Creator'}
                      </span>
                      {v.view_count !== null && v.view_count !== undefined && (
                        <span className="flex items-center gap-1 text-[#0f172a] font-bold">
                          <Eye className="w-3.5 h-3.5 text-indigo-600" />
                          {Number(v.view_count).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Card Footer */}
                <div className="p-4 pt-2 border-t border-slate-200 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {v.has_transcript ? (
                      <span className="flex items-center gap-1 text-[#065f46] bg-[#ecfdf5] px-2.5 py-0.5 rounded-md border border-[#a7f3d0] font-bold text-[11px]">
                        <FileText className="w-3 h-3 text-emerald-600" /> Captions
                      </span>
                    ) : (
                      <span className="text-[#64748b] font-semibold text-[11px]">No Captions</span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => handleDelete(e, v.id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-700 hover:bg-rose-50 transition-colors cursor-pointer"
                      title="Delete record"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <span className="p-1.5 text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                      <ExternalLink className="w-4 h-4" />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Floating Compare Action Bar */}
      {selectedForCompare.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 text-white px-5 py-3 rounded-2xl shadow-2xl border border-slate-700 flex items-center gap-4 backdrop-blur-md animate-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center gap-2 text-xs">
            <Scale className="w-4 h-4 text-indigo-400" />
            <span className="font-bold">{selectedForCompare.length} video{selectedForCompare.length > 1 ? 's' : ''} selected</span>
          </div>

          <div className="h-4 w-px bg-slate-700" />

          <button
            onClick={() => onNavigateToCompare && onNavigateToCompare(selectedForCompare)}
            disabled={selectedForCompare.length < 2}
            className="px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold text-white shadow-sm transition-colors flex items-center gap-1.5"
          >
            <span>Compare Now</span>
            {selectedForCompare.length < 2 && <span className="text-[10px] text-indigo-200">(select $\ge$ 2)</span>}
          </button>

          <button
            onClick={() => setSelectedForCompare([])}
            className="p-1 text-slate-400 hover:text-white transition-colors"
            title="Clear selection"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
