import os
from pathlib import Path
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.schemas.storage import StorageCategoryInfo, StorageOverviewResponse

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

class StorageService:
    @staticmethod
    def get_dir_stats(path: Path) -> tuple[int, int]:
        total_size = 0
        file_count = 0
        if path.exists() and path.is_dir():
            for root, _, files in os.walk(path):
                for f in files:
                    if f == ".gitkeep":
                        continue
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
        elif path.exists() and path.is_file():
            total_size = os.path.getsize(path)
            file_count = 1
        return total_size, file_count

    @classmethod
    def get_overview(cls) -> StorageOverviewResponse:
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

        return StorageOverviewResponse(
            total_size_bytes=total_bytes,
            total_size_human=format_bytes(total_bytes),
            categories=cat_infos,
            saved_video_library=saved_vid_info
        )
