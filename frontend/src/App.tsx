import { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  PlusCircle, 
  Film, 
  Scale, 
  HardDrive, 
  Settings as SettingsIcon,
  Activity,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Layers,
  Cpu,
  Headphones,
  RefreshCw
} from 'lucide-react';
import type { HealthStatus, StorageOverview } from './types';
import { AddVideosView } from './components/AddVideosView';
import { LibraryView } from './components/LibraryView';
import { CompareView } from './components/CompareView';
import { TranscriptionView } from './components/TranscriptionView';
import { VideoDetailModal } from './components/VideoDetailModal';
import { ErrorBoundary } from './components/ErrorBoundary';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'add' | 'library' | 'compare' | 'transcription' | 'storage' | 'settings'>('dashboard');
  const [engineState, setEngineState] = useState<'starting' | 'online' | 'offline'>('starting');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [storage, setStorage] = useState<StorageOverview | null>(null);
  const [storageLoading, setStorageLoading] = useState<boolean>(true);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [compareVideoIds, setCompareVideoIds] = useState<string[]>([]);

  // 1. Independent Health Status Check with bounded 10s retry polling
  const checkHealth = async () => {
    try {
      const res = await fetch('/api/v1/health');
      if (res.ok) {
        const data: HealthStatus = await res.json();
        setHealth(data);
        setEngineState(data.database_connected ? 'online' : 'offline');
      } else {
        setEngineState('offline');
      }
    } catch {
      setEngineState('offline');
    }
  };

  // 2. Independent Storage Overview Fetch
  const fetchStorage = async () => {
    setStorageLoading(true);
    try {
      const res = await fetch('/api/v1/storage');
      if (res.ok) {
        const data: StorageOverview = await res.json();
        setStorage(data);
      }
    } catch (err) {
      console.error('Failed to fetch storage status:', err);
    } finally {
      setStorageLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    fetchStorage();

    // Bounded health check polling every 10s
    const healthInterval = setInterval(checkHealth, 10000);
    return () => clearInterval(healthInterval);
  }, []);

  // When switching to Storage tab, refresh storage if needed
  useEffect(() => {
    if (activeTab === 'storage') {
      fetchStorage();
    }
  }, [activeTab]);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, color: 'text-indigo-600' },
    { id: 'add', label: 'Add Videos', icon: PlusCircle, color: 'text-indigo-600' },
    { id: 'library', label: 'Library', icon: Film, color: 'text-blue-600' },
    { id: 'compare', label: 'Compare', icon: Scale, color: 'text-rose-600' },
    { id: 'transcription', label: 'Transcription', icon: Headphones, color: 'text-cyan-600' },
    { id: 'storage', label: 'Storage', icon: HardDrive, color: 'text-emerald-600' },
    { id: 'settings', label: 'Settings', icon: SettingsIcon, color: 'text-slate-700' },
  ] as const;

  return (
    <div className="flex h-screen bg-[#f1f5f9] text-[#0f172a] font-sans antialiased overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-300 bg-white flex flex-col justify-between shadow-sm z-10">
        <div>
          {/* Logo Area */}
          <div className="p-6 border-b border-slate-200 flex items-center gap-3.5 bg-slate-50/50">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-600/30 tracking-wider">
              VI
            </div>
            <div>
              <h1 className="font-extrabold text-sm tracking-tight text-[#0f172a]">Video Intelligence</h1>
              <p className="text-xs text-[#475569] font-medium">Research Workspace</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer ${
                    isActive 
                      ? 'bg-indigo-50 text-indigo-900 border-2 border-indigo-600/30 shadow-xs' 
                      : 'text-[#334155] hover:text-[#0f172a] hover:bg-slate-100/80 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-slate-500'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Local System Status Badge */}
        <div className="p-4 m-3 rounded-xl bg-[#f8fafc] border border-slate-300 shadow-2xs">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-[#0f172a] font-bold flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-indigo-600" /> Engine Status
            </span>
            {engineState === 'online' ? (
              <span className="flex items-center gap-1 text-[#065f46] bg-[#ecfdf5] px-2.5 py-0.5 rounded-full text-[11px] font-bold border border-[#a7f3d0]">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Online
              </span>
            ) : engineState === 'starting' ? (
              <span className="flex items-center gap-1 text-indigo-900 bg-indigo-50 px-2.5 py-0.5 rounded-full text-[11px] font-bold border border-indigo-200">
                <RefreshCw className="w-3 h-3 text-indigo-600 animate-spin" /> Starting...
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[#92400e] bg-[#fffbeb] px-2.5 py-0.5 rounded-full text-[11px] font-bold border border-[#fde68a]">
                <AlertCircle className="w-3 h-3 text-amber-600" /> Offline
              </span>
            )}
          </div>
          <div className="text-xs text-[#475569] space-y-1 font-medium">
            <p>Database: <strong className="text-[#0f172a]">{health?.database_connected ? 'SQLite Connected' : (engineState === 'starting' ? 'Connecting...' : 'Disconnected')}</strong></p>
            <p>Containment: <strong className="text-[#0f172a]">Local Sandbox</strong></p>
          </div>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="flex-1 flex flex-col overflow-y-auto bg-[#f1f5f9]">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-300 px-8 flex items-center justify-between bg-white sticky top-0 z-10 shadow-xs">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-extrabold text-[#0f172a] capitalize tracking-tight">
              {activeTab === 'add' ? 'Add Videos for Analysis' : activeTab}
            </h2>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-900 font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
              Mode: <span className="text-[#0f172a] font-bold">Analyze Only</span>
            </div>
            <div className="px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-900 font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
              Storage: <span className="text-[#0f172a] font-bold">
                {storageLoading && !storage ? 'Calculating...' : (storage?.total_size_human || '0.00 B')}
              </span>
            </div>
          </div>
        </header>

        {/* Dynamic Content Views */}
        <div className="p-8 max-w-6xl w-full mx-auto space-y-6">
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Metric Highlights */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Metric 1 */}
                <div 
                  onClick={() => setActiveTab('library')}
                  className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between cursor-pointer hover:border-indigo-400 transition-colors"
                >
                  <div>
                    <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Analyzed Videos</p>
                    <p className="text-3xl font-black text-[#0f172a] mt-2">Ready</p>
                    <p className="text-xs text-[#334155] mt-1 font-medium">Browse research library</p>
                  </div>
                  <div className="p-3 rounded-xl bg-indigo-100 text-indigo-700 border border-indigo-200 shadow-2xs">
                    <Film className="w-6 h-6" />
                  </div>
                </div>

                {/* Metric 2 */}
                <div 
                  onClick={() => setActiveTab('add')}
                  className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between cursor-pointer hover:border-blue-400 transition-colors"
                >
                  <div>
                    <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Job Pipeline</p>
                    <p className="text-3xl font-black text-[#0f172a] mt-2">Active</p>
                    <p className="text-xs text-[#334155] mt-1 font-medium">2 concurrent worker limit</p>
                  </div>
                  <div className="p-3 rounded-xl bg-blue-100 text-blue-700 border border-blue-200 shadow-2xs">
                    <Cpu className="w-6 h-6" />
                  </div>
                </div>

                {/* Metric 3 */}
                <div 
                  onClick={() => setActiveTab('storage')}
                  className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between cursor-pointer hover:border-emerald-400 transition-colors"
                >
                  <div>
                    <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Project Footprint</p>
                    <p className="text-3xl font-black text-[#065f46] mt-2">
                      {storageLoading && !storage ? 'Calculating...' : (storage?.total_size_human || '0 B')}
                    </p>
                    <p className="text-xs text-[#334155] mt-1 font-medium">100% contained in project</p>
                  </div>
                  <div className="p-3 rounded-xl bg-emerald-100 text-emerald-700 border border-emerald-200 shadow-2xs">
                    <HardDrive className="w-6 h-6" />
                  </div>
                </div>
              </div>

              {/* Informational Product Banner */}
              <div className="p-6 rounded-2xl bg-white border-2 border-indigo-200 shadow-sm space-y-3">
                <div className="flex items-center gap-2 text-indigo-950 font-bold text-sm">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  <span>Video Intelligence Lab Ready</span>
                </div>
                <p className="text-sm text-[#334155] leading-relaxed max-w-3xl font-normal">
                  Analyze individual videos, study transcripts and visual structure, and compare research records from your Library.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'add' && (
            <AddVideosView onOpenVideo={(vid) => setSelectedVideoId(vid)} />
          )}

          {activeTab === 'library' && (
            <LibraryView 
              onOpenVideo={(vid) => setSelectedVideoId(vid)} 
              onNavigateToCompare={(ids) => {
                setCompareVideoIds(ids);
                setActiveTab('compare');
              }}
            />
          )}

          {activeTab === 'compare' && (
            <ErrorBoundary fallbackTitle="Comparison View Error" fallbackMessage="An error occurred while loading the comparison workspace. You can reset to continue.">
              <CompareView 
                initialVideoIds={compareVideoIds} 
                onOpenVideoDetail={(vid) => setSelectedVideoId(vid)} 
              />
            </ErrorBoundary>
          )}

          {activeTab === 'transcription' && (
            <TranscriptionView />
          )}

          {activeTab === 'storage' && (
            <div className="space-y-6">
              <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-[#0f172a]">Project Storage Categories</h3>
                    <p className="text-xs text-[#475569] mt-0.5">Strictly project-contained storage footprint breakdown.</p>
                  </div>
                  <button
                    onClick={fetchStorage}
                    disabled={storageLoading}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-indigo-600 ${storageLoading ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>
                
                <div className="overflow-hidden rounded-xl border border-slate-300">
                  <table className="w-full text-left text-xs text-[#0f172a]">
                    <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
                      <tr>
                        <th className="py-3 px-4">Category</th>
                        <th className="py-3 px-4">Relative Path</th>
                        <th className="py-3 px-4">Items</th>
                        <th className="py-3 px-4">Size</th>
                        <th className="py-3 px-4">Regeneratable</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {storageLoading && !storage ? (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-500 font-medium">
                            <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin mx-auto mb-2" />
                            Calculating storage categories...
                          </td>
                        </tr>
                      ) : (
                        storage?.categories.map((cat) => (
                          <tr key={cat.category} className="hover:bg-slate-50 transition-colors">
                            <td className="py-3.5 px-4 font-bold text-[#0f172a] capitalize text-xs">{cat.category}</td>
                            <td className="py-3.5 px-4 font-mono text-[#334155] font-medium">{cat.relative_path}</td>
                            <td className="py-3.5 px-4 font-semibold text-[#0f172a]">{cat.file_count}</td>
                            <td className="py-3.5 px-4 font-bold text-[#0f172a]">{cat.size_human}</td>
                            <td className="py-3.5 px-4">
                              <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                                cat.is_regeneratable 
                                  ? 'bg-indigo-50 text-indigo-900 border border-indigo-200' 
                                  : 'bg-slate-100 text-slate-700 border border-slate-300'
                              }`}>
                                {cat.is_regeneratable ? 'Yes' : 'No'}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="p-16 rounded-2xl bg-white border border-slate-300 shadow-sm text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto border border-indigo-200">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-[#0f172a] capitalize">Settings Workspace</h3>
              <p className="text-xs text-[#475569] max-w-md mx-auto leading-relaxed font-medium">
                Local system sandbox, execution timeouts, and subtitle language routing configurations.
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Video Detail Modal */}
      {selectedVideoId && (
        <VideoDetailModal
          videoId={selectedVideoId}
          onClose={() => setSelectedVideoId(null)}
        />
      )}
    </div>
  );
}
