export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database_connected: boolean;
  storage_directories_ready: boolean;
}

export interface StorageCategory {
  category: string;
  relative_path: string;
  absolute_path: string;
  size_bytes: number;
  size_human: string;
  file_count: number;
  is_regeneratable: boolean;
}

export interface StorageOverview {
  total_size_bytes: number;
  total_size_human: string;
  categories: StorageCategory[];
  saved_video_library: StorageCategory;
}

export interface JobValidationItem {
  raw_url: string;
  platform: 'youtube' | 'instagram' | 'unsupported' | 'blocked' | 'unknown';
  video_id: string;
  canonical_url: string;
  is_valid: boolean;
  error?: string;
  is_duplicate_in_batch: boolean;
  already_in_library: boolean;
}

export interface JobBatchValidation {
  total_urls: number;
  valid_urls: number;
  invalid_urls: number;
  duplicates_in_batch: number;
  items: JobValidationItem[];
}

export interface ApiError {
  code: string;
  message: string;
  status_code?: number;
  retryable?: boolean;
  details?: any;
}

export interface ApiErrorResponse {
  error: ApiError;
}

export interface Job {
  id: string;
  video_id?: string;
  url: string;
  processing_mode: string;
  requested_transcript_language?: string;
  state: 'QUEUED' | 'VALIDATING' | 'EXTRACTING_METADATA' | 'GETTING_CAPTIONS' | 'PROCESSING_TRANSCRIPT' | 'ACQUIRING_AUDIO' | 'PREPARING_AUDIO' | 'TRANSCRIBING_LOCAL_ASR' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED' | 'CANCELLED';
  progress_percent: number;
  current_step: string;
  warnings: string[];
  error_details?: ApiError;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface CreatorSummary {
  id: string;
  platform: string;
  platform_creator_id?: string;
  name: string;
  handle?: string;
  url?: string;
}

export interface VideoSummary {
  id: string;
  platform: string;
  platform_video_id: string;
  original_url: string;
  title: string;
  duration_seconds: number;
  creator?: CreatorSummary;
  processing_status: string;
  media_state: string;
  published_at?: string;
  created_at: string;
  thumbnail_url?: string;
  view_count?: number;
  like_count?: number;
  has_transcript: boolean;
}

export interface TranscriptSegment {
  sequence_index: number;
  start_time: number;
  end_time: number;
  duration: number;
  text: string;
  word_count: number;
}

export interface TranscriptData {
  id: string;
  video_id: string;
  language: string;
  requested_language?: string;
  source_type: string;
  caption_source?: string;
  caption_language_code?: string;
  asr_model?: string;
  is_generated: boolean;
  full_text: string;
  segment_count: number;
  segments: TranscriptSegment[];
}

export interface VideoDetail {
  id: string;
  platform: string;
  platform_video_id: string;
  original_url: string;
  title: string;
  duration_seconds: number;
  creator?: CreatorSummary;
  processing_status: string;
  media_state: string;
  published_at?: string;
  created_at: string;
  description?: string;
  thumbnail_url?: string;
  chapters?: Array<{ title: string; start_time: number }>;
  hashtags?: string[];
  tags?: string[];
  categories?: string[];
  view_count?: number;
  like_count?: number;
  comment_count?: number;
  technical_details?: Record<string, any>;
  has_transcript: boolean;
  has_raw_data: boolean;
}

export interface QuestionEvidenceItem {
  text: string;
  timestamp: number;
  sequence_index: number;
}

export interface ExclamationEvidenceItem {
  text: string;
  timestamp: number;
  sequence_index: number;
}

export interface OccurrenceItem {
  text: string;
  timestamp: number;
  sequence_index: number;
}

export interface DictionaryMatchEvidence {
  expression: string;
  count: number;
  occurrences: OccurrenceItem[];
}

export interface RepeatedPhraseItem {
  phrase: string;
  count: number;
  word_count: number;
  occurrences: OccurrenceItem[];
}

export interface PaceTimelineWindow {
  window_index: number;
  start_time: number;
  end_time: number;
  duration: number;
  word_count: number;
  estimated_wpm: number;
  question_count: number;
  exclamation_count: number;
  filler_count: number;
  transition_count: number;
}

export interface ScriptMetricsData {
  id: string;
  video_id: string;
  calculation_version: string;
  calculated_at: string;
  word_count: number;
  unique_words: number;
  lexical_diversity_ttr: number;
  root_ttr: number;
  sentence_count: number;
  avg_sentence_length: number;
  median_sentence_length: number;
  min_sentence_length: number;
  max_sentence_length: number;
  sentence_length_distribution: Record<string, number>;
  total_spoken_duration: number;
  estimated_wpm: number;
  pace_timeline: PaceTimelineWindow[];
  question_count: number;
  exclamation_count: number;
  question_evidence: QuestionEvidenceItem[];
  exclamation_evidence: ExclamationEvidenceItem[];
  word_frequencies: Record<string, number>;
  word_frequencies_filtered: Record<string, number>;
  phrase_frequencies: {
    '2': Record<string, number>;
    '3': Record<string, number>;
    '4': Record<string, number>;
  };
  repeated_phrases: RepeatedPhraseItem[];
  filler_word_counts: Record<string, number>;
  transition_phrase_counts: Record<string, number>;
  filler_evidence: DictionaryMatchEvidence[];
  transition_evidence: DictionaryMatchEvidence[];
  opening_extracts: Record<string, string>;
  closing_extracts: Record<string, string>;
}

export interface FrameData {
  id: string;
  visual_metrics_id: string;
  video_id: string;
  frame_number: number;
  timestamp: number;
  frame_type: string;
  file_path: string;
  file_size_bytes: number;
  width: number;
  height: number;
  created_at: string;
  image_url: string;
}

export interface VisualSegmentData {
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  representative_frame_id?: string;
  change_score?: number;
}

export interface VisualActivityWindow {
  window_index: number;
  start_time: number;
  end_time: number;
  duration: number;
  boundary_count: number;
  change_density: number;
  representative_frame_ids: string[];
}

export interface OCREvidenceData {
  id: string;
  timestamp: number;
  detected_text: string;
  confidence: number;
  frame_id?: string;
}

export interface VisualMetricsData {
  id: string;
  video_id: string;
  algorithm_version: string;
  scene_threshold: number;
  analyzed_at: string;
  scene_count: number;
  avg_scene_duration: number;
  median_scene_duration: number;
  shortest_scene_duration: number;
  longest_scene_duration: number;
  scene_change_frequency: number;
  scene_timestamps: number[];
  visual_segments: VisualSegmentData[];
  segment_duration_distribution: Record<string, number>;
  visual_activity_timeline: VisualActivityWindow[];
  technical_properties: Record<string, any>;
  frames: FrameData[];
  ocr_results: OCREvidenceData[];
  ocr_available: boolean;
}

export interface ComparisonVideoItem {
  video_id: string;
  title: string;
  platform: string;
  duration_seconds: number;
  creator_name?: string | null;
  thumbnail_url?: string | null;
}

export interface ComparisonSavedItem {
  id: string;
  title: string;
  notes?: string | null;
  created_at: string;
  updated_at?: string | null;
  videos: ComparisonVideoItem[];
}

export interface MetricMatrixCell {
  raw_value?: number | string | null;
  display_value: string;
  normalized_per_min?: number | null;
  is_min: boolean;
  is_max: boolean;
  status: 'AVAILABLE' | 'NOT_ANALYZED' | 'UNAVAILABLE' | 'NOT_APPLICABLE';
}

export interface MetricMatrixRow {
  key: string;
  label: string;
  category: string;
  unit: string;
  values: Record<string, MetricMatrixCell>;
}

export interface NormalizedTimelinePoint {
  decile: number;
  decile_label: string;
  series: Record<string, {
    wpm: number;
    words: number;
    scene_changes: number;
    cuts_per_minute: number;
    has_transcript: boolean;
    has_visuals: boolean;
  }>;
}

export interface TimelineEventItem {
  timestamp: number;
  normalized_position_pct: number;
  formatted_time: string;
  duration_seconds?: number | null;
}

export interface WordFrequencyItem {
  word: string;
  count: number;
  occurrences_per_thousand: number;
}

export interface NGramItem {
  ngram: string;
  count: number;
}

export interface VideoVocabularyProfile {
  video_id: string;
  title: string;
  total_words: number;
  unique_words: number;
  ttr: number;
  top_words: WordFrequencyItem[];
  signature_words: WordFrequencyItem[];
  top_bigrams: NGramItem[];
  top_trigrams: NGramItem[];
  top_fourgrams: NGramItem[];
  repeated_phrases: NGramItem[];
}

export interface SharedVocabularyItem {
  word: string;
  counts: Record<string, number>;
  total_count: number;
  video_count: number;
  occurrences_per_thousand_avg: number;
}

export interface SharedPhraseItem {
  phrase: string;
  counts: Record<string, number>;
  total_count: number;
  video_count: number;
}

export interface OpeningClosingSnippet {
  video_id: string;
  title: string;
  duration_seconds: number;
  first_sentence?: string | null;
  first_3s_text?: string | null;
  first_5s_text?: string | null;
  first_10s_text?: string | null;
  opening_text?: string | null;
  opening_duration_sec: number;
  opening_word_count: number;
  opening_wpm: number;
  opening_questions: number;
  words_in_first_5s: number;
  words_in_first_10s: number;
  final_sentence?: string | null;
  last_5s_text?: string | null;
  last_10s_text?: string | null;
  closing_text?: string | null;
  closing_duration_sec: number;
  closing_word_count: number;
  closing_wpm: number;
  status: string;
}

export interface KeyframeGalleryItem {
  position_pct: number;
  label: string;
  frame_id?: string | null;
  timestamp?: number | null;
  file_path?: string | null;
  image_url?: string | null;
  width?: number | null;
  height?: number | null;
  status: string;
}

export interface OCREvidenceItem {
  video_id: string;
  video_title: string;
  timestamp: number;
  formatted_time: string;
  detected_text: string;
  confidence: number;
}

export interface CreatorAggregateMetrics {
  creator_id?: string | null;
  creator_name: string;
  platform: string;
  sample_size_n: number;
  mean_duration_seconds: number;
  median_duration_seconds: number;
  mean_wpm?: number | null;
  mean_vocabulary_richness?: number | null;
  mean_cut_rate_per_min?: number | null;
  total_views?: number | null;
  mean_views?: number | null;
  total_likes?: number | null;
  mean_likes?: number | null;
  total_comments?: number | null;
  mean_comments?: number | null;
  video_ids: string[];
}

export interface VideoComparisonSummary {
  id: string;
  title: string;
  platform: string;
  duration_seconds: number;
  creator_name?: string | null;
  thumbnail_url?: string | null;
  published_at?: string | null;
  views?: number | null;
  likes?: number | null;
  comments?: number | null;
  like_view_ratio?: number | null;
  comment_view_ratio?: number | null;
  has_transcript: boolean;
  transcript_language?: string | null;
  transcript_source?: string | null;
  requested_language?: string | null;
  asr_model?: string | null;
  is_generated?: boolean | null;
  has_script_metrics: boolean;
  has_visual_metrics: boolean;
}

export interface MultiVideoComparisonResult {
  videos: VideoComparisonSummary[];
  matrix: MetricMatrixRow[];
  timeline_deciles: NormalizedTimelinePoint[];
  timeline_events: Record<string, TimelineEventItem[]>;
  shared_vocabulary: SharedVocabularyItem[];
  shared_phrases: SharedPhraseItem[];
  video_vocabularies: Record<string, VideoVocabularyProfile>;
  openings_closings: OpeningClosingSnippet[];
  keyframe_gallery: Record<string, KeyframeGalleryItem[]>;
  ocr_evidence: OCREvidenceItem[];
  creator_aggregates: CreatorAggregateMetrics[];
  has_mixed_languages: boolean;
  detected_languages: string[];
  generated_at: string;
}

export interface ModelCatalogItem {
  model_id: string;
  provider_id: string;
  family: string;
  display_name: string;
  description: string;
  supported_languages: string[];
  is_multilingual: boolean;
  recommended_use: string;
  runtime_requirement: string;
  expected_download_size: string;
  expected_installed_size: string;
  license_info: string;
  source_repository: string;
  hardware_notes: string;
  status: 'NOT_INSTALLED' | 'DOWNLOADING' | 'VERIFYING' | 'READY' | 'ERROR' | 'INCOMPATIBLE' | 'CORRUPTED' | 'FILES_MISSING';
  status_detail?: string;
  local_path?: string;
  installed_size_bytes: number;
  installed_size_human: string;
  last_verified_at?: string;
}

export interface LanguageRoutingConfig {
  language_code: string;
  language_name: string;
  configured_model_id?: string;
  configured_model_name?: string;
  status: 'READY' | 'NO_MODEL_CONFIGURED' | 'MODEL_NOT_READY';
}

export interface HardwareInfo {
  cpu_info: string;
  cpu_cores: number;
  total_ram_gb: number;
  available_ram_gb: number;
  gpu_name?: string;
  gpu_vram_gb?: number;
  notes: string;
}

export interface TranscriptionSubsystemStatus {
  status: 'NOT_CONFIGURED' | 'READY' | 'DEGRADED';
  automatic_fallback_enabled: boolean;
  installed_models_count: number;
  total_catalog_models_count: number;
  languages_configured_count: number;
  total_languages_count: number;
  model_storage_path: string;
  model_storage_size_bytes: number;
  model_storage_size_human: string;
  hardware: HardwareInfo;
  language_routes: LanguageRoutingConfig[];
}

export interface TranscriptionSettings {
  automatic_asr_fallback_enabled: boolean;
  default_language_mode: string;
  default_model_english?: string;
  default_model_tamil?: string;
  default_model_malayalam?: string;
  allow_multilingual_fallback: boolean;
}

export type SegmentRangeType = 'ENTIRE' | 'ABSOLUTE' | 'RELATIVE' | 'OPENING' | 'CLOSING';

export interface SegmentRangeRequest {
  type: SegmentRangeType;
  start_seconds?: number | null;
  end_seconds?: number | null;
  start_percent?: number | null;
  end_percent?: number | null;
  duration_seconds?: number | null;
}

export interface SegmentComparisonRequest {
  video_ids: string[];
  range: SegmentRangeRequest;
}

export interface TranscriptSegmentItem {
  id: string;
  sequence_index: number;
  start_time: number;
  end_time: number;
  duration: number;
  text: string;
  word_count: number;
  formatted_start_time: string;
}

export interface SegmentScriptMetrics {
  word_count: number;
  segment_count: number;
  sentence_count: number;
  unique_words: number;
  lexical_diversity: number; // TTR %
  average_sentence_length: number;
  question_count: number;
  exclamation_count: number;
  filler_count: number;
  transition_count: number;
  repeated_phrase_count: number;
  range_wpm: number | null;
  effective_duration_seconds: number | null;
}

export interface VideoSegmentComparisonItem {
  video_id: string;
  title: string;
  creator_name?: string | null;
  platform: string;
  thumbnail_url?: string | null;
  duration_seconds?: number | null;
  requested_transcript_language?: string | null;
  actual_transcript_language?: string | null;
  transcript_source?: string | null;
  asr_model?: string | null;
  has_transcript: boolean;
  requested_range_label: string;
  effective_start_seconds?: number | null;
  effective_end_seconds?: number | null;
  effective_duration_seconds?: number | null;
  segments: TranscriptSegmentItem[];
  full_text?: string | null;
  word_count: number;
  segment_count: number;
  metrics?: SegmentScriptMetrics | null;
  availability: 'AVAILABLE' | 'NOT_AVAILABLE' | 'NO_TRANSCRIPT' | 'EMPTY_RANGE';
  warning?: string | null;
}

export interface SegmentComparisonResponse {
  range_definition: SegmentRangeRequest;
  videos: VideoSegmentComparisonItem[];
  total_videos: number;
  has_mixed_languages?: boolean;
  detected_languages?: string[];
  compared_at: string;
}

