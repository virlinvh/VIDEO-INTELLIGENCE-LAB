import pytest
from backend.app.services.caption_service import CaptionService

def test_vtt_parsing_and_deduplication():
    vtt_sample = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
Hello and welcome

00:00:02.500 --> 00:00:05.000
Hello and welcome to this video

00:00:05.000 --> 00:00:08.000
<c>Here is</c> <00:00:06.120>some interesting</00:00:06.120> text
"""
    segments = CaptionService.parse_vtt(vtt_sample)
    assert len(segments) == 2
    assert segments[0].text == "Hello and welcome to this video"
    assert segments[1].text == "Here is some interesting text"
    assert segments[0].duration > 0
    assert segments[1].word_count == 5

def test_language_normalization():
    assert CaptionService.normalize_language_code("en") == "en"
    assert CaptionService.normalize_language_code("en-US") == "en"
    assert CaptionService.normalize_language_code("en-GB") == "en"
    assert CaptionService.normalize_language_code("en-orig") == "en"
    assert CaptionService.normalize_language_code("ta") == "ta"
    assert CaptionService.normalize_language_code("ta-IN") == "ta"
    assert CaptionService.normalize_language_code("ta-LK") == "ta"
    assert CaptionService.normalize_language_code("ml") == "ml"
    assert CaptionService.normalize_language_code("ml-IN") == "ml"

def test_caption_selection_case_1_english_requested():
    """
    CASE 1
    Requested: English
    Available: en manual, ta automatic
    Expected: en manual
    """
    raw_info = {
        "subtitles": {
            "en": [{"url": "https://example.com/en_manual.vtt", "ext": "vtt", "name": "English"}]
        },
        "automatic_captions": {
            "ta": [{"url": "https://example.com/ta_auto.vtt", "ext": "vtt", "name": "Tamil"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected = CaptionService.select_caption_track(tracks, requested_language="en")
    assert selected is not None
    assert selected.normalized_code == "en"
    assert selected.source == "manual"
    assert selected.is_automatic is False
    assert selected.url == "https://example.com/en_manual.vtt"

def test_caption_selection_case_2_tamil_requested_with_tamil_auto():
    """
    CASE 2
    Requested: Tamil
    Available: en manual, ta automatic
    Expected: ta automatic
    """
    raw_info = {
        "subtitles": {
            "en": [{"url": "https://example.com/en_manual.vtt", "ext": "vtt", "name": "English"}]
        },
        "automatic_captions": {
            "ta": [{"url": "https://example.com/ta_auto.vtt", "ext": "vtt", "name": "Tamil"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected = CaptionService.select_caption_track(tracks, requested_language="ta")
    assert selected is not None
    assert selected.normalized_code == "ta"
    assert selected.source == "automatic"
    assert selected.is_automatic is True
    assert selected.url == "https://example.com/ta_auto.vtt"

def test_caption_selection_case_3_tamil_requested_only_english_available():
    """
    CASE 3
    Requested: Tamil
    Available: en manual, en automatic
    Expected: no matching platform caption (returns None to route to Tamil ASR)
    """
    raw_info = {
        "subtitles": {
            "en": [{"url": "https://example.com/en_manual.vtt", "ext": "vtt", "name": "English"}]
        },
        "automatic_captions": {
            "en": [{"url": "https://example.com/en_auto.vtt", "ext": "vtt", "name": "English (auto)"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected = CaptionService.select_caption_track(tracks, requested_language="ta")
    assert selected is None  # Strictly None, so pipeline routes to Tamil Local ASR!

def test_caption_selection_case_4_malayalam_requested_with_malayalam_manual():
    """
    CASE 4
    Requested: Malayalam
    Available: ml manual, en manual
    Expected: ml manual
    """
    raw_info = {
        "subtitles": {
            "ml": [{"url": "https://example.com/ml_manual.vtt", "ext": "vtt", "name": "Malayalam"}],
            "en": [{"url": "https://example.com/en_manual.vtt", "ext": "vtt", "name": "English"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected = CaptionService.select_caption_track(tracks, requested_language="ml")
    assert selected is not None
    assert selected.normalized_code == "ml"
    assert selected.source == "manual"
    assert selected.is_automatic is False
    assert selected.url == "https://example.com/ml_manual.vtt"

def test_caption_selection_case_5_malayalam_requested_only_english_auto():
    """
    CASE 5
    Requested: Malayalam
    Available: en automatic
    Expected: None (routes to Malayalam local ASR)
    """
    raw_info = {
        "automatic_captions": {
            "en": [{"url": "https://example.com/en_auto.vtt", "ext": "vtt", "name": "English (auto)"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected = CaptionService.select_caption_track(tracks, requested_language="ml")
    assert selected is None  # Strictly None!

def test_caption_selection_with_language_regional_variants():
    """
    Verify regional variant codes like en-US, ta-IN, ml-IN match requested family codes.
    """
    raw_info = {
        "subtitles": {
            "ta-IN": [{"url": "https://example.com/ta_in.vtt", "ext": "vtt", "name": "Tamil (India)"}]
        },
        "automatic_captions": {
            "en-US": [{"url": "https://example.com/en_us.vtt", "ext": "vtt", "name": "English (US)"}]
        }
    }
    tracks = CaptionService.discover_caption_tracks(raw_info)
    selected_ta = CaptionService.select_caption_track(tracks, requested_language="ta")
    assert selected_ta is not None
    assert selected_ta.normalized_code == "ta"
    assert selected_ta.url == "https://example.com/ta_in.vtt"

    selected_en = CaptionService.select_caption_track(tracks, requested_language="en")
    assert selected_en is not None
    assert selected_en.normalized_code == "en"
    assert selected_en.url == "https://example.com/en_us.vtt"
