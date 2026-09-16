import math
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.entities import Video, Transcript, TranscriptSegment, Creator, VideoMetadata
from backend.app.schemas.comparison import (
    SegmentRangeRequest,
    SegmentComparisonRequest,
    TranscriptSegmentItem,
    SegmentScriptMetrics,
    VideoSegmentComparisonItem,
    SegmentComparisonResponse,
)
from backend.app.services.script_analysis_service import ScriptAnalysisService
from backend.app.db.base import utc_now

def format_time_sec(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds is None or math.isnan(seconds) or math.isinf(seconds):
        return "00:00"
    secs = int(max(0, seconds))
    hrs = secs // 3600
    mins = (secs % 3600) // 60
    rem_secs = secs % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{rem_secs:02d}"
    return f"{mins:02d}:{rem_secs:02d}"

class SegmentQueryService:
    @staticmethod
    def validate_request(req: SegmentComparisonRequest) -> None:
        """Validate bounds, duplicate IDs, and range specifications."""
        # 1. Video ID Count Validation
        if len(req.video_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 videos are required for comparison.")
        if len(req.video_ids) > 10:
            raise HTTPException(status_code=400, detail="Cannot compare more than 10 videos simultaneously.")
        
        # Check duplicate video IDs
        if len(set(req.video_ids)) != len(req.video_ids):
            raise HTTPException(status_code=400, detail="Duplicate video IDs provided in comparison set.")

        r = req.range
        # 2. Range Type Validation
        if r.type == "ABSOLUTE":
            if r.start_seconds is not None and r.start_seconds < 0:
                raise HTTPException(status_code=400, detail="start_seconds cannot be negative.")
            if r.end_seconds is None:
                raise HTTPException(status_code=400, detail="end_seconds is required for ABSOLUTE range.")
            if r.end_seconds <= (r.start_seconds or 0.0):
                raise HTTPException(status_code=400, detail="end_seconds must be strictly greater than start_seconds.")

        elif r.type == "RELATIVE":
            sp = r.start_percent if r.start_percent is not None else 0.0
            ep = r.end_percent if r.end_percent is not None else 100.0
            if sp < 0 or sp > 100:
                raise HTTPException(status_code=400, detail="start_percent must be between 0 and 100.")
            if ep < 0 or ep > 100:
                raise HTTPException(status_code=400, detail="end_percent must be between 0 and 100.")
            if sp >= ep:
                raise HTTPException(status_code=400, detail="start_percent must be strictly less than end_percent.")

        elif r.type == "OPENING":
            if r.duration_seconds is not None and r.duration_seconds <= 0:
                raise HTTPException(status_code=400, detail="duration_seconds for OPENING range must be greater than 0.")

        elif r.type == "CLOSING":
            if r.duration_seconds is not None and r.duration_seconds <= 0:
                raise HTTPException(status_code=400, detail="duration_seconds for CLOSING range must be greater than 0.")

    @staticmethod
    def calculate_segment_metrics(
        matched_segs: List[TranscriptSegment],
        full_text: Optional[str],
        eff_start: Optional[float],
        eff_end: Optional[float],
        availability: str,
        dictionaries: Dict[str, Any]
    ) -> Optional[SegmentScriptMetrics]:
        """
        Deterministic in-memory computation of 12 segment-level script metrics
        over the exact interval evidence without database round-trips.
        """
        if availability in ("NO_TRANSCRIPT", "NOT_AVAILABLE"):
            return None

        eff_dur = round(eff_end - eff_start, 2) if eff_start is not None and eff_end is not None else None

        if availability == "EMPTY_RANGE" or not matched_segs or not full_text or not full_text.strip():
            range_wpm = 0.0 if eff_dur is not None and eff_dur > 0 else None
            return SegmentScriptMetrics(
                word_count=0,
                segment_count=0,
                sentence_count=0,
                unique_words=0,
                lexical_diversity=0.0,
                average_sentence_length=0.0,
                question_count=0,
                exclamation_count=0,
                filler_count=0,
                transition_count=0,
                repeated_phrase_count=0,
                range_wpm=range_wpm,
                effective_duration_seconds=eff_dur
            )

        # 1. Unicode-aware Word Tokenization & Lexical Diversity
        tokens = ScriptAnalysisService.tokenize_words(full_text)
        total_words, unique_words, ttr, _ = ScriptAnalysisService.compute_lexical_diversity(tokens)

        # 2. Sentences & Sentence Metrics
        sentences = ScriptAnalysisService.segment_sentences(full_text)
        sent_metrics = ScriptAnalysisService.compute_sentence_metrics(sentences)

        # 3. Questions & Exclamations
        q_count, _, exc_count, _ = ScriptAnalysisService.detect_questions_and_exclamations(matched_segs)

        # 4. Fillers & Transitions
        fillers = dictionaries.get("fillers", [])
        transitions = dictionaries.get("transitions", [])
        filler_counts, _ = ScriptAnalysisService.match_dictionary_expressions(matched_segs, fillers)
        trans_counts, _ = ScriptAnalysisService.match_dictionary_expressions(matched_segs, transitions)

        # 5. Repeated Phrases (exact normalized repetition)
        stopwords = dictionaries.get("stopwords", [])
        _, _, _, repeated_list = ScriptAnalysisService.compute_frequencies_and_ngrams(tokens, stopwords, matched_segs)

        # 6. Range WPM = word_count / (effective_range_duration_seconds / 60)
        range_wpm: Optional[float] = None
        if eff_dur is not None and eff_dur > 0:
            range_wpm = round(total_words / (eff_dur / 60.0), 1)

        return SegmentScriptMetrics(
            word_count=total_words,
            segment_count=len(matched_segs),
            sentence_count=sent_metrics["sentence_count"],
            unique_words=unique_words,
            lexical_diversity=ttr,
            average_sentence_length=sent_metrics["avg_sentence_length"],
            question_count=q_count,
            exclamation_count=exc_count,
            filler_count=sum(filler_counts.values()),
            transition_count=sum(trans_counts.values()),
            repeated_phrase_count=len(repeated_list),
            range_wpm=range_wpm,
            effective_duration_seconds=eff_dur
        )

    @staticmethod
    async def query_segments(
        db: AsyncSession,
        request: SegmentComparisonRequest
    ) -> SegmentComparisonResponse:
        """
        Query and extract transcript segment intervals across 2 to 10 videos
        without N+1 database queries, computing deterministic segment metrics in memory.
        """
        SegmentQueryService.validate_request(request)
        dictionaries = ScriptAnalysisService.load_dictionaries()

        # 1. Single Grouped Query for all videos and transcripts
        stmt = (
            select(Video)
            .where(Video.id.in_(request.video_ids))
            .options(
                selectinload(Video.creator),
                selectinload(Video.metadata_rel),
                selectinload(Video.transcript).selectinload(Transcript.segments)
            )
        )
        res = await db.execute(stmt)
        found_videos = res.scalars().all()
        video_map: Dict[str, Video] = {v.id: v for v in found_videos}

        # Check for unknown video IDs
        missing_ids = [vid for vid in request.video_ids if vid not in video_map]
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"The following video ID(s) were not found in the Library: {', '.join(missing_ids)}"
            )

        # Preserve requested video ID ordering
        ordered_videos = [video_map[vid] for vid in request.video_ids]

        results: List[VideoSegmentComparisonItem] = []
        r_type = request.range.type
        detected_languages: set = set()

        for v in ordered_videos:
            dur = float(v.duration_seconds) if v.duration_seconds is not None and v.duration_seconds > 0 else None
            t = v.transcript
            has_t = t is not None and len(t.segments) > 0

            # Transcript Metadata
            req_lang = t.requested_language if t else None
            act_lang = t.language if t else None
            if act_lang:
                detected_languages.add(act_lang)
            elif req_lang:
                detected_languages.add(req_lang)

            t_source = (t.caption_source or t.source_type) if t else None
            asr_m = t.asr_model if t else None

            eff_start: Optional[float] = None
            eff_end: Optional[float] = None
            range_lbl: str = ""
            warning: Optional[str] = None
            availability: str = "AVAILABLE"

            # Compute effective range based on range_type
            if r_type == "ENTIRE":
                eff_start = 0.0
                if dur is not None:
                    eff_end = dur
                elif has_t:
                    eff_end = round(t.segments[-1].end_time, 2)
                else:
                    eff_end = None
                range_lbl = "Entire Script"
                
                matched_segs = t.segments if has_t else []

            elif r_type == "ABSOLUTE":
                req_s = max(0.0, float(request.range.start_seconds or 0.0))
                req_e = float(request.range.end_seconds or 0.0)
                range_lbl = f"{format_time_sec(req_s)} – {format_time_sec(req_e)}"
                eff_start = req_s
                
                # Graceful handling for video shorter than requested end time
                if dur is not None:
                    eff_end = min(dur, req_e)
                else:
                    eff_end = req_e

                if has_t:
                    # Interval intersection: seg.end > req_s AND seg.start < req_e
                    matched_segs = [s for s in t.segments if s.end_time > req_s and s.start_time < req_e]
                else:
                    matched_segs = []

            elif r_type == "RELATIVE":
                sp = float(request.range.start_percent if request.range.start_percent is not None else 0.0)
                ep = float(request.range.end_percent if request.range.end_percent is not None else 100.0)
                range_lbl = f"{sp:g}% – {ep:g}%"

                if dur is None:
                    matched_segs = []
                    availability = "NOT_AVAILABLE"
                    warning = "Video duration is missing or zero; relative percentage window cannot be computed."
                else:
                    eff_start = round((sp / 100.0) * dur, 2)
                    eff_end = round((ep / 100.0) * dur, 2)
                    if has_t:
                        matched_segs = [s for s in t.segments if s.end_time > eff_start and s.start_time < eff_end]
                    else:
                        matched_segs = []

            elif r_type == "OPENING":
                req_dur = float(request.range.duration_seconds or 5.0)
                range_lbl = f"Opening (First {req_dur:g}s)"
                eff_start = 0.0
                if dur is not None:
                    eff_end = min(dur, req_dur)
                else:
                    eff_end = req_dur

                if has_t:
                    matched_segs = [s for s in t.segments if s.end_time > 0.0 and s.start_time < req_dur]
                else:
                    matched_segs = []

            elif r_type == "CLOSING":
                req_dur = float(request.range.duration_seconds or 5.0)
                range_lbl = f"Closing (Last {req_dur:g}s)"

                if dur is None:
                    matched_segs = []
                    availability = "NOT_AVAILABLE"
                    warning = "Video duration is missing or zero; closing window cannot be computed."
                else:
                    eff_start = max(0.0, round(dur - req_dur, 2))
                    eff_end = round(dur, 2)
                    if has_t:
                        matched_segs = [s for s in t.segments if s.end_time > eff_start and s.start_time < eff_end]
                    else:
                        matched_segs = []
            else:
                matched_segs = []

            # Format segments
            seg_items: List[TranscriptSegmentItem] = []
            for s in matched_segs:
                seg_items.append(TranscriptSegmentItem(
                    id=s.id,
                    sequence_index=s.sequence_index,
                    start_time=round(s.start_time, 2),
                    end_time=round(s.end_time, 2),
                    duration=round(s.duration, 2),
                    text=s.text,
                    word_count=s.word_count,
                    formatted_start_time=format_time_sec(s.start_time)
                ))

            # Availability classification
            if availability == "AVAILABLE":
                if not has_t:
                    availability = "NO_TRANSCRIPT"
                elif len(seg_items) == 0:
                    availability = "EMPTY_RANGE"

            full_text = " ".join(s.text.strip() for s in seg_items if s.text.strip()) if seg_items else None
            eff_dur = round(eff_end - eff_start, 2) if eff_start is not None and eff_end is not None else None

            # Calculate deterministic in-memory SegmentScriptMetrics
            metrics = SegmentQueryService.calculate_segment_metrics(
                matched_segs=matched_segs,
                full_text=full_text,
                eff_start=eff_start,
                eff_end=eff_end,
                availability=availability,
                dictionaries=dictionaries
            )

            w_count = metrics.word_count if metrics else sum(s.word_count for s in seg_items)

            c_name = v.creator.name if v.creator else None
            thumb_url = v.metadata_rel.thumbnail_url if v.metadata_rel else None

            results.append(VideoSegmentComparisonItem(
                video_id=v.id,
                title=v.title,
                creator_name=c_name,
                platform=v.platform,
                thumbnail_url=thumb_url,
                duration_seconds=dur,
                requested_transcript_language=req_lang,
                actual_transcript_language=act_lang,
                transcript_source=t_source,
                asr_model=asr_m,
                has_transcript=has_t,
                requested_range_label=range_lbl,
                effective_start_seconds=round(eff_start, 2) if eff_start is not None else None,
                effective_end_seconds=round(eff_end, 2) if eff_end is not None else None,
                effective_duration_seconds=eff_dur,
                segments=seg_items,
                full_text=full_text,
                word_count=w_count,
                segment_count=len(seg_items),
                metrics=metrics,
                availability=availability,
                warning=warning
            ))

        sorted_languages = sorted(list(detected_languages))

        return SegmentComparisonResponse(
            range_definition=request.range,
            videos=results,
            total_videos=len(results),
            has_mixed_languages=len(sorted_languages) > 1,
            detected_languages=sorted_languages,
            compared_at=utc_now()
        )
