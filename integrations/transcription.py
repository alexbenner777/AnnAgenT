"""🎙 Транскрипция встреч (аудио → текст). Перенесено из бота Logos.
Провайдеры переключаемые: ElevenLabs Scribe (лучше для русского, тянет файл целиком)
или OpenAI Whisper. Длинные файлы режутся ffmpeg на куски и склеиваются.

В LOS аудио приходит уже ≤20 МБ (лимит Bot API), так что нарезка почти никогда не
нужна — но оставлена на случай локального Bot API сервера (файлы до 2 ГБ)."""
from __future__ import annotations

import asyncio
import glob
import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod

log = logging.getLogger("los.transcribe")

CHUNK_SECONDS = 600  # 10-минутные куски при нарезке


def _split(audio_path: str) -> list:
    """Режет длинный файл на куски (моно 16кГц mp3) через ffmpeg."""
    outdir = tempfile.mkdtemp(prefix="chunks_")
    pattern = os.path.join(outdir, "chunk_%03d.mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", audio_path,
             "-ac", "1", "-ar", "16000", "-b:a", "64k",
             "-f", "segment", "-segment_time", str(CHUNK_SECONDS), "-y", pattern],
            check=True, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("Не найден ffmpeg — нужен для очень длинных записей.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg не смог нарезать файл: {e.stderr.decode()[:200]}")
    return sorted(glob.glob(os.path.join(outdir, "chunk_*.mp3")))


class TranscriptionProvider(ABC):
    max_bytes = 24 * 1024 * 1024  # порог нарезки; провайдеры переопределяют

    @abstractmethod
    async def _transcribe_one(self, path: str, language: str) -> str:
        ...

    async def transcribe(self, audio_path: str, language: str = "ru") -> str:
        if os.path.getsize(audio_path) <= self.max_bytes:
            return await self._transcribe_one(audio_path, language)
        chunks = await asyncio.to_thread(_split, audio_path)
        parts = []
        try:
            for c in chunks:
                parts.append(await self._transcribe_one(c, language))
        finally:
            for c in chunks:
                if os.path.exists(c):
                    os.unlink(c)
            try:
                os.rmdir(os.path.dirname(chunks[0]))
            except (OSError, IndexError):
                pass
        return "\n".join(p for p in parts if p).strip()


class OpenAIWhisper(TranscriptionProvider):
    max_bytes = 24 * 1024 * 1024

    def __init__(self, api_key: str, model: str = "whisper-1"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def _transcribe_one(self, path: str, language: str) -> str:
        with open(path, "rb") as f:
            resp = await self.client.audio.transcriptions.create(
                model=self.model, file=f, language=language)
        return (resp.text or "").strip()


class ElevenLabsScribe(TranscriptionProvider):
    """ElevenLabs Scribe — лидер по русскому, принимает файл целиком (до ~1 ГБ)."""
    max_bytes = 900 * 1024 * 1024
    URL = "https://api.elevenlabs.io/v1/speech-to-text"

    def __init__(self, api_key: str, model: str = "scribe_v1"):
        self.api_key = api_key
        self.model = model

    async def _transcribe_one(self, path: str, language: str) -> str:
        import httpx
        with open(path, "rb") as fh:
            content = fh.read()
        files = {"file": (os.path.basename(path), content, "application/octet-stream")}
        data = {"model_id": self.model}
        if language:
            data["language_code"] = language
        async with httpx.AsyncClient(timeout=600) as client:
            r = await client.post(self.URL, headers={"xi-api-key": self.api_key},
                                  data=data, files=files)
        r.raise_for_status()
        return (r.json().get("text") or "").strip()


def make_transcription_provider(cfg):
    """Строит провайдер по конфигу. Откатывается на доступный, если выбранного ключа нет."""
    p = cfg.transcription_provider
    if p == "elevenlabs" and cfg.has_elevenlabs:
        return ElevenLabsScribe(cfg.elevenlabs_api_key, cfg.elevenlabs_stt_model)
    if cfg.has_openai:
        return OpenAIWhisper(cfg.openai_api_key, cfg.openai_transcribe_model)
    if cfg.has_elevenlabs:
        return ElevenLabsScribe(cfg.elevenlabs_api_key, cfg.elevenlabs_stt_model)
    return None  # нечем транскрибировать
