import pytest
import subprocess
import shutil
from pathlib import Path
from backend.app.config import settings
from backend.app.services.visual_analysis_service import VisualAnalysisService

@pytest.fixture(scope="module")
def synthetic_video_path():
    """
    Generates a tiny 3-second synthetic video with 3 distinct color scenes (1s red, 1s green, 1s blue) using FFmpeg.
    """
    out_dir = settings.temp_path / "test_fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    video_file = out_dir / "synthetic_scenes.mp4"

    cmd = [
        "ffmpeg",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
        "-f", "lavfi", "-i", "smptebars=duration=1:size=320x240:rate=25",
        "-f", "lavfi", "-i", "testsrc2=duration=1:size=320x240:rate=25",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
        "-map", "[v]",
        "-pix_fmt", "yuv420p",
        "-y",
        str(video_file)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    yield video_file

    # Teardown
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)

@pytest.fixture(scope="module")
def synthetic_solid_video():
    """
    Generates a 2-second single-color video with zero scene changes.
    """
    out_dir = settings.temp_path / "test_fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    video_file = out_dir / "solid_black.mp4"

    cmd = [
        "ffmpeg",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
        "-pix_fmt", "yuv420p",
        "-y",
        str(video_file)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    yield video_file

    if video_file.exists():
        video_file.unlink()

def test_ffprobe_inspection(synthetic_video_path):
    tech = VisualAnalysisService.inspect_media_ffprobe(synthetic_video_path)
    assert tech["width"] == 320
    assert tech["height"] == 240
    assert tech["duration"] >= 2.9
    assert tech["frame_rate"] > 0
    assert tech["file_size_bytes"] > 0

def test_visual_boundary_detection(synthetic_video_path):
    boundaries = VisualAnalysisService.detect_visual_boundaries(synthetic_video_path, threshold=0.3)
    # The 3-second synthetic video has color changes at 1.0s and 2.0s
    assert len(boundaries) >= 2
    assert any(0.8 <= b <= 1.2 for b in boundaries)
    assert any(1.8 <= b <= 2.2 for b in boundaries)

def test_zero_boundary_handling(synthetic_solid_video):
    boundaries = VisualAnalysisService.detect_visual_boundaries(synthetic_solid_video, threshold=0.3)
    assert len(boundaries) == 0

    # Even with 0 boundaries, exactly 1 continuous segment must be generated
    segments, stats = VisualAnalysisService.construct_segments(boundaries, 2.0)
    assert len(segments) == 1
    assert segments[0]["sequence"] == 1
    assert segments[0]["start_time"] == 0.0
    assert segments[0]["end_time"] == 2.0
    assert segments[0]["duration"] == 2.0
    assert stats["scene_count"] == 1
    assert stats["scene_change_frequency"] == 0.0

def test_segment_construction_and_statistics(synthetic_video_path):
    boundaries = [1.0, 2.0]
    segments, stats = VisualAnalysisService.construct_segments(boundaries, 3.0)
    assert len(segments) == 3
    assert segments[0]["duration"] == 1.0
    assert segments[1]["duration"] == 1.0
    assert segments[2]["duration"] == 1.0
    assert stats["scene_count"] == 3
    assert stats["avg_scene_duration"] == 1.0
    assert stats["median_scene_duration"] == 1.0
    assert stats["shortest_scene_duration"] == 1.0
    assert stats["longest_scene_duration"] == 1.0
    assert stats["segment_duration_distribution"]["1-2s"] == 3

def test_representative_frame_extraction(synthetic_video_path):
    video_id = "test_vid_123"
    segments = [
        {"sequence": 1, "start_time": 0.0, "end_time": 1.0, "duration": 1.0},
        {"sequence": 2, "start_time": 1.0, "end_time": 2.0, "duration": 1.0},
        {"sequence": 3, "start_time": 2.0, "end_time": 3.0, "duration": 1.0},
    ]
    frames = VisualAnalysisService.extract_representative_frames(synthetic_video_path, video_id, segments, max_frames=2)
    # Bounded to max_frames=2
    assert len(frames) == 2
    for f in frames:
        f_path = settings.project_root / f["file_path"]
        assert f_path.exists()
        assert f["file_size_bytes"] > 0
        assert f["width"] == 320
        assert f["height"] == 240

    # Cleanup test frames
    f_dir = settings.frames_path / video_id
    if f_dir.exists():
        shutil.rmtree(f_dir, ignore_errors=True)

def test_visual_activity_timeline():
    boundaries = [1.0, 2.0, 16.5]
    timeline = VisualAnalysisService.compute_visual_activity_timeline(boundaries, 20.0, [])
    # 20s duration with 15s window -> 2 windows
    assert len(timeline) == 2
    assert timeline[0]["start_time"] == 0.0
    assert timeline[0]["boundary_count"] == 2
    assert timeline[1]["boundary_count"] == 1
