import pytest
from pathlib import Path
from backend.app.core.security import validate_path_containment, is_safe_deletion_target, SecurityError
from backend.app.config import settings

def test_path_containment():
    inside_project = settings.storage_root / "temp" / "job_123"
    assert validate_path_containment(inside_project) == inside_project.resolve()

    saved_library_file = settings.saved_videos_path / "video.mp4"
    assert validate_path_containment(saved_library_file) == saved_library_file.resolve()

    outside_path = Path("C:/Windows/System32/drivers/etc/hosts")
    with pytest.raises(SecurityError):
        validate_path_containment(outside_path)

def test_safe_deletion_targets():
    temp_file = settings.temp_path / "scratch.mp4"
    assert is_safe_deletion_target(temp_file) is True

    cache_file = settings.cache_path / "temp.cache"
    assert is_safe_deletion_target(cache_file) is True

    # Critical: database and root files must NOT be deemed safe for auto-delete
    db_file = settings.data_root / "app.db"
    assert is_safe_deletion_target(db_file) is False

    saved_video = settings.saved_videos_path / "permanent.mp4"
    assert is_safe_deletion_target(saved_video) is False
