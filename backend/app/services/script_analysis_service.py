import json
import re
import math
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.db.models.entities import Video, Transcript, TranscriptSegment, ScriptMetrics
from backend.app.db.base import utc_now

CALCULATION_VERSION = "1.0.0"

class ScriptAnalysisService:
    @staticmethod
    def load_dictionaries() -> Dict[str, Any]:
        cfg_path = settings.project_root / "config" / "fillers_transitions.json"
        if cfg_path.exists():
            try:
                return json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "fillers": ["um", "uh", "like", "you know", "actually", "basically", "literally", "i mean", "right", "so"],
            "transitions": ["however", "therefore", "for example", "for instance", "in addition", "finally", "first", "second"],
            "stopwords": ["the", "and", "a", "to", "of", "in", "i", "is", "that", "it", "on", "you", "this", "for", "with"]
        }

    @staticmethod
    def tokenize_words(text: str) -> List[str]:
        """
        Deterministic word tokenization:
        - Lowercases text
        - Replaces typographic/curly apostrophes with standard single quote
        - Extracts word sequences preserving internal contractions (e.g. don't, it's) and Unicode scripts (Tamil, Malayalam, Hindi, etc.)
        - Removes standalone punctuation and isolated symbols
        """
        if not text:
            return []
        cleaned = text.lower().replace("’", "'").replace("`", "'")
        # Split on whitespace and strip leading/trailing punctuation characters
        raw_words = cleaned.split()
        tokens = []
        strip_chars = ".,!?:;\"'()[]{}«»“”‘’—–-/\t\n\r"
        for w in raw_words:
            t = w.strip(strip_chars)
            if t:
                tokens.append(t)
        return tokens

    @staticmethod
    def segment_sentences(text: str) -> List[str]:
        """
        Deterministic sentence segmentation:
        - Splits on [.!?]+ followed by whitespace or string end
        - Protects common abbreviations (e.g. Mr., Dr., etc.) and acronyms (e.g. D.C., U.S.)
        """
        if not text or not text.strip():
            return []
        
        normalized = text.strip()
        temp = normalized
        # Protect multi-dot acronyms like D.C., U.S.A., Ph.D.
        temp = re.sub(r"\b([A-Za-z]\.)+([A-Za-z]\.)?", lambda m: m.group(0).replace(".", "__DOT__"), temp)
        
        # Protect specific honorifics / abbreviations
        abbrevs = [
            (r"\b(mr|mrs|ms|dr|prof|sr|jr|vs|etc|e\.g|i\.e)\.", r"\1__DOT__")
        ]
        for pattern, repl in abbrevs:
            temp = re.sub(pattern, repl, temp, flags=re.IGNORECASE)
            
        parts = re.split(r"(?<=[.!?])\s+", temp)
        sentences = []
        for p in parts:
            p_restored = p.replace("__DOT__", ".").strip()
            if p_restored:
                sentences.append(p_restored)
        return sentences

    @staticmethod
    def compute_lexical_diversity(tokens: List[str]) -> Tuple[int, int, float, float]:
        total_words = len(tokens)
        if total_words == 0:
            return 0, 0, 0.0, 0.0
        unique_words = len(set(tokens))
        ttr = round((unique_words / total_words) * 100, 2)
        root_ttr = round(unique_words / math.sqrt(total_words), 2)
        return total_words, unique_words, ttr, root_ttr

    @staticmethod
    def compute_sentence_metrics(sentences: List[str]) -> Dict[str, Any]:
        count = len(sentences)
        if count == 0:
            return {
                "sentence_count": 0,
                "avg_sentence_length": 0.0,
                "median_sentence_length": 0.0,
                "min_sentence_length": 0,
                "max_sentence_length": 0,
                "sentence_length_distribution": {"1-5": 0, "6-10": 0, "11-15": 0, "16-20": 0, "21-30": 0, "31+": 0}
            }
        
        lengths = [len(ScriptAnalysisService.tokenize_words(s)) for s in sentences]
        lengths.sort()
        avg_len = round(sum(lengths) / count, 2)
        
        mid = count // 2
        if count % 2 == 1:
            median_len = float(lengths[mid])
        else:
            median_len = round((lengths[mid - 1] + lengths[mid]) / 2.0, 2)
            
        min_len = lengths[0]
        max_len = lengths[-1]

        dist = {"1-5": 0, "6-10": 0, "11-15": 0, "16-20": 0, "21-30": 0, "31+": 0}
        for l in lengths:
            if l <= 5:
                dist["1-5"] += 1
            elif l <= 10:
                dist["6-10"] += 1
            elif l <= 15:
                dist["11-15"] += 1
            elif l <= 20:
                dist["16-20"] += 1
            elif l <= 30:
                dist["21-30"] += 1
            else:
                dist["31+"] += 1

        return {
            "sentence_count": count,
            "avg_sentence_length": avg_len,
            "median_sentence_length": median_len,
            "min_sentence_length": min_len,
            "max_sentence_length": max_len,
            "sentence_length_distribution": dist
        }

    @staticmethod
    def compute_speaking_rate_and_timeline(
        segments: List[TranscriptSegment], 
        video_duration: int = 0
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        if not segments:
            return 0.0, 0.0, []

        start_times = [s.start_time for s in segments]
        end_times = [s.end_time for s in segments]
        min_t = min(start_times)
        max_t = max(end_times)
        
        spoken_duration = max(max_t - min_t, sum(s.duration for s in segments))
        total_words = sum(len(ScriptAnalysisService.tokenize_words(s.text)) for s in segments)
        
        duration_minutes = spoken_duration / 60.0 if spoken_duration > 0 else 0.0
        overall_wpm = round(total_words / duration_minutes, 1) if duration_minutes > 0 else 0.0

        # Timeline window sizing: 15s if short (< 120s), else 30s
        win_size = 15.0 if max_t < 120 else 30.0
        num_windows = max(1, math.ceil(max_t / win_size))
        
        timeline: List[Dict[str, Any]] = []
        for i in range(num_windows):
            w_start = round(i * win_size, 1)
            w_end = round((i + 1) * win_size, 1)
            
            w_words = 0
            w_questions = 0
            w_exclamations = 0
            
            for s in segments:
                if s.end_time > w_start and s.start_time < w_end:
                    tokens = ScriptAnalysisService.tokenize_words(s.text)
                    seg_len = max(0.1, s.end_time - s.start_time)
                    overlap = min(s.end_time, w_end) - max(s.start_time, w_start)
                    ratio = min(1.0, max(0.0, overlap / seg_len))
                    w_words += int(round(len(tokens) * ratio))
                    if "?" in s.text:
                        w_questions += 1
                    if "!" in s.text:
                        w_exclamations += 1

            w_dur_min = win_size / 60.0
            w_wpm = round(w_words / w_dur_min, 1)

            timeline.append({
                "window_index": i,
                "start_time": w_start,
                "end_time": w_end,
                "duration": win_size,
                "word_count": w_words,
                "estimated_wpm": w_wpm,
                "question_count": w_questions,
                "exclamation_count": w_exclamations,
                "filler_count": 0,
                "transition_count": 0
            })

        return round(spoken_duration, 2), overall_wpm, timeline

    @staticmethod
    def detect_questions_and_exclamations(
        segments: List[TranscriptSegment]
    ) -> Tuple[int, List[Dict[str, Any]], int, List[Dict[str, Any]]]:
        question_evidence: List[Dict[str, Any]] = []
        exclamation_evidence: List[Dict[str, Any]] = []
        
        for s in segments:
            sents = ScriptAnalysisService.segment_sentences(s.text)
            for sentence in sents:
                cleaned = sentence.strip()
                if "?" in cleaned:
                    question_evidence.append({
                        "text": cleaned,
                        "timestamp": round(s.start_time, 2),
                        "sequence_index": s.sequence_index
                    })
                if "!" in cleaned:
                    exclamation_evidence.append({
                        "text": cleaned,
                        "timestamp": round(s.start_time, 2),
                        "sequence_index": s.sequence_index
                    })
                    
        return len(question_evidence), question_evidence, len(exclamation_evidence), exclamation_evidence

    @staticmethod
    def extract_opening_closing(
        segments: List[TranscriptSegment],
        full_text: str
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        if not segments:
            return {}, {}

        # Opening Extracts
        first_sentence = ""
        sentences = ScriptAnalysisService.segment_sentences(full_text)
        if sentences:
            first_sentence = sentences[0]
            final_sentence = sentences[-1]
        else:
            final_sentence = ""

        def get_text_until(sec: float) -> str:
            matched = [s.text for s in segments if s.start_time < sec]
            return " ".join(matched).strip()

        opening = {
            "first_sentence": first_sentence,
            "first_3s": get_text_until(3.0),
            "first_5s": get_text_until(5.0),
            "first_10s": get_text_until(10.0),
            "first_15s": get_text_until(15.0),
            "first_30s": get_text_until(30.0),
        }

        # Closing Extracts
        max_time = max(s.end_time for s in segments)
        def get_text_from(sec_before_end: float) -> str:
            cutoff = max(0.0, max_time - sec_before_end)
            matched = [s.text for s in segments if s.end_time > cutoff]
            return " ".join(matched).strip()

        closing = {
            "final_sentence": final_sentence,
            "last_5s": get_text_from(5.0),
            "last_10s": get_text_from(10.0),
            "last_15s": get_text_from(15.0),
            "last_30s": get_text_from(30.0),
        }

        return opening, closing

    @staticmethod
    def compute_frequencies_and_ngrams(
        tokens: List[str], 
        stopwords: List[str],
        segments: List[TranscriptSegment]
    ) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, Dict[str, int]], List[Dict[str, Any]]]:
        if not tokens:
            return {}, {}, {"2": {}, "3": {}, "4": {}}, []

        stopword_set = set(s.lower() for s in stopwords)
        
        # All word frequencies
        word_freq = dict(Counter(tokens).most_common(100))
        
        # Filtered word frequencies
        filtered_tokens = [w for w in tokens if w not in stopword_set and len(w) > 1]
        word_freq_filtered = dict(Counter(filtered_tokens).most_common(100))

        # N-grams (2, 3, 4)
        def generate_ngrams(n: int) -> Counter:
            if len(tokens) < n:
                return Counter()
            grams = [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
            return Counter(grams)

        ngrams_2 = generate_ngrams(2)
        ngrams_3 = generate_ngrams(3)
        ngrams_4 = generate_ngrams(4)

        phrase_freqs = {
            "2": dict(ngrams_2.most_common(50)),
            "3": dict(ngrams_3.most_common(50)),
            "4": dict(ngrams_4.most_common(50)),
        }

        # Repeated Phrases (min count >= 2, phrase length 2..4)
        repeated_list: List[Dict[str, Any]] = []
        
        all_repeated = []
        for n, counter in [(4, ngrams_4), (3, ngrams_3), (2, ngrams_2)]:
            for phrase, count in counter.items():
                if count >= 2:
                    words_in_p = phrase.split()
                    if all(w in stopword_set for w in words_in_p):
                        continue
                    all_repeated.append((phrase, count, n))

        all_repeated.sort(key=lambda x: (x[1], x[2]), reverse=True)

        for phrase, count, n in all_repeated[:30]:
            occurrences = []
            for s in segments:
                s_tokens = ScriptAnalysisService.tokenize_words(s.text)
                s_text_joined = " ".join(s_tokens)
                if phrase in s_text_joined:
                    occurrences.append({
                        "text": s.text,
                        "timestamp": round(s.start_time, 2),
                        "sequence_index": s.sequence_index
                    })
            repeated_list.append({
                "phrase": phrase,
                "count": count,
                "word_count": n,
                "occurrences": occurrences[:10]
            })

        return word_freq, word_freq_filtered, phrase_freqs, repeated_list

    @staticmethod
    def match_dictionary_expressions(
        segments: List[TranscriptSegment],
        dictionary_items: List[str]
    ) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
        counts: Dict[str, int] = {}
        evidence: List[Dict[str, Any]] = []

        for item in dictionary_items:
            norm_item = item.strip().lower()
            if not norm_item:
                continue
            item_tokens = ScriptAnalysisService.tokenize_words(norm_item)
            item_joined = " ".join(item_tokens)
            item_count = 0
            occurrences = []

            for s in segments:
                s_tokens = ScriptAnalysisService.tokenize_words(s.text)
                s_joined = " ".join(s_tokens)
                
                pattern = r"\b" + re.escape(item_joined) + r"\b"
                matches = re.findall(pattern, s_joined)
                if matches:
                    c = len(matches)
                    item_count += c
                    occurrences.append({
                        "text": s.text,
                        "timestamp": round(s.start_time, 2),
                        "sequence_index": s.sequence_index
                    })

            if item_count > 0:
                counts[norm_item] = item_count
                evidence.append({
                    "expression": norm_item,
                    "count": item_count,
                    "occurrences": occurrences
                })

        evidence.sort(key=lambda x: x["count"], reverse=True)
        return counts, evidence

    @classmethod
    async def analyze_and_persist(cls, video_id: str, session: AsyncSession) -> Optional[ScriptMetrics]:
        stmt = select(Transcript).options(
            selectinload(Transcript.segments)
        ).where(Transcript.video_id == video_id)
        res = await session.execute(stmt)
        transcript = res.scalar_one_or_none()

        if not transcript or not transcript.segments:
            return None

        segments = sorted(transcript.segments, key=lambda s: s.sequence_index)
        full_text = transcript.full_text or " ".join(s.text for s in segments)
        tokens = cls.tokenize_words(full_text)

        # 1. Lexical diversity
        word_count, unique_words, ttr, root_ttr = cls.compute_lexical_diversity(tokens)

        # 2. Sentences
        sentences = cls.segment_sentences(full_text)
        sent_metrics = cls.compute_sentence_metrics(sentences)

        # 3. Speaking rate & pace timeline
        spoken_dur, overall_wpm, timeline = cls.compute_speaking_rate_and_timeline(segments)

        # 4. Questions & Exclamations
        q_count, q_evidence, ex_count, ex_evidence = cls.detect_questions_and_exclamations(segments)

        # 5. Opening & Closing Extracts
        opening, closing = cls.extract_opening_closing(segments, full_text)

        # 6. Dictionaries
        dicts = cls.load_dictionaries()
        fillers = dicts.get("fillers", [])
        transitions = dicts.get("transitions", [])
        stopwords = dicts.get("stopwords", [])

        filler_counts, filler_evidence = cls.match_dictionary_expressions(segments, fillers)
        trans_counts, trans_evidence = cls.match_dictionary_expressions(segments, transitions)

        # 7. Frequencies & N-Grams
        word_freq, word_freq_filt, phrase_freqs, repeated_phrases = cls.compute_frequencies_and_ngrams(
            tokens, stopwords, segments
        )

        # Update timeline with filler & transition events
        for win in timeline:
            w_s = win["start_time"]
            w_e = win["end_time"]
            f_count = sum(1 for f in filler_evidence for occ in f["occurrences"] if w_s <= occ["timestamp"] < w_e)
            t_count = sum(1 for t in trans_evidence for occ in t["occurrences"] if w_s <= occ["timestamp"] < w_e)
            win["filler_count"] = f_count
            win["transition_count"] = t_count

        # Persist or update ScriptMetrics
        sm_stmt = select(ScriptMetrics).where(ScriptMetrics.video_id == video_id)
        sm_res = await session.execute(sm_stmt)
        sm = sm_res.scalar_one_or_none()

        if not sm:
            sm = ScriptMetrics(video_id=video_id)
            session.add(sm)

        sm.calculation_version = CALCULATION_VERSION
        sm.calculated_at = utc_now()
        sm.word_count = word_count
        sm.unique_words = unique_words
        sm.lexical_diversity_ttr = ttr
        sm.root_ttr = root_ttr

        sm.sentence_count = sent_metrics["sentence_count"]
        sm.avg_sentence_length = sent_metrics["avg_sentence_length"]
        sm.median_sentence_length = sent_metrics["median_sentence_length"]
        sm.min_sentence_length = sent_metrics["min_sentence_length"]
        sm.max_sentence_length = sent_metrics["max_sentence_length"]
        sm.sentence_length_distribution = sent_metrics["sentence_length_distribution"]

        sm.total_spoken_duration = spoken_dur
        sm.estimated_wpm = overall_wpm
        sm.pace_timeline = timeline

        sm.question_count = q_count
        sm.exclamation_count = ex_count
        sm.question_evidence = q_evidence
        sm.exclamation_evidence = ex_evidence

        sm.word_frequencies = word_freq
        sm.word_frequencies_filtered = word_freq_filt
        sm.phrase_frequencies = phrase_freqs
        sm.repeated_phrases = repeated_phrases

        sm.filler_word_counts = filler_counts
        sm.transition_phrase_counts = trans_counts
        sm.filler_evidence = filler_evidence
        sm.transition_evidence = trans_evidence

        sm.opening_extracts = opening
        sm.closing_extracts = closing

        await session.commit()
        await session.refresh(sm)
        return sm
