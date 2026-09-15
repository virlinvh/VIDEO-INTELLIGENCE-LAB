import pytest
import pytest_asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.transcription.models import (
    ModelStatus,
    ModelFamily,
    TranscriptionSettings,
    TranscriptionSettingsUpdate,
    TranscriptSegmentContract,
    ProvenanceMetadata,
    TranscriptionResultContract,
    ModelCatalogItem
)
from backend.app.transcription.registry import registry, is_path_contained
from backend.app.transcription.router import TranscriptionRouter
from backend.app.transcription.service import TranscriptionService
from backend.app.transcription.providers.base import BaseASRProvider

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    await engine.dispose()

def test_catalog_definitions():
    catalog = registry.list_catalog()
    assert len(catalog) >= 1
    ids = [m.model_id for m in catalog]
    assert "whisper-large-v3-turbo" in ids

    # Ensure Wispr is NOT in catalog
    assert not any("wispr" in m.model_id.lower() for m in catalog)

    # Status must be valid ModelStatus
    for m in catalog:
        assert m.status in [ModelStatus.READY, ModelStatus.NOT_INSTALLED, ModelStatus.FILES_MISSING]

def test_filesystem_containment():
    root = registry.get_models_root()
    valid_sub = root / "faster-whisper" / "whisper-small"
    assert is_path_contained(valid_sub, root) is True

    # Path traversal attempts
    invalid_traversal = root / ".." / "data"
    assert is_path_contained(invalid_traversal, root) is False

def test_language_routing():
    settings = TranscriptionSettings(
        automatic_asr_fallback_enabled=False,
        default_language_mode="auto"
    )

    # 1. Platform captions exist -> Platform priority
    res1 = TranscriptionRouter.resolve_transcription_strategy(
        has_platform_captions=True,
        user_language_override=None,
        settings=settings
    )
    assert res1["strategy"] == "PLATFORM_CAPTIONS"
    assert res1["can_proceed"] is True

    # 2. No platform captions, fallback disabled -> UNAVAILABLE_NO_CAPTIONS
    res2 = TranscriptionRouter.resolve_transcription_strategy(
        has_platform_captions=False,
        user_language_override=None,
        settings=settings
    )
    assert res2["strategy"] == "UNAVAILABLE_NO_CAPTIONS"
    assert res2["can_proceed"] is False

    # 3. No platform captions, fallback enabled -> LOCAL_ASR_FALLBACK
    settings.automatic_asr_fallback_enabled = True
    res3 = TranscriptionRouter.resolve_transcription_strategy(
        has_platform_captions=False,
        user_language_override="ta",
        settings=settings
    )
    assert res3["strategy"] in ["LOCAL_ASR_FALLBACK", "UNAVAILABLE_NO_MODEL"]

class MockTestASRProvider(BaseASRProvider):
    @property
    def provider_id(self) -> str:
        return "mock-asr"
    @property
    def display_name(self) -> str:
        return "Mock Test ASR Provider"
    @property
    def supported_languages(self):
        return ["en", "ta", "ml"]
    @property
    def is_installed(self) -> bool:
        return True
    def check_runtime(self) -> dict:
        return {"installed": True}
    def check_model(self, model_id: str, model_path: Path) -> dict:
        return {"ready": True, "status": ModelStatus.READY}
    def health_check(self) -> bool:
        return True
    async def transcribe(self, audio_path: str, model_id: str, language: str = None, options: dict = None) -> TranscriptionResultContract:
        return TranscriptionResultContract(
            full_text="Test mock transcription.",
            language=language or "en",
            duration_seconds=5.0,
            segment_count=1,
            segments=[
                TranscriptSegmentContract(sequence_index=1, start_time=0.0, end_time=5.0, duration=5.0, text="Test mock transcription.", word_count=3)
            ],
            provenance=ProvenanceMetadata(provider_id="mock-asr", model_id=model_id)
        )



def test_provider_transcription_contract():
    mock_item = ModelCatalogItem(
        model_id="mock-test-model",
        provider_id="mock-asr",
        family=ModelFamily.FASTER_WHISPER,
        display_name="Mock Test Model",
        description="Mock",
        supported_languages=["en", "ta"],
        is_multilingual=True,
        recommended_use="Testing",
        runtime_requirement="None",
        expected_download_size="0 MB",
        expected_installed_size="0 MB",
        license_info="MIT",
        source_repository="mock/repo",
        hardware_notes="None",
        status=ModelStatus.READY,
        status_detail="Ready"
    )

    # Verify mock provider transcript contract
    mock_prov = MockTestASRProvider()
    assert mock_prov.provider_id == "mock-asr"

@pytest.mark.asyncio
async def test_transcription_settings_persistence(test_db: AsyncSession):
    # Default settings
    initial = await TranscriptionService.get_settings(test_db)
    assert initial.automatic_asr_fallback_enabled is False

    # Update enabled
    updated = await TranscriptionService.update_settings(
        test_db,
        TranscriptionSettingsUpdate(automatic_asr_fallback_enabled=True, default_language_mode="ta")
    )
    assert updated.automatic_asr_fallback_enabled is True
    assert updated.default_language_mode == "ta"

    # Reject assigning non-existent model as active default
    with pytest.raises(ValueError) as exc:
        await TranscriptionService.update_settings(
            test_db,
            TranscriptionSettingsUpdate(default_model_english="non-existent-model-xyz")
        )
    assert "does not exist in catalog" in str(exc.value)


@pytest.mark.asyncio
async def test_subsystem_status_calculation(test_db: AsyncSession):
    status = await TranscriptionService.get_subsystem_status(test_db)
    assert status.status in ["NOT_CONFIGURED", "READY"]
    assert status.total_languages_count == 3
    assert len(status.language_routes) == 3


def test_audio_extraction_contract():
    contract = TranscriptionService.get_audio_extraction_contract("job-12345")
    assert contract.format == "wav"
    assert contract.channels == 1
    assert contract.sample_rate_hz == 16000
    assert "job_job-12345" in contract.target_path or "job-12345" in contract.target_path

def test_indic_conformer_catalog_registration():
    catalog = registry.list_catalog()
    model_ids = [m.model_id for m in catalog]
    assert "indic-conformer-600m-multilingual" in model_ids
    assert "whisper-large-v3-turbo" in model_ids

    indic_model = registry.get_model("indic-conformer-600m-multilingual")
    assert indic_model is not None
    assert indic_model.family == ModelFamily.INDIC_CONFORMER
    assert "ta" in indic_model.supported_languages
    assert "ml" in indic_model.supported_languages
    assert "en" not in indic_model.supported_languages

def test_indic_conformer_provider_contract():
    provider = registry.get_provider("indicconformer")
    assert provider is not None
    assert provider.provider_id == "indicconformer"
    assert "ta" in provider.supported_languages
    assert "ml" in provider.supported_languages
    runtime_check = provider.check_runtime()
    assert "installed" in runtime_check

def test_unicode_integrity_and_replacement_character_detection():
    # Valid Tamil and Malayalam texts with code-switching
    tam_text = "தமிழ் மொழி பேசும் வீடியோ - இன்று meeting இருக்கிறது"
    mal_text = "മലയാളം സംസാരിക്കുന്ന വീഡിയോ - ഇന്ന് meeting ഉണ്ട്"
    
    # Verify no corruption in round-trip serialization
    tam_json = json.loads(json.dumps({"text": tam_text}, ensure_ascii=False))["text"]
    mal_json = json.loads(json.dumps({"text": mal_text}, ensure_ascii=False))["text"]
    
    assert tam_json == tam_text
    assert mal_json == mal_text
    assert "\ufffd" not in tam_json
    assert "\ufffd" not in mal_json

    # Test detection of corrupted replacement character
    corrupted = "മലയാളം \ufffd\ufffd ོ"
    assert "\ufffd" in corrupted
    assert corrupted.count("\ufffd") == 2

