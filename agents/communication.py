"""🎙 Communication Intelligence Agent [Фаза 2]
Разбор переговоров/встреч. Перенесено и улучшено из бота Logos:
запись → транскрипция (ElevenLabs/Whisper) → сводка (Claude) в разных форматах,
вопросы по встрече, переговорная линза (кто что пообещал / договорённости / риски /
action items). Встречи сохраняются в БД (переживают перезапуск).

Файл-запись приходит из bot/handlers напрямую (как голос/фото), не через оркестратор.
Текстовые запросы («что по последней встрече», «action items») — через оркестратор."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime

from agents.base import chat
from database import crud
from integrations.transcription import make_transcription_provider

log = logging.getLogger("los.comm")

SYSTEM_SUMMARY = (
    "Ты превращаешь транскрипт деловой встречи/переговоров в чёткую структурированную "
    "заметку на русском. По делу, без воды. НЕ выдумывай факты, которых нет в транскрипте. "
    "Если ответственный или срок не назван — пиши «не указано».\n"
    "Заметку читают С ТЕЛЕФОНА — оформляй под мобильный экран: заголовки разделов через "
    "##, **жирным** выделяй важное, перечни давай списками через «- ». "
    "НЕ используй таблицы (| ... |) — на телефоне они обрезаются; любые перечни, "
    "включая задачи, оформляй списком."
)

SYSTEM_QA = (
    "Ты — ассистент по этой встрече. Отвечай на вопросы, опираясь на транскрипт ниже. "
    "Если ответа в транскрипте нет — честно скажи. По-русски, компактно, простым текстом "
    "(без markdown и таблиц), под телефон."
)

# Форматы заметки: ключ -> (подпись кнопки, инструкция модели). Все — в Markdown
# (## заголовки, **жирный**, списки «- »), без таблиц — см. SYSTEM_SUMMARY.
FORMATS = {
    "protocol": (
        "📋 Протокол",
        "Сделай по транскрипту структурированный протокол в Markdown. "
        "Раздели крупные секции линией `---`. Структура:\n"
        "## Краткое содержание (3–5 предложений)\n"
        "---\n"
        "## Ключевые решения (список «- », можно с вложенностью)\n"
        "---\n"
        "## Задачи — СПИСКОМ (не таблицей!), каждая отдельным пунктом:\n"
        "`- Задача — 👤 ответственный (или «не указано») · 🗓 срок (или «не указано»)`\n"
        "---\n"
        "## Открытые вопросы (список «- »)",
    ),
    "tasks": (
        "✅ Только задачи",
        "Выпиши ТОЛЬКО задачи (action items) как список с чекбоксами (Markdown). "
        "Каждая строка строго:\n"
        "`- [ ] Задача — 👤 ответственный (или «не указано») · 🗓 срок (или «не указано»)`",
    ),
    "email": (
        "✉️ Письмо-итог",
        "Напиши участникам короткое деловое письмо (Markdown) с итогами встречи: что "
        "обсудили, что решили, что кому делать (списком «- », НЕ таблицей). К отправке.",
    ),
    "tldr": (
        "⚡ TL;DR",
        "Дай очень краткую выжимку: 3–5 пунктов «- » самого важного. Markdown.",
    ),
    "translate_en": (
        "🌐 Перевод EN",
        "Make a concise English summary of the meeting (decisions + tasks) in Markdown. "
        "Tasks as a bulleted list, NOT a table (mobile-friendly).",
    ),
}

# Глубокий разбор переговоров (раздел 3.6 ТЗ) — психологический + юридический.
SYSTEM_NEGOTIATION = (
    "Ты — аналитик переговоров системы LOS: психологический и юридический разбор. "
    "Анализируешь транскрипт встречи. По-русски, по делу, под телефон, в Markdown.\n"
    "ЖЁСТКИЕ ПРАВИЛА:\n"
    "— НЕ выноси вердикт «врёт/лжёт» — фиксируй «признаки» и «несоответствия».\n"
    "— Опирайся ТОЛЬКО на транскрипт; короткие цитаты как доказательство.\n"
    "— Если данных мало для блока — честно пиши «недостаточно данных», не выдумывай.\n"
    "— Без таблиц (обрезаются на телефоне) — только заголовки ## и списки «- »."
)

NEGOTIATION_INSTR = (
    "Сделай разбор переговоров по блокам (Markdown):\n"
    "## 🎭 Манипуляции\n"
    "Техники (газлайтинг, давление, лесть, уклонение, искусственный дефицит времени) — "
    "каждая пунктом «- » с короткой цитатой. Нет — пиши «не замечено».\n"
    "## ⚔️ Скрытые конфликты\n"
    "Противоречия, избегаемые темы, точки напряжения.\n"
    "## 🔍 Искренность\n"
    "Логические нестыковки и уклончивые формулировки как ПРИЗНАКИ (без вердикта о лжи).\n"
    "## 🧠 Профайлинг\n"
    "По каждому ключевому участнику: тип личности, мотивации, вероятные слабые точки.\n"
    "## ⚖️ Юридический анализ\n"
    "Риски позиции, уязвимости, рекомендации по следующим шагам.\n"
    "## ⚠️ Итоговый риск\n"
    "ПЕРВОЙ строкой ровно «Уровень риска: высокий» (или «средний», или «низкий»), "
    "затем 1–2 предложения с конкретной рекомендацией."
)


async def analyze_negotiation(services, meeting_id: int) -> dict:
    """Глубокий разбор переговоров: манипуляции/конфликты/искренность/профайлинг/право.
    Возвращает {ok, text, risk: high|medium|low, title}."""
    m = await crud.get_meeting(services.db, meeting_id)
    if not m:
        return {"ok": False, "text": "Встреча не найдена — пришли запись заново."}
    user = f'{NEGOTIATION_INSTR}\n\nТранскрипт:\n"""\n{m["transcript"][:_MAXLEN]}\n"""'
    out = await chat(services, SYSTEM_NEGOTIATION, user, max_tokens=4000)
    if not out:
        return {"ok": False, "text": "Не получилось разобрать — попробуй ещё раз."}
    low = out.lower()
    risk = "high" if "риска: высок" in low else ("medium" if "риска: сред" in low else "low")
    return {"ok": True, "text": out, "risk": risk, "title": m.get("title", "Встреча")}

_MAXLEN = 200_000  # страховка по длине транскрипта в промпте (символы)


def _safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", s or "").strip()
    return re.sub(r"\s+", " ", s)[:60]


async def _summarize(services, transcript: str, fmt_key: str) -> str | None:
    instr = FORMATS.get(fmt_key, FORMATS["protocol"])[1]
    user = f'{instr}\n\nТранскрипт:\n"""\n{transcript[:_MAXLEN]}\n"""'
    return await chat(services, SYSTEM_SUMMARY, user, max_tokens=3500)


async def _make_title(services, transcript: str) -> str:
    out = await chat(
        services, SYSTEM_SUMMARY,
        "Придумай короткое название встречи (3–6 слов) на русском — только суть, без "
        "кавычек и точки. Верни ТОЛЬКО название одной строкой.\n\nНачало транскрипта:\n"
        f'"""\n{transcript[:1500]}\n"""',
        max_tokens=40)
    return _safe_name(out or "") or "Встреча"


async def process_recording(services, file_path: str, src_name: str | None, chat_id: int) -> dict:
    """Запись → транскрипт → сводка-протокол → сохранить встречу. Возвращает dict с
    ключами ok/meeting_id/title/summary/transcript либо ok=False+error."""
    provider = make_transcription_provider(services.config)
    if provider is None:
        return {"ok": False, "error": "Нет ключа для распознавания речи "
                "(ELEVENLABS_API_KEY или OPENAI_API_KEY)."}
    try:
        transcript = await provider.transcribe(file_path, language="ru")
    except Exception as e:
        log.error("transcribe: %s", e)
        return {"ok": False, "error": f"Не смог распознать запись: {e}"}
    if not transcript:
        return {"ok": False, "error": "Речь не распозналась (пусто)."}

    if src_name:
        title = _safe_name(os.path.splitext(src_name)[0]) or "Встреча"
    else:
        try:
            title = await _make_title(services, transcript)
        except Exception:
            title = "Встреча"

    summary = None
    try:
        summary = await _summarize(services, transcript, "protocol")
    except Exception as e:
        log.error("summary: %s", e)

    m = await crud.add_meeting(services.db, chat_id, title, transcript, summary)
    return {"ok": True, "meeting_id": m["id"], "title": title,
            "summary": summary, "transcript": transcript}


async def format_meeting(services, meeting_id: int, fmt_key: str) -> str:
    m = await crud.get_meeting(services.db, meeting_id)
    if not m:
        return "Встреча не найдена — пришли запись заново."
    # протокол кэшируем (он генерится при загрузке)
    if fmt_key == "protocol" and m.get("summary"):
        return m["summary"]
    out = await _summarize(services, m["transcript"], fmt_key)
    if out and fmt_key == "protocol":
        await crud.update_meeting_summary(services.db, meeting_id, out)
    return out or "Не получилось собрать заметку — попробуй ещё раз."


async def share_recap(services, meeting_id: int) -> str:
    """Короткая заметка для пересылки участникам (суть + решения + задачи)."""
    m = await crud.get_meeting(services.db, meeting_id)
    if not m:
        return "Встреча не найдена."
    instr = (
        "Сделай короткую заметку по встрече для отправки участникам (для пересылки). "
        "В Markdown: 1–2 предложения сути, **Решения** списком «- », **Задачи** списком "
        "(с ответственным и сроком, где есть). Кратко, по делу, без лишнего."
    )
    user = f'{instr}\n\nТранскрипт:\n"""\n{m["transcript"][:_MAXLEN]}\n"""'
    out = await chat(services, SYSTEM_SUMMARY, user, max_tokens=2000)
    return out or "Не получилось собрать заметку — попробуй ещё раз."


async def answer_meeting(services, meeting_id: int, question: str) -> str:
    m = await crud.get_meeting(services.db, meeting_id)
    if not m:
        return "Встреча не найдена."
    system = f'{SYSTEM_QA}\n\nТранскрипт встречи:\n"""\n{m["transcript"][:_MAXLEN]}\n"""'
    out = await chat(services, system, question, max_tokens=1500)
    return out or "Не смог ответить — попробуй переформулировать."


async def extract_action_items(services, meeting_id: int) -> list:
    """Достаёт задачи из встречи как [{title, datetime|None}] для переноса в напоминания."""
    m = await crud.get_meeting(services.db, meeting_id)
    if not m:
        return []
    now = datetime.now(services.config.tz).strftime("%Y-%m-%d %H:%M (%A)")
    out = await chat(
        services, "Ты извлекаешь задачи (action items) из транскрипта встречи. "
        "Верни ТОЛЬКО JSON-массив объектов вида "
        '{"title": "что сделать (коротко, по-русски)", '
        '"datetime": "YYYY-MM-DD HH:MM или null если срок не назван"}. '
        f"Сейчас: {now} — от этого считай «завтра», «в пятницу» и т.п. "
        "Только реальные задачи из текста, не выдумывай.",
        f'Транскрипт:\n"""\n{m["transcript"][:_MAXLEN]}\n"""',
        max_tokens=1500)
    if not out:
        return []
    mt = re.search(r"\[.*\]", out, re.S)
    if not mt:
        return []
    try:
        items = json.loads(mt.group(0))
    except Exception:
        return []
    res = []
    for it in items if isinstance(items, list) else []:
        title = (it.get("title") or "").strip() if isinstance(it, dict) else ""
        if title:
            res.append({"title": title, "datetime": (it.get("datetime") or None)})
    return res


# ---------- для оркестратора (текстовые запросы) ----------
async def last_meeting_text(services, chat_id=None, fmt_key: str = "protocol") -> str:
    m = await crud.latest_meeting(services.db, chat_id)
    if not m:
        return ("Пока нет разобранных встреч. Пришли запись разговора (голосом или "
                "файлом) — расшифрую и сделаю сводку.")
    body = await format_meeting(services, m["id"], fmt_key)
    return f"🎙 {m['title']}\n\n{body}"


async def ask_last_meeting(services, chat_id, question: str) -> str:
    m = await crud.latest_meeting(services.db, chat_id)
    if not m:
        return "Пока нет разобранных встреч — пришли запись разговора."
    return await answer_meeting(services, m["id"], question)


async def run(services, question: str = None) -> str:
    """Точка для оркестратора по умолчанию — последняя встреча (протокол)."""
    return await last_meeting_text(services, fmt_key="protocol")
