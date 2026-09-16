import pytest
from backend.app.services.url_service import URLService

def test_youtube_url_parsing():
    valid_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/3jZpXQ_5YvQ", "3jZpXQ_5YvQ"),
        ("youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url, expected_id in valid_urls:
        parsed = URLService.parse_url(url)
        assert parsed.is_valid is True
        assert parsed.platform == "youtube"
        assert parsed.video_id == expected_id

def test_instagram_url_parsing():
    valid_reels = [
        ("https://www.instagram.com/reel/C8q8q8q8q8q/", "C8q8q8q8q8q"),
        ("https://instagram.com/p/C8q8q8q8q8q", "C8q8q8q8q8q"),
    ]
    for url, expected_id in valid_reels:
        parsed = URLService.parse_url(url)
        assert parsed.is_valid is True
        assert parsed.platform == "instagram"
        assert parsed.video_id == expected_id

def test_unsupported_and_blocked_urls():
    blocked = URLService.parse_url("http://localhost:8000/test")
    assert blocked.is_valid is False
    assert "prohibited" in blocked.error.lower()

    unsupported = URLService.parse_url("https://vimeo.com/123456")
    assert unsupported.is_valid is False
    assert "unsupported" in unsupported.error.lower()

def test_channel_playlist_rejection():
    channel = URLService.parse_url("https://www.youtube.com/@mkbhd")
    assert channel.is_valid is False
    assert "channel" in channel.error.lower()

    playlist = URLService.parse_url("https://www.youtube.com/playlist?list=PL12345")
    assert playlist.is_valid is False
    assert "playlist" in playlist.error.lower()

def test_batch_url_parsing():
    text = """
    https://www.youtube.com/watch?v=video1
    https://www.youtube.com/watch?v=video2
    https://www.youtube.com/watch?v=video1
    invalid-url-here
    """
    res = URLService.parse_batch(text)
    assert res["total_urls"] == 4
    assert res["valid_urls"] == 3
    assert res["invalid_urls"] == 1
    assert res["duplicates_in_batch"] == 1
