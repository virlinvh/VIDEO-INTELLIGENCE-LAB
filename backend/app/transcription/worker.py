import sys
import os
import json
import time
import argparse
from pathlib import Path

# Redirect all caches to application-local paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_CACHE_DIR = PROJECT_ROOT / 'storage' / 'cache' / 'faster_whisper'
LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ['HF_HOME'] = str(LOCAL_CACHE_DIR)
os.environ['HUGGINGFACE_HUB_CACHE'] = str(LOCAL_CACHE_DIR)
os.environ['TORCH_HOME'] = str(LOCAL_CACHE_DIR)

# Dynamically add nvidia runtime DLL directories to os.environ['PATH'] and os.add_dll_directory
venv_site = Path(sys.executable).parent.parent / 'Lib' / 'site-packages'
if venv_site.exists():
    for nvidia_dir in venv_site.glob('nvidia/*'):
        bin_dir = nvidia_dir / 'bin'
        if bin_dir.exists():
            os.environ['PATH'] = str(bin_dir) + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(str(bin_dir))
                except Exception:
                    pass


def cmd_download(repo_id: str, staging_dir: str, target_dir: str):
    from huggingface_hub import snapshot_download
    print(json.dumps({'status': 'DOWNLOADING', 'message': f'Starting snapshot download for {repo_id}'}), flush=True)
    
    staging_path = Path(staging_dir)
    staging_path.mkdir(parents=True, exist_ok=True)
    
    try:
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(staging_path),
            local_dir_use_symlinks=False
        )
        
        print(json.dumps({'status': 'VERIFYING', 'message': 'Validating model weights and config files...'}), flush=True)
        
        required_files = ['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json']
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
            'message': 'Model successfully installed and verified.',
            'installed_path': str(target_path),
            'size_bytes': total_size
        }), flush=True)
    except Exception as e:
        print(json.dumps({'status': 'ERROR', 'message': str(e)}), flush=True)
        sys.exit(1)

def cmd_transcribe(model_path: str, audio_path: str, language: str = None, vad_filter: bool = True):
    from faster_whisper import WhisperModel
    import ctranslate2
    
    has_cuda = ctranslate2.get_cuda_device_count() > 0
    device = 'cuda' if has_cuda else 'cpu'
    compute_type = 'float16' if has_cuda else 'int8'
    device_warning = None
    
    model = None
    if has_cuda:
        try:
            model = WhisperModel(model_path, device='cuda', compute_type='float16')
        except Exception as e:
            device_warning = f'CUDA execution failed ({str(e)}). Falling back to CPU int8.'
            device = 'cpu'
            compute_type = 'int8'
            
    if model is None:
        model = WhisperModel(model_path, device='cpu', compute_type='int8')
        
    start_time = time.perf_counter()
    
    target_lang = None if (not language or language == 'auto') else language
    
    segments_list = []
    full_text_parts = []
    detected_language = None
    language_probability = 1.0

    try:
        segments_gen, info = model.transcribe(
            audio_path,
            language=target_lang,
            beam_size=5,
            vad_filter=vad_filter,
            vad_parameters=dict(min_silence_duration_ms=500),
            word_timestamps=False
        )
        detected_language = info.language
        language_probability = info.language_probability
        
        for idx, seg in enumerate(segments_gen):
            clean_text = seg.text.strip()
            if not clean_text:
                continue
            words = clean_text.split()
            segments_list.append({
                'sequence_index': idx + 1,
                'start_time': round(seg.start, 2),
                'end_time': round(seg.end, 2),
                'duration': round(seg.end - seg.start, 2),
                'text': clean_text,
                'word_count': len(words),
                'avg_logprob': getattr(seg, 'avg_logprob', None),
                'no_speech_prob': getattr(seg, 'no_speech_prob', None)
            })
            full_text_parts.append(clean_text)
    except Exception as cuda_err:
        if device == 'cuda':
            device_warning = f'CUDA runtime failed ({str(cuda_err)}). Retrying on CPU int8.'
            device = 'cpu'
            compute_type = 'int8'
            model = WhisperModel(model_path, device='cpu', compute_type='int8')
            segments_gen, info = model.transcribe(
                audio_path,
                language=target_lang,
                beam_size=5,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500),
                word_timestamps=False
            )
            detected_language = info.language
            language_probability = info.language_probability
            segments_list = []
            full_text_parts = []
            for idx, seg in enumerate(segments_gen):
                clean_text = seg.text.strip()
                if not clean_text:
                    continue
                words = clean_text.split()
                segments_list.append({
                    'sequence_index': idx + 1,
                    'start_time': round(seg.start, 2),
                    'end_time': round(seg.end, 2),
                    'duration': round(seg.end - seg.start, 2),
                    'text': clean_text,
                    'word_count': len(words),
                    'avg_logprob': getattr(seg, 'avg_logprob', None),
                    'no_speech_prob': getattr(seg, 'no_speech_prob', None)
                })
                full_text_parts.append(clean_text)
        else:
            raise cuda_err

        
    proc_duration = round(time.perf_counter() - start_time, 3)
    audio_duration = round(info.duration, 2) if getattr(info, 'duration', None) else 0.0
    rtf = round(proc_duration / audio_duration, 4) if audio_duration > 0 else 0.0
    speed_factor = round(audio_duration / proc_duration, 2) if proc_duration > 0 else 0.0
    
    result = {
        'status': 'SUCCESS',
        'full_text': ' '.join(full_text_parts),
        'language': info.language,
        'detected_language': info.language,
        'language_probability': round(info.language_probability, 4) if getattr(info, 'language_probability', None) else None,
        'duration_seconds': audio_duration,
        'segment_count': len(segments_list),
        'segments': segments_list,
        'provenance': {
            'source_type': 'LOCAL_ASR',
            'provider_id': 'faster-whisper',
            'model_id': Path(model_path).name,
            'execution_device': device.upper(),
            'compute_type': compute_type,
            'device_warning': device_warning,
            'processing_duration_sec': proc_duration,
            'realtime_factor': rtf,
            'speed_multiplier': speed_factor,
            'vad_enabled': vad_filter,
            'runtime_version': 'faster-whisper 1.1.1 (ctranslate2)',
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    }
    print(json.dumps(result), flush=True)

def main():
    parser = argparse.ArgumentParser(description='Isolated Faster-Whisper ASR Worker')
    subparsers = parser.add_subparsers(dest='command')
    
    dl_parser = subparsers.add_parser('download')
    dl_parser.add_argument('--repo-id', required=True)
    dl_parser.add_argument('--staging-dir', required=True)
    dl_parser.add_argument('--target-dir', required=True)
    
    tr_parser = subparsers.add_parser('transcribe')
    tr_parser.add_argument('--model-path', required=True)
    tr_parser.add_argument('--audio-path', required=True)
    tr_parser.add_argument('--language', default=None)
    tr_parser.add_argument('--no-vad', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'download':
        cmd_download(args.repo_id, args.staging_dir, args.target_dir)
    elif args.command == 'transcribe':
        cmd_transcribe(args.model_path, args.audio_path, args.language, vad_filter=not args.no_vad)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
