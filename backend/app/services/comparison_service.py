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
    Video, Creator, Comparison, ComparisonVideo, ScriptMetrics, VisualMetrics, VideoMetadata, Transcript, TranscriptSegment, Frame
)
from backend.app.schemas.comparison import (
    ComparisonCreate,
    ComparisonRead,
    ComparisonVideoItem,
    ComparisonAnalyzeRequest,
    MetricMatrixCell,
    MetricMatrixRow,
    NormalizedTimelinePoint,
    WordFrequencyItem,
    NGramItem,
    VideoVocabularyProfile,
    SharedVocabularyItem,
    OpeningClosingSnippet,
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

def format_number(val: Optional[int]) -> str:
    if val is None:
        return "Unavailable"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)

def extract_tokens(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9']+\b", text)]

def extract_ngrams(tokens: List[str], n: int) -> List[str]:
    filtered = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
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
            )
        )
        res = await db.execute(stmt)
        videos = res.scalars().all()

        video_map = {v.id: v for v in videos}
        ordered_videos: List[Video] = [video_map[vid] for vid in unique_ids if vid in video_map]

        if len(ordered_videos) < len(unique_ids):
            missing = set(unique_ids) - set(video_map.keys())
            raise HTTPException(status_code=404, detail=f"Videos not found: {list(missing)}")

        # 1. Summaries
        summaries: List[VideoComparisonSummary] = []
        for v in ordered_videos:
            thumb = v.metadata_rel.thumbnail_url if v.metadata_rel else None
            creator_name = v.creator.name if v.creator else "Unknown Creator"
            summaries.append(
                VideoComparisonSummary(
                    id=v.id,
                    title=v.title,
                    platform=v.platform,
                    duration_seconds=v.duration_seconds,
                    creator_name=creator_name,
                    thumbnail_url=thumb,
                    published_at=v.published_at,
                    has_transcript=v.transcript is not None,
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

        add_row("platform", "Platform", "METADATA", "", lambda v: (v.platform, v.platform.capitalize(), None, "AVAILABLE"))
        add_row("duration", "Duration", "METADATA", "seconds", lambda v: (v.duration_seconds, format_duration(v.duration_seconds), None, "AVAILABLE"))
        add_row("views", "View Count", "METADATA", "views", lambda v: (
            v.metadata_rel.view_count if v.metadata_rel and v.metadata_rel.view_count is not None else None,
            format_number(v.metadata_rel.view_count) if v.metadata_rel else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.view_count is not None) else "UNAVAILABLE"
        ))
        add_row("likes", "Like Count", "METADATA", "likes", lambda v: (
            v.metadata_rel.like_count if v.metadata_rel and v.metadata_rel.like_count is not None else None,
            format_number(v.metadata_rel.like_count) if v.metadata_rel else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.like_count is not None) else "UNAVAILABLE"
        ))
        add_row("comments", "Comment Count", "METADATA", "comments", lambda v: (
            v.metadata_rel.comment_count if v.metadata_rel and v.metadata_rel.comment_count is not None else None,
            format_number(v.metadata_rel.comment_count) if v.metadata_rel else "Unavailable",
            None,
            "AVAILABLE" if (v.metadata_rel and v.metadata_rel.comment_count is not None) else "UNAVAILABLE"
        ))

        def word_count_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.word_count / mins, 1)
            return (v.script_metrics.word_count, f"{v.script_metrics.word_count:,} w", norm, "AVAILABLE")
        add_row("word_count", "Total Words", "SPEECH", "words", word_count_ext)

        def wpm_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.estimated_wpm, f"{v.script_metrics.estimated_wpm:.1f} WPM", v.script_metrics.estimated_wpm, "AVAILABLE")
        add_row("wpm", "Speaking Rate (WPM)", "SPEECH", "WPM", wpm_ext)

        def ttr_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            return (v.script_metrics.lexical_diversity_ttr, f"{v.script_metrics.lexical_diversity_ttr:.3f}", v.script_metrics.lexical_diversity_ttr, "AVAILABLE")
        add_row("vocabulary_richness", "Vocabulary Richness (TTR)", "VOCABULARY", "TTR", ttr_ext)

        def questions_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.question_count / mins, 2)
            return (v.script_metrics.question_count, f"{v.script_metrics.question_count} ({norm}/min)", norm, "AVAILABLE")
        add_row("questions", "Questions Asked", "SPEECH", "questions", questions_ext)

        def exclamations_ext(v: Video):
            if not v.script_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.script_metrics.exclamation_count / mins, 2)
            return (v.script_metrics.exclamation_count, f"{v.script_metrics.exclamation_count} ({norm}/min)", norm, "AVAILABLE")
        add_row("exclamations", "Exclamations", "SPEECH", "exclamations", exclamations_ext)

        def scene_changes_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            mins = max(v.duration_seconds, 1) / 60.0
            norm = round(v.visual_metrics.scene_count / mins, 2)
            return (v.visual_metrics.scene_count, f"{v.visual_metrics.scene_count} cuts ({norm}/min)", norm, "AVAILABLE")
        add_row("scene_changes", "Scene / Shot Changes", "VISUAL", "cuts", scene_changes_ext)

        def avg_shot_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            return (v.visual_metrics.avg_scene_duration, f"{v.visual_metrics.avg_scene_duration:.1f}s", v.visual_metrics.avg_scene_duration, "AVAILABLE")
        add_row("avg_shot_duration", "Avg Shot Duration", "VISUAL", "seconds", avg_shot_ext)

        def cut_rate_ext(v: Video):
            if not v.visual_metrics:
                return (None, "Not Analyzed", None, "NOT_ANALYZED")
            return (v.visual_metrics.scene_change_frequency, f"{v.visual_metrics.scene_change_frequency:.2f}/min", v.visual_metrics.scene_change_frequency, "AVAILABLE")
        add_row("cut_rate", "Cut Frequency", "VISUAL", "cuts/min", cut_rate_ext)

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

        # 3. Normalized 0-100% Progress Timeline
        deciles_data: List[NormalizedTimelinePoint] = []
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
            cnt = Counter([t for t in toks if t not in STOP_WORDS and len(t) > 2])
            all_word_counters[v.id] = cnt

        all_unique_words = set()
        for cnt in all_word_counters.values():
            all_unique_words.update(cnt.keys())

        shared_vocabulary: List[SharedVocabularyItem] = []
        for word in all_unique_words:
            video_counts = {}
            total_c = 0
            v_count = 0
            for vid, cnt in all_word_counters.items():
                if cnt[word] > 0:
                    video_counts[vid] = cnt[word]
                    total_c += cnt[word]
                    v_count += 1
            if v_count >= 2:
                shared_vocabulary.append(SharedVocabularyItem(
                    word=word,
                    counts=video_counts,
                    total_count=total_c,
                    video_count=v_count
                ))

        shared_vocabulary.sort(key=lambda x: (x.video_count, x.total_count), reverse=True)
        shared_vocabulary = shared_vocabulary[:50]

        for v in ordered_videos:
            toks = video_tokens_map[v.id]
            cnt = all_word_counters[v.id]
            
            signature_words: List[WordFrequencyItem] = []
            for w, c in cnt.most_common():
                other_counts = [all_word_counters[other_id][w] for other_id in all_word_counters if other_id != v.id]
                max_other = max(other_counts) if other_counts else 0
                if max_other == 0 or c >= (max_other * 3):
                    signature_words.append(WordFrequencyItem(word=w, count=c))
                if len(signature_words) >= 15:
                    break

            bigrams = extract_ngrams(toks, 2)
            trigrams = extract_ngrams(toks, 3)
            top_bg = [NGramItem(ngram=ng, count=c) for ng, c in Counter(bigrams).most_common(10)]
            top_tg = [NGramItem(ngram=ng, count=c) for ng, c in Counter(trigrams).most_common(10)]

            ttr = v.script_metrics.lexical_diversity_ttr if v.script_metrics else (len(set(toks)) / max(len(toks), 1))
            video_vocabularies[v.id] = VideoVocabularyProfile(
                video_id=v.id,
                title=v.title,
                total_words=len(toks),
                unique_words=len(set(toks)),
                ttr=round(ttr, 3),
                signature_words=signature_words,
                top_bigrams=top_bg,
                top_trigrams=top_tg
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

            open_segs = [s for s in v.transcript.segments if s.start_time <= open_cutoff]
            close_segs = [s for s in v.transcript.segments if s.end_time >= close_cutoff]

            open_text = " ".join(s.text.strip() for s in open_segs if s.text.strip())
            close_text = " ".join(s.text.strip() for s in close_segs if s.text.strip())

            open_words = sum(s.word_count for s in open_segs)
            close_words = sum(s.word_count for s in close_segs)

            open_dur = min(open_cutoff, dur)
            close_dur = max(dur - close_cutoff, 1.0)

            open_wpm = round(open_words / (open_dur / 60.0), 1) if open_dur > 0 else 0.0
            close_wpm = round(close_words / (close_dur / 60.0), 1) if close_dur > 0 else 0.0

            openings_closings.append(OpeningClosingSnippet(
                video_id=v.id,
                title=v.title,
                duration_seconds=v.duration_seconds,
                opening_text=open_text[:600] + ("..." if len(open_text) > 600 else "") if open_text else None,
                opening_duration_sec=round(open_dur, 1),
                opening_word_count=open_words,
                opening_wpm=open_wpm,
                closing_text=close_text[-600:] if len(close_text) > 600 else (close_text or None),
                closing_duration_sec=round(close_dur, 1),
                closing_word_count=close_words,
                closing_wpm=close_wpm,
                status="AVAILABLE"
            ))

        # 6. Creator Aggregates
        creator_ids = list(set(v.creator_id for v in ordered_videos if v.creator_id))
        creator_aggregates: List[CreatorAggregateMetrics] = []

        for cid in creator_ids:
            c_stmt = (
                select(Video)
                .where(Video.creator_id == cid)
                .options(
                    selectinload(Video.creator),
                    selectinload(Video.metadata_rel),
                    selectinload(Video.script_metrics),
                    selectinload(Video.visual_metrics)
                )
            )
            c_res = await db.execute(c_stmt)
            creator_videos = c_res.scalars().all()
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
                video_ids=[cv.id for cv in creator_videos]
            ))

        return MultiVideoComparisonResult(
            videos=summaries,
            matrix=matrix_rows,
            timeline_deciles=deciles_data,
            shared_vocabulary=shared_vocabulary,
            video_vocabularies=video_vocabularies,
            openings_closings=openings_closings,
            creator_aggregates=creator_aggregates,
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

        comp = Comparison(title=data.title)
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
            created_at=comp.created_at,
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
            video_ids=[cv.id for cv in creator_videos]
        )
