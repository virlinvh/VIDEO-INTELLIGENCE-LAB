from pathlib import Path
from typing import List
import yaml
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    app_name: str = "Video Intelligence Lab"
    version: str = "0.1.0"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000

    project_root: Path = PROJECT_ROOT
    storage_root: Path = PROJECT_ROOT / "storage"
    data_root: Path = PROJECT_ROOT / "data"
    logs_root: Path = PROJECT_ROOT / "logs"
    database_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"

    saved_videos_path: Path = PROJECT_ROOT / "storage" / "saved_videos"
    temp_path: Path = PROJECT_ROOT / "storage" / "temp"
    cache_path: Path = PROJECT_ROOT / "storage" / "cache"
    thumbnails_path: Path = PROJECT_ROOT / "storage" / "thumbnails"
    frames_path: Path = PROJECT_ROOT / "storage" / "frames"
    audio_path: Path = PROJECT_ROOT / "storage" / "audio"
    transcripts_path: Path = PROJECT_ROOT / "storage" / "transcripts"
    metadata_path: Path = PROJECT_ROOT / "storage" / "metadata"
    reports_path: Path = PROJECT_ROOT / "storage" / "reports"
    models_path: Path = PROJECT_ROOT / "storage" / "models"

    default_mode: str = "ANALYZE_ONLY"
    max_concurrent_jobs: int = 2
    request_timeout_seconds: int = 120
    subtitles_languages: List[str] = ["en", "en-US", "en-GB"]

    wpm_window_seconds: int = 15
    scene_threshold: float = 0.3
    contact_sheet_columns: int = 5

def get_settings() -> Settings:
    config_file = PROJECT_ROOT / "config" / "default_config.yaml"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return Settings(
                app_name=cfg.get("app", {}).get("name", "Video Intelligence Lab"),
                version=cfg.get("app", {}).get("version", "0.1.0"),
                environment=cfg.get("app", {}).get("environment", "development"),
                host=cfg.get("app", {}).get("host", "127.0.0.1"),
                port=cfg.get("app", {}).get("port", 8000),
                default_mode=cfg.get("processing", {}).get("default_mode", "ANALYZE_ONLY"),
                max_concurrent_jobs=cfg.get("processing", {}).get("max_concurrent_jobs", 2),
                request_timeout_seconds=cfg.get("processing", {}).get("request_timeout_seconds", 120),
                subtitles_languages=cfg.get("processing", {}).get("subtitles_languages", ["en", "en-US", "en-GB"]),
                wpm_window_seconds=cfg.get("analysis", {}).get("wpm_window_seconds", 15),
                scene_threshold=cfg.get("analysis", {}).get("scene_threshold", 0.3),
                contact_sheet_columns=cfg.get("analysis", {}).get("contact_sheet_columns", 5),
            )
    return Settings()

settings = get_settings()
