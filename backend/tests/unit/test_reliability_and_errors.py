import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.adapters.ytdlp_adapter import (
    YtDlpAdapter, UpstreamRateLimitError, UpstreamAuthRequiredError,
    UpstreamUnavailableError, YouTubeCircuitBreaker
)

client = TestClient(app)

def test_api_structured_error_404():
    response = client.get('/api/v1/videos/non_existent_id_12345')
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/json')
    data = response.json()
    assert 'error' in data
    assert data['error']['code'] == 'NOT_FOUND'
    assert data['error']['status_code'] == 404
    assert data['error']['retryable'] is False

def test_youtube_circuit_breaker_and_rate_limiting():
    YouTubeCircuitBreaker.record_429()
    assert YouTubeCircuitBreaker.is_cooling_down() is True
    assert YouTubeCircuitBreaker.get_remaining_cooldown() > 0

    # Reset circuit breaker
    YouTubeCircuitBreaker.record_success()
    assert YouTubeCircuitBreaker.is_cooling_down() is False
    assert YouTubeCircuitBreaker.get_remaining_cooldown() == 0

@pytest.mark.asyncio
async def test_extract_metadata_circuit_breaker_active():
    YouTubeCircuitBreaker.record_429()
    with pytest.raises(UpstreamRateLimitError) as exc_info:
        await YtDlpAdapter.extract_metadata('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    assert exc_info.value.code == 'UPSTREAM_RATE_LIMIT'
    assert exc_info.value.retryable is True

    # Cleanup
    YouTubeCircuitBreaker.record_success()

@pytest.mark.asyncio
async def test_ytdlp_error_classification():
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        instance = mock_ydl.return_value.__enter__.return_value
        instance.extract_info.side_effect = Exception('HTTP Error 429: Too Many Requests')

        with pytest.raises(UpstreamRateLimitError) as exc_info:
            await YtDlpAdapter.extract_metadata('https://www.instagram.com/reel/abc')
        assert exc_info.value.code == 'UPSTREAM_RATE_LIMIT'
        assert exc_info.value.retryable is True

@pytest.mark.asyncio
async def test_download_media_circuit_breaker_active():
    YouTubeCircuitBreaker.record_429()
    with pytest.raises(UpstreamRateLimitError) as exc_info:
        await YtDlpAdapter.download_media(
            url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            output_template='dummy_path.mp4',
            format_spec='best'
        )
    assert exc_info.value.code == 'UPSTREAM_RATE_LIMIT'
    assert exc_info.value.retryable is True

    # Cleanup
    YouTubeCircuitBreaker.record_success()

def test_submit_duplicate_active_job_protection():
    # Submit job first time
    res1 = client.post('/api/v1/jobs', json={
        "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        "default_processing_mode": "ANALYZE_ONLY",
        "default_requested_transcript_language": "en"
    })
    assert res1.status_code == 200
    job_id_1 = res1.json()[0]["id"]

    # Submit job second time while first is in active queue / existing
    res2 = client.post('/api/v1/jobs', json={
        "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        "default_processing_mode": "ANALYZE_ONLY",
        "default_requested_transcript_language": "en"
    })
    assert res2.status_code == 200
    job_id_2 = res2.json()[0]["id"]
    assert job_id_1 == job_id_2

