import type { VideoSegmentComparisonItem } from '../../types';

export interface SingleCopyOptions {
  includeTimestamps?: boolean;
}

export interface ComparisonCopyOptions {
  scope: 'current_range' | 'full_scripts';
  format: 'clean' | 'research';
  includeTimestamps: boolean;
  includeMetrics: boolean;
  pinnedVideoId?: string | null;
  showAll12Metrics?: boolean;
}

export function formatTime(seconds?: number | null): string {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) return '00:00';
  const s = Math.floor(seconds);
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function formatTimestampRange(start?: number | null, end?: number | null): string {
  return `[${formatTime(start)} - ${formatTime(end)}]`;
}

/**
 * Format segments with timestamps: [MM:SS - MM:SS] text
 */
export function formatSegmentsWithTimestamps(segments: { start_time: number; end_time: number; text: string }[]): string {
  if (!segments || segments.length === 0) {
    return '';
  }
  return segments
    .map(seg => `${formatTimestampRange(seg.start_time, seg.end_time)} ${seg.text.trim()}`)
    .join('\n');
}

/**
 * Format single video script (either clean text or with timestamps)
 */
export function formatSingleVideoScript(
  video: VideoSegmentComparisonItem,
  options: SingleCopyOptions = {}
): string {
  if (video.availability === 'NO_TRANSCRIPT') {
    return '[Transcript unavailable]';
  }
  if (video.availability === 'NOT_AVAILABLE') {
    return '[Video unavailable]';
  }

  if (options.includeTimestamps) {
    if (!video.segments || video.segments.length === 0) {
      return '[No transcript segments in selected range]';
    }
    return formatSegmentsWithTimestamps(video.segments);
  }

  // Clean text
  if (!video.full_text || video.full_text.trim() === '') {
    return '[No transcript segments in selected range]';
  }
  return video.full_text.trim();
}

/**
 * Format Plain Text Metrics Table
 */
export function formatMetricsSummaryTable(
  videos: VideoSegmentComparisonItem[],
  showAll12: boolean = false
): string {
  if (!videos || videos.length === 0) return '';

  const coreMetricKeys: { key: string; label: string; suffix?: string }[] = [
    { key: 'word_count', label: 'Words' },
    { key: 'range_wpm', label: 'Range WPM' },
    { key: 'sentence_count', label: 'Sentences' },
    { key: 'unique_words', label: 'Unique Words' },
    { key: 'question_count', label: 'Questions' }
  ];

  const extendedMetricKeys: { key: string; label: string; suffix?: string }[] = [
    { key: 'segment_count', label: 'Segments' },
    { key: 'lexical_diversity', label: 'Lexical Diversity', suffix: '%' },
    { key: 'average_sentence_length', label: 'Avg Sentence Length', suffix: ' w/s' },
    { key: 'exclamation_count', label: 'Exclamations' },
    { key: 'filler_count', label: 'Fillers' },
    { key: 'transition_count', label: 'Transitions' },
    { key: 'repeated_phrase_count', label: 'Repeated Phrases' }
  ];

  const keys = showAll12 ? [...coreMetricKeys, ...extendedMetricKeys] : coreMetricKeys;

  const colWidths = [24, ...videos.map(v => Math.max(16, Math.min(28, (v.title || '').length + 2)))];

  const pad = (str: string, len: number) => {
    if (str.length > len) return str.slice(0, len - 1) + '…';
    return str.padEnd(len);
  };

  // Header row
  const header = ['Metric'.padEnd(colWidths[0]), ...videos.map((v, idx) => pad(v.title || `Video ${idx + 1}`, colWidths[idx + 1]))].join(' | ');
  const separator = colWidths.map(w => '-'.repeat(w)).join('-|-');

  const rows = keys.map(item => {
    const rowCells = [pad(item.label, colWidths[0])];
    videos.forEach((v, idx) => {
      if (v.availability === 'NO_TRANSCRIPT' || v.availability === 'NOT_AVAILABLE' || !v.metrics) {
        rowCells.push(pad('—', colWidths[idx + 1]));
      } else {
        const val = (v.metrics as any)[item.key];
        const displayVal = val === null || val === undefined
          ? '—'
          : `${typeof val === 'number' ? val.toLocaleString() : val}${item.suffix || ''}`;
        rowCells.push(pad(displayVal, colWidths[idx + 1]));
      }
    });
    return rowCells.join(' | ');
  });

  return [header, separator, ...rows].join('\n');
}

/**
 * Format Multi-Video Clean Scripts
 */
export function formatMultiVideoClean(
  videos: VideoSegmentComparisonItem[],
  options: { includeTimestamps: boolean; pinnedVideoId?: string | null }
): string {
  const divider = '='.repeat(80);

  return videos.map((v, idx) => {
    const isRef = v.video_id === options.pinnedVideoId;
    const refTag = isRef ? ' [REFERENCE SCRIPT]' : '';
    const creator = v.creator_name || v.platform || 'Unknown Creator';
    const lang = (v.actual_transcript_language || 'en').toUpperCase();
    const duration = formatTime(v.duration_seconds);
    const range = v.requested_range_label || 'Selected Range';
    const scriptContent = formatSingleVideoScript(v, { includeTimestamps: options.includeTimestamps });

    return [
      divider,
      `${idx + 1}. ${v.title}${refTag}`,
      `Creator: ${creator} | Language: ${lang} | Duration: ${duration} | Range: ${range}`,
      divider,
      scriptContent,
      ''
    ].join('\n');
  }).join('\n');
}

/**
 * Format Multi-Video Research Comparison Export
 */
export function formatMultiVideoResearch(
  videos: VideoSegmentComparisonItem[],
  options: ComparisonCopyOptions
): string {
  const majorDivider = '='.repeat(80);
  const sectionDivider = '-'.repeat(80);
  const now = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';

  const scopeLabel = options.scope === 'full_scripts' ? 'Full Scripts (Complete Canonical Transcripts)' : (videos[0]?.requested_range_label || 'Selected Range');
  const pinnedVideo = options.pinnedVideoId ? videos.find(v => v.video_id === options.pinnedVideoId) : null;

  const headerLines = [
    majorDivider,
    'VIDEO INTELLIGENCE LAB — SCRIPT COMPARISON RESEARCH REPORT',
    `Generated: ${now}`,
    `Scope: ${scopeLabel}`,
    `Total Videos Compared: ${videos.length}`,
    pinnedVideo ? `Pinned Reference Video: "${pinnedVideo.title}" (${pinnedVideo.video_id})` : 'Pinned Reference Video: None (Independent Peer Comparison)',
    majorDivider,
    ''
  ];

  // Optional Metrics Section (only if scope is current_range and includeMetrics is true)
  const metricsSection: string[] = [];
  if (options.scope === 'current_range' && options.includeMetrics) {
    metricsSection.push('### SELECTED RANGE METRICS SUMMARY ###');
    metricsSection.push('');
    metricsSection.push(formatMetricsSummaryTable(videos, options.showAll12Metrics));
    metricsSection.push('');
    metricsSection.push(majorDivider);
    metricsSection.push('');
  }

  // Video Sections
  const videoSections = videos.map((v, idx) => {
    const isRef = v.video_id === options.pinnedVideoId;
    const role = isRef ? 'REFERENCE SCRIPT (Pinned)' : `Comparison Video #${idx + 1}`;
    const creator = v.creator_name || v.platform || 'Unknown Creator';
    const lang = (v.actual_transcript_language || 'en').toUpperCase();
    const source = v.asr_model ? `${v.transcript_source || 'ASR'} (${v.asr_model})` : (v.transcript_source || 'Unknown');
    const totalDuration = formatTime(v.duration_seconds);
    const effStart = v.effective_start_seconds !== null && v.effective_start_seconds !== undefined ? formatTime(v.effective_start_seconds) : '00:00';
    const effEnd = v.effective_end_seconds !== null && v.effective_end_seconds !== undefined ? formatTime(v.effective_end_seconds) : totalDuration;
    const effectiveRange = `${effStart} - ${effEnd}`;

    const scriptBody = formatSingleVideoScript(v, { includeTimestamps: options.includeTimestamps });

    const metadataLines = [
      `[VIDEO ${idx + 1} OF ${videos.length}] ${v.title}`,
      sectionDivider,
      `Role:             ${role}`,
      `Video ID:         ${v.video_id}`,
      `Creator:          ${creator}`,
      `Language:         ${lang}`,
      `Transcript Model: ${source}`,
      `Total Duration:   ${totalDuration}`,
      `Effective Range:  ${effectiveRange} (${v.requested_range_label || 'Range'})`,
    ];

    if (options.scope === 'current_range' && v.metrics) {
      metadataLines.push(
        `Range Words:      ${v.metrics.word_count.toLocaleString()} words (${v.metrics.range_wpm} WPM | ${v.metrics.sentence_count} sentences)`
      );
    }

    metadataLines.push(sectionDivider);
    metadataLines.push('SCRIPT CONTENT:');
    metadataLines.push('');
    metadataLines.push(scriptBody);
    metadataLines.push('');

    return metadataLines.join('\n');
  });

  return [
    ...headerLines,
    ...metricsSection,
    ...videoSections,
    majorDivider,
    'END OF COMPARISON EXPORT',
    majorDivider
  ].join('\n');
}
