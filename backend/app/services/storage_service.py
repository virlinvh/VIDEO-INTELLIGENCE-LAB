import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.config import settings
from backend.app.schemas.storage import StorageCategoryInfo, StorageOverviewResponse

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

class StorageService:
    _cached_overview: Optional[StorageOverviewResponse] = None
    _cached_time: float = 0.0
    _cache_ttl_seconds: float = 60.0

    _dir_stats_cache: Dict[str, tuple[int, int, float]] = {}

    @classmethod
    def invalidate_cache(cls):
        cls._cached_overview = None
        cls._cached_time = 0.0

    @classmethod
    def get_dir_stats(cls, path: Path) -> tuple[int, int]:
        p_str = str(path.resolve())
        now = time.time()
        
        # Check cache
        if p_str in cls._dir_stats_cache:
            size, count, ts = cls._dir_stats_cache[p_str]
            # Static runtimes cache for 1 hour; other dirs cache for 30s
            ttl = 3600.0 if "runtimes" in p_str else 30.0
            if (now - ts) < ttl:
                return size, count

        total_size = 0
        file_count = 0
        if path.exists() and path.is_dir():
            for root, _, files in os.walk(path):
                for f in files:
                    if f == ".gitkeep":
                        continue
                    fp = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        continue
        elif path.exists() and path.is_file():
            try:
                total_size = os.path.getsize(path)
                file_count = 1
            except OSError:
                total_size = 0
                file_count = 0

        cls._dir_stats_cache[p_str] = (total_size, file_count, now)
        return total_size, file_count

    @classmethod
    def get_overview(cls, force_refresh: bool = False) -> StorageOverviewResponse:
        now = time.time()
        if not force_refresh and cls._cached_overview is not None and (now - cls._cached_time) < cls._cache_ttl_seconds:
            return cls._cached_overview

        cats = [
            ("database", "data/app.db", settings.data_root / "app.db", False),
            ("metadata", "storage/metadata", settings.metadata_path, False),
            ("transcripts", "storage/transcripts", settings.transcripts_path, True),
            ("thumbnails", "storage/thumbnails", settings.thumbnails_path, True),
            ("frames", "storage/frames", settings.frames_path, True),
            ("audio", "storage/audio", settings.audio_path, True),
            ("models", "storage/models", settings.models_path, True),
            ("runtimes", "runtimes", settings.project_root / "runtimes", True),
            ("cache", "storage/cache", settings.cache_path, True),
            ("temp", "storage/temp", settings.temp_path, True),
            ("reports", "storage/reports", settings.reports_path, True),
            ("logs", "logs", settings.logs_root, True),
        ]

        total_bytes = 0
        cat_infos: List[StorageCategoryInfo] = []

        for name, rel, abs_path, regen in cats:
            size_b, count = cls.get_dir_stats(abs_path)
            total_bytes += size_b
            cat_infos.append(StorageCategoryInfo(
                category=name,
                relative_path=rel,
                absolute_path=str(abs_path.resolve()),
                size_bytes=size_b,
                size_human=format_bytes(size_b),
                file_count=count,
                is_regeneratable=regen
            ))

        sv_size, sv_count = cls.get_dir_stats(settings.saved_videos_path)
        saved_vid_info = StorageCategoryInfo(
            category="saved_videos",
            relative_path="storage/saved_videos",
            absolute_path=str(settings.saved_videos_path.resolve()),
            size_bytes=sv_size,
            size_human=format_bytes(sv_size),
            file_count=sv_count,
            is_regeneratable=False
        )

        overview = StorageOverviewResponse(
            total_size_bytes=total_bytes,
            total_size_human=format_bytes(total_bytes),
            categories=cat_infos,
            saved_video_library=saved_vid_info
        )

        cls._cached_overview = overview
        cls._cached_time = now
        return overview
