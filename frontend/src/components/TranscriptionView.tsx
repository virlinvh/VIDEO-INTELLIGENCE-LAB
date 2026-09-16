import { useState, useEffect } from 'react';
import { 
  Headphones, 
  Cpu, 
  HardDrive, 
  RefreshCw, 
  ShieldCheck, 
  X, 
  Languages, 
  ToggleLeft, 
  ToggleRight, 
  SlidersHorizontal,
  DownloadCloud,
  CheckCircle2
} from 'lucide-react';
import type { 
  TranscriptionSubsystemStatus, 
  TranscriptionSettings, 
  ModelCatalogItem 
} from '../types';

export function TranscriptionView() {
  const [status, setStatus] = useState<TranscriptionSubsystemStatus | null>(null);
  const [settings, setSettings] = useState<TranscriptionSettings | null>(null);
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<ModelCatalogItem | null>(null);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [downloadProgress, setDownloadProgress] = useState<any>(null);

  const fetchData = async () => {
    try {
      const [resStatus, resSettings, resModels] = await Promise.all([
        fetch('/api/v1/transcription/status').then(r => r.json()),
        fetch('/api/v1/transcription/settings').then(r => r.json()),
        fetch('/api/v1/transcription/models').then(r => r.json()),
      ]);
      setStatus(resStatus);
      setSettings(resSettings);
      setModels(resModels);
    } catch (err) {
      console.error('Failed to load transcription data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let interval: any = null;
    if (downloading) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('/api/v1/transcription/models/whisper-large-v3-turbo/progress').then(r => r.json());
          setDownloadProgress(res);
          if (res.status === 'READY' || res.status === 'ERROR') {
            setDownloading(false);
            fetchData();
          }
        } catch (e) {
          console.error(e);
        }
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [downloading]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleStartDownload = async (modelId: string) => {
    try {
      setDownloading(true);
      setDownloadProgress({ status: 'DOWNLOADING', message: 'Initiating download...' });
      await fetch(`/api/v1/transcription/models/${modelId}/download`, { method: 'POST' });
    } catch (err) {
      console.error('Download failed to start:', err);
      setDownloading(false);
    }
  };

  const handleToggleFallback = async () => {
    if (!settings) return;
    const nextVal = !settings.automatic_asr_fallback_enabled;
    try {
      const res = await fetch('/api/v1/transcription/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ automatic_asr_fallback_enabled: nextVal })
      });
      if (res.ok) {
        const updated = await res.json();
        setSettings(updated);
        handleRefresh();
      }
    } catch (err) {
      console.error('Failed to toggle automatic fallback:', err);
    }
  };

  const installedModels = models.filter(m => m.status === 'READY');

  if (loading && !status) {
    return (
      <div className="p-16 rounded-2xl bg-white border border-slate-300 shadow-sm text-center">
        <RefreshCw className="w-8 h-8 text-cyan-600 animate-spin mx-auto mb-2" />
        <p className="text-xs font-bold text-[#475569]">Loading transcription architecture status...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-cyan-700 font-bold text-xs uppercase tracking-wider">
              <Headphones className="w-4 h-4" />
              <span>Phase 4.5A Local Transcription Control Center</span>
            </div>
            <h2 className="text-2xl font-black text-[#0f172a] mt-1 tracking-tight">Model & Transcription Management</h2>
            <p className="text-xs text-[#475569] mt-0.5 font-medium">
              Authoritative model registry, language routing, and isolated runtime boundaries for offline speech recognition.
            </p>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl border border-slate-300 transition-all flex items-center gap-1.5 self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-700 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh Status</span>
          </button>
        </div>
      </div>

      {/* System Status Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Status 1: Subsystem State */}
        <div className="p-5 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Subsystem Status</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`w-2.5 h-2.5 rounded-full ${status?.status === 'READY' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <p className="text-xl font-black text-[#0f172a]">
                {status?.status === 'READY' ? 'Ready' : 'Not Configured'}
              </p>
            </div>
            <p className="text-xs text-[#64748b] mt-1 font-medium">
              {installedModels.length} installed models
            </p>
          </div>
          <div className="p-3 rounded-xl bg-cyan-50 text-cyan-700 border border-cyan-200 shadow-2xs">
            <Headphones className="w-5 h-5" />
          </div>
        </div>

        {/* Status 2: Automatic Fallback Switch */}
        <div className="p-5 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Automatic ASR Fallback</p>
            <div className="flex items-center gap-2 mt-2">
              <button 
                onClick={handleToggleFallback}
                className="text-cyan-700 hover:text-cyan-800 transition-colors"
                title="Toggle automatic transcription fallback"
              >
                {settings?.automatic_asr_fallback_enabled ? (
                  <ToggleRight className="w-8 h-8 text-cyan-600 fill-cyan-100" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-slate-400" />
                )}
              </button>
              <span className="text-sm font-bold text-[#0f172a]">
                {settings?.automatic_asr_fallback_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="text-[11px] text-[#64748b] mt-1 font-medium">
              Fallback if platform captions absent
            </p>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 text-slate-700 border border-slate-200 shadow-2xs">
            <SlidersHorizontal className="w-5 h-5" />
          </div>
        </div>

        {/* Status 3: Languages Configured */}
        <div className="p-5 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Languages Configured</p>
            <p className="text-xl font-black text-[#0f172a] mt-2">
              {status?.languages_configured_count || 0} / {status?.total_languages_count || 3}
            </p>
            <p className="text-xs text-[#64748b] mt-1 font-medium">English, Tamil, Malayalam</p>
          </div>
          <div className="p-3 rounded-xl bg-teal-50 text-teal-700 border border-teal-200 shadow-2xs">
            <Languages className="w-5 h-5" />
          </div>
        </div>

        {/* Status 4: Model Storage Footprint */}
        <div className="p-5 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-bold text-[#475569] uppercase tracking-wider">Model Storage Used</p>
            <p className="text-xl font-black text-[#0f172a] mt-2">
              {status?.model_storage_size_human || '0.00 B'}
            </p>
            <p className="text-xs text-[#059669] mt-1 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Project-contained
            </p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs">
            <HardDrive className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Language Routing Table */}
      <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-4">
        <div>
          <h3 className="text-base font-bold text-[#0f172a]">Language Routing & Default Models</h3>
          <p className="text-xs text-[#475569] mt-0.5">
            Default model resolution for automatic fallback transcription. Only installed, verified models can be selected as active defaults.
          </p>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-300">
          <table className="w-full text-left text-xs text-[#0f172a]">
            <thead className="bg-[#f8fafc] text-[#334155] font-bold uppercase text-[11px] tracking-wider border-b border-slate-300">
              <tr>
                <th className="py-3.5 px-4">Language</th>
                <th className="py-3.5 px-4">Language Code</th>
                <th className="py-3.5 px-4">Assigned Default Model</th>
                <th className="py-3.5 px-4">Routing Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {status?.language_routes.map((lr) => (
                <tr key={lr.language_code} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#0f172a] text-xs">{lr.language_name}</td>
                  <td className="py-3.5 px-4 font-mono text-cyan-700 font-bold uppercase">{lr.language_code}</td>
                  <td className="py-3.5 px-4 font-medium text-[#475569]">
                    {lr.configured_model_name || <span className="italic text-slate-400">No installed model assigned</span>}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                      lr.status === 'READY'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : 'bg-slate-100 text-slate-700 border border-slate-300'
                    }`}>
                      {lr.status === 'READY' ? 'Ready' : 'No Model Installed'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Production ASR Engines: English + Indic */}
      <div className="space-y-6">
        <div>
          <h3 className="text-base font-bold text-[#0f172a]">Production Transcription Engines</h3>
          <p className="text-xs text-[#475569] mt-0.5">
            Dedicated local models isolated in separate runtimes for maximum accuracy and zero environment conflicts.
          </p>
        </div>

        {models.map((model) => (
          <div key={model.model_id} className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-cyan-100 text-cyan-900 border border-cyan-300 uppercase">
                    {model.family === 'faster-whisper' ? 'ENGLISH ENGINE' : 'INDIC ENGINE'}
                  </span>
                  <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-300 uppercase">
                    {model.runtime_requirement}
                  </span>
                </div>
                <h3 className="text-xl font-black text-[#0f172a] mt-2">{model.display_name}</h3>
                <p className="text-xs text-[#475569] mt-1 max-w-2xl font-medium">
                  {model.description}
                </p>
              </div>

              {/* Install / Ready Action Button */}
              <div>
                {model.status === 'READY' ? (
                  <div className="px-4 py-2.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 font-bold text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Model Installed & Ready</span>
                  </div>
                ) : (downloading && selectedModel?.model_id === model.model_id) || downloadProgress?.status === 'DOWNLOADING' || downloadProgress?.status === 'VERIFYING' ? (
                  <div className="px-5 py-3 rounded-xl bg-cyan-50 border border-cyan-300 text-cyan-900 space-y-2 min-w-[240px]">
                    <div className="flex items-center justify-between text-xs font-bold">
                      <span className="flex items-center gap-1.5">
                        <RefreshCw className="w-3.5 h-3.5 text-cyan-700 animate-spin" />
                        {downloadProgress?.status === 'VERIFYING' ? 'Verifying Integrity...' : 'Downloading Weights...'}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#475569] truncate font-medium">
                      {downloadProgress?.message || 'Transactional download staging...'}
                    </p>
                  </div>
                ) : (
                  <button
                    onClick={() => {
                      setSelectedModel(model);
                      handleStartDownload(model.model_id);
                    }}
                    className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-xs shadow-sm transition-all flex items-center gap-2 cursor-pointer"
                  >
                    <DownloadCloud className="w-4 h-4" />
                    <span>Download & Install Model ({model.expected_download_size})</span>
                  </button>
                )}
              </div>
            </div>

            {/* Model Specification Matrix */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[#64748b] font-semibold uppercase text-[10px]">Target Languages</span>
                <p className="font-bold text-[#0f172a] text-sm">
                  {model.supported_languages.map(l => l === 'en' ? 'English' : l === 'ta' ? 'Tamil' : l === 'ml' ? 'Malayalam' : l).join(', ')}
                </p>
                <p className="text-[11px] text-[#64748b]">Code-switched & Native speech</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[#64748b] font-semibold uppercase text-[10px]">Acceleration Device</span>
                <p className="font-bold text-[#0f172a] text-sm">NVIDIA GPU (CUDA / ONNX)</p>
                <p className="text-[11px] text-[#64748b]">Automatic CPU fallback</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[#64748b] font-semibold uppercase text-[10px]">Isolated Runtime</span>
                <p className="font-bold text-[#0f172a] text-sm font-mono truncate">
                  {model.family === 'faster-whisper' ? 'runtimes/faster-whisper' : 'runtimes/indicconformer'}
                </p>
                <p className="text-[11px] text-[#64748b]">Protected main Python env</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[#64748b] font-semibold uppercase text-[10px]">Local Model Storage</span>
                <p className="font-bold text-[#0f172a] text-sm font-mono truncate" title={model.local_path || ''}>
                  storage/models/{model.family}/
                </p>
                <p className="text-[11px] text-[#64748b]">Size: {model.installed_size_human}</p>
              </div>
            </div>
          </div>
        ))}
      </div>


      {/* Hardware Information Card */}
      {status?.hardware && (
        <div className="p-6 rounded-2xl bg-white border border-slate-300 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-[#0f172a] font-bold text-sm">
            <Cpu className="w-4 h-4 text-cyan-700" />
            <span>Detected Local Hardware</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <p className="text-[#64748b] font-semibold">CPU Information</p>
              <p className="text-sm font-bold text-[#0f172a] mt-0.5">{status.hardware.cpu_info}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <p className="text-[#64748b] font-semibold">System Memory (RAM)</p>
              <p className="text-sm font-bold text-[#0f172a] mt-0.5">{status.hardware.total_ram_gb} GB ({status.hardware.available_ram_gb} GB avail)</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <p className="text-[#64748b] font-semibold">Acceleration / GPU</p>
              <p className="text-sm font-bold text-[#0f172a] mt-0.5">{status.hardware.gpu_name || 'CPU Default'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Model Detail Inspection Modal */}
      {selectedModel && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-300 shadow-2xl max-w-xl w-full p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-3 border-b border-slate-200">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-50 text-cyan-900 border border-cyan-200 uppercase">
                  {selectedModel.family}
                </span>
                <h3 className="text-lg font-black text-[#0f172a] mt-1">{selectedModel.display_name}</h3>
                <p className="text-xs font-mono text-[#64748b]">{selectedModel.model_id}</p>
              </div>
              <button
                onClick={() => setSelectedModel(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-[#334155]">
              <div>
                <p className="font-bold text-[#0f172a] uppercase text-[11px]">Description</p>
                <p className="mt-0.5 leading-relaxed text-[#475569]">{selectedModel.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[#64748b] font-semibold">Supported Languages:</span>
                  <p className="font-bold text-[#0f172a] mt-0.5 uppercase">{selectedModel.supported_languages.join(', ')}</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[#64748b] font-semibold">License:</span>
                  <p className="font-bold text-[#0f172a] mt-0.5">{selectedModel.license_info}</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[#64748b] font-semibold">Expected Download Size:</span>
                  <p className="font-bold text-[#0f172a] mt-0.5">{selectedModel.expected_download_size}</p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[#64748b] font-semibold">Expected Installed Size:</span>
                  <p className="font-bold text-[#0f172a] mt-0.5">{selectedModel.expected_installed_size}</p>
                </div>
              </div>

              <div>
                <p className="font-bold text-[#0f172a] uppercase text-[11px]">Hardware Notes</p>
                <p className="mt-0.5 leading-relaxed text-[#475569]">{selectedModel.hardware_notes}</p>
              </div>

              <div>
                <p className="font-bold text-[#0f172a] uppercase text-[11px]">Target Storage Destination</p>
                <p className="mt-0.5 font-mono text-[11px] text-[#0f172a] bg-slate-50 p-2 rounded-lg border border-slate-200 break-all">
                  {selectedModel.local_path}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedModel(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-[#0f172a] text-xs font-bold rounded-xl transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
