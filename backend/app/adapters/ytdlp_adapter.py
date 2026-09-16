import json
import time
import urllib.request
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
import yt_dlp
from backend.app.config import settings
from backend.app.services.caption_service import CaptionService, CaptionTrack

class UpstreamRateLimitError(Exception):
    """Raised when upstream video provider returns HTTP 429 or rate limits requests."""
    def __init__(self, message: str = "Platform rate limit encountered (HTTP 429).", retry_after_seconds: int = 60):
        super().__init__(message)
        self.code = "UPSTREAM_RATE_LIMIT"
        self.retry_after_seconds = retry_after_seconds
        self.retryable = True

class UpstreamAuthRequiredError(Exception):
    """Raised when upstream video provider requires user login or bot verification."""
    def __init__(self, message: str = "Authentication or verification required."):
        super().__init__(message)
        self.code = "UPSTREAM_AUTH_REQUIRED"
        self.retryable = False

class UpstreamUnavailableError(Exception):
    """Raised when upstream video is deleted, private, or not found."""
    def __init__(self, message: str = "Video is private or unavailable."):
        super().__init__(message)
        self.code = "UPSTREAM_UNAVAILABLE"
        self.retryable = False

class YouTubeCircuitBreaker:
    """
    Shared circuit breaker for YouTube upstream requests.
    Prevents cascading request storms when HTTP 429 rate limiting is active.
    """
    _cooldown_until: float = 0.0
    _consecutive_429s: int = 0
    _cooldown_duration: float = 60.0  # 60s cooldown

    @classmethod
    def record_429(cls):
        cls._consecutive_429s += 1
        # Exponential cooldown scaling: 60s, 120s, max 300s
        dur = min(300.0, cls._cooldown_duration * (2 ** (cls._consecutive_429s - 1)))
        cls._cooldown_until = time.time() + dur

    @classmethod
    def record_success(cls):
        cls._consecutive_429s = 0
        cls._cooldown_until = 0.0

    @classmethod
    def is_cooling_down(cls) -> bool:
        return time.time() < cls._cooldown_until

    @classmethod
    def get_remaining_cooldown(cls) -> int:
        rem = cls._cooldown_until - time.time()
        return max(0, int(rem))

class YtDlpAdapter:
    """
    Encapsulated extraction adapter using yt-dlp.
    Guarantees that frontend and application services never invoke CLI commands directly.
    """

    @classmethod
    def _get_base_opts(cls) -> Dict[str, Any]:
        return {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "cachedir": str(settings.cache_path.resolve()),
            "timeout": settings.request_timeout_seconds,
            "noplaylist": True,
            "sleep_interval_requests": 1,
            "sleep_interval_subtitles": 1,
        }

    @classmethod
    async def extract_metadata(cls, url: str) -> Dict[str, Any]:
        """
        Extracts comprehensive metadata, formats, and available subtitle tracks without media download.
        Includes circuit-breaker checks, request pacing, and bounded exponential backoff on HTTP 429.
        """
        is_youtube = "youtube.com" in url or "youtu.be" in url

        if is_youtube and YouTubeCircuitBreaker.is_cooling_down():
            rem = YouTubeCircuitBreaker.get_remaining_cooldown()
            raise UpstreamRateLimitError(
                f"YouTube is temporarily rate-limiting requests. Cooldown active for {rem}s. Please retry later.",
                retry_after_seconds=rem
            )

        opts = cls._get_base_opts()
        max_attempts = 3
        backoffs = [2.0, 5.0, 10.0]

        loop = asyncio.get_running_loop()

        for attempt in range(max_attempts):
            try:
                def _extract():
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        return ydl.extract_info(url, download=False)

                raw_info = await loop.run_in_executor(None, _extract)
                if is_youtube:
                    YouTubeCircuitBreaker.record_success()
                return raw_info or {}
            except Exception as e:
                err_msg = str(e)
                is_429 = "HTTP Error 429" in err_msg or "Too Many Requests" in err_msg or "Sign in to confirm you're not a bot" in err_msg

                if is_429:
                    if attempt < max_attempts - 1:
                        backoff = backoffs[attempt]
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        if is_youtube:
                            YouTubeCircuitBreaker.record_429()
                        raise UpstreamRateLimitError(
                            "YouTube temporarily rate-limited requests (HTTP 429). Please retry later.",
                            retry_after_seconds=60
                        )

                if "Private video" in err_msg:
                    raise UpstreamUnavailableError("This video is private and cannot be extracted.")
                elif "Video unavailable" in err_msg or "not found" in err_msg or "does not exist" in err_msg:
                    raise UpstreamUnavailableError("Video is unavailable or has been removed.")
                elif "login" in err_msg.lower() or "requires authentication" in err_msg.lower():
                    raise UpstreamAuthRequiredError("This content requires login/authentication to view.")
                else:
                    raise ValueError(f"Extraction failed: {err_msg}")

        raise UpstreamRateLimitError("Max extraction retries exceeded due to upstream rate limits.")

    @classmethod
    async def download_media(
        cls,
        url: str,
        output_template: str,
        format_spec: str = "bestaudio/best"
    ) -> Path:
        """
        Safely downloads media streams through the yt-dlp adapter with circuit breaker checks and pacing.
        """
        is_youtube = "youtube.com" in url or "youtu.be" in url
        if is_youtube and YouTubeCircuitBreaker.is_cooling_down():
            rem = YouTubeCircuitBreaker.get_remaining_cooldown()
            raise UpstreamRateLimitError(
                f"YouTube is temporarily rate-limiting requests. Cooldown active for {rem}s. Please retry later.",
                retry_after_seconds=rem
            )

        opts = cls._get_base_opts()
        opts.update({
            "skip_download": False,
            "format": format_spec,
            "outtmpl": output_template,
            "overwrites": True
        })

        loop = asyncio.get_running_loop()
        try:
            def _dl():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=True)

            raw_info = await loop.run_in_executor(None, _dl)
            if is_youtube:
                YouTubeCircuitBreaker.record_success()
            
            # Find the downloaded file
            out_p = Path(output_template)
            parent = out_p.parent
            base_name = out_p.name.replace(".%(ext)s", "")
            matches = list(parent.glob(f"{base_name}.*"))
            if matches:
                return matches[0]
            raise RuntimeError("Downloaded media file not found on disk.")
        except Exception as e:
            err_msg = str(e)
            is_429 = "HTTP Error 429" in err_msg or "Too Many Requests" in err_msg or "Sign in to confirm you're not a bot" in err_msg
            if is_429:
                if is_youtube:
                    YouTubeCircuitBreaker.record_429()
                raise UpstreamRateLimitError(
                    "YouTube temporarily rate-limited requests (HTTP 429). Please retry later.",
                    retry_after_seconds=60
                )
            raise ValueError(f"Media download failed: {err_msg}")

    @classmethod
    async def fetch_caption_content(cls, caption_url: str) -> str:
        """
        Asynchronously fetches caption content from a given direct subtitle URL.
        """
        def _fetch():
            req = urllib.request.Request(
                caption_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _fetch)

    @classmethod
    def select_best_caption_track(
        cls,
        raw_info: Dict[str, Any],
        requested_language: str = "en"
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Selects the best caption track matching the requested language.
        Returns (caption_url, normalized_language, is_generated).
        """
        tracks = CaptionService.discover_caption_tracks(raw_info)
        selected = CaptionService.select_caption_track(tracks, requested_language)
        if selected:
            return selected.url, selected.normalized_code, selected.is_automatic
        return None, None, False

