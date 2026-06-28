"""🎯 Decision Support Agent [MVP]
Агрегирует контекст агентов: утренний брифинг 07:00, вечерний дайджест 22:00,
а также ad-hoc мультилинзовый анализ по запросу."""
from datetime import datetime

from agents.base import chat
from agents import neuro_bio, medication, network, esoteric, health
from integrations import calendar

SYSTEM = """Ты — Decision Support Agent системы LOS.
Агрегируешь контекст всех агентов и формируешь мультилинзовый анализ.
Линзы: физическая (Neuro&Bio), эзотерическая (Фаза 2), медицинская (Фаза 2),
репутационная (Network, Фаза 2), коммуникационная (Comm, Фаза 2).
Арбитраж: физическое состояние > эзотерика > остальное.
Пиши по-русски, структурно, без вступлений «Конечно!». Максимум 3-4 блока.
При критическом алерте — сначала алерт, потом детали."""

_WD = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def _date_ru(dt: datetime) -> str:
    return f"{dt.day:02d}.{dt.month:02d}.{dt.year}, {_WD[dt.weekday()]}"


async def run(services, mode: str = "morning", question: str = None) -> str:
    if mode == "adhoc":
        return await _adhoc(services, question or "")
    return await _briefing(services, mode)


async def _briefing(services, mode: str) -> str:
    cfg = services.config
    now = datetime.now(cfg.tz)
    neuro = await neuro_bio.run(services)
    meds = await medication.schedule_text(services, header=False)

    if mode == "morning":
        sched = await calendar.schedule_text(services)
        dates = await network.upcoming_text(services)
        eso = await esoteric.day_quality(services)
        hb = await health.briefing_block(services)
        components = (f"СОСТОЯНИЕ:\n{neuro}\n\n"
                      f"РАСПИСАНИЕ:\n{sched}\n\n"
                      f"ВАЖНЫЕ ДАТЫ:\n{dates or 'нет'}\n\n"
                      f"ПРЕПАРАТЫ СЕГОДНЯ:\n{meds}\n\n"
                      f"КАЧЕСТВО ДНЯ:\n{eso}")
        if hb:
            components += f"\n\n{hb}"
        out = await chat(
            services, SYSTEM,
            f"Составь УТРЕННИЙ БРИФИНГ на {_date_ru(now)} из данных ниже. "
            f"Формат: заголовок «☀️ ДОБРОЕ УТРО», блоки Состояние / Препараты / "
            f"Здоровье (если есть данные) / Качество дня / Приоритеты дня (если можешь вывести). "
            f"В конце: «Введи состояние: /state».\n\n{components}",
            max_tokens=1000)
        if out:
            return out
        return (f"☀️ ДОБРОЕ УТРО. {_date_ru(now)}\n\n{components}\n\n"
                f"Введи состояние: /state")

    # evening
    components = f"ИТОГ ПО СОСТОЯНИЮ:\n{neuro}\n\nПрепараты: {meds}"
    out = await chat(
        services, SYSTEM,
        f"Составь ВЕЧЕРНИЙ ДАЙДЖЕСТ на {_date_ru(now)}: блоки День / Не закрыто / "
        f"Завтра (предварительно). Данные:\n\n{components}",
        max_tokens=800)
    if out:
        return out
    return f"🌙 ВЕЧЕРНИЙ ИТОГ. {_date_ru(now)}\n\n{components}"


async def _adhoc(services, question: str) -> str:
    neuro = await neuro_bio.run(services)
    meds = await medication.schedule_text(services, header=False)
    ctx = f"Состояние: {neuro}\nПрепараты сегодня: {meds}"
    out = await chat(
        services, SYSTEM,
        f"ВОПРОС БОССА: {question}\n\nКОНТЕКСТ:\n{ctx}\n\n"
        f"Дай мультилинзовый анализ и конкретную рекомендацию (не «возможно», а «рекомендую»).",
        max_tokens=900)
    if out:
        return out
    return (f"По вопросу «{question}»:\n{ctx}\n\n"
            f"(Для полноценного анализа подключи OPENAI_API_KEY.)")
