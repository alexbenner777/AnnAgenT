"""Скачиваем присланный в Telegram файл (фото/документ) в память (bytes).
Лимит Bot API на скачивание — 20 МБ; бланк анализов в него укладывается."""
from __future__ import annotations

import logging

log = logging.getLogger("los.upload")


async def download_bytes(services, file_id: str) -> bytes | None:
    bot = services.bot
    try:
        file = await bot.get_file(file_id)
        buf = await bot.download_file(file.file_path)  # destination=None → BytesIO
        return buf.read() if buf else None
    except Exception as e:
        log.error("download_bytes: %s", e)
        return None


async def download_to_tempfile(services, file_id: str, suffix: str = "") -> str | None:
    """Скачивает файл из Telegram во временный файл на диске, возвращает путь.
    Для аудио/видео встреч (их отдаём распознавалке по пути). Удалять — вызывающему."""
    import os
    import tempfile
    bot = services.bot
    try:
        file = await bot.get_file(file_id)
    except Exception as e:
        log.error("get_file: %s", e)
        return None
    fd, path = tempfile.mkstemp(suffix=suffix or "")
    os.close(fd)
    try:
        await bot.download_file(file.file_path, destination=path)
        return path
    except Exception as e:
        log.error("download_to_tempfile: %s", e)
        try:
            os.remove(path)
        except OSError:
            pass
        return None
