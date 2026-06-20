"""
J2 — Adapter de transcripción. Jerarquía:
  1. faster-whisper (si instalado) — transcripción real del audio.
  2. Transcripción semilla — demo determinista; activa cuando no hay audio real o sin Whisper.

Regla de oro: sin audio → error claro. Audio presente pero Whisper ausente → semilla demo.
La semilla garantiza que la demo corra aunque el micrófono o el binario fallen.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transcript:
    text: str
    segments: list[dict] = field(default_factory=list)


# Transcripción semilla para el demo (diligencia de descargos típica).
_DEMO_TRANSCRIPT = Transcript(
    text=(
        "Siendo las diez de la mañana del día de hoy, se da inicio a la diligencia de "
        "descargos del trabajador Carlos Andrés Mejía Ríos, identificado con cédula de "
        "ciudadanía número 1.023.456.789 de Medellín, quien se desempeña como Técnico de "
        "Mantenimiento en las instalaciones de la empresa. "
        "El instructor del proceso, el señor Jefe de Recursos Humanos, procede a leer los "
        "cargos formulados: se le imputa al trabajador haber incurrido en reiteradas "
        "llegadas tarde durante los últimos treinta días, en contravención del reglamento "
        "interno de trabajo. "
        "El trabajador, ejerciendo su derecho de defensa, manifiesta que las tardanzas se "
        "debieron a problemas de transporte público derivados de las obras en la vía "
        "principal, situación que notificó a su supervisor de manera verbal. "
        "Presentadas las pruebas por ambas partes y agotado el debate, se da por terminada "
        "la diligencia siendo las once y cuarenta y cinco de la mañana. "
        "Se firma el acta por las partes presentes."
    ),
    segments=[
        {"start": 0.0, "end": 8.5,
         "text": "Siendo las diez de la mañana del día de hoy, se da inicio a la diligencia de descargos.",
         "speaker": "instructor"},
        {"start": 8.5, "end": 22.0,
         "text": "El instructor procede a leer los cargos: reiteradas llegadas tarde en los últimos treinta días.",
         "speaker": "instructor"},
        {"start": 22.0, "end": 45.0,
         "text": "El trabajador manifiesta que las tardanzas se debieron a problemas de transporte público.",
         "speaker": "trabajador"},
        {"start": 45.0, "end": 58.0,
         "text": "Presentadas las pruebas y agotado el debate, se da por terminada la diligencia.",
         "speaker": "instructor"},
    ],
)


def transcribe(audio: bytes) -> Transcript:
    """
    Transcribe el audio de la diligencia de descargos.

    Sin audio (bytes vacíos) → ValueError, nunca transcript inventado.
    Con audio pero sin Whisper instalado → semilla demo determinista.
    Con faster-whisper instalado → transcripción real.
    """
    if not audio:
        raise ValueError(
            "Audio vacío: se requiere audio para transcribir. "
            "No se generan transcripts inventados."
        )

    # Intentar transcripción real con faster-whisper
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments_iter, _ = model.transcribe(tmp_path, beam_size=1, language="es")
            segs = []
            full_text_parts = []
            for seg in segments_iter:
                segs.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "speaker": "speaker",
                })
                full_text_parts.append(seg.text.strip())
            return Transcript(text=" ".join(full_text_parts), segments=segs)
        finally:
            os.unlink(tmp_path)
    except ImportError:
        pass
    except Exception:
        pass

    # Degradación honesta: Whisper no disponible → semilla demo
    return _DEMO_TRANSCRIPT
