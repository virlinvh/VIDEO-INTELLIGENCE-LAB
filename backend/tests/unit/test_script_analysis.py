import pytest
import math
from backend.app.services.script_analysis_service import ScriptAnalysisService
from backend.app.db.models.entities import TranscriptSegment

def test_tokenize_words():
    text = "Hello world! Don't let the 2026 AI hype distract you from deterministic-systems."
    tokens = ScriptAnalysisService.tokenize_words(text)
    assert "hello" in tokens
    assert "world" in tokens
    assert "don't" in tokens
    assert "2026" in tokens
    assert "deterministic-systems" in tokens
    assert "!" not in tokens

def test_segment_sentences():
    text = "Hello there! How are you doing today? Dr. Smith went to Washington D.C. yesterday. It was great."
    sentences = ScriptAnalysisService.segment_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "Hello there!"
    assert sentences[1] == "How are you doing today?"
    assert sentences[2] == "Dr. Smith went to Washington D.C. yesterday."
    assert sentences[3] == "It was great."

def test_compute_lexical_diversity():
    # Zero words
    tw, uw, ttr, rttr = ScriptAnalysisService.compute_lexical_diversity([])
    assert tw == 0 and uw == 0 and ttr == 0.0 and rttr == 0.0

    # Repeating words
    tokens = ["the", "cat", "saw", "the", "cat"]
    tw, uw, ttr, rttr = ScriptAnalysisService.compute_lexical_diversity(tokens)
    assert tw == 5
    assert uw == 3
    assert ttr == 60.0
    assert rttr == round(3 / math.sqrt(5), 2)

def test_compute_sentence_metrics():
    sentences = [
        "Short one.", # 2 words
        "This is a medium length sentence.", # 6 words
        "This is a much longer sentence that contains quite a few additional descriptive words.", # 14 words
    ]
    metrics = ScriptAnalysisService.compute_sentence_metrics(sentences)
    assert metrics["sentence_count"] == 3
    assert metrics["min_sentence_length"] == 2
    assert metrics["max_sentence_length"] == 14
    assert metrics["avg_sentence_length"] == round((2 + 6 + 14) / 3, 2)
    assert metrics["median_sentence_length"] == 6.0
    assert metrics["sentence_length_distribution"]["1-5"] == 1
    assert metrics["sentence_length_distribution"]["6-10"] == 1
    assert metrics["sentence_length_distribution"]["11-15"] == 1

def test_speaking_rate_and_timeline():
    segs = [
        TranscriptSegment(sequence_index=0, start_time=0.0, end_time=10.0, duration=10.0, text="Hello and welcome to this video analysis."),
        TranscriptSegment(sequence_index=1, start_time=10.0, end_time=20.0, duration=10.0, text="Today we discuss deterministic algorithms."),
        TranscriptSegment(sequence_index=2, start_time=20.0, end_time=30.0, duration=10.0, text="Is this working? Yes it is!"),
    ]
    spoken_dur, wpm, timeline = ScriptAnalysisService.compute_speaking_rate_and_timeline(segs)
    assert spoken_dur == 30.0
    assert wpm > 0.0
    assert len(timeline) >= 1
    assert timeline[0]["start_time"] == 0.0
    assert timeline[0]["estimated_wpm"] > 0

def test_detect_questions_and_exclamations():
    segs = [
        TranscriptSegment(sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text="What is going on here?"),
        TranscriptSegment(sequence_index=1, start_time=5.0, end_time=10.0, duration=5.0, text="This is incredible!"),
        TranscriptSegment(sequence_index=2, start_time=10.0, end_time=15.0, duration=5.0, text="Just a normal sentence."),
    ]
    q_count, q_ev, ex_count, ex_ev = ScriptAnalysisService.detect_questions_and_exclamations(segs)
    assert q_count == 1
    assert q_ev[0]["text"] == "What is going on here?"
    assert q_ev[0]["timestamp"] == 0.0
    assert ex_count == 1
    assert ex_ev[0]["text"] == "This is incredible!"
    assert ex_ev[0]["timestamp"] == 5.0

def test_extract_opening_closing():
    segs = [
        TranscriptSegment(sequence_index=0, start_time=0.0, end_time=2.0, duration=2.0, text="First words spoken."),
        TranscriptSegment(sequence_index=1, start_time=2.0, end_time=8.0, duration=6.0, text="Next section continues."),
        TranscriptSegment(sequence_index=2, start_time=8.0, end_time=20.0, duration=12.0, text="Middle discussion."),
        TranscriptSegment(sequence_index=3, start_time=20.0, end_time=28.0, duration=8.0, text="Almost finished now."),
        TranscriptSegment(sequence_index=4, start_time=28.0, end_time=30.0, duration=2.0, text="Final sentence here."),
    ]
    full_text = "First words spoken. Next section continues. Middle discussion. Almost finished now. Final sentence here."
    opening, closing = ScriptAnalysisService.extract_opening_closing(segs, full_text)
    
    assert opening["first_sentence"] == "First words spoken."
    assert "First words spoken" in opening["first_3s"]
    assert closing["final_sentence"] == "Final sentence here."
    assert "Final sentence here" in closing["last_5s"]

def test_frequencies_and_ngrams():
    text = "the quick brown fox jumps over the lazy dog and the quick brown fox was fast"
    tokens = ScriptAnalysisService.tokenize_words(text)
    stopwords = ["the", "and", "was", "over"]
    segs = [TranscriptSegment(sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text=text)]
    
    word_freq, word_freq_filt, phrase_freqs, repeated_phrases = ScriptAnalysisService.compute_frequencies_and_ngrams(
        tokens, stopwords, segs
    )
    assert word_freq["the"] == 3
    assert "the" not in word_freq_filt
    assert word_freq_filt["quick"] == 2
    assert "quick brown" in phrase_freqs["2"]
    assert phrase_freqs["2"]["quick brown"] == 2
    assert any(r["phrase"] == "quick brown" for r in repeated_phrases)

def test_dictionary_matching():
    segs = [
        TranscriptSegment(sequence_index=0, start_time=0.0, end_time=5.0, duration=5.0, text="Um so basically you know what I mean?"),
        TranscriptSegment(sequence_index=1, start_time=5.0, end_time=10.0, duration=5.0, text="However on the other hand we have facts."),
    ]
    fillers = ["um", "basically", "you know", "i mean"]
    transitions = ["however", "on the other hand"]
    
    f_counts, f_ev = ScriptAnalysisService.match_dictionary_expressions(segs, fillers)
    assert f_counts.get("um") == 1
    assert f_counts.get("basically") == 1
    assert f_counts.get("you know") == 1
    assert len(f_ev) == 4

    t_counts, t_ev = ScriptAnalysisService.match_dictionary_expressions(segs, transitions)
    assert t_counts.get("however") == 1
    assert t_counts.get("on the other hand") == 1
    assert len(t_ev) == 2
