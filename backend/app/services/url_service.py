import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

class ParsedVideoURL:
    def __init__(self, raw_url: str, platform: str, video_id: str, canonical_url: str, is_valid: bool = True, error: Optional[str] = None):
        self.raw_url = raw_url
        self.platform = platform
        self.video_id = video_id
        self.canonical_url = canonical_url
        self.is_valid = is_valid
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_url": self.raw_url,
            "platform": self.platform,
            "video_id": self.video_id,
            "canonical_url": self.canonical_url,
            "is_valid": self.is_valid,
            "error": self.error
        }

class URLService:
    # YouTube patterns
    YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
    # Instagram domains
    INSTAGRAM_DOMAINS = {"instagram.com", "www.instagram.com", "m.instagram.com"}

    @classmethod
    def parse_url(cls, raw_url: str) -> ParsedVideoURL:
        url = raw_url.strip()
        if not url:
            return ParsedVideoURL(raw_url, "unknown", "", "", False, "Empty URL")

        # Basic URL structure check
        try:
            parsed = urlparse(url)
        except Exception as e:
            return ParsedVideoURL(url, "unknown", "", "", False, f"Invalid URL format: {str(e)}")

        if not parsed.scheme:
            # Attempt adding https://
            url = "https://" + url
            parsed = urlparse(url)

        domain = parsed.netloc.lower()
        # Strip port if any
        if ":" in domain:
            domain = domain.split(":")[0]

        # Security check: disallow local/internal targets
        if domain in {"localhost", "127.0.0.1", "0.0.0.0"} or domain.startswith("192.168.") or domain.startswith("10."):
            return ParsedVideoURL(url, "blocked", "", "", False, "Local or private network URLs are prohibited")

        # YouTube Matching
        if domain in cls.YOUTUBE_DOMAINS or domain.endswith(".youtube.com") or domain.endswith(".youtu.be"):
            # Check for playlist/channel URLs
            if "/channel/" in parsed.path or "/c/" in parsed.path or "/@" in parsed.path and "/watch" not in parsed.path and "/shorts/" not in parsed.path:
                if "/shorts/" not in parsed.path and "/watch" not in parsed.path:
                    return ParsedVideoURL(url, "youtube", "", "", False, "Channel URLs are not supported. Submit individual video URLs.")

            if parsed.path.startswith("/playlist"):
                return ParsedVideoURL(url, "youtube", "", "", False, "Playlist URLs are not supported. Submit individual video URLs.")

            # youtu.be/<id>
            if domain == "youtu.be" or domain.endswith(".youtu.be"):
                vid_id = parsed.path.lstrip("/").split("/")[0]
                if vid_id:
                    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "", vid_id)
                    return ParsedVideoURL(url, "youtube", clean_id, f"https://www.youtube.com/watch?v={clean_id}", True)

            # youtube.com/watch?v=<id>
            if parsed.path == "/watch" or parsed.path.startswith("/watch/"):
                qs = parse_qs(parsed.query)
                if "v" in qs and qs["v"]:
                    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "", qs["v"][0])
                    return ParsedVideoURL(url, "youtube", clean_id, f"https://www.youtube.com/watch?v={clean_id}", True)

            # youtube.com/shorts/<id>
            if "/shorts/" in parsed.path:
                match = re.search(r"/shorts/([a-zA-Z0-9_-]+)", parsed.path)
                if match:
                    clean_id = match.group(1)
                    return ParsedVideoURL(url, "youtube", clean_id, f"https://www.youtube.com/watch?v={clean_id}", True)

            # youtube.com/embed/<id> or /v/<id>
            match = re.search(r"/(?:embed|v)/([a-zA-Z0-9_-]+)", parsed.path)
            if match:
                clean_id = match.group(1)
                return ParsedVideoURL(url, "youtube", clean_id, f"https://www.youtube.com/watch?v={clean_id}", True)

            return ParsedVideoURL(url, "youtube", "", "", False, "Could not identify YouTube video ID from URL")

        # Instagram Matching
        if domain in cls.INSTAGRAM_DOMAINS or domain.endswith(".instagram.com"):
            # instagram.com/reel/<id> or /reels/<id> or /p/<id> or /tv/<id>
            match = re.search(r"/(?:reel|reels|p|tv)/([a-zA-Z0-9_-]+)", parsed.path)
            if match:
                clean_id = match.group(1)
                return ParsedVideoURL(url, "instagram", clean_id, f"https://www.instagram.com/reel/{clean_id}/", True)

            if parsed.path.strip("/").count("/") == 0 and parsed.path.strip("/"):
                return ParsedVideoURL(url, "instagram", "", "", False, "Profile URLs are not supported. Submit individual reel/post URLs.")

            return ParsedVideoURL(url, "instagram", "", "", False, "Could not identify Instagram reel/post ID from URL")

        return ParsedVideoURL(url, "unsupported", "", "", False, f"Unsupported platform or domain: {domain}. Only YouTube and Instagram are supported.")

    @classmethod
    def parse_batch(cls, raw_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
        total = len(lines)
        results: List[Dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0
        seen_keys = set()
        duplicates_count = 0

        for line in lines:
            parsed = cls.parse_url(line)
            p_dict = parsed.to_dict()
            if parsed.is_valid:
                key = f"{parsed.platform}:{parsed.video_id}"
                if key in seen_keys:
                    p_dict["is_duplicate_in_batch"] = True
                    duplicates_count += 1
                else:
                    seen_keys.add(key)
                    p_dict["is_duplicate_in_batch"] = False
                valid_count += 1
            else:
                invalid_count += 1
                p_dict["is_duplicate_in_batch"] = False
            results.append(p_dict)

        return {
            "total_urls": total,
            "valid_urls": valid_count,
            "invalid_urls": invalid_count,
            "duplicates_in_batch": duplicates_count,
            "items": results
        }
