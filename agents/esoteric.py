"""🔮 Esoteric Intelligence Agent — «качество дня» по трём системам.

Принцип топовых движков: точная математика считает ФАКТЫ, LLM их интерпретирует
(модель не выдумывает положения планет).
- Нумерология: личный год/месяц/день (арифметика).
- Матрица судьбы: арканы 1–22 из даты (метод Ладини).
- Астрология: Swiss Ephemeris — натал, транзиты к наталу, фаза Луны, Луна без курса.
Результат кэшируется на день и сшивается с реальным днём (календарь + состояние).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from agents.base import chat
from agents import astro
from database import crud

log = logging.getLogger("los.esoteric")

_WD_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

ARCANA = {
    1: "Маг", 2: "Жрица", 3: "Императрица", 4: "Император", 5: "Иерофант",
    6: "Влюблённые", 7: "Колесница", 8: "Справедливость", 9: "Отшельник",
    10: "Колесо Фортуны", 11: "Сила", 12: "Повешенный", 13: "Смерть/Трансформация",
    14: "Умеренность", 15: "Дьявол", 16: "Башня", 17: "Звезда", 18: "Луна",
    19: "Солнце", 20: "Суд", 21: "Мир", 22: "Шут",
}

# ---------- нумерология ----------
def _reduce9(n, master=True):
    while n > 9:
        if master and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def numerology(bd: datetime, today) -> dict:
    py = _reduce9(bd.day + bd.month + sum(int(d) for d in str(today.year)))
    pm = _reduce9(py + today.month)
    pd = _reduce9(pm + today.day)
    life = _reduce9(sum(int(d) for d in bd.strftime("%Y%m%d")))
    return {"личный_год": py, "личный_месяц": pm, "личный_день": pd, "число_жизни": life}


# ---------- матрица судьбы (Ладини) ----------
def _reduce22(n):
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n


def matrix(bd: datetime) -> dict:
    day = _reduce22(bd.day)
    month = _reduce22(bd.month)
    year = _reduce22(sum(int(d) for d in str(bd.year)))
    center = _reduce22(day + month + year)
    def a(n):
        return f"{n} ({ARCANA.get(n, '?')})"
    return {"личность": a(day), "таланты": a(month), "род": a(year), "центр_предназначение": a(center)}


SYSTEM = """Ты — Esoteric Intelligence Agent системы LOS. Тебе дают ТОЧНЫЕ расчёты
(нумерология, Матрица судьбы, астрономические факты из Swiss Ephemeris). Твоя задача —
кратко и по делу интерпретировать их в «качество дня» для занятого руководителя.

ПРАВИЛА:
- Только рекомендации, не «предсказания судьбы». Решение всегда за человеком.
- Всегда давай обоснование (почему именно так), опираясь на данные факты.
- Никаких финансовых и медицинских советов на основе эзотерики.
- Серьёзный, спокойный тон советника. Без мистического тумана и воды.
- Если даны встречи дня и состояние — дай КОНКРЕТНЫЕ тайминги (электив): лучшее окно
  для переговоров/подписаний/отдыха; что перенести (напр. при «Луне без курса»).

Тебе дан СЛОЁНЫЙ прогноз: глава жизни (zodiacal_releasing/фирдар) → год (профекции +
управитель года + соляр) → день (транзиты + электив). Сходящиеся (applying) аспекты —
это нарастающее/будущее (важнее), расходящиеся — уходящее. Электив (сходящиеся аспекты
Луны, достоинства, планетарный час) используй, чтобы назвать лучшее окно сегодня.

ФОРМАТ (Markdown, коротко, без воды; заголовки ##):
## ⚖️ Общая оценка
[высокая/средняя/низкая/нейтральная] — одно предложение почему
## 📆 Год
[акцент года по профекциям (управитель года) и соляру]
## 🧭 Глава жизни
[крупный период по ZR/фирдар — если есть; 1 фраза]
## 🌌 День (астрология)
[ключевые транзиты + Луна/электив + лучшее окно времени]
## 🃏 Матрица
[тон дня]
## 🔢 Нумерология
[личный день N — характеристика]
## ✅ Рекомендация
[что делать / чего избегать сегодня, конкретно]"""


async def day_quality(services, with_context: bool = True) -> str:
    db = services.db
    birth = await crud.get_birth(db)
    if not birth or not birth.get("date"):
        return ("🔮 Не задана дата рождения — без неё нет расчёта. Укажи: "
                "/birth 14.03.1985 09:20 Москва")

    tz = services.config.tz
    now = datetime.now(tz)
    today = now.date()

    # кэш на день
    cached = await crud.get_setting(db, "eso_day")
    if cached:
        try:
            obj = json.loads(cached)
            if obj.get("date") == today.isoformat():
                return obj["text"]
        except Exception:
            pass

    bd = datetime.strptime(birth["date"], "%Y-%m-%d")
    facts = {
        "нумерология": numerology(bd, today),
        "матрица_судьбы": matrix(bd),
        "астрология": astro.facts(birth, now),
    }

    context = ""
    if with_context:
        try:
            from integrations import calendar
            sched = await calendar.schedule_text(services)
            dh = await crud.get_daily_health(db, today) or {}
            state = (f"энергия {dh.get('energy_subjective')}/10"
                     if dh.get("energy_subjective") else "состояние не введено")
            context = f"\n\nРЕАЛЬНЫЙ ДЕНЬ (для электива):\n{sched}\nСостояние: {state}"
        except Exception:
            pass

    payload = (f"ДАТА: {today.strftime('%d.%m.%Y')} ({_WD_RU[today.weekday()]})\n\nТОЧНЫЕ РАСЧЁТЫ:\n"
               + json.dumps(facts, ensure_ascii=False, indent=2) + context)
    text = await chat(services, SYSTEM, payload, max_tokens=1300)
    if not text:
        text = ("🔮 КАЧЕСТВО ДНЯ (без Claude):\n"
                f"Нумерология: личный день {facts['нумерология']['личный_день']}\n"
                f"Матрица: центр {facts['матрица_судьбы']['центр_предназначение']}\n"
                f"Луна: {facts['астрология'].get('луна_сегодня', {}).get('фаза', '—')}")

    await crud.set_setting(db, "eso_day", json.dumps({"date": today.isoformat(), "text": text},
                                                     ensure_ascii=False))
    return text


async def facts_text(services) -> str:
    """«Решение задачи»: точные цифры, на которых построен разбор дня."""
    birth = await crud.get_birth(services.db)
    if not birth or not birth.get("date"):
        return "Нет данных рождения — /birth."
    bd = datetime.strptime(birth["date"], "%Y-%m-%d")
    now = datetime.now(services.config.tz)
    today = now.date()
    num = numerology(bd, today)
    mat = matrix(bd)
    af = astro.facts(birth, now)

    L = ["# 🔍 На чём построен разбор\n",
         f"Дата: {today.strftime('%d.%m.%Y')} ({_WD_RU[today.weekday()]})",
         f"Рождение: {birth_summary(birth)}",
         "\n## 🔢 Нумерология (Пифагор)",
         f"• Личный год {num['личный_год']} = {bd.day}+{bd.month}+Σ{today.year}",
         f"• Личный месяц {num['личный_месяц']} = {num['личный_год']}+{today.month}",
         f"• Личный день {num['личный_день']} = {num['личный_месяц']}+{today.day}",
         f"• Число жизни {num['число_жизни']} (из полной даты рождения)",
         "\n## 🃏 Матрица судьбы (Ладини)",
         f"• Личность: {mat['личность']} · Таланты: {mat['таланты']}",
         f"• Род: {mat['род']} · Центр/предназначение: {mat['центр_предназначение']}"]
    if af:
        L.append("\n## ♒ Астрология (Swiss Ephemeris)")
        n = af.get("натал", {})
        if n:
            L.append("• Натал: " + ", ".join(f"{k} {v}" for k, v in n.items()))
        pr = af.get("профекции_год")
        if pr:
            L.append(f"• Год (профекции): {pr['возраст']} лет → {pr['дом_года']}-й дом, "
                     f"{pr['знак_года']}, управитель года {pr['управитель_года']} "
                     f"(в {pr['управитель_в_знаке']})")
        sr = af.get("соляр_год")
        if sr:
            extra = (" · угловые: " + ", ".join(sr["угловые"])) if sr.get("угловые") else ""
            L.append(f"• Соляр (карта года): Асц {sr.get('асцендент_года', '?')}{extra}")
        zr = af.get("zodiacal_releasing")
        if zr:
            L.append(f"• Глава жизни (ZR): {zr['глава_L1']} [{zr['L1_годы']}] · "
                     f"подпериод {zr['подпериод_L2']}")
        fd = af.get("фирдар")
        if fd:
            L.append(f"• Фирдар: период {fd['период']} / подпериод {fd['подпериод']}")
        mt = af.get("луна_сегодня")
        if mt:
            L.append(f"• Луна: {mt['фаза']}; {mt['достоинство_луны']}")
            L.append("• Сходящиеся аспекты Луны: " + "; ".join(mt.get("сходящиеся_аспекты_луны", [])))
        tr = af.get("транзиты") or []
        if tr:
            L.append("• Транзиты к наталу: " + "; ".join(tr))
        ph = af.get("планетарные_часы")
        if ph:
            L.append(f"• Планетарный час сейчас: {ph['час_сейчас']} (упр. дня {ph['управитель_дня']})")
    else:
        L.append("\n♒ Астрология: расчёт недоступен (проверь данные рождения).")
    L.append("\nℹ️ Цифры — точные (математика и эфемериды). Формулировку «качества дня» "
             "даёт Claude поверх этих фактов, не выдумывая их.")
    return "\n".join(L)


def birth_summary(birth: dict) -> str:
    if not birth:
        return "не задано"
    s = birth.get("date", "?")
    if birth.get("time"):
        s += f" {birth['time']}"
    if birth.get("city"):
        s += f", {birth['city']}"
    return s
