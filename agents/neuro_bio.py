"""🔋 Neuro & Bio Intelligence Agent [MVP]
Анализ физического/ментального состояния по Oura + субъективному вводу."""
import json
from datetime import datetime

from agents.base import chat
from database import crud
from integrations import calendar

SYSTEM = """Ты — Neuro & Bio Intelligence Agent системы LOS.
Анализируешь физическое и ментальное состояние босса и оптимизируешь расписание.

ПРАВИЛА АНАЛИЗА:
- Readiness < 65: флаг low_readiness, предложи перенести тяжёлые встречи
- Readiness < 50: критический флаг, настаивай на перестановке расписания
- Снижение 3+ дня подряд: флаг fatigue_pattern
- Высокая нагрузка при низком readiness: флаг cognitive_risk
- При конфликте субъективного и Oura: используй субъективное, ставь флаг data_conflict

ТИПЫ ВСТРЕЧ: strategic/negotiations/public_speaking/travel → HIGH;
team_operational/one_on_one → MEDIUM; administrative/routine → LOW;
sport/rest → PROTECTED (не трогать); family → UNTOUCHABLE (игнорировать).

Отвечай только на русском, кратко, с конкретными рекомендациями по времени."""


async def run(services, question: str = None) -> str:
    cfg = services.config
    today = datetime.now(cfg.tz).date()

    oura = await services.oura.snapshot(today) if services.oura else {}
    dh = await crud.get_daily_health(services.db, today) or {}
    recent = await crud.get_recent_health(services.db, 7)
    meetings = await calendar.events_today(services)

    payload = {
        "date": today.isoformat(),
        "oura": oura,
        "subjective": {k: dh.get(k) for k in
                       ("energy_subjective", "focus_subjective", "mood_subjective",
                        "workout_done", "massage_done", "alcohol")},
        "readiness_trend_7d": [r.get("readiness_score") for r in recent],
        "meetings_today": [{"time": m.get("time"), "title": m.get("title")} for m in meetings],
        "question": question,
    }
    text = await chat(services, SYSTEM,
                      "Данные:\n" + json.dumps(payload, ensure_ascii=False, indent=2),
                      max_tokens=800)
    return text or _fallback(oura, dh, cfg)


def _fallback(oura: dict, dh: dict, cfg) -> str:
    """Если OpenAI не настроен — простая интерпретация по правилам."""
    r = oura.get("readiness_score")
    energy = dh.get("energy_subjective")
    parts = []
    if r is not None:
        if r < cfg.readiness_critical_threshold:
            parts.append(f"🔴 Readiness {r} — критически низко. Настаиваю перенести тяжёлые встречи.")
        elif r < cfg.readiness_low_threshold:
            parts.append(f"🟡 Readiness {r} — низковато. Тяжёлые встречи лучше разгрузить.")
        else:
            parts.append(f"🟢 Readiness {r} — норма.")
    else:
        parts.append("Данных Oura нет (токен не настроен или нет синка).")
    if energy is not None:
        parts.append(f"Субъективно: энергия {energy}/10"
                     + (f", фокус {dh['focus_subjective']}/10" if dh.get("focus_subjective") else "")
                     + (f", настроение {dh['mood_subjective']}/10" if dh.get("mood_subjective") else ""))
    else:
        parts.append("Субъективное состояние не введено — пришли /state.")
    return "\n".join(parts)
