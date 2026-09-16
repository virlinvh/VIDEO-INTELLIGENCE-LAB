import os
import re
import json
import math
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.db.models.entities import Video, VisualMetrics, Frame, OCRResult, MediaFile, Artifact
from backend.app.db.base import utc_now
from backend.app.adapters.ytdlp_adapter import YtDlpAdapter

ALGORITHM_VERSION = "1.0.0"
MAX_RETAINED_FRAMES = 50
DEFAULT_SCENE_THRESHOLD = 0.3

class VisualAnalysisService:
    @staticmethod
    def inspect_media_ffprobe(media_path: Path) -> Dict[str, Any]:
        """
        Extract technical video properties via FFprobe deterministically.
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(media_path)
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            probe_data = json.loads(res.stdout)
            
            video_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "audio"), {})
            fmt = probe_data.get("format", {})

            # Frame rate calculation
            r_fps = video_stream.get("r_frame_rate", "0/0")
            fps = 0.0
            if "/" in r_fps:
                num, den = r_fps.split("/")
                if float(den) > 0:
                    fps = round(float(num) / float(den), 2)
            elif r_fps:
                fps = round(float(r_fps), 2)

            duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)
            width = int(video_stream.get("width") or 0)
            height = int(video_stream.get("height") or 0)
            aspect_ratio = video_stream.get("display_aspect_ratio") or (f"{width}:{height}" if width and height else None)

            return {
                "duration": round(duration, 2),
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "frame_rate": fps,
                "video_codec": video_stream.get("codec_name"),
                "audio_codec": audio_stream.get("codec_name"),
                "bit_rate": int(fmt.get("bit_rate") or video_stream.get("bit_rate") or 0),
                "format_name": fmt.get("format_name"),
                "file_size_bytes": int(fmt.get("size") or media_path.stat().st_size)
            }
        except Exception as e:
            return {
                "duration": 0.0,
                "width": 0,
                "height": 0,
                "aspect_ratio": None,
                "frame_rate": 0.0,
                "video_codec": None,
                "audio_codec": None,
                "bit_rate": 0,
                "format_name": None,
                "file_size_bytes": media_path.stat().st_size if media_path.exists() else 0,
                "error": str(e)
            }

    @staticmethod
    def detect_visual_boundaries(media_path: Path, threshold: float = DEFAULT_SCENE_THRESHOLD) -> List[float]:
        """
        Deterministic scene-change detection using FFmpeg's scene filter.
        Returns sorted list of change timestamps (pts_time).
        """
        cmd = [
            "ffmpeg",
            "-i", str(media_path),
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null",
            "-"
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stderr_out = res.stderr

            timestamps: List[float] = []
            for line in stderr_out.splitlines():
                if "showinfo" in line and "pts_time:" in line:
                    match = re.search(r"pts_time:([0-9.]+)", line)
                    if match:
                        t = float(match.group(1))
                        timestamps.append(round(t, 2))

            timestamps.sort()
            return timestamps
        except Exception:
            return []

    @staticmethod
    def construct_segments(
        boundaries: List[float], 
        total_duration: float
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Constructs visual segments and calculates aggregate duration statistics.
        """
        total_duration = max(0.1, round(total_duration, 2))
        
        # Build segments
        segments: List[Dict[str, Any]] = []
        points = [0.0] + [b for b in boundaries if 0.0 < b < total_duration] + [total_duration]
        # Deduplicate sorted points
        points = sorted(list(set(points)))

        for i in range(len(points) - 1):
            s_start = round(points[i], 2)
            s_end = round(points[i + 1], 2)
            s_dur = max(0.01, round(s_end - s_start, 2))
            segments.append({
                "sequence": i + 1,
                "start_time": s_start,
                "end_time": s_end,
                "duration": s_dur,
                "representative_frame_id": None,
                "change_score": None
            })

        count = len(segments)
        durations = [s["duration"] for s in segments]
        durations.sort()

        avg_dur = round(sum(durations) / count, 2) if count > 0 else 0.0
        
        if count == 0:
            med_dur = 0.0
        elif count % 2 == 1:
            med_dur = float(durations[count // 2])
        else:
            med_dur = round((durations[count // 2 - 1] + durations[count // 2]) / 2.0, 2)

        min_dur = durations[0] if durations else 0.0
        max_dur = durations[-1] if durations else 0.0

        dur_min = total_duration / 60.0
        changes_per_min = round(len(boundaries) / dur_min, 1) if dur_min > 0 else 0.0

        # Distribution buckets (<1s, 1-2s, 2-5s, 5-10s, 10-20s, 20s+)
        dist = {"<1s": 0, "1-2s": 0, "2-5s": 0, "5-10s": 0, "10-20s": 0, "20s+": 0}
        for d in durations:
            if d < 1.0:
                dist["<1s"] += 1
            elif d <= 2.0:
                dist["1-2s"] += 1
            elif d <= 5.0:
                dist["2-5s"] += 1
            elif d <= 10.0:
                dist["5-10s"] += 1
            elif d <= 20.0:
                dist["10-20s"] += 1
            else:
                dist["20s+"] += 1

        stats = {
            "scene_count": count,
            "avg_scene_duration": avg_dur,
            "median_scene_duration": med_dur,
            "shortest_scene_duration": min_dur,
            "longest_scene_duration": max_dur,
            "scene_change_frequency": changes_per_min,
            "segment_duration_distribution": dist
        }

        return segments, stats

    @staticmethod
    def extract_representative_frames(
        media_path: Path, 
        video_id: str, 
        segments: List[Dict[str, Any]], 
        max_frames: int = MAX_RETAINED_FRAMES
    ) -> List[Dict[str, Any]]:
        """
        Extracts representative JPEG frames for segments using FFmpeg.
        Downsamples uniformly if segment count exceeds max_frames.
        """
        out_dir = settings.frames_path / video_id
        out_dir.mkdir(parents=True, exist_ok=True)

        if not segments:
            return []

        # Select candidate segments
        if len(segments) <= max_frames:
            selected_segs = segments
        else:
            step = len(segments) / float(max_frames)
            selected_indices = [int(i * step) for i in range(max_frames)]
            selected_segs = [segments[idx] for idx in selected_indices if idx < len(segments)]

        extracted_frames: List[Dict[str, Any]] = []

        for seg in selected_segs:
            seq = seg["sequence"]
            t_target = round(seg["start_time"] + (seg["duration"] / 2.0), 2)
            frame_filename = f"frame_{seq:04d}_{t_target:.2f}s.jpg"
            frame_path = out_dir / frame_filename

            # Extract single frame via FFmpeg
            cmd = [
                "ffmpeg",
                "-ss", str(t_target),
                "-i", str(media_path),
                "-frames:v", "1",
                "-q:v", "2",
                "-y",
                str(frame_path)
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if frame_path.exists() and frame_path.stat().st_size > 0:
                    # Inspect image dimensions via ffprobe
                    probe = VisualAnalysisService.inspect_media_ffprobe(frame_path)
                    f_dict = {
                        "frame_number": seq,
                        "timestamp": t_target,
                        "file_path": str(frame_path.relative_to(settings.project_root)).replace("\\", "/"),
                        "file_size_bytes": frame_path.stat().st_size,
                        "width": probe.get("width", 0),
                        "height": probe.get("height", 0),
                        "segment_sequence": seq
                    }
                    extracted_frames.append(f_dict)
            except Exception:
                continue

        return extracted_frames

    @staticmethod
    def compute_visual_activity_timeline(
        boundaries: List[float], 
        total_duration: float, 
        frames: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Computes continuous time-windowed visual change activity.
        """
        total_duration = max(0.1, round(total_duration, 2))
        win_size = 15.0 if total_duration < 120 else 30.0
        num_windows = max(1, math.ceil(total_duration / win_size))

        timeline: List[Dict[str, Any]] = []
        for i in range(num_windows):
            w_start = round(i * win_size, 1)
            w_end = round(min(total_duration, (i + 1) * win_size), 1)
            w_dur = max(0.1, w_end - w_start)

            # Count boundaries falling in window
            b_count = sum(1 for b in boundaries if w_start <= b < w_end)
            density = round(b_count / (w_dur / 60.0), 1) if w_dur > 0 else 0.0

            matched_frames = [
                f.get("id") or str(f.get("frame_number"))
                for f in frames if w_start <= f.get("timestamp", 0.0) < w_end
            ]

            timeline.append({
                "window_index": i,
                "start_time": w_start,
                "end_time": w_end,
                "duration": round(w_dur, 2),
                "boundary_count": b_count,
                "change_density": density,
                "representative_frame_ids": matched_frames
            })

        return timeline

    @classmethod
    async def analyze_video(
        cls, 
        video_id: str, 
        session: AsyncSession, 
        force_keep: bool = False
    ) -> Tuple[Optional[VisualMetrics], Optional[str]]:
        """
        Full deterministic visual analysis workflow with bounded media lifecycle.
        """
        v_stmt = select(Video).where(Video.id == video_id)
        v_res = await session.execute(v_stmt)
        video = v_res.scalar_one_or_none()

        if not video:
            return None, "Video record not found"

        # Check if permanently saved media exists
        perm_file = settings.saved_videos_path / f"{video.id}.mp4"
        job_temp_dir = settings.temp_path / f"visual_{video.id}"
        temp_media_file = job_temp_dir / f"{video.id}_analysis.mp4"

        using_permanent = perm_file.exists() and perm_file.stat().st_size > 0
        media_path = perm_file if using_permanent else temp_media_file

        # Step 1: Acquire source media if not present
        if not using_permanent:
            job_temp_dir.mkdir(parents=True, exist_ok=True)
            try:
                # Use YtDlpAdapter to download analysis stream safely (max 720p) respecting circuit breaker
                await YtDlpAdapter.download_media(
                    url=video.original_url,
                    output_template=str(temp_media_file),
                    format_spec="bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best"
                )
            except Exception as dl_err:
                return None, f"Failed to acquire source video for visual analysis: {str(dl_err)}"

        if not media_path.exists() or media_path.stat().st_size == 0:
            return None, "Media file could not be accessed"

        try:
            # Step 2: Technical properties inspection via FFprobe
            tech_props = cls.inspect_media_ffprobe(media_path)
            duration = tech_props.get("duration") or video.duration_seconds or 1.0

            # Step 3: Deterministic visual boundary detection via FFmpeg
            boundaries = cls.detect_visual_boundaries(media_path, threshold=DEFAULT_SCENE_THRESHOLD)

            # Step 4: Construct segments & statistics
            segments, stats = cls.construct_segments(boundaries, duration)

            # Step 5: Extract representative evidence frames
            extracted_frames = cls.extract_representative_frames(media_path, video.id, segments)

            # Step 6: Visual change activity timeline
            timeline = cls.compute_visual_activity_timeline(boundaries, duration, extracted_frames)

            # Step 7: Persist or update VisualMetrics and Frame entities
            vm_stmt = select(VisualMetrics).where(VisualMetrics.video_id == video.id)
            vm_res = await session.execute(vm_stmt)
            vm = vm_res.scalar_one_or_none()

            if not vm:
                vm = VisualMetrics(video_id=video.id)
                session.add(vm)
                await session.flush()

            vm.algorithm_version = ALGORITHM_VERSION
            vm.scene_threshold = DEFAULT_SCENE_THRESHOLD
            vm.analyzed_at = utc_now()
            vm.scene_count = stats["scene_count"]
            vm.avg_scene_duration = stats["avg_scene_duration"]
            vm.median_scene_duration = stats["median_scene_duration"]
            vm.shortest_scene_duration = stats["shortest_scene_duration"]
            vm.longest_scene_duration = stats["longest_scene_duration"]
            vm.scene_change_frequency = stats["scene_change_frequency"]
            vm.scene_timestamps = boundaries
            vm.visual_segments = segments
            vm.segment_duration_distribution = stats["segment_duration_distribution"]
            vm.visual_activity_timeline = timeline
            vm.technical_properties = tech_props

            # Remove previous frames from DB
            old_frames_stmt = select(Frame).where(Frame.visual_metrics_id == vm.id)
            old_frames_res = await session.execute(old_frames_stmt)
            for of in old_frames_res.scalars().all():
                await session.delete(of)
            await session.flush()

            # Add newly extracted frames
            for f_info in extracted_frames:
                frame_entity = Frame(
                    visual_metrics_id=vm.id,
                    video_id=video.id,
                    frame_number=f_info["frame_number"],
                    timestamp=f_info["timestamp"],
                    frame_type="representative",
                    file_path=f_info["file_path"],
                    file_size_bytes=f_info["file_size_bytes"],
                    width=f_info["width"],
                    height=f_info["height"]
                )
                session.add(frame_entity)
                await session.flush()

                # Register frame artifact
                session.add(Artifact(
                    video_id=video.id,
                    artifact_type="frame_jpeg",
                    relative_path=f_info["file_path"],
                    file_size_bytes=f_info["file_size_bytes"],
                    is_regeneratable=True,
                    retention_state="ACTIVE"
                ))

            # Step 8: Media Lifecycle Cleanup
            if force_keep or video.media_state == "PERMANENTLY_SAVED":
                if not using_permanent and temp_media_file.exists():
                    shutil.move(str(temp_media_file), str(perm_file))
                    video.media_state = "PERMANENTLY_SAVED"
            else:
                # ANALYZE ONLY -> wipe temporary directory immediately
                if job_temp_dir.exists():
                    shutil.rmtree(job_temp_dir, ignore_errors=True)
                video.media_state = "DELETED_AFTER_PROCESSING"

            await session.commit()
            await session.refresh(vm)
            return vm, None

        except Exception as proc_err:
            await session.rollback()
            return None, f"Visual analysis failed: {str(proc_err)}"
