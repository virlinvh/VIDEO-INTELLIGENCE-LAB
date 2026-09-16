import sys
import os
import json
import time
import argparse
from pathlib import Path

# Redirect all caches to application-local paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CACHE_DIR = PROJECT_ROOT / 'storage' / 'cache' / 'indicconformer'
LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ['HF_HOME'] = str(LOCAL_CACHE_DIR)
os.environ['HUGGINGFACE_HUB_CACHE'] = str(LOCAL_CACHE_DIR)
os.environ['TORCH_HOME'] = str(LOCAL_CACHE_DIR)

def cmd_download(repo_id: str, staging_dir: str, target_dir: str):
    from huggingface_hub import snapshot_download, get_token
    from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
    
    print(json.dumps({'status': 'DOWNLOADING', 'message': f'Starting snapshot download for {repo_id}'}), flush=True)
    
    staging_path = Path(staging_dir)
    staging_path.mkdir(parents=True, exist_ok=True)
    
    token = get_token()
    
    try:
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(staging_path),
            local_dir_use_symlinks=False,
            token=token
        )
        
        print(json.dumps({'status': 'VERIFYING', 'message': 'Validating IndicConformer model weights and configs...'}), flush=True)
        
        required_files = ['config.json', 'assets/rnnt_decoder.onnx', 'assets/vocab.json']
        missing = [f for f in required_files if not (staging_path / f).exists()]
        if missing:
            print(json.dumps({'status': 'ERROR', 'message': f'Missing required model files: {missing}'}), flush=True)
            sys.exit(1)
            
        print(json.dumps({'status': 'FINALIZING', 'message': 'Moving verified model to permanent storage...'}), flush=True)
        target_path = Path(target_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if target_path.exists():
            import shutil
            shutil.rmtree(str(target_path))
            
        staging_path.rename(target_path)
        
        total_size = sum(f.stat().st_size for f in target_path.glob('**/*') if f.is_file())
        print(json.dumps({
            'status': 'READY',
            'message': 'IndicConformer model successfully installed and verified.',
            'installed_path': str(target_path),
            'size_bytes': total_size
        }), flush=True)
    except GatedRepoError as gre:
        auth_msg = (
            f"Access to repository '{repo_id}' is restricted. "
            "Please visit https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual to accept the access agreement, "
            "then ensure your Hugging Face token is active."
        )
        print(json.dumps({'status': 'AUTHENTICATION_REQUIRED', 'message': auth_msg}), flush=True)
        sys.exit(1)
    except Exception as e:
        err_str = str(e)
        if "403" in err_str or "restricted" in err_str.lower() or "authorized" in err_str.lower():
            auth_msg = (
                f"Access authorization required for '{repo_id}'. "
                "Please visit https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual to request access."
            )
            print(json.dumps({'status': 'AUTHENTICATION_REQUIRED', 'message': auth_msg}), flush=True)
        else:
            print(json.dumps({'status': 'ERROR', 'message': err_str}), flush=True)
        sys.exit(1)

def cmd_transcribe(model_path: str, audio_path: str, language: str = "ta", decoder: str = "ctc", chunk_sec: float = 20.0, overlap_sec: float = 1.0):
    """
    Executes chunked ASR inference with AI4Bharat IndicConformer.
    Produces authentic timestamps, tracks progress, and calculates diagnostic script ratios.
    """
    import torch
    import torchaudio
    from transformers import AutoModel
    
    start_time = time.perf_counter()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Load audio
    wav, sr = torchaudio.load(audio_path)
    if wav.shape[0] > 1:
        wav = torch.mean(wav, dim=0, keepdim=True)
        
    if sr != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
        wav = resampler(wav)
        sr = 16000
        
    total_samples = wav.shape[1]
    audio_duration = round(total_samples / sr, 2)
    
    # Load model
    model = AutoModel.from_pretrained(model_path, trust_remote_code=True)
    if device == "cuda":
        model = model.to("cuda")
        
    chunk_samples = int(chunk_sec * sr)
    overlap_samples = int(overlap_sec * sr)
    step_samples = chunk_samples - overlap_samples
    
    segments = []
    full_text_list = []
    total_chunks = max(1, (total_samples + step_samples - 1) // step_samples)
    
    cur_pos = 0
    chunk_idx = 0
    
    while cur_pos < total_samples:
        chunk_idx += 1
        end_pos = min(total_samples, cur_pos + chunk_samples)
        chunk_wav = wav[:, cur_pos:end_pos]
        
        chunk_start_sec = round(cur_pos / sr, 2)
        chunk_end_sec = round(end_pos / sr, 2)
        chunk_dur_sec = round(chunk_end_sec - chunk_start_sec, 2)
        
        # Transcribe chunk
        with torch.no_grad():
            if device == "cuda":
                chunk_wav = chunk_wav.to("cuda")
            transcription = model(chunk_wav, language, decoder)
            
        chunk_text = str(transcription).strip() if transcription else ""
        if chunk_text:
            # Conservative deduplication against previous segment tail
            words = chunk_text.split()
            if segments and words:
                prev_words = segments[-1]["text"].split()
                # Check 1-3 word overlap
                for overlap_len in range(min(3, len(words), len(prev_words)), 0, -1):
                    if prev_words[-overlap_len:] == words[:overlap_len]:
                        words = words[overlap_len:]
                        break
            clean_chunk = " ".join(words)
            if clean_chunk:
                segments.append({
                    "sequence_index": len(segments) + 1,
                    "start_time": chunk_start_sec,
                    "end_time": chunk_end_sec,
                    "duration": chunk_dur_sec,
                    "text": clean_chunk,
                    "word_count": len(words)
                })
                full_text_list.append(clean_chunk)
                
        cur_pos += step_samples
        
    full_text = " ".join(full_text_list)
    proc_duration = round(time.perf_counter() - start_time, 3)
    rtf = round(proc_duration / audio_duration, 4) if audio_duration > 0 else 0.0
    speed_factor = round(audio_duration / proc_duration, 2) if proc_duration > 0 else 0.0
    
    # Calculate Script Ratio Diagnostics
    tamil_chars = sum(1 for c in full_text if '\u0B80' <= c <= '\u0BFF')
    malayalam_chars = sum(1 for c in full_text if '\u0D00' <= c <= '\u0D7F')
    latin_chars = sum(1 for c in full_text if ('a' <= c.lower() <= 'z'))
    digits = sum(1 for c in full_text if c.isdigit())
    spaces_punct = sum(1 for c in full_text if c.isspace() or not c.isalnum())
    total_chars = max(1, len(full_text))
    
    target_indic_chars = tamil_chars if language == "ta" else malayalam_chars
    other_chars = total_chars - (tamil_chars + malayalam_chars + latin_chars + digits + spaces_punct)
    has_u_fffd = "\ufffd" in full_text
    
    script_mismatch_warning = None
    if has_u_fffd:
        script_mismatch_warning = f"Detected {full_text.count(chr(0xFFFD))} Unicode replacement character(s) U+FFFD."
    elif other_chars / total_chars > 0.15:
        script_mismatch_warning = "Possible transcription/script mismatch: high ratio of unrelated characters detected."
        
    result = {
        "status": "SUCCESS",
        "full_text": full_text,
        "language": language,
        "detected_language": language,
        "language_probability": 1.0,
        "duration_seconds": audio_duration,
        "segment_count": len(segments),
        "segments": segments,
        "provenance": {
            "source_type": "LOCAL_ASR",
            "provider_id": "indicconformer",
            "model_id": Path(model_path).name,
            "decoder": decoder.upper(),
            "execution_device": device.upper(),
            "processing_duration_sec": proc_duration,
            "realtime_factor": rtf,
            "speed_multiplier": speed_factor,
            "script_diagnostics": {
                "target_indic_ratio": round(target_indic_chars / total_chars, 4),
                "latin_codeswitch_ratio": round(latin_chars / total_chars, 4),
                "other_unrelated_ratio": round(other_chars / total_chars, 4),
                "has_u_fffd": has_u_fffd,
                "warning": script_mismatch_warning
            },
            "runtime_version": "AI4Bharat IndicConformer (torch/onnx)",
            "generated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)

def main():
    parser = argparse.ArgumentParser(description='Isolated IndicConformer ASR Worker')
    subparsers = parser.add_subparsers(dest='command')
    
    dl_parser = subparsers.add_parser('download')
    dl_parser.add_argument('--repo-id', required=True)
    dl_parser.add_argument('--staging-dir', required=True)
    dl_parser.add_argument('--target-dir', required=True)
    
    tr_parser = subparsers.add_parser('transcribe')
    tr_parser.add_argument('--model-path', required=True)
    tr_parser.add_argument('--audio-path', required=True)
    tr_parser.add_argument('--language', default='ta')
    tr_parser.add_argument('--decoder', default='ctc', choices=['ctc', 'rnnt'])
    tr_parser.add_argument('--chunk-sec', type=float, default=20.0)
    tr_parser.add_argument('--overlap-sec', type=float, default=1.0)
    
    args = parser.parse_args()
    
    if args.command == 'download':
        cmd_download(args.repo_id, args.staging_dir, args.target_dir)
    elif args.command == 'transcribe':
        cmd_transcribe(args.model_path, args.audio_path, args.language, args.decoder, args.chunk_sec, args.overlap_sec)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
