"""
Tests del adapter de transcripción (J2).
Contrato:
  - Sin audio → ValueError, nunca transcript inventado.
  - Audio presente (sin Whisper) → transcript semilla no-vacío con segmentos.
  - Semilla es determinista: mismo input → mismo output.
"""
import pytest
from app.adapters.transcription.whisper_client import transcribe, _DEMO_TRANSCRIPT


def test_audio_vacio_lanza_error():
    with pytest.raises(ValueError, match="Audio vacío"):
        transcribe(b"")


def test_audio_con_bytes_devuelve_transcript_no_vacio():
    result = transcribe(b"dummy-audio-bytes")
    assert len(result.text) > 10
    assert isinstance(result.segments, list)
    assert len(result.segments) > 0


def test_segmentos_tienen_campos_requeridos():
    result = transcribe(b"dummy-audio-bytes")
    for seg in result.segments:
        assert "start" in seg
        assert "end" in seg
        assert "text" in seg
        assert "speaker" in seg


def test_fallback_es_determinista():
    r1 = transcribe(b"audio1")
    r2 = transcribe(b"audio2")
    # Sin Whisper ambos devuelven la misma semilla
    assert r1.text == r2.text


def test_demo_transcript_tiene_contenido():
    assert len(_DEMO_TRANSCRIPT.text) > 50
    assert len(_DEMO_TRANSCRIPT.segments) >= 1
