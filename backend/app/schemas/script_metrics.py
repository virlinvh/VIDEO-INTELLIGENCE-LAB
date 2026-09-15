from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.common import BaseSchema

class QuestionEvidenceItem(BaseSchema):
    text: str
    timestamp: float
    sequence_index: int

class ExclamationEvidenceItem(BaseSchema):
    text: str
    timestamp: float
    sequence_index: int

class OccurrenceItem(BaseSchema):
    text: str
    timestamp: float
    sequence_index: int

class DictionaryMatchEvidence(BaseSchema):
    expression: str
    count: int
    occurrences: List[OccurrenceItem]

class RepeatedPhraseItem(BaseSchema):
    phrase: str
    count: int
    word_count: int
    occurrences: List[OccurrenceItem]

class PaceTimelineWindow(BaseSchema):
    window_index: int
    start_time: float
    end_time: float
    duration: float
    word_count: int
    estimated_wpm: float
    question_count: int
    exclamation_count: int
    filler_count: int
    transition_count: int

class ScriptMetricsResponse(BaseSchema):
    id: str
    video_id: str
    calculation_version: str
    calculated_at: datetime
    
    # Core Word Metrics
    word_count: int
    unique_words: int
    lexical_diversity_ttr: float
    root_ttr: float

    # Sentence Structure
    sentence_count: int
    avg_sentence_length: float
    median_sentence_length: float
    min_sentence_length: int
    max_sentence_length: int
    sentence_length_distribution: Dict[str, int]

    # Speaking Rate & Timeline
    total_spoken_duration: float
    estimated_wpm: float
    pace_timeline: List[PaceTimelineWindow]

    # Detected Punctuation Patterns
    question_count: int
    exclamation_count: int
    question_evidence: List[QuestionEvidenceItem]
    exclamation_evidence: List[ExclamationEvidenceItem]

    # Frequency & N-Grams
    word_frequencies: Dict[str, int]
    word_frequencies_filtered: Dict[str, int]
    phrase_frequencies: Dict[str, Dict[str, int]]
    repeated_phrases: List[RepeatedPhraseItem]

    # Rule-Based Dictionaries
    filler_word_counts: Dict[str, int]
    transition_phrase_counts: Dict[str, int]
    filler_evidence: List[DictionaryMatchEvidence]
    transition_evidence: List[DictionaryMatchEvidence]

    # Temporal Extracts
    opening_extracts: Dict[str, str]
    closing_extracts: Dict[str, str]
