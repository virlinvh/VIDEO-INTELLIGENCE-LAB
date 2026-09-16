import re
import math
import statistics
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from backend.app.db.models.entities import (
    Video, Creator, Comparison, ComparisonVideo, ScriptMetrics, VisualMetrics, VideoMetadata, Transcript, TranscriptSegment, Frame, OCRResult
)
from backend.app.schemas.comparison import (
    ComparisonCreate,
    ComparisonUpdate,
    ComparisonRead,
    ComparisonVideoItem,
    ComparisonAnalyzeRequest,
    MetricMatrixCell,
    MetricMatrixRow,
    NormalizedTimelinePoint,
    TimelineEventItem,
    WordFrequencyItem,
    NGramItem,
    VideoVocabularyProfile,
    SharedVocabularyItem,
    SharedPhraseItem,
    OpeningClosingSnippet,
    KeyframeItem,
    OCREvidenceItem,
    CreatorAggregateMetrics,
    VideoComparisonSummary,
    MultiVideoComparisonResult,
)
from backend.app.db.base import utc_now

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
    "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "just", "like", "get", "know", "see", "also", "one", "even", "well", "way", "actually", "going", "really"
}

def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def format_time_sec(seconds: float) -> str:
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"

def format_number(val: Optional[int]) -> str:
    if val is None:
        return "Unavailable"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)

def extract_tokens(text: str) -> List[str]:
    if not text:
        return []
    # Unicode-aware word tokenization preserving Tamil, Malayalam, English, etc.
    # Strips punctuation while preserving multi-byte Indic and Unicode characters and combining marks
    words = re.findall(r"[^\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~—–…“”‘’«»]+", text)
    return [w.lower() for w in words if w]

def extract_ngrams(tokens: List[str], n: int) -> List[str]:
    filtered = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    if len(filtered) < n:
        return []
    return [" ".join(filtered[i:i+n]) for i in range(len(filtered) - n + 1)]

class ComparisonService:
    @staticmethod
    async def compare_videos(db: AsyncSession, video_ids: List[str]) -> MultiVideoComparisonResult:
        if len(video_ids) < 2:
            raise HTTPException(status_code=400, detail="Comparison requires at least 2 videos.")
        if len(video_ids) > 10:
            raise HTTPException(status_code=400, detail="Comparison supports a maximum of 10 videos.")

        unique_ids = list(dict.fromkeys(video_ids))
        if len(unique_ids) < 2:
            raise HTTPException(status_code=400, detail="Comparison requires at least 2 distinct videos.")

        stmt = (
            select(Video)
            .where(Video.id.in_(unique_ids))
            .options(
                selectinload(Video.creator),
                selectinload(Video.metadata_rel),
                selectinload(Video.transcript).selectinload(Transcript.segments),
                selectinload(Video.script_metrics),
                selectinload(Video.visual_metrics).selectinload(VisualMetrics.frames),
                selectinload(Video.visual_metrics).selectinload(VisualMetrics.ocr_results),
            )
        )
        res = await db.execute(stmt)
        videos = res.scalars().all()

        video_map = {v.id: v for v in videos}
        ordered_videos: List[Video] = [video_map[vid] for vid in unique_ids if vid in video_map]

        if len(ordered_videos) < len(unique_ids):
            missing = set(unique_ids) - set(video_map.keys())
            raise HTTPException(status_code=404, detail=f"Videos not found: {list(missing)}")

        # Detect languages across transcripts
        detected_langs: List[str] = []
        for v in ordered_videos:
            if v.transcript and v.transcript.language:
                detected_langs.append(v.transcript.language)
        unique_detected = list(dict.fromkeys(detected_langs))
        has_mixed = len(unique_detected) > 1

        # 1. Summaries & Engagement
        summaries: List[VideoComparisonSummary] = []
        for v in ordered_videos:
            thumb = v.metadata_rel.thumbnail_url if v.metadata_rel else None
            creator_name = v.creator.name if v.creator else "Unknown Creator"
            
            views = v.metadata_rel.view_count if v.metadata_rel and v.metadata_rel.view_count is not None else None
            likes = v.metadata_rel.like_count if v.metadata_rel and v.metadata_rel.like_count is not None else None
            comments = v.metadata_rel.comment_count if v.metadata_rel and v.metadata_rel.comment_count is not None else None

            # Safe division for engagement ratios
            like_ratio = None
            if views is not None and views > 0 and likes is not None:
                like_ratio = round((likes / views) * 100.0, 2)

            comment_ratio = None
            if views is not None and views > 0 and comments is not None:
                comment_ratio = round((comments / views) * 100.0, 2)

            summaries.append(
                VideoComparisonSummary(
                    id=v.id,
                    title=v.title,
                    platform=v.platform,
                    duration_seconds=v.duration_seconds,
                    creator_name=creator_name,
                    thumbnail_url=thumb,
                    published_at=v.published_at,
                    views=views,
                    likes=likes,
                    comments=comments,
                    like_view_ratio=like_ratio,
                    comment_view_ratio=comment_ratio,
                    has_transcript=v.transcript is not None,
                    transcript_language=v.transcript.language if v.transcript else None,
                    transcript_source=v.transcript.caption_source if v.transcript else None,
                    requested_language=v.transcript.requested_language if v.transcript else None,
                    asr_model=v.transcript.asr_model if v.transcript else None,
                    is_generated=v.transcript.is_generated if v.transcript else None,
                    has_script_metrics=v.script_metrics is not None,
                    has_visual_metrics=v.visual_metrics is not None,
                )
            )

        # 2. Metric Matrix Rows
        matrix_rows: List[MetricMatrixRow] = []

        def add_row(
            key: str,
            label: str,
            category: str,
            unit: str,
            extractor_func
        ):
            cells: Dict[str, MetricMatrixCell] = {}
            numeric_vals: List[Tuple[str, float]] = []

            for v in ordered_videos:
                raw_val, disp_val, norm_val, status = extractor_func(v)
                cells[v.id] = MetricMatrixCell(
                    raw_value=raw_val,
                    display_value=str(disp_val),
                    normalized_per_min=norm_val,
                    status=status
                )
                if status == "AVAILABLE" and isinstance(raw_val, (int, float)):
                    comp_val = norm_val if norm_val is not None else float(raw_val)
                    numeric_vals.append((v.id, comp_val))

            if len(numeric_vals) >= 2:
                vals_only = [x[1] for x in numeric_vals]
                min_v = min(vals_only)
                max_v = max(vals_only)
                if min_v != max_v:
                    for vid, comp_v in numeric_vals:
                        if comp_v == min_v:
                            cells[vid].is_min = True
                        if comp_v == max_v:
                            cells[vid].is_max = True

            matrix_rows.append(MetricMatrixRow(
                key=key,
                label=label,
                category=category,
                unit=unit,
                values=cells
            ))

        # Metadata Category
        add_row("platform", "Platform", "METADATA", "", lambda v: (v.platform, v.platform.capitalize(), None, "AVAILABLE"))
        add_row("duration", "Duration", "METADATA", "seconds", lambda v: (v.duration_seconds, format_duration(v.duration_seconds), None, "AVAILABLE"))

        # Engagement Category
        add_row("views", "View Count", "ENGAGEMENT", "views", lambda v: (
            v.metadata_rel.view_count if v.metadata_rel and v.metadata_rel.view_count is not None else None,
            format_number(v.metadata_rel.view_count) if (v.metadata_rel and v.metadata_rel.view_count is not None) else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.view_count is not None) else "UNAVAILABLE"
        ))
        add_row("likes", "Like Count", "ENGAGEMENT", "likes", lambda v: (
            v.metadata_rel.like_count if v.metadata_rel and v.metadata_rel.like_count is not None else None,
            format_number(v.metadata_rel.like_count) if (v.metadata_rel and v.metadata_rel.like_count is not None) else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.like_count is not None) else "UNAVAILABLE"
        ))
        add_row("comments", "Comment Count", "ENGAGEMENT", "comments", lambda v: (
            v.metadata_rel.comment_count if v.metadata_rel and v.metadata_rel.comment_count is not None else None,
            format_number(v.metadata_rel.comment_count) if (v.metadata_rel and v.metadata_rel.comment_count is not None) else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.comment_count is not None) else "UNAVAILABLE"
        ))
        add_row("like_view_ratio", "Like/View Ratio", "ENGAGEMENT", "%", lambda v: (
            round((v.metadata_rel.like_count / v.metadata_rel.view_count) * 100.0, 2)
            if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.like_count is not None)
            else None,
            f"{(v.metadata_rel.like_count / v.metadata_rel.view_count) * 100.0:.2f}%"
            if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.like_count is not None)
            else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.like_count is not None) else "UNAVAILABLE"
        ))
        add_row("comment_view_ratio", "Comment/View Ratio", "ENGAGEMENT", "%", lambda v: (
            round((v.metadata_rel.comment_count / v.metadata_rel.view_count) * 100.0, 2)
            if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.comment_count is not None)
            else None,
            f"{(v.metadata_rel.comment_count / v.metadata_rel.view_count) * 100.0:.2f}%"
            if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.comment_count is not None)
            else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.view_count and v.metadata_rel.view_count > 0 and v.metadata_rel.comment_count is not None) else "UNAVAILABLE"
        ))

        # Speech / Script Category
        def word_count_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.word_count / mins, 1)
            return (v.script_metrics.word_count, f"{v.script_metrics.word_count:,} words", norm, "AVAILABLE")
        add_row("word_count", "Total Words", "SPEECH", "words", word_count_ext)

        def wpm_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.estimated_wpm, f"{v.script_metrics.estimated_wpm:.1f} WPM", v.script_metrics.estimated_wpm, "AVAILABLE")
        add_row("wpm", "Speaking Rate (WPM)", "SPEECH", "WPM", wpm_ext)

        def sentence_count_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.sentence_count / mins, 1)
            return (v.script_metrics.sentence_count, f"{v.script_metrics.sentence_count}", norm, "AVAILABLE")
        add_row("sentence_count", "Total Sentences", "SPEECH", "sentences", sentence_count_ext)

        def avg_sentence_len_ext(v: Video):
            if not v.script_metrics or v.script_metrics.avg_sentence_length is None:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.avg_sentence_length, f"{v.script_metrics.avg_sentence_length:.1f} words", v.script_metrics.avg_sentence_length, "AVAILABLE")
        add_row("avg_sentence_length", "Avg Sentence Length", "SPEECH", "words/sentence", avg_sentence_len_ext)

        def questions_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.question_count / mins, 2)
            return (v.script_metrics.question_count, f"{v.script_metrics.question_count}", norm, "AVAILABLE")
        add_row("questions", "Questions Asked", "SPEECH", "questions", questions_ext)

        def questions_per_min_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.question_count / mins, 2)
            return (norm, f"{norm:.2f}/min", norm, "AVAILABLE")
        add_row("questions_per_min", "Questions Frequency", "SPEECH", "questions/min", questions_per_min_ext)

        def exclamations_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.exclamation_count / mins, 2)
            return (v.script_metrics.exclamation_count, f"{v.script_metrics.exclamation_count}", norm, "AVAILABLE")
        add_row("exclamations", "Exclamations", "SPEECH", "exclamations", exclamations_ext)

        def exclamations_per_min_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.exclamation_count / mins, 2)
            return (norm, f"{norm:.2f}/min", norm, "AVAILABLE")
        add_row("exclamations_per_min", "Exclamation Frequency", "SPEECH", "exclamations/min", exclamations_per_min_ext)

        def fillers_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            tot = sum(v.script_metrics.filler_word_counts.values()) if v.script_metrics.filler_word_counts else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(tot / mins, 2)
            return (tot, f"{tot}", norm, "AVAILABLE")
        add_row("fillers", "Filler Words Count", "SPEECH", "fillers", fillers_ext)

        def fillers_per_min_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            tot = sum(v.script_metrics.filler_word_counts.values()) if v.script_metrics.filler_word_counts else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(tot / mins, 2)
            return (norm, f"{norm:.2f}/min", norm, "AVAILABLE")
        add_row("fillers_per_min", "Filler Frequency", "SPEECH", "fillers/min", fillers_per_min_ext)

        def transitions_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            tot = sum(v.script_metrics.transition_phrase_counts.values()) if v.script_metrics.transition_phrase_counts else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(tot / mins, 2)
            return (tot, f"{tot}", norm, "AVAILABLE")
        add_row("transitions", "Transitions Count", "SPEECH", "transitions", transitions_ext)

        def transitions_per_min_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            tot = sum(v.script_metrics.transition_phrase_counts.values()) if v.script_metrics.transition_phrase_counts else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(tot / mins, 2)
            return (norm, f"{norm:.2f}/min", norm, "AVAILABLE")
        add_row("transitions_per_min", "Transition Frequency", "SPEECH", "transitions/min", transitions_per_min_ext)

        def repeated_phrases_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            tot = len(v.script_metrics.repeated_phrases) if v.script_metrics.repeated_phrases else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(tot / mins, 2)
            return (tot, f"{tot}", norm, "AVAILABLE")
        add_row("repeated_phrases_count", "Repeated Phrases Count", "SPEECH", "phrases", repeated_phrases_ext)

        # Vocabulary Category
        def unique_words_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.unique_words, f"{v.script_metrics.unique_words}", None, "AVAILABLE")
        add_row("unique_words", "Unique Words", "VOCABULARY", "words", unique_words_ext)

        def ttr_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.lexical_diversity_ttr, f"{v.script_metrics.lexical_diversity_ttr:.3f}", v.script_metrics.lexical_diversity_ttr, "AVAILABLE")
        add_row("vocabulary_richness", "Vocabulary Richness (TTR)", "VOCABULARY", "TTR", ttr_ext)

        # Visual Category
        def scene_changes_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.visual_metrics.scene_count / mins, 2)
            return (v.visual_metrics.scene_count, f"{v.visual_metrics.scene_count} cuts", norm, "AVAILABLE")
        add_row("scene_changes", "Scene / Shot Changes", "VISUAL", "cuts", scene_changes_ext)

        def cut_rate_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.visual_metrics.scene_change_frequency, f"{v.visual_metrics.scene_change_frequency:.2f}/min", v.visual_metrics.scene_change_frequency, "AVAILABLE")
        add_row("cut_rate", "Cut Frequency", "VISUAL", "cuts/min", cut_rate_ext)

        def avg_shot_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            return (v.visual_metrics.avg_scene_duration, f"{v.visual_metrics.avg_scene_duration:.1f}s", v.visual_metrics.avg_scene_duration, "AVAILABLE")
        add_row("avg_shot_duration", "Avg Shot Duration", "VISUAL", "seconds", avg_shot_ext)

        def keyframe_count_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            cnt = len(v.visual_metrics.frames) if v.visual_metrics.frames else 0
            return (cnt, f"{cnt} frames", None, "AVAILABLE")
        add_row("keyframe_count", "Stored Keyframes", "VISUAL", "frames", keyframe_count_ext)

        def ocr_count_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            cnt = len(v.visual_metrics.ocr_results) if v.visual_metrics.ocr_results else 0
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(cnt / mins, 2)
            return (cnt, f"{cnt}", norm, "AVAILABLE")
        add_row("ocr_detections", "OCR Text Detections", "VISUAL", "detections", ocr_count_ext)

        def ocr_unique_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not analyzed", None, "NOT_ANALYZED")
            unique_ocr = len(set(r.detected_text.strip().lower() for r in v.visual_metrics.ocr_results)) if v.visual_metrics.ocr_results else 0
            return (unique_ocr, f"{unique_ocr}", None, "AVAILABLE")
        add_row("ocr_unique_strings", "Unique OCR Strings", "VISUAL", "strings", ocr_unique_ext)

        def res_ext(v: Video):
            if not v.visual_metrics or not v.visual_metrics.technical_properties:
                return (None, "Unavailable", None, "UNAVAILABLE")
            res_val = v.visual_metrics.technical_properties.get("resolution")
            if not res_val:
                return (None, "Unavailable", None, "UNAVAILABLE")
            return (res_val, str(res_val), None, "AVAILABLE")
        add_row("resolution", "Resolution", "VISUAL", "", res_ext)

        def fps_ext(v: Video):
            if not v.visual_metrics or not v.visual_metrics.technical_properties:
                return (None, "Unavailable", None, "UNAVAILABLE")
            fps_val = v.visual_metrics.technical_properties.get("fps")
            if fps_val is None:
                return (None, "Unavailable", None, "UNAVAILABLE")
            return (fps_val, f"{float(fps_val):.2f} fps", float(fps_val), "AVAILABLE")
        add_row("fps", "Frame Rate", "VISUAL", "fps", fps_ext)

        # 3. Normalized 0-100% Progress Timeline & Events
        deciles_data: List[NormalizedTimelinePoint] = []
        timeline_events_map: Dict[str, List[TimelineEventItem]] = {}

        for v in ordered_videos:
            dur = max(float(v.duration_seconds), 1.0)
            events: List[TimelineEventItem] = []
            if v.visual_metrics and v.visual_metrics.scene_timestamps:
                for idx, ts in enumerate(v.visual_metrics.scene_timestamps):
                    norm_pos = round((ts / dur) * 100.0, 2)
                    # compute scene duration if available
                    seg_dur = None
                    if idx + 1 < len(v.visual_metrics.scene_timestamps):
                        seg_dur = round(v.visual_metrics.scene_timestamps[idx+1] - ts, 2)
                    elif ts < dur:
                        seg_dur = round(dur - ts, 2)
                    
                    events.append(TimelineEventItem(
                        timestamp=round(ts, 2),
                        normalized_position_pct=min(100.0, max(0.0, norm_pos)),
                        formatted_time=format_time_sec(ts),
                        duration_seconds=seg_dur
                    ))
            timeline_events_map[v.id] = events

        for d in range(10):
            d_start_pct = d * 10
            d_end_pct = (d + 1) * 10
            label = f"{d_start_pct}-{d_end_pct}%"
            series: Dict[str, Dict[str, Any]] = {}

            for v in ordered_videos:
                dur = max(float(v.duration_seconds), 1.0)
                decile_duration_min = (dur / 10.0) / 60.0

                w_count = 0
                has_t = v.transcript is not None and len(v.transcript.segments) > 0
                if has_t:
                    t_start_sec = (d_start_pct / 100.0) * dur
                    t_end_sec = (d_end_pct / 100.0) * dur
                    for seg in v.transcript.segments:
                        mid = (seg.start_time + seg.end_time) / 2.0
                        if t_start_sec <= mid < t_end_sec:
                            w_count += seg.word_count
                
                wpm_in_decile = round(w_count / max(decile_duration_min, 0.001), 1) if has_t else 0.0

                cut_count = 0
                has_v = v.visual_metrics is not None and len(v.visual_metrics.scene_timestamps) > 0
                if has_v:
                    t_start_sec = (d_start_pct / 100.0) * dur
                    t_end_sec = (d_end_pct / 100.0) * dur
                    for ts in v.visual_metrics.scene_timestamps:
                        if t_start_sec <= ts < t_end_sec:
                            cut_count += 1
                
                cuts_per_min = round(cut_count / max(decile_duration_min, 0.001), 2) if has_v else 0.0

                series[v.id] = {
                    "wpm": wpm_in_decile,
                    "words": w_count,
                    "scene_changes": cut_count,
                    "cuts_per_minute": cuts_per_min,
                    "has_transcript": has_t,
                    "has_visuals": has_v
                }

            deciles_data.append(NormalizedTimelinePoint(
                decile=d,
                decile_label=label,
                series=series
            ))

        # 4. Vocabulary & N-Grams
        video_tokens_map: Dict[str, List[str]] = {}
        video_vocabularies: Dict[str, VideoVocabularyProfile] = {}
        all_word_counters: Dict[str, Counter] = {}

        for v in ordered_videos:
            if v.transcript and v.transcript.full_text:
                toks = extract_tokens(v.transcript.full_text)
            else:
                toks = []
            video_tokens_map[v.id] = toks
            cnt = Counter([t for t in toks if t not in STOP_WORDS and len(t) > 1])
            all_word_counters[v.id] = cnt

        all_unique_words = set()
        for cnt in all_word_counters.values():
            all_unique_words.update(cnt.keys())

        shared_vocabulary: List[SharedVocabularyItem] = []
        for word in all_unique_words:
            video_counts = {}
            total_c = 0
            v_count = 0
            norm_per_k_sum = 0.0
            for vid, cnt in all_word_counters.items():
                if cnt[word] > 0:
                    video_counts[vid] = cnt[word]
                    total_c += cnt[word]
                    v_count += 1
                    tot_w = max(len(video_tokens_map[vid]), 1)
                    norm_per_k_sum += (cnt[word] / tot_w) * 1000.0
            if v_count >= 2:
                shared_vocabulary.append(SharedVocabularyItem(
                    word=word,
                    counts=video_counts,
                    total_count=total_c,
                    video_count=v_count,
                    occurrences_per_thousand_avg=round(norm_per_k_sum / max(v_count, 1), 2)
                ))

        shared_vocabulary.sort(key=lambda x: (x.video_count, x.total_count), reverse=True)
        shared_vocabulary = shared_vocabulary[:50]

        # Shared Phrases across matching languages
        all_phrases_map: Dict[str, Dict[str, int]] = {}
        for v in ordered_videos:
            toks = video_tokens_map[v.id]
            bg = extract_ngrams(toks, 2)
            tg = extract_ngrams(toks, 3)
            all_p = bg + tg
            for p, c in Counter(all_p).items():
                if p not in all_phrases_map:
                    all_phrases_map[p] = {}
                all_phrases_map[p][v.id] = c

        shared_phrases: List[SharedPhraseItem] = []
        for phrase, v_counts in all_phrases_map.items():
            if len(v_counts) >= 2:
                shared_phrases.append(SharedPhraseItem(
                    phrase=phrase,
                    counts=v_counts,
                    total_count=sum(v_counts.values()),
                    video_count=len(v_counts)
                ))
        shared_phrases.sort(key=lambda x: (x.video_count, x.total_count), reverse=True)
        shared_phrases = shared_phrases[:30]

        for v in ordered_videos:
            toks = video_tokens_map[v.id]
            cnt = all_word_counters[v.id]
            tot_w = max(len(toks), 1)

            top_w = [
                WordFrequencyItem(
                    word=w,
                    count=c,
                    occurrences_per_thousand=round((c / tot_w) * 1000.0, 2)
                )
                for w, c in cnt.most_common(20)
            ]
            
            signature_words: List[WordFrequencyItem] = []
            for w, c in cnt.most_common():
                other_counts = [all_word_counters[other_id][w] for other_id in all_word_counters if other_id != v.id]
                max_other = max(other_counts) if other_counts else 0
                if max_other == 0 or c >= (max_other * 3):
                    signature_words.append(WordFrequencyItem(
                        word=w,
                        count=c,
                        occurrences_per_thousand=round((c / tot_w) * 1000.0, 2)
                    ))
                if len(signature_words) >= 15:
                    break

            bigrams = extract_ngrams(toks, 2)
            trigrams = extract_ngrams(toks, 3)
            fourgrams = extract_ngrams(toks, 4)
            top_bg = [NGramItem(ngram=ng, count=c) for ng, c in Counter(bigrams).most_common(10)]
            top_tg = [NGramItem(ngram=ng, count=c) for ng, c in Counter(trigrams).most_common(10)]
            top_fg = [NGramItem(ngram=ng, count=c) for ng, c in Counter(fourgrams).most_common(10)]

            rep_phrases = []
            if v.script_metrics and v.script_metrics.repeated_phrases:
                rep_phrases = [
                    NGramItem(ngram=rp.get("phrase", ""), count=rp.get("count", 0))
                    for rp in v.script_metrics.repeated_phrases[:10]
                    if isinstance(rp, dict)
                ]

            ttr = v.script_metrics.lexical_diversity_ttr if v.script_metrics else (len(set(toks)) / max(len(toks), 1))
            video_vocabularies[v.id] = VideoVocabularyProfile(
                video_id=v.id,
                title=v.title,
                total_words=len(toks),
                unique_words=len(set(toks)),
                ttr=round(ttr, 3),
                top_words=top_w,
                signature_words=signature_words,
                top_bigrams=top_bg,
                top_trigrams=top_tg,
                top_fourgrams=top_fg,
                repeated_phrases=rep_phrases
            )

        # 5. Openings & Closings
        openings_closings: List[OpeningClosingSnippet] = []
        for v in ordered_videos:
            if not v.transcript or not v.transcript.segments:
                openings_closings.append(OpeningClosingSnippet(
                    video_id=v.id,
                    title=v.title,
                    duration_seconds=v.duration_seconds,
                    status="NOT_ANALYZED"
                ))
                continue

            dur = max(float(v.duration_seconds), 1.0)
            open_cutoff = max(dur * 0.10, 30.0)
            close_cutoff = max(dur * 0.90, dur - 30.0)

            first_seg = v.transcript.segments[0].text if v.transcript.segments else None
            last_seg = v.transcript.segments[-1].text if v.transcript.segments else None

            segs_3s = [s for s in v.transcript.segments if s.start_time <= 3.0]
            segs_5s = [s for s in v.transcript.segments if s.start_time <= 5.0]
            segs_10s = [s for s in v.transcript.segments if s.start_time <= 10.0]

            close_5s = [s for s in v.transcript.segments if s.end_time >= (dur - 5.0)]
            close_10s = [s for s in v.transcript.segments if s.end_time >= (dur - 10.0)]

            open_segs = [s for s in v.transcript.segments if s.start_time <= open_cutoff]
            close_segs = [s for s in v.transcript.segments if s.end_time >= close_cutoff]

            open_text = " ".join(s.text.strip() for s in open_segs if s.text.strip())
            close_text = " ".join(s.text.strip() for s in close_segs if s.text.strip())

            open_words = sum(s.word_count for s in open_segs)
            close_words = sum(s.word_count for s in close_segs)

            w_5s = sum(s.word_count for s in segs_5s)
            w_10s = sum(s.word_count for s in segs_10s)

            open_dur = min(open_cutoff, dur)
            close_dur = max(dur - close_cutoff, 1.0)

            open_wpm = round(open_words / (open_dur / 60.0), 1) if open_dur > 0 else 0.0
            close_wpm = round(close_words / (close_dur / 60.0), 1) if close_dur > 0 else 0.0

            q_open = sum(1 for s in open_segs if "?" in s.text or "எப்படி" in s.text or "என்ன" in s.text)

            openings_closings.append(OpeningClosingSnippet(
                video_id=v.id,
                title=v.title,
                duration_seconds=v.duration_seconds,
                first_sentence=first_seg,
                first_3s_text=" ".join(s.text.strip() for s in segs_3s) if segs_3s else None,
                first_5s_text=" ".join(s.text.strip() for s in segs_5s) if segs_5s else None,
                first_10s_text=" ".join(s.text.strip() for s in segs_10s) if segs_10s else None,
                opening_text=open_text[:600] + ("..." if len(open_text) > 600 else "") if open_text else None,
                opening_duration_sec=round(open_dur, 1),
                opening_word_count=open_words,
                opening_wpm=open_wpm,
                opening_questions=q_open,
                words_in_first_5s=w_5s,
                words_in_first_10s=w_10s,
                final_sentence=last_seg,
                last_5s_text=" ".join(s.text.strip() for s in close_5s) if close_5s else None,
                last_10s_text=" ".join(s.text.strip() for s in close_10s) if close_10s else None,
                closing_text=close_text[-600:] if len(close_text) > 600 else (close_text or None),
                closing_duration_sec=round(close_dur, 1),
                closing_word_count=close_words,
                closing_wpm=close_wpm,
                status="AVAILABLE"
            ))

        # 6. Keyframe Gallery
        keyframe_gallery: Dict[str, List[KeyframeItem]] = {}
        positions = [
            (0, "Opening (0%)"),
            (25, "25% Position"),
            (50, "Midpoint (50%)"),
            (75, "75% Position"),
            (100, "Closing (100%)")
        ]

        for v in ordered_videos:
            dur = max(float(v.duration_seconds), 1.0)
            v_frames: List[KeyframeItem] = []

            has_frames = v.visual_metrics and v.visual_metrics.frames and len(v.visual_metrics.frames) > 0

            for pct, lbl in positions:
                target_ts = (pct / 100.0) * dur
                if has_frames:
                    # Find nearest frame
                    best_f = min(v.visual_metrics.frames, key=lambda f: abs(f.timestamp - target_ts))
                    # Relativize image URL for frontend
                    img_url = f"/api/v1/videos/frames/{best_f.id}/image" if best_f.id else None
                    v_frames.append(KeyframeItem(
                        position_pct=pct,
                        label=lbl,
                        frame_id=best_f.id,
                        timestamp=round(best_f.timestamp, 2),
                        file_path=best_f.file_path,
                        image_url=img_url,
                        width=best_f.width,
                        height=best_f.height,
                        status="AVAILABLE"
                    ))
                else:
                    v_frames.append(KeyframeItem(
                        position_pct=pct,
                        label=lbl,
                        status="NOT_ANALYZED"
                    ))
            keyframe_gallery[v.id] = v_frames

        # 7. OCR Evidence
        ocr_evidence_list: List[OCREvidenceItem] = []
        for v in ordered_videos:
            if v.visual_metrics and v.visual_metrics.ocr_results:
                for r in v.visual_metrics.ocr_results:
                    ocr_evidence_list.append(OCREvidenceItem(
                        video_id=v.id,
                        video_title=v.title,
                        timestamp=round(r.timestamp, 2),
                        formatted_time=format_time_sec(r.timestamp),
                        detected_text=r.detected_text,
                        confidence=round(r.confidence, 2)
                    ))
        ocr_evidence_list.sort(key=lambda x: x.timestamp)

        # 8. Creator Aggregates (Grouped Single Query)
        creator_ids = list(set(v.creator_id for v in ordered_videos if v.creator_id))
        creator_aggregates: List[CreatorAggregateMetrics] = []

        if creator_ids:
            c_stmt = (
                select(Video)
                .where(Video.creator_id.in_(creator_ids))
                .options(
                    selectinload(Video.creator),
                    selectinload(Video.metadata_rel),
                    selectinload(Video.script_metrics),
                    selectinload(Video.visual_metrics)
                )
            )
            c_res = await db.execute(c_stmt)
            all_creator_videos = c_res.scalars().all()

            from collections import defaultdict
            videos_by_creator = defaultdict(list)
            for cv in all_creator_videos:
                videos_by_creator[cv.creator_id].append(cv)

            for cid in creator_ids:
                creator_videos = videos_by_creator.get(cid, [])
                if not creator_videos:
                    continue

                c_obj = creator_videos[0].creator
                c_name = c_obj.name if c_obj else "Unknown"
                c_plat = c_obj.platform if c_obj else "unknown"

                n = len(creator_videos)
                durations = [cv.duration_seconds for cv in creator_videos]
                mean_dur = round(statistics.mean(durations), 1) if durations else 0.0
                median_dur = round(statistics.median(durations), 1) if durations else 0.0

                wpms = [cv.script_metrics.estimated_wpm for cv in creator_videos if cv.script_metrics and cv.script_metrics.estimated_wpm is not None]
                mean_wpm = round(statistics.mean(wpms), 1) if wpms else None

                ttrs = [cv.script_metrics.lexical_diversity_ttr for cv in creator_videos if cv.script_metrics and cv.script_metrics.lexical_diversity_ttr is not None]
                mean_ttr = round(statistics.mean(ttrs), 3) if ttrs else None

                cuts = [cv.visual_metrics.scene_change_frequency for cv in creator_videos if cv.visual_metrics and cv.visual_metrics.scene_change_frequency is not None]
                mean_cuts = round(statistics.mean(cuts), 2) if cuts else None

                views = [cv.metadata_rel.view_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.view_count is not None]
                tot_views = sum(views) if views else None
                mean_views = round(statistics.mean(views), 1) if views else None

                likes = [cv.metadata_rel.like_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.like_count is not None]
                tot_likes = sum(likes) if likes else None
                mean_likes = round(statistics.mean(likes), 1) if likes else None

                comments = [cv.metadata_rel.comment_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.comment_count is not None]
                tot_comments = sum(comments) if comments else None
                mean_comments = round(statistics.mean(comments), 1) if comments else None

                creator_aggregates.append(CreatorAggregateMetrics(
                    creator_id=cid,
                    creator_name=c_name,
                    platform=c_plat,
                    sample_size_n=n,
                    mean_duration_seconds=mean_dur,
                    median_duration_seconds=median_dur,
                    mean_wpm=mean_wpm,
                    mean_vocabulary_richness=mean_ttr,
                    mean_cut_rate_per_min=mean_cuts,
                    total_views=tot_views,
                    mean_views=mean_views,
                    total_likes=tot_likes,
                    mean_likes=mean_likes,
                    total_comments=tot_comments,
                    mean_comments=mean_comments,
                    video_ids=[cv.id for cv in creator_videos]
                ))

        return MultiVideoComparisonResult(
            videos=summaries,
            matrix=matrix_rows,
            timeline_deciles=deciles_data,
            timeline_events=timeline_events_map,
            shared_vocabulary=shared_vocabulary,
            shared_phrases=shared_phrases,
            video_vocabularies=video_vocabularies,
            openings_closings=openings_closings,
            keyframe_gallery=keyframe_gallery,
            ocr_evidence=ocr_evidence_list,
            creator_aggregates=creator_aggregates,
            has_mixed_languages=has_mixed,
            detected_languages=unique_detected,
            generated_at=utc_now()
        )

    @staticmethod
    async def create_comparison(db: AsyncSession, data: ComparisonCreate) -> ComparisonRead:
        if len(data.video_ids) < 2:
            raise HTTPException(status_code=400, detail="Comparison requires at least 2 videos.")
        if len(data.video_ids) > 10:
            raise HTTPException(status_code=400, detail="Comparison supports a maximum of 10 videos.")

        res = await db.execute(select(Video).where(Video.id.in_(data.video_ids)))
        existing_videos = res.scalars().all()
        if len(existing_videos) < len(set(data.video_ids)):
            raise HTTPException(status_code=404, detail="One or more specified video IDs do not exist.")

        comp = Comparison(
            title=data.title,
            notes=data.notes
        )
        db.add(comp)
        await db.flush()

        for vid in data.video_ids:
            item = ComparisonVideo(
                comparison_id=comp.id,
                video_id=vid
            )
            db.add(item)
        
        await db.commit()
        await db.refresh(comp)

        return await ComparisonService.get_comparison_by_id(db, comp.id)

    @staticmethod
    async def update_comparison(db: AsyncSession, comparison_id: str, data: ComparisonUpdate) -> ComparisonRead:
        res = await db.execute(select(Comparison).where(Comparison.id == comparison_id))
        comp = res.scalar_one_or_none()
        if not comp:
            raise HTTPException(status_code=404, detail="Comparison not found.")

        if data.title is not None:
            comp.title = data.title
        if data.notes is not None:
            comp.notes = data.notes
        comp.updated_at = utc_now()

        await db.commit()
        return await ComparisonService.get_comparison_by_id(db, comp.id)

    @staticmethod
    async def list_comparisons(db: AsyncSession) -> List[ComparisonRead]:
        res = await db.execute(select(Comparison).order_by(desc(Comparison.created_at)))
        comps = res.scalars().all()
        results: List[ComparisonRead] = []
        for c in comps:
            results.append(await ComparisonService.get_comparison_by_id(db, c.id))
        return results

    @staticmethod
    async def get_comparison_by_id(db: AsyncSession, comparison_id: str) -> ComparisonRead:
        stmt = (
            select(Comparison)
            .where(Comparison.id == comparison_id)
            .options(selectinload(Comparison.items))
        )
        res = await db.execute(stmt)
        comp = res.scalar_one_or_none()
        if not comp:
            raise HTTPException(status_code=404, detail="Comparison not found.")

        video_ids = [item.video_id for item in comp.items]
        v_stmt = (
            select(Video)
            .where(Video.id.in_(video_ids))
            .options(selectinload(Video.creator), selectinload(Video.metadata_rel))
        )
        v_res = await db.execute(v_stmt)
        videos = v_res.scalars().all()
        v_map = {v.id: v for v in videos}

        video_items: List[ComparisonVideoItem] = []
        for vid in video_ids:
            if vid in v_map:
                v = v_map[vid]
                video_items.append(ComparisonVideoItem(
                    video_id=v.id,
                    title=v.title,
                    platform=v.platform,
                    duration_seconds=v.duration_seconds,
                    creator_name=v.creator.name if v.creator else None,
                    thumbnail_url=v.metadata_rel.thumbnail_url if v.metadata_rel else None
                ))

        return ComparisonRead(
            id=comp.id,
            title=comp.title,
            notes=comp.notes,
            created_at=comp.created_at,
            updated_at=comp.updated_at,
            videos=video_items
        )

    @staticmethod
    async def delete_comparison(db: AsyncSession, comparison_id: str) -> None:
        res = await db.execute(select(Comparison).where(Comparison.id == comparison_id))
        comp = res.scalar_one_or_none()
        if not comp:
            raise HTTPException(status_code=404, detail="Comparison not found.")
        await db.delete(comp)
        await db.commit()

    @staticmethod
    async def get_creator_metrics(db: AsyncSession, creator_id: str) -> CreatorAggregateMetrics:
        stmt = (
            select(Video)
            .where(Video.creator_id == creator_id)
            .options(
                selectinload(Video.creator),
                selectinload(Video.metadata_rel),
                selectinload(Video.script_metrics),
                selectinload(Video.visual_metrics)
            )
        )
        res = await db.execute(stmt)
        creator_videos = res.scalars().all()
        if not creator_videos:
            raise HTTPException(status_code=404, detail="Creator not found or has no videos.")

        c_obj = creator_videos[0].creator
        c_name = c_obj.name if c_obj else "Unknown"
        c_plat = c_obj.platform if c_obj else "unknown"

        n = len(creator_videos)
        durations = [cv.duration_seconds for cv in creator_videos]
        mean_dur = round(statistics.mean(durations), 1) if durations else 0.0
        median_dur = round(statistics.median(durations), 1) if durations else 0.0

        wpms = [cv.script_metrics.estimated_wpm for cv in creator_videos if cv.script_metrics and cv.script_metrics.estimated_wpm is not None]
        mean_wpm = round(statistics.mean(wpms), 1) if wpms else None

        ttrs = [cv.script_metrics.lexical_diversity_ttr for cv in creator_videos if cv.script_metrics and cv.script_metrics.lexical_diversity_ttr is not None]
        mean_ttr = round(statistics.mean(ttrs), 3) if ttrs else None

        cuts = [cv.visual_metrics.scene_change_frequency for cv in creator_videos if cv.visual_metrics and cv.visual_metrics.scene_change_frequency is not None]
        mean_cuts = round(statistics.mean(cuts), 2) if cuts else None

        views = [cv.metadata_rel.view_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.view_count is not None]
        tot_views = sum(views) if views else None
        mean_views = round(statistics.mean(views), 1) if views else None

        likes = [cv.metadata_rel.like_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.like_count is not None]
        tot_likes = sum(likes) if likes else None
        mean_likes = round(statistics.mean(likes), 1) if likes else None

        comments = [cv.metadata_rel.comment_count for cv in creator_videos if cv.metadata_rel and cv.metadata_rel.comment_count is not None]
        tot_comments = sum(comments) if comments else None
        mean_comments = round(statistics.mean(comments), 1) if comments else None

        return CreatorAggregateMetrics(
            creator_id=creator_id,
            creator_name=c_name,
            platform=c_plat,
            sample_size_n=n,
            mean_duration_seconds=mean_dur,
            median_duration_seconds=median_dur,
            mean_wpm=mean_wpm,
            mean_vocabulary_richness=mean_ttr,
            mean_cut_rate_per_min=mean_cuts,
            total_views=tot_views,
            mean_views=mean_views,
            total_likes=tot_likes,
            mean_likes=mean_likes,
            total_comments=tot_comments,
            mean_comments=mean_comments,
            video_ids=[cv.id for cv in creator_videos]
        )

