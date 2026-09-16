from typing import Optional, Dict, Any, Tuple
from backend.app.transcription.models import ModelStatus, ModelCatalogItem, TranscriptionSettings
from backend.app.transcription.registry import registry

class TranscriptionRouter:
    """
    Evaluates transcript availability and routes to the appropriate model based on
    Platform Captions Priority -> User Language Preference -> Configured Model -> Fallback.
    """
    @staticmethod
    def resolve_transcription_strategy(
        has_platform_captions: bool,
        user_language_override: Optional[str],
        settings: TranscriptionSettings
    ) -> Dict[str, Any]:
        # 1. Platform Captions Priority (Always preferred)
        if has_platform_captions:
            return {
                "strategy": "PLATFORM_CAPTIONS",
                "can_proceed": True,
                "message": "Platform captions found and will be used as primary source.",
                "model": None,
                "language": None
            }

        # 2. Check if local ASR fallback is enabled
        if not settings.automatic_asr_fallback_enabled:
            return {
                "strategy": "UNAVAILABLE_NO_CAPTIONS",
                "can_proceed": False,
                "message": "No platform captions found. Local ASR fallback is currently disabled.",
                "model": None,
                "language": None
            }

        # 3. Determine target language
        target_lang = user_language_override or settings.default_language_mode
        if not target_lang:
            target_lang = "auto"

        # 4. Resolve configured model for specific language
        target_model_id = None
        if target_lang == "en":
            target_model_id = settings.default_model_english
        elif target_lang == "ta":
            target_model_id = settings.default_model_tamil
        elif target_lang == "ml":
            target_model_id = settings.default_model_malayalam

        # 5. If specific model configured, check its live status
        catalog = registry.list_catalog()
        model_map = {m.model_id: m for m in catalog}

        if target_model_id and target_model_id in model_map:
            model = model_map[target_model_id]
            if model.status == ModelStatus.READY:
                return {
                    "strategy": "LOCAL_ASR",
                    "can_proceed": True,
                    "message": f"Routed to configured model '{model.display_name}'.",
                    "model": model,
                    "language": target_lang
                }

        # 6. Fallback to general multilingual model if allowed or if language is AUTO
        if settings.allow_multilingual_fallback or target_lang == "auto":
            for m in catalog:
                if m.is_multilingual and m.status == ModelStatus.READY:
                    if target_lang == "auto" or target_lang in m.supported_languages:
                        return {
                            "strategy": "LOCAL_ASR_FALLBACK",
                            "can_proceed": True,
                            "message": f"Routed to multilingual fallback model '{m.display_name}'.",
                            "model": m,
                            "language": target_lang
                        }

        # 7. No compatible model installed
        lang_label = {"en": "English", "ta": "Tamil", "ml": "Malayalam", "auto": "Automatic"}.get(target_lang, target_lang)
        return {
            "strategy": "UNAVAILABLE_NO_MODEL",
            "can_proceed": False,
            "message": f"No platform captions were found, and no compatible local transcription model is installed for {lang_label}.",
            "model": None,
            "language": target_lang
        }
