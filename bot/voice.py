"""Голосовые: скачиваем OGG из Telegram → Whisper → текст."""
from __future__ import annotations

import logging
import os
import tempfile

from integrations.whisper import transcribe

log = logging.getLogger("los.voice")


async def handle_voice(services, message) -> str | None:
    bot = services.bot
    try:
        file = await bot.get_file(message.voice.file_id)
    except Exception as e:
        log.error("get_file: %s", e)
        return None
    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)
    try:
        await bot.download_file(file.file_path, destination=path)
        return await transcribe(services, path)
    except Exception as e:
        log.error("download/transcribe: %s", e)
        return None
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
