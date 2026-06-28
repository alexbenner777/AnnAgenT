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
