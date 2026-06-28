"""Транскрипция голосовых через OpenAI Whisper. Без ключа OpenAI — возвращает None."""
from __future__ import annotations

import logging

log = logging.getLogger("los.whisper")


async def transcribe(services, file_path: str) -> str | None:
    if not services.openai:
        return None
    try:
        with open(file_path, "rb") as f:
            tr = await services.openai.audio.transcriptions.create(
                model=services.config.whisper_model,
                file=f,
                language="ru",
            )
        return tr.text
    except Exception as e:
        log.error("Ошибка транскрипции: %s", e)
        return None
