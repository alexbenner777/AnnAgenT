"""❤️ Health & Maintenance Agent [Фаза 2]
Ведёт здоровье босса и дополняет 💊 Medication:
- АНАЛИЗЫ: фото/PDF/текст бланка → Claude vision вытаскивает показатели →
  копим в БД → тренды по каждому показателю (динамика + норма);
- РЕСЁРЧ ПРЕПАРАТОВ: что это, как принимать, побочки и ВЗАИМОДЕЙСТВИЯ с текущими;
- ВИЗИТЫ: план/факт визитов к врачам, что назначили, когда повторно.

NB: ввод файлов (фото/PDF) идёт напрямую из bot/handlers (минуя оркестратор) —
как голос. Текстовые запросы («динамика витамина D», «расскажи про X») —
через оркестратор (orchestrator/tools.py).

Opus 4.8 принимает image- и document-блоки. JSON просим у модели и парсим сами.
Это НЕ медицинский совет — везде дисклеймер, решение всегда за врачом."""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timedelta

from agents.base import chat
from database import crud

log = logging.getLogger("los.health")

_FLAG_EMOJI = {"low": "🔻", "high": "🔺", "normal": "✅"}

EXTRACT_SYSTEM = (
    "Ты извлекаешь данные из бланка медицинских анализов. Возвращай ТОЛЬКО JSON "
    "(без пояснений, без markdown-ограждений) строго в форме:\n"
    '{"taken_on": "YYYY-MM-DD или null", "lab_name": "строка или null", '
    '"results": [{"marker": "имя по-русски", "value": число или null, '
    '"value_text": "оригинал если не число (напр. отрицательно, <0.5) иначе null", '
    '"unit": "ед.изм. или null", "ref_low": число или null, "ref_high": число или null}]}\n'
    "Правила: только то, что реально есть на бланке — НИЧЕГО не выдумывай. "
    "Числа выводи числами (десятичный разделитель — точка). Референс «3.0-5.2» → "
    "ref_low=3.0, ref_high=5.2; «<5.0» → ref_high=5.0; «>30» → ref_low=30. "
    "Имена показателей — по-русски и единообразно (Гемоглобин, Холестерин общий, "
    "Витамин D 25-OH, ТТГ, Глюкоза…). Если дата сдачи не видна — taken_on=null."
)
EXTRACT_PROMPT = "Извлеки все показатели из этого бланка анализов в JSON по заданной схеме."

RESEARCH_SYSTEM = (
    "Ты — медицинский ресёрч-ассистент LOS. По препарату/добавке дай структурно и кратко:\n"
    "• Что это и класс; • Зачем применяют; • Как обычно принимают (общие сведения); "
    "• Частые побочные; • ⚠️ ВЗАИМОДЕЙСТВИЯ с текущими препаратами босса (разбери по списку ниже, "
    "если пересечений нет — так и скажи); • Важные предостережения; • Когда срочно к врачу.\n"
    "Опирайся на доказательную медицину, не ставь диагноз и не назначай дозировки. "
    "По-русски, по делу. В КОНЦЕ обязательно строкой: "
    "«⚠️ Не медицинский совет — дозировки и решение только с лечащим врачом»."
)


# ---------- утилиты ----------
def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _fmt_num(v):
    if v is None:
        return None
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _norm_date(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _ddmm(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m")
    except (ValueError, TypeError):
        return iso or ""


def _ref(rec):
    lo, hi = rec.get("ref_low"), rec.get("ref_high")
    if lo is not None and hi is not None:
        return f"норма {_fmt_num(lo)}–{_fmt_num(hi)}"
    if hi is not None:
        return f"норма <{_fmt_num(hi)}"
    if lo is not None:
        return f"норма >{_fmt_num(lo)}"
    return ""


def _value_str(rec):
    val = _fmt_num(rec.get("value"))
    return val if val is not None else (rec.get("value_text") or "—")


def _line(rec, with_date=True):
    emo = _FLAG_EMOJI.get(rec.get("flag"), "•")
    s = f"{emo} {rec['marker']} {_value_str(rec)}"
    if rec.get("unit"):
        s += f" {rec['unit']}"
    ref = _ref(rec)
    if ref:
        s += f" ({ref})"
    if with_date and rec.get("taken_on"):
        s += f" — {_ddmm(rec['taken_on'])}"
    return s


def _extract_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# ---------- разбор и сохранение анализов ----------
async def _store_payload(services, payload, source: str):
    db = services.db
    taken_on = _norm_date(payload.get("taken_on")) or datetime.now(services.config.tz).date().isoformat()
    panel_id = await crud.add_lab_panel(
        db, taken_on=taken_on, lab_name=payload.get("lab_name"), source=source)
    stored = []
    for r in payload.get("results", []) or []:
        marker = (r.get("marker") or "").strip()
        if not marker:
            continue
        rec = await crud.add_lab_result(
            db, panel_id, taken_on, marker,
            value=_num(r.get("value")), value_text=(r.get("value_text") or None),
            unit=(r.get("unit") or None),
            ref_low=_num(r.get("ref_low")), ref_high=_num(r.get("ref_high")))
        stored.append(rec)
    return taken_on, payload.get("lab_name"), stored


def _ingest_summary(taken_on, lab_name, stored):
    if not stored:
        return ("🧪 Не нашёл показателей на бланке. Пришли фото почётче или впиши вручную: "
                "«добавь анализ: Витамин D 31 нг/мл, норма 30-100».")
    head = f"🧪 Анализы разобраны"
    meta = ", ".join(x for x in (lab_name, _ddmm(taken_on)) if x)
    if meta:
        head += f" ({meta})"
    head += f": {len(stored)} показателей."
    flagged = [r for r in stored if r.get("flag") in ("low", "high")]
    parts = [head]
    if flagged:
        parts.append("Вне нормы:\n" + "\n".join(_line(r, with_date=False) for r in flagged))
        parts.append(f"В норме: {len(stored) - len(flagged)}.")
    else:
        parts.append("✅ Все показатели в норме.")
    parts.append("Динамику смотри так: «динамика витамина D». Обзор: /health.")
    return "\n\n".join(parts)


async def ingest_file(services, data: bytes, media_type: str, source: str) -> str:
    """Фото (image/*) или PDF (application/pdf) бланка → показатели в БД."""
    if not services.anthropic:
        return "❤️ Чтобы разбирать анализы по фото, нужен ANTHROPIC_API_KEY (Claude vision)."
    b64 = base64.standard_b64encode(data).decode()
    if media_type == "application/pdf":
        block = {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    else:
        block = {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}}
    content = [block, {"type": "text", "text": EXTRACT_PROMPT}]
    try:
        resp = await services.anthropic.messages.create(
            model=services.config.anthropic_model, max_tokens=2500,
            system=EXTRACT_SYSTEM, messages=[{"role": "user", "content": content}])
        text = "".join(b.text for b in resp.content if b.type == "text")
    except Exception as e:
        log.error("vision extract: %s", e)
        return "⚠️ Не смог разобрать файл анализов. Попробуй фото почётче или PDF."
    payload = _extract_json(text)
    if not payload:
        return "⚠️ Не удалось распознать показатели на бланке. Пришли фото почётче."
    taken_on, lab_name, stored = await _store_payload(services, payload, source)
    return _ingest_summary(taken_on, lab_name, stored)


async def ingest_text(services, raw: str) -> str:
    """Разобрать вставленный ТЕКСТ анализов (или одну строку «маркер значение норма»)."""
    if not services.anthropic:
        return "❤️ Для разбора текста анализов нужен ANTHROPIC_API_KEY."
    text = await chat(services, EXTRACT_SYSTEM,
                      EXTRACT_PROMPT + "\n\nТекст бланка:\n" + raw, max_tokens=2000)
    payload = _extract_json(text)
    if not payload:
        return "Не разобрал. Формат: «Витамин D 31 нг/мл, норма 30-100»."
    taken_on, lab_name, stored = await _store_payload(services, payload, "text")
    return _ingest_summary(taken_on, lab_name, stored)


# ---------- тренды ----------
async def trend_text(services, marker_query: str) -> str:
    found = await crud.find_markers(services.db, marker_query, limit=1)
    if not found:
        return (f"По «{marker_query}» нет данных. Загрузи анализы (фото/PDF) — "
                f"начну вести динамику.")
    mk = found[0]
    series = await crud.marker_series(services.db, mk["marker_key"], limit=12)
    if not series:
        return f"По «{mk['marker']}» пока одна точка или нет данных."
    unit = next((r["unit"] for r in reversed(series) if r.get("unit")), "")
    head = f"📈 {mk['marker']}" + (f" ({unit})" if unit else "")
    ref = _ref(series[-1])
    if ref:
        head += f", {ref}"
    lines, prev = [], None
    for r in series:
        v = r.get("value")
        arrow = ""
        if prev is not None and v is not None:
            arrow = " ↑" if v > prev else (" ↓" if v < prev else " →")
        emo = _FLAG_EMOJI.get(r.get("flag"), "•")
        lines.append(f"{_ddmm(r.get('taken_on'))}  {_value_str(r)} {emo}{arrow}")
        if v is not None:
            prev = v
    tail = ""
    nums = [r["value"] for r in series if r.get("value") is not None]
    if len(nums) >= 2:
        d = nums[-1] - nums[0]
        trend = "растёт" if d > 0 else ("снижается" if d < 0 else "без изменений")
        state = {"low": "ниже нормы", "high": "выше нормы", "normal": "в норме"}.get(
            series[-1].get("flag"), "")
        tail = "\n\nДинамика: " + trend + (f". Сейчас {state}." if state else ".")
    return head + ":\n" + "\n".join(lines) + tail


# ---------- ресёрч препаратов ----------
async def research_drug(services, query: str) -> str:
    meds = await crud.list_active_medications(services.db)
    meds_list = ", ".join(
        m["name"] + (f" {m['dosage']}" if m.get("dosage") else "") for m in meds) or "нет данных"
    out = await chat(
        services, RESEARCH_SYSTEM,
        f"Препарат/вопрос: {query}\n\nТекущие препараты босса (для проверки взаимодействий): "
        f"{meds_list}",
        max_tokens=1300)
    if out:
        return "💊 " + out
    return ("Для ресёрча препаратов нужен ANTHROPIC_API_KEY. "
            "⚠️ Не медицинский совет — решение с лечащим врачом.")


# ---------- визиты ----------
def _visit_line(v):
    when = _ddmm(v["visit_date"]) if v.get("visit_date") else "дата?"
    who = " ".join(x for x in (v.get("specialty"), v.get("doctor")) if x) or "визит"
    s = f"• {when} — {who}"
    if v.get("reason"):
        s += f": {v['reason']}"
    if v.get("status") == "done" and v.get("outcome"):
        s += f"\n   итог: {v['outcome']}"
    if v.get("followup_date"):
        s += f"\n   повтор: {_ddmm(v['followup_date'])}"
    return s + f" (#{v['id']})"


async def visits_text(services, upcoming_only: bool = False) -> str:
    visits = await crud.list_visits(services.db, upcoming_only=upcoming_only)
    if not visits:
        return ("👨‍⚕️ Визитов нет. Добавь: «запиши визит к кардиологу 30 июня, "
                "плановый осмотр».")
    head = "👨‍⚕️ БЛИЖАЙШИЕ ВИЗИТЫ:" if upcoming_only else "👨‍⚕️ ВИЗИТЫ:"
    return head + "\n" + "\n".join(_visit_line(v) for v in visits)


# ---------- обзор и блок для брифинга ----------
async def overview_text(services) -> str:
    latest = await crud.latest_lab_results(services.db, limit=18)
    parts = ["## ❤️ Здоровье"]
    if latest:
        flagged = [r for r in latest if r.get("flag") in ("low", "high")]
        normal = [r for r in latest if r.get("flag") not in ("low", "high")]
        lab_lines = [_line(r) for r in flagged] + [_line(r) for r in normal[:8]]
        more = len(normal) - 8
        block = "🧪 Последние анализы:\n" + "\n".join(lab_lines)
        if more > 0:
            block += f"\n…и ещё {more} в норме."
        parts.append(block)
    else:
        parts.append("🧪 Анализы ещё не загружены. Пришли фото или PDF бланка — "
                     "разберу и буду вести динамику по каждому показателю.")
    upcoming = await crud.list_visits(services.db, upcoming_only=True)
    if upcoming:
        parts.append("👨‍⚕️ Ближайшие визиты:\n" + "\n".join(_visit_line(v) for v in upcoming[:5]))
    return "\n\n".join(parts)


async def briefing_block(services) -> str:
    """Короткий блок здоровья для утреннего брифинга. Пусто, если нечего показать."""
    lines = []
    latest = await crud.latest_lab_results(services.db, limit=40)
    flagged = [r for r in latest if r.get("flag") in ("low", "high")]
    if flagged:
        lines.append("Вне нормы: " + "; ".join(
            f"{r['marker']} {_value_str(r)}{(' ' + r['unit']) if r.get('unit') else ''}"
            for r in flagged[:5]))
    today = datetime.now(services.config.tz).date()
    soon = today + timedelta(days=7)
    upcoming = await crud.list_visits(services.db, upcoming_only=True)
    near = [v for v in upcoming if v.get("visit_date")
            and today.isoformat() <= v["visit_date"] <= soon.isoformat()]
    for v in near[:3]:
        who = " ".join(x for x in (v.get("specialty"), v.get("doctor")) if x) or "визит"
        lines.append(f"визит {_ddmm(v['visit_date'])} — {who}")
    return "❤️ ЗДОРОВЬЕ: " + "; ".join(lines) if lines else ""


async def run(services, question: str = None) -> str:
    """Точка для оркестратора по умолчанию — обзор здоровья."""
    return await overview_text(services)


# публичные обёртки форматтеров для оркестратора
result_line = _line
visit_line = _visit_line
