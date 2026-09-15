import os
from pathlib import Path
from backend.app.config import settings

class SecurityError(Exception):
    """Raised when an operation violates containment or security policies."""
    pass

def validate_path_containment(target_path: Path | str, allow_saved_library: bool = True) -> Path:
    """Ensures target path resolves strictly inside project_root or user-configured saved_videos_path."""
    resolved = Path(target_path).resolve()
    project_root = settings.project_root.resolve()
    saved_videos = settings.saved_videos_path.resolve()

    try:
        resolved.relative_to(project_root)
        return resolved
    except ValueError:
        pass

    if allow_saved_library:
        try:
            resolved.relative_to(saved_videos)
            return resolved
        except ValueError:
            pass

    raise SecurityError(f"Access denied: Path '{target_path}' is outside project-controlled containment.")

def is_safe_deletion_target(target_path: Path | str) -> bool:
    """Automatic deletion is strictly restricted to temporary and cache directories inside storage."""
    resolved = Path(target_path).resolve()
    temp_dir = settings.temp_path.resolve()
    cache_dir = settings.cache_path.resolve()

    try:
        resolved.relative_to(temp_dir)
        return True
    except ValueError:
        pass

    try:
        resolved.relative_to(cache_dir)
        return True
    except ValueError:
        pass

    return False
