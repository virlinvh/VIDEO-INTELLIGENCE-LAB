import re
import html
import json
from typing import List, Dict, Any, Optional

class CaptionTrack:
    def __init__(
        self,
        raw_code: str,
        normalized_code: str,
        language_name: str,
        source: str,  # "manual" or "automatic"
        is_automatic: bool,
        url: str,
        ext: str
    ):
        self.raw_code = raw_code
        self.normalized_code = normalized_code
        self.language_name = language_name
        self.source = source
        self.is_automatic = is_automatic
        self.url = url
        self.ext = ext

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language_code": self.normalized_code,
            "raw_code": self.raw_code,
            "language_name": self.language_name,
            "source": self.source,
            "automatic": self.is_automatic,
            "url": self.url,
            "ext": self.ext
        }

class CaptionSegment:
    def __init__(self, sequence_index: int, start_time: float, end_time: float, text: str):
        self.sequence_index = sequence_index
        self.start_time = round(start_time, 3)
        self.end_time = round(end_time, 3)
        self.duration = round(max(0.0, self.end_time - self.start_time), 3)
        self.text = text.strip()
        self.word_count = len(re.findall(r"\b\w+(?:'\w+)?\b", self.text))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_index": self.sequence_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "text": self.text,
            "word_count": self.word_count
        }

class CaptionService:
    @staticmethod
    def normalize_language_code(code: str) -> str:
        """
        Conservatively normalizes language identifiers to their primary language family.
        Examples:
          en, en-US, en-GB, en-orig -> en
          ta, ta-IN, ta-LK          -> ta
          ml, ml-IN                 -> ml
        """
        if not code:
            return "unknown"
        
        c = code.strip().lower()
        if c == "en" or c.startswith("en-") or c.startswith("en_"):
            return "en"
        if c == "ta" or c.startswith("ta-") or c.startswith("ta_"):
            return "ta"
        if c == "ml" or c.startswith("ml-") or c.startswith("ml_"):
            return "ml"
        
        parts = re.split(r"[-_]", c)
        return parts[0] if parts else c

    @classmethod
    def discover_caption_tracks(cls, raw_info: Dict[str, Any]) -> List[CaptionTrack]:
        """
        Discovers and structures all available subtitle and automatic caption tracks from raw extraction info.
        Separates track discovery from selection.
        """
        tracks: List[CaptionTrack] = []
        subtitles = raw_info.get("subtitles") or {}
        auto_subtitles = raw_info.get("automatic_captions") or {}

        # 1. Discover manual / creator-uploaded subtitles
        for raw_code, track_list in subtitles.items():
            if not track_list:
                continue
            best_t = None
            for t in track_list:
                if t.get("ext") in ("vtt", "json3"):
                    best_t = t
                    break
            if not best_t:
                best_t = track_list[0]

            name = best_t.get("name") or raw_code
            url = best_t.get("url")
            ext = best_t.get("ext") or "vtt"
            if url:
                tracks.append(CaptionTrack(
                    raw_code=raw_code,
                    normalized_code=cls.normalize_language_code(raw_code),
                    language_name=name,
                    source="manual",
                    is_automatic=False,
                    url=url,
                    ext=ext
                ))

        # 2. Discover automatic platform captions
        for raw_code, track_list in auto_subtitles.items():
            if not track_list:
                continue
            best_t = None
            for t in track_list:
                if t.get("ext") in ("vtt", "json3"):
                    best_t = t
                    break
            if not best_t:
                best_t = track_list[0]

            name = best_t.get("name") or f"{raw_code} (auto-generated)"
            url = best_t.get("url")
            ext = best_t.get("ext") or "vtt"
            if url:
                tracks.append(CaptionTrack(
                    raw_code=raw_code,
                    normalized_code=cls.normalize_language_code(raw_code),
                    language_name=name,
                    source="automatic",
                    is_automatic=True,
                    url=url,
                    ext=ext
                ))

        return tracks

    @classmethod
    def select_caption_track(
        cls,
        tracks: List[CaptionTrack],
        requested_language: str
    ) -> Optional[CaptionTrack]:
        """
        Selects the best caption track strictly matching the requested language.
        Rules:
        - For requested language L:
            1. Manual caption matching L
            2. Automatic caption matching L
            3. None (route to local ASR for L)
        - A manual caption in language A NEVER beats an automatic caption in requested language L.
        - Cross-language matches are strictly rejected (no English caption when Tamil was requested).
        """
        if not tracks:
            return None

        req_norm = cls.normalize_language_code(requested_language) if requested_language != "auto" else "auto"

        if req_norm == "auto":
            # Auto selection: prefer manual over auto across all tracks
            manual_tracks = [t for t in tracks if not t.is_automatic]
            if manual_tracks:
                for t in manual_tracks:
                    if t.normalized_code == "en":
                        return t
                return manual_tracks[0]
            
            auto_tracks = [t for t in tracks if t.is_automatic]
            if auto_tracks:
                for t in auto_tracks:
                    if t.normalized_code == "en":
                        return t
                return auto_tracks[0]
            return None

        # Priority 1: Manual caption matching requested language
        for t in tracks:
            if t.normalized_code == req_norm and not t.is_automatic:
                return t

        # Priority 2: Automatic caption matching requested language
        for t in tracks:
            if t.normalized_code == req_norm and t.is_automatic:
                return t

        # Priority 3: No matching caption available for requested language
        return None

    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""
        # Unescape HTML entities (&amp;, &#39;, &quot;, etc.)
        text = html.unescape(raw_text)
        # Strip WebVTT timestamp cue tags like <00:00:04.120> or <c> tags
        text = re.sub(r"<[^>]+>", "", text)
        # Replace multiple spaces/newlines with single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def parse_vtt(cls, vtt_content: str) -> List[CaptionSegment]:
        """
        Parses standard WebVTT subtitle content into clean, non-overlapping segments.
        Handles YouTube's rolling auto-captions by deduplicating repeating consecutive lines.
        """
        lines = vtt_content.splitlines()
        segments: List[CaptionSegment] = []
        time_pattern = re.compile(r"((?:\d+:)?\d{2}:\d{2}\.\d{3})\s*-->\s*((?:\d+:)?\d{2}:\d{2}\.\d{3})")

        def time_to_seconds(t_str: str) -> float:
            parts = t_str.strip().split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return float(parts[0])

        current_start = None
        current_end = None
        current_texts = []
        seq = 0

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("WEBVTT") or line_str.startswith("NOTE") or line_str.startswith("STYLE"):
                continue

            match = time_pattern.search(line_str)
            if match:
                # If we had a previous cue block, save it
                if current_start is not None and current_texts:
                    joined_text = cls.clean_text(" ".join(current_texts))
                    if joined_text:
                        segments.append(CaptionSegment(seq, current_start, current_end, joined_text))
                        seq += 1
                current_start = time_to_seconds(match.group(1))
                current_end = time_to_seconds(match.group(2))
                current_texts = []
            elif current_start is not None:
                # Text line
                cleaned = cls.clean_text(line_str)
                if cleaned and cleaned not in current_texts:
                    current_texts.append(cleaned)

        # Final block
        if current_start is not None and current_texts:
            joined_text = cls.clean_text(" ".join(current_texts))
            if joined_text:
                segments.append(CaptionSegment(seq, current_start, current_end, joined_text))

        return cls.deduplicate_rolling_captions(segments)

    @classmethod
    def parse_json3(cls, json3_data: Dict[str, Any]) -> List[CaptionSegment]:
        """
        Parses YouTube JSON3 caption format.
        """
        segments: List[CaptionSegment] = []
        events = json3_data.get("events", [])
        seq = 0

        for event in events:
            t_start = float(event.get("tStartMs", 0)) / 1000.0
            d_dur = float(event.get("dDurationMs", 0)) / 1000.0
            t_end = t_start + d_dur
            segs = event.get("segs", [])
            text_parts = [s.get("utf8", "") for s in segs if s.get("utf8")]
            combined = cls.clean_text("".join(text_parts))
            if combined and combined != "\n":
                segments.append(CaptionSegment(seq, t_start, t_end, combined))
                seq += 1

        return cls.deduplicate_rolling_captions(segments)

    @classmethod
    def deduplicate_rolling_captions(cls, raw_segments: List[CaptionSegment]) -> List[CaptionSegment]:
        """
        Deduplicates YouTube rolling automatic captions where each cue repeats previous lines.
        """
        if not raw_segments:
            return []

        deduped: List[CaptionSegment] = []
        last_text = ""

        for seg in raw_segments:
            text = seg.text
            if not text:
                continue

            # Exact duplicate check
            if text == last_text:
                continue

            # Prefix overlap: if new text starts with previous text, or previous text was a subset
            if last_text and text.startswith(last_text):
                # Replace the last segment with the more complete one, adjusting timing
                if deduped:
                    deduped[-1].end_time = seg.end_time
                    deduped[-1].duration = round(deduped[-1].end_time - deduped[-1].start_time, 3)
                    deduped[-1].text = text
                    deduped[-1].word_count = len(re.findall(r"\b\w+(?:'\w+)?\b", text))
                    last_text = text
                    continue

            deduped.append(CaptionSegment(len(deduped), seg.start_time, seg.end_time, text))
            last_text = text

        return deduped
