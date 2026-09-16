import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.app.config import settings
from backend.app.transcription.providers.base import BaseASRProvider
from backend.app.transcription.models import (
    TranscriptionResultContract,
    TranscriptSegmentContract,
    ProvenanceMetadata
)

class IndicConformerProvider(BaseASRProvider):
    @property
    def provider_id(self) -> str:
        return "indicconformer"

    @property
    def display_name(self) -> str:
        return "AI4Bharat IndicConformer 600M"

    @property
    def supported_languages(self) -> List[str]:
        return ["ta", "ml"]

    def _get_worker_python(self) -> Path:
        runtime_dir = settings.project_root / "runtimes" / "indicconformer" / ".venv"
        if sys.platform == "win32":
            py_path = runtime_dir / "Scripts" / "python.exe"
        else:
            py_path = runtime_dir / "bin" / "python"
        return py_path

    def _get_worker_script(self) -> Path:
        return settings.project_root / "runtimes" / "indicconformer" / "worker.py"

    def check_runtime(self) -> Dict[str, Any]:
        py_path = self._get_worker_python()
        if not py_path.exists():
            return {
                "installed": False,
                "runtime_path": str(py_path.parent.parent),
                "message": "AI4Bharat IndicConformer isolated runtime virtualenv not found."
            }
        return {
            "installed": True,
            "runtime_path": str(py_path.parent.parent),
            "message": "AI4Bharat IndicConformer isolated runtime verified."
        }

    def check_model(self, model_id: str, model_path: str) -> Dict[str, Any]:
        p = Path(model_path)
        if not p.exists():
            return {"ready": False, "status": "NOT_INSTALLED", "detail": "Directory does not exist"}
        
        req_files = ["config.json", "assets/rnnt_decoder.onnx", "assets/vocab.json"]
        existing = [f for f in req_files if (p / f).exists()]
        if len(existing) == 0:
            return {"ready": False, "status": "NOT_INSTALLED", "detail": "Model weight files missing"}
        if len(existing) < len(req_files):
            return {"ready": False, "status": "FILES_MISSING", "detail": f"Missing files: {set(req_files) - set(existing)}"}
        return {"ready": True, "status": "READY", "detail": "Model files intact"}

    async def download_model(
        self,
        repo_id: str,
        staging_dir: Path,
        target_dir: Path,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        py_path = self._get_worker_python()
        if not py_path.exists():
            raise RuntimeError(f"Isolated runtime python not found at {py_path}")

        script_path = self._get_worker_script()
        cmd = [
            str(py_path),
            str(script_path),
            "download",
            "--repo-id", repo_id,
            "--staging-dir", str(staging_dir),
            "--target-dir", str(target_dir)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        last_status = {}
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                last_status = data
                if progress_callback:
                    await progress_callback(data)
            except Exception:
                pass

        stderr_bytes = await proc.stderr.read()
        await proc.wait()

        if proc.returncode != 0:
            err_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Download failed with code {proc.returncode}: {last_status.get('message', err_msg)}")

        return last_status

    async def transcribe(
        self,
        audio_path: str,
        model_id: str,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> TranscriptionResultContract:
        py_path = self._get_worker_python()
        if not py_path.exists():
            raise RuntimeError(f"Isolated runtime python not found at {py_path}")

        model_path = settings.models_path / "indicconformer" / model_id
        if not model_path.exists():
            raise RuntimeError(f"Model path does not exist: {model_path}")

        script_path = self._get_worker_script()
        target_lang = language or "ta"
        decoder = (options or {}).get("decoder", "ctc")

        cmd = [
            str(py_path),
            str(script_path),
            "transcribe",
            "--model-path", str(model_path),
            "--audio-path", str(audio_path),
            "--language", target_lang,
            "--decoder", decoder
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"IndicConformer worker failed (code {proc.returncode}): {err_msg}")

        out_str = stdout_bytes.decode("utf-8", errors="replace").strip()
        result_json = None
        for line in out_str.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    if "full_text" in data:
                        result_json = data
                        break
                except Exception:
                    continue

        if not result_json:
            raise RuntimeError(f"Invalid IndicConformer worker output: {out_str}")

        segments = [
            TranscriptSegmentContract(
                sequence_index=s["sequence_index"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                duration=s["duration"],
                text=s["text"],
                word_count=s["word_count"]
            )
            for s in result_json.get("segments", [])
        ]

        prov_data = result_json.get("provenance", {})
        provenance = ProvenanceMetadata(
            source_type="LOCAL_ASR",
            provider_id="indicconformer",
            model_id=model_id,
            model_version="600m-multilingual",
            runtime_version=prov_data.get("runtime_version", "AI4Bharat IndicConformer"),
            generated_at=datetime.utcnow(),
            processing_duration_sec=prov_data.get("processing_duration_sec", 0.0),
            configuration=prov_data
        )

        return TranscriptionResultContract(
            full_text=result_json.get("full_text", ""),
            language=result_json.get("language", target_lang),
            detected_language=result_json.get("detected_language", target_lang),
            language_probability=result_json.get("language_probability", 1.0),
            duration_seconds=result_json.get("duration_seconds", 0.0),
            segment_count=len(segments),
            segments=segments,
            provenance=provenance
        )

    def health_check(self) -> bool:
        return self._get_worker_python().exists()
