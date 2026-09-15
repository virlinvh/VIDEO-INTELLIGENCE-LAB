import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.db.session import async_session_factory
from backend.app.db.models.entities import (
    ExtractionJob, Video, Creator, VideoMetadata, Transcript, TranscriptSegment, Artifact
)
from backend.app.services.url_service import URLService
from backend.app.services.caption_service import CaptionService
from backend.app.services.script_analysis_service import ScriptAnalysisService
from backend.app.transcription.service import TranscriptionService
from backend.app.transcription.router import TranscriptionRouter
from backend.app.transcription.registry import registry
from backend.app.adapters.ytdlp_adapter import YtDlpAdapter

def utc_now():
    return datetime.now(timezone.utc)

class JobWorkerPool:
    def __init__(self, max_concurrency: int = 2):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.asr_semaphore = asyncio.Semaphore(1)  # Bound ASR GPU/CPU concurrency to exactly 1
        self.active_tasks: Dict[str, asyncio.Task] = {}

    def enqueue_job(self, job_id: str):
        task = asyncio.create_task(self._run_job_guarded(job_id))
        self.active_tasks[job_id] = task
        task.add_done_callback(lambda _: self.active_tasks.pop(job_id, None))

    async def cancel_job(self, job_id: str):
        if job_id in self.active_tasks:
            self.active_tasks[job_id].cancel()

    async def _run_job_guarded(self, job_id: str):
        async with self.semaphore:
            async with async_session_factory() as session:
                res = await session.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
                job = res.scalar_one_or_none()
                if not job or job.state in ("CANCELLED", "COMPLETED"):
                    return
                if job.processing_mode == "RETRANSCRIBE":
                    await self._process_retranscribe_job(session, job)
                else:
                    await self._process_job(session, job)

    async def _process_job(self, session: AsyncSession, job: ExtractionJob):
        job.state = "VALIDATING"
        job.progress_percent = 5
        job.current_step = "Validating URL and platform"
        job.started_at = utc_now()
        await session.commit()

        parsed = URLService.parse_url(job.url)
        if not parsed.is_valid:
            job.state = "FAILED"
            job.progress_percent = 100
            job.current_step = "Validation Failed"
            job.error_details = {"code": "INVALID_URL", "message": parsed.error or "Invalid URL"}
            job.completed_at = utc_now()
            await session.commit()
            return

        warnings: List[str] = []

        try:
            # Step 1: Extract Metadata
            job.state = "EXTRACTING_METADATA"
            job.progress_percent = 25
            job.current_step = f"Retrieving {parsed.platform.title()} metadata & available caption tracks"
            await session.commit()

            raw_info = await YtDlpAdapter.extract_metadata(parsed.canonical_url)

            title = raw_info.get("title") or "Untitled Video"
            duration = int(raw_info.get("duration") or 0)
            uploader_name = raw_info.get("uploader") or raw_info.get("channel") or raw_info.get("creator") or "Unknown Creator"
            uploader_id = raw_info.get("uploader_id") or raw_info.get("channel_id")
            uploader_url = raw_info.get("uploader_url") or raw_info.get("channel_url")
            upload_date_str = raw_info.get("upload_date")
            pub_date = None
            if upload_date_str and len(upload_date_str) == 8:
                try:
                    pub_date = datetime.strptime(upload_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            # Persist or update Creator
            creator_id = None
            if uploader_name:
                c_stmt = select(Creator).where(Creator.platform == parsed.platform, Creator.name == uploader_name)
                c_res = await session.execute(c_stmt)
                existing_creator = c_res.scalar_one_or_none()
                if existing_creator:
                    creator_id = existing_creator.id
                else:
                    new_creator = Creator(
                        platform=parsed.platform,
                        platform_creator_id=str(uploader_id) if uploader_id else None,
                        name=uploader_name,
                        handle=f"@{uploader_id}" if uploader_id else None,
                        url=uploader_url
                    )
                    session.add(new_creator)
                    await session.flush()
                    creator_id = new_creator.id

            # Persist or update Video Record
            v_stmt = select(Video).where(Video.platform == parsed.platform, Video.platform_video_id == parsed.video_id)
            v_res = await session.execute(v_stmt)
            video = v_res.scalar_one_or_none()

            if not video:
                video = Video(
                    platform=parsed.platform,
                    platform_video_id=parsed.video_id,
                    original_url=parsed.canonical_url,
                    title=title,
                    duration_seconds=duration,
                    creator_id=creator_id,
                    processing_status="PROCESSING",
                    media_state="NOT_DOWNLOADED",
                    published_at=pub_date
                )
                session.add(video)
                await session.flush()
            else:
                video.title = title
                video.duration_seconds = duration
                video.creator_id = creator_id
                video.processing_status = "PROCESSING"
                if pub_date:
                    video.published_at = pub_date

            job.video_id = video.id

            # Persist VideoMetadata
            # Store raw payload safely in storage/metadata/
            raw_meta_file = settings.metadata_path / f"{video.id}.json"
            raw_meta_file.write_text(json.dumps(raw_info, default=str), encoding="utf-8")

            # Extract technical summary
            tech_details = {
                "format": raw_info.get("format"),
                "format_id": raw_info.get("format_id"),
                "ext": raw_info.get("ext"),
                "resolution": raw_info.get("resolution"),
                "width": raw_info.get("width"),
                "height": raw_info.get("height"),
                "fps": raw_info.get("fps"),
                "vcodec": raw_info.get("vcodec"),
                "acodec": raw_info.get("acodec"),
                "tbr": raw_info.get("tbr"),
                "abr": raw_info.get("abr"),
            }

            vm_stmt = select(VideoMetadata).where(VideoMetadata.video_id == video.id)
            vm_res = await session.execute(vm_stmt)
            vmeta = vm_res.scalar_one_or_none()

            if not vmeta:
                vmeta = VideoMetadata(
                    video_id=video.id,
                    description=raw_info.get("description"),
                    thumbnail_url=raw_info.get("thumbnail"),
                    chapters=raw_info.get("chapters") or [],
                    tags=raw_info.get("tags") or [],
                    categories=raw_info.get("categories") or [],
                    view_count=raw_info.get("view_count"),
                    like_count=raw_info.get("like_count"),
                    comment_count=raw_info.get("comment_count"),
                    technical_details=tech_details,
                    raw_payload={"meta_file": f"storage/metadata/{video.id}.json"}
                )
                session.add(vmeta)
            else:
                vmeta.description = raw_info.get("description")
                vmeta.thumbnail_url = raw_info.get("thumbnail")
                vmeta.chapters = raw_info.get("chapters") or []
                vmeta.tags = raw_info.get("tags") or []
                vmeta.categories = raw_info.get("categories") or []
                vmeta.view_count = raw_info.get("view_count")
                vmeta.like_count = raw_info.get("like_count")
                vmeta.comment_count = raw_info.get("comment_count")
                vmeta.technical_details = tech_details
                vmeta.raw_payload = {"meta_file": f"storage/metadata/{video.id}.json"}

            # Save metadata artifact record
            session.add(Artifact(
                video_id=video.id,
                job_id=job.id,
                artifact_type="metadata_json",
                relative_path=f"storage/metadata/{video.id}.json",
                file_size_bytes=raw_meta_file.stat().st_size,
                is_regeneratable=True,
                retention_state="ACTIVE"
            ))

            await session.commit()

            # Step 2: Caption Acquisition / Local ASR Fallback with Language Routing
            if job.processing_mode != "METADATA_ONLY":
                requested_lang = job.requested_transcript_language or "en"
                job.state = "GETTING_CAPTIONS"
                job.progress_percent = 50
                job.current_step = f"Searching for matching {requested_lang.upper()} platform caption tracks"
                await session.commit()

                cap_url, cap_lang, is_auto = YtDlpAdapter.select_best_caption_track(
                    raw_info,
                    requested_language=requested_lang
                )
                has_captions = cap_url is not None

                transcription_settings = await TranscriptionService.get_settings(session)
                strategy_res = TranscriptionRouter.resolve_transcription_strategy(
                    has_platform_captions=has_captions,
                    user_language_override=requested_lang if requested_lang != "auto" else None,
                    settings=transcription_settings
                )

                if strategy_res["strategy"] == "PLATFORM_CAPTIONS":
                    raw_captions = await YtDlpAdapter.fetch_caption_content(cap_url)
                    job.state = "PROCESSING_TRANSCRIPT"
                    job.progress_percent = 80
                    job.current_step = f"Normalizing {cap_lang.upper()} transcript and deduplicating segments"
                    await session.commit()

                    if "WEBVTT" in raw_captions:
                        parsed_segments = CaptionService.parse_vtt(raw_captions)
                    elif raw_captions.strip().startswith("{"):
                        try:
                            json_caps = json.loads(raw_captions)
                            parsed_segments = CaptionService.parse_json3(json_caps)
                        except Exception:
                            parsed_segments = []
                    else:
                        parsed_segments = CaptionService.parse_vtt(raw_captions)

                    if parsed_segments:
                        full_clean_text = " ".join([s.text for s in parsed_segments])
                        
                        # Remove existing transcript if any
                        t_stmt = select(Transcript).where(Transcript.video_id == video.id)
                        t_res = await session.execute(t_stmt)
                        old_t = t_res.scalar_one_or_none()
                        if old_t:
                            await session.delete(old_t)
                            await session.flush()

                        source_name = f"{parsed.platform.title()} {'Automatic' if is_auto else 'Manual'} Captions"
                        new_t = Transcript(
                            video_id=video.id,
                            language=cap_lang or requested_lang,
                            requested_language=requested_lang,
                            source_type="automatic" if is_auto else "native",
                            caption_source=source_name,
                            caption_language_code=cap_lang,
                            asr_model=None,
                            is_generated=is_auto,
                            full_text=full_clean_text
                        )
                        session.add(new_t)
                        await session.flush()

                        for s in parsed_segments:
                            session.add(TranscriptSegment(
                                transcript_id=new_t.id,
                                sequence_index=s.sequence_index,
                                start_time=s.start_time,
                                end_time=s.end_time,
                                duration=s.duration,
                                text=s.text,
                                word_count=s.word_count
                            ))

                        # Save transcript artifact
                        t_file = settings.transcripts_path / f"{video.id}.txt"
                        t_file.write_text(full_clean_text, encoding="utf-8")
                        session.add(Artifact(
                            video_id=video.id,
                            job_id=job.id,
                            artifact_type="transcript_txt",
                            relative_path=f"storage/transcripts/{video.id}.txt",
                            file_size_bytes=t_file.stat().st_size,
                            is_regeneratable=True,
                            retention_state="ACTIVE"
                        ))
                        await session.flush()

                        # Deterministically calculate and persist ScriptMetrics
                        try:
                            await ScriptAnalysisService.analyze_and_persist(video.id, session)
                        except Exception as sme:
                            warnings.append(f"Script analysis warning: {str(sme)}")
                    else:
                        warnings.append("Caption track existed but no valid segments could be parsed.")

                elif strategy_res["strategy"] in ("LOCAL_ASR", "LOCAL_ASR_FALLBACK"):
                    # Execute Local Whisper ASR Fallback
                    target_model = strategy_res["model"]
                    req_lang = strategy_res["language"] or requested_lang
                    
                    job.state = "ACQUIRING_AUDIO"
                    job.progress_percent = 60
                    job.current_step = f"No {requested_lang.upper()} platform captions found. Acquiring audio stream for local ASR"
                    await session.commit()

                    job_temp_asr = settings.temp_path / f"job_{job.id}" / "asr"
                    job_temp_asr.mkdir(parents=True, exist_ok=True)
                    audio_wav_path = job_temp_asr / "audio.wav"

                    # Check if permanent saved video exists
                    perm_file = settings.saved_videos_path / f"{video.id}.mp4"
                    media_source = None

                    if perm_file.exists() and perm_file.stat().st_size > 0:
                        media_source = perm_file
                    else:
                        temp_dl_file = job_temp_asr / "source_stream.%(ext)s"
                        media_source = await YtDlpAdapter.download_media(
                            url=parsed.canonical_url,
                            output_template=str(temp_dl_file),
                            format_spec="bestaudio/best"
                        )


                    # Standardize to 16 kHz mono WAV via FFmpeg
                    job.state = "PREPARING_AUDIO"
                    job.progress_percent = 70
                    job.current_step = "Standardizing audio to 16 kHz mono PCM"
                    await session.commit()

                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-i", str(media_source),
                        "-vn",
                        "-ac", "1",
                        "-ar", "16000",
                        "-c:a", "pcm_s16le",
                        "-y",
                        str(audio_wav_path)
                    ]
                    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

                    # Run Local Transcription with Concurrency Guard
                    job.state = "TRANSCRIBING_LOCAL_ASR"
                    job.progress_percent = 80
                    job.current_step = f"Transcribing speech locally via {target_model.display_name} ({req_lang.upper()})"
                    await session.commit()

                    provider = registry.get_provider(target_model.provider_id)
                    if not provider:
                        raise RuntimeError(f"Provider '{target_model.provider_id}' not found.")

                    async with self.asr_semaphore:
                        asr_res = await provider.transcribe(
                            audio_path=str(audio_wav_path),
                            model_id=target_model.model_id,
                            language=req_lang
                        )

                    # Persist Transcript
                    if asr_res.segments:
                        full_clean_text = asr_res.full_text
                        
                        t_stmt = select(Transcript).where(Transcript.video_id == video.id)
                        t_res = await session.execute(t_stmt)
                        old_t = t_res.scalar_one_or_none()
                        if old_t:
                            await session.delete(old_t)
                            await session.flush()

                        new_t = Transcript(
                            video_id=video.id,
                            language=asr_res.detected_language or asr_res.language or req_lang,
                            requested_language=requested_lang,
                            source_type="local_asr",
                            caption_source="Local ASR",
                            asr_model=target_model.display_name,
                            caption_language_code=None,
                            is_generated=True,
                            full_text=full_clean_text
                        )
                        session.add(new_t)
                        await session.flush()

                        for s in asr_res.segments:
                            session.add(TranscriptSegment(
                                transcript_id=new_t.id,
                                sequence_index=s.sequence_index,
                                start_time=s.start_time,
                                end_time=s.end_time,
                                duration=s.duration,
                                text=s.text,
                                word_count=s.word_count
                            ))

                        t_file = settings.transcripts_path / f"{video.id}.txt"
                        t_file.write_text(full_clean_text, encoding="utf-8")
                        session.add(Artifact(
                            video_id=video.id,
                            job_id=job.id,
                            artifact_type="transcript_txt",
                            relative_path=f"storage/transcripts/{video.id}.txt",
                            file_size_bytes=t_file.stat().st_size,
                            is_regeneratable=True,
                            retention_state="ACTIVE"
                        ))
                        await session.flush()

                        # Deterministically calculate ScriptMetrics
                        try:
                            await ScriptAnalysisService.analyze_and_persist(video.id, session)
                        except Exception as sme:
                            warnings.append(f"Script analysis warning: {str(sme)}")
                    else:
                        warnings.append("Local ASR executed successfully but produced no transcribed speech.")

                    # Safe Temp Cleanup
                    try:
                        shutil.rmtree(str(settings.temp_path / f"job_{job.id}"), ignore_errors=True)
                    except Exception:
                        pass

                else:
                    warnings.append(strategy_res["message"])

            # Finalize Job
            video.processing_status = "COMPLETED" if not warnings else "COMPLETED_WITH_WARNINGS"
            job.state = "COMPLETED" if not warnings else "COMPLETED_WITH_WARNINGS"
            job.progress_percent = 100
            job.current_step = "Completed Successfully" if not warnings else "Completed with warnings"
            job.warnings = warnings
            job.completed_at = utc_now()
            await session.commit()

        except asyncio.CancelledError:
            job.state = "CANCELLED"
            job.progress_percent = 100
            job.current_step = "Job cancelled by user"
            job.completed_at = utc_now()
            await session.commit()
        except Exception as e:
            err_code = getattr(e, "code", "EXTRACTION_FAILED")
            retryable = getattr(e, "retryable", False)
            job.state = "FAILED"
            job.progress_percent = 100
            job.current_step = "Execution Failed"
            job.error_details = {
                "code": err_code,
                "message": str(e),
                "retryable": retryable
            }
            job.completed_at = utc_now()
            await session.commit()

    async def _process_retranscribe_job(self, session: AsyncSession, job: ExtractionJob):
        """
        Executes an asynchronous retranscription job with atomic transcript replacement.
        Guarantees that existing transcripts remain completely intact if retranscription fails.
        """
        video_id = job.video_id
        target_lang = job.requested_transcript_language or "en"

        job.state = "VALIDATING"
        job.progress_percent = 10
        job.current_step = f"Starting retranscription for language: {target_lang.upper()}"
        job.started_at = utc_now()
        await session.commit()

        v_stmt = select(Video).where(Video.id == video_id)
        v_res = await session.execute(v_stmt)
        video = v_res.scalar_one_or_none()

        if not video:
            job.state = "FAILED"
            job.progress_percent = 100
            job.current_step = "Video not found"
            job.error_details = {"code": "VIDEO_NOT_FOUND", "message": "Target video record does not exist."}
            job.completed_at = utc_now()
            await session.commit()
            return

        job_temp_dir = settings.temp_path / f"job_{job.id}"
        job_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Check if platform caption in target_lang is already available in cached metadata
            raw_meta_file = settings.metadata_path / f"{video.id}.json"
            raw_info = {}
            if raw_meta_file.exists():
                try:
                    raw_info = json.loads(raw_meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            job.state = "GETTING_CAPTIONS"
            job.progress_percent = 30
            job.current_step = f"Checking for existing {target_lang.upper()} platform captions"
            await session.commit()

            cap_url, cap_lang, is_auto = YtDlpAdapter.select_best_caption_track(
                raw_info,
                requested_language=target_lang
            )

            new_full_text = ""
            new_segments = []
            new_source_type = "platform"
            new_caption_source = "Platform Captions"
            new_asr_model = None
            new_is_generated = False
            actual_lang = target_lang

            if cap_url:
                try:
                    content = await YtDlpAdapter.fetch_caption_content(cap_url)
                    if cap_url.endswith(".json3") or "fmt=json3" in cap_url:
                        new_segments, new_full_text = CaptionService.parse_json3(content)
                    else:
                        new_segments, new_full_text = CaptionService.parse_vtt(content)
                    new_source_type = "platform"
                    new_caption_source = "Platform Captions"
                    new_asr_model = None
                    new_is_generated = is_auto
                    actual_lang = cap_lang or target_lang
                except Exception:
                    new_full_text = ""
                    new_segments = []

            # 2. If no platform caption or empty text, fallback to Local ASR
            if not new_full_text or not new_segments:
                target_model = registry.get_default_model_for_language(target_lang)
                if not target_model:
                    raise RuntimeError(f"No ASR model configured for language: {target_lang}")

                job.state = "DOWNLOADING_MEDIA"
                job.progress_percent = 50
                job.current_step = f"Acquiring audio for {target_model.display_name} ({target_lang.upper()})"
                await session.commit()

                raw_audio_template = job_temp_dir / f"retranscribe_{job.id}_raw.%(ext)s"
                await YtDlpAdapter.download_media(
                    url=video.original_url,
                    output_template=str(raw_audio_template),
                    format_spec="bestaudio/best"
                )

                # Locate downloaded audio file
                dl_files = list(job_temp_dir.glob(f"retranscribe_{job.id}_raw.*"))
                if not dl_files:
                    raise RuntimeError("Failed to acquire audio stream from source URL.")
                downloaded_audio_path = dl_files[0]

                # Convert to standard 16kHz mono WAV for ASR
                audio_wav_path = job_temp_dir / f"retranscribe_{job.id}_16k.wav"
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(downloaded_audio_path),
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    str(audio_wav_path)
                ]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

                # Run Local Transcription with Concurrency Guard
                job.state = "TRANSCRIBING_LOCAL_ASR"
                job.progress_percent = 80
                job.current_step = f"Transcribing speech locally via {target_model.display_name} ({target_lang.upper()})"
                await session.commit()

                provider = registry.get_provider(target_model.provider_id)
                if not provider:
                    raise RuntimeError(f"Provider '{target_model.provider_id}' not found.")

                async with self.asr_semaphore:
                    asr_res = await provider.transcribe(
                        audio_path=str(audio_wav_path),
                        model_id=target_model.model_id,
                        language=target_lang
                    )

                if not asr_res.segments or not asr_res.full_text:
                    raise RuntimeError("Local ASR produced empty transcript.")

                new_full_text = asr_res.full_text
                new_segments = asr_res.segments
                new_source_type = "local_asr"
                new_caption_source = "Local ASR"
                new_asr_model = target_model.display_name
                new_is_generated = True
                actual_lang = asr_res.detected_language or asr_res.language or target_lang

            # Atomic database transcript replacement
            t_stmt = select(Transcript).where(Transcript.video_id == video.id)
            t_res = await session.execute(t_stmt)
            old_t = t_res.scalar_one_or_none()
            if old_t:
                await session.delete(old_t)
                await session.flush()

            new_t = Transcript(
                video_id=video.id,
                language=actual_lang,
                requested_language=target_lang,
                source_type=new_source_type,
                caption_source=new_caption_source,
                caption_language_code=cap_lang if (new_source_type == "platform" and cap_url) else None,
                asr_model=new_asr_model,
                is_generated=new_is_generated,
                full_text=new_full_text
            )
            session.add(new_t)
            await session.flush()

            for s in new_segments:
                session.add(TranscriptSegment(
                    transcript_id=new_t.id,
                    sequence_index=s.sequence_index,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    duration=s.duration,
                    text=s.text,
                    word_count=s.word_count
                ))

            # Update file artifact
            t_file = settings.transcripts_path / f"{video.id}.txt"
            t_file.write_text(new_full_text, encoding="utf-8")
            session.add(Artifact(
                video_id=video.id,
                job_id=job.id,
                artifact_type="transcript_txt",
                relative_path=f"storage/transcripts/{video.id}.txt",
                file_size_bytes=t_file.stat().st_size,
                is_regeneratable=True,
                retention_state="ACTIVE"
            ))
            await session.flush()

            # Recalculate script metrics deterministically
            try:
                await ScriptAnalysisService.analyze_and_persist(video.id, session)
            except Exception:
                pass

            job.state = "COMPLETED"
            job.progress_percent = 100
            job.current_step = f"Retranscription complete ({actual_lang.upper()})"
            job.completed_at = utc_now()
            await session.commit()

        except asyncio.CancelledError:
            job.state = "CANCELLED"
            job.progress_percent = 100
            job.current_step = "Retranscription cancelled by user"
            job.completed_at = utc_now()
            await session.commit()
        except Exception as e:
            err_code = getattr(e, "code", "RETRANSCRIBE_FAILED")
            retryable = getattr(e, "retryable", True)
            job.state = "FAILED"
            job.progress_percent = 100
            job.current_step = "Retranscription Failed"
            job.error_details = {
                "code": err_code,
                "message": str(e),
                "retryable": retryable
            }
            job.completed_at = utc_now()
            await session.commit()
        finally:
            try:
                shutil.rmtree(str(job_temp_dir), ignore_errors=True)
            except Exception:
                pass

global_worker_pool = JobWorkerPool(max_concurrency=settings.max_concurrent_jobs)
