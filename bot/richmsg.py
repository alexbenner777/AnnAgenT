"""Rich-сообщения Telegram (Bot API 10.1, метод sendRichMessage) через ПРЯМОЙ HTTP —
aiogram их пока не умеет. Дают настоящие заголовки, списки, чекбоксы, формулы и
СВОРАЧИВАЕМЫЕ блоки <details>. Если метод недоступен — вызывающий код откатывается
на обычное сообщение (см. bot/richfmt.py)."""
from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("los.richmsg")

API_BASE = (os.getenv("TELEGRAM_API_BASE") or "https://api.telegram.org").rstrip("/")

# Капабилити-кэш: если облако/сервер не знает sendRichMessage — больше не долбимся,
# сразу уходим в фолбэк. None=ещё не пробовали, True=поддерживается, False=нет.
_RICH_SUPPORTED: bool | None = None


def rich_disabled() -> bool:
    return _RICH_SUPPORTED is False


async def _post(token: str, method: str, payload: dict) -> dict:
    global _RICH_SUPPORTED
    url = f"{API_BASE}/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(url, json=payload)
    ctype = r.headers.get("content-type", "")
    data = r.json() if ctype.startswith("application/json") else {}
    if r.status_code == 200 and data.get("ok"):
        _RICH_SUPPORTED = True
        return data
    body = (r.text or "")[:300]
    # «метода нет» (старый/облачный API) → выключаем rich навсегда в этой сессии
    if r.status_code in (404, 501) or "not found" in body.lower() or "unknown method" in body.lower():
        _RICH_SUPPORTED = False
        log.info("sendRichMessage недоступен — дальше обычные сообщения.")
    raise RuntimeError(f"{method} {r.status_code}: {body}")


async def send_rich_md(token: str, chat_id: int, markdown: str, reply_markup: dict | None = None) -> dict:
    """rich-сообщение из markdown (заголовки/списки/чекбоксы/таблицы/формулы) + опц. кнопки."""
    if _RICH_SUPPORTED is False:
        raise RuntimeError("rich disabled")
    payload = {"chat_id": chat_id, "rich_message": {"markdown": markdown}}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await _post(token, "sendRichMessage", payload)


async def send_rich_or_plain(bot, token: str, chat_id: int, markdown: str, reply_markup=None):
    """Красиво (rich-markdown), а если метод недоступен/сбой — обычным сообщением через
    aiogram-бот, чтобы ничего не пропало. reply_markup — aiogram-клавиатура или None."""
    rm = reply_markup.model_dump(exclude_none=True) if reply_markup is not None else None
    try:
        return await send_rich_md(token, chat_id, markdown, reply_markup=rm)
    except Exception:
        pass
    from bot.richfmt import md_to_tg_html
    try:
        return await bot.send_message(chat_id, md_to_tg_html(markdown), reply_markup=reply_markup)
    except Exception:
        return await bot.send_message(chat_id, markdown, reply_markup=reply_markup, parse_mode=None)


async def send_rich_html(token: str, chat_id: int, html_content: str) -> dict:
    """rich-сообщение из HTML — нужно для сворачиваемых <details> (markdown их не умеет)."""
    if _RICH_SUPPORTED is False:
        raise RuntimeError("rich disabled")
    return await _post(token, "sendRichMessage",
                       {"chat_id": chat_id, "rich_message": {"html": html_content}})


def md_to_html(md: str) -> str:
    """markdown → HTML (таблицы, аккуратные списки, код) для вложения в <details>."""
    import markdown as _md
    return _md.markdown(md or "", extensions=["tables", "sane_lists", "fenced_code"])
