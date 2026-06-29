"""Реестр инструментов для ReAct-оркестратора (OpenAI function calling).
tool_specs() — схемы для модели; dispatch() — фактический вызов агентов."""
import logging
from datetime import datetime

from agents import (neuro_bio, decision_support, medication,
                    esoteric, health, network, communication)
from database import crud

log = logging.getLogger("los.tools")

# Пн=0..Вс=6 (как datetime.weekday()). Принимаем en/ru сокращения.
_DAYMAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6,
}
_RU_DAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _parse_days(raw):
    """['sat'] / ['сб'] → [5]; пусто/непонятно → None (= каждый день)."""
    out = []
    for d in (raw or []):
        key = str(d).strip().lower()[:3] if str(d).strip().lower()[:3] in _DAYMAP else str(d).strip().lower()[:2]
        if key in _DAYMAP:
            out.append(_DAYMAP[key])
    return sorted(set(out)) or None


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_time(s):
    if not s:
        return None
    for fmt in ("%H:%M", "%H.%M", "%H-%M"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def tool_specs() -> list:
    # Формат Anthropic tool use: name / description / input_schema.
    def fn(name, desc, props=None, required=None):
        return {"name": name, "description": desc,
                "input_schema": {"type": "object",
                                 "properties": props or {},
                                 "required": required or []}}

    return [
        fn("neuro_bio_agent",
           "Физическое/ментальное состояние, готовность (Oura), нагрузка дня.",
           {"question": {"type": "string"}}),
        fn("decision_support_agent",
           "Стратегический мультилинзовый анализ и рекомендация по вопросу босса.",
           {"question": {"type": "string"}}, ["question"]),
        fn("medication_schedule",
           "Показать график приёма препаратов на сегодня."),
        fn("calendar_today",
           "Показать встречи из календаря на сегодня."),
        fn("esoteric_today",
           "Качество дня: астрология, нумерология, матрица судьбы + тайминги."),
        fn("save_daily_state",
           "Сохранить субъективное состояние босса (энергия/фокус/настроение 1-10, флаги).",
           {"energy": {"type": "integer"}, "focus": {"type": "integer"},
            "mood": {"type": "integer"}, "workout": {"type": "boolean"},
            "massage": {"type": "boolean"}, "alcohol": {"type": "boolean"}}),
        fn("add_medication",
           "Добавить препарат/добавку в график приёма.",
           {"name": {"type": "string"}, "dosage": {"type": "string"},
            "times": {"type": "array", "items": {"type": "string"},
                      "description": "времена приёма в формате HH:MM"},
            "days": {"type": "array", "items": {"type": "string"},
                     "description": ("дни недели: mon,tue,wed,thu,fri,sat,sun "
                                     "(или пн,вт,ср,чт,пт,сб,вс). Пусто = каждый день")},
            "with_food": {"type": "string", "enum": ["before", "with", "after", "any"]},
            "is_critical": {"type": "boolean"}},
           ["name", "times"]),
        fn("add_reminder",
           "Поставить напоминание о ЧЁМ УГОДНО (не таблетки). Разовое — через datetime; "
           "повторяющееся — через times (+ days).",
           {"title": {"type": "string"},
            "datetime": {"type": "string",
                         "description": ("разовое: 'YYYY-MM-DD HH:MM'. Посчитай из "
                                         "«через 2 часа»/«завтра»/«в субботу» по текущему времени")},
            "times": {"type": "array", "items": {"type": "string"},
                      "description": "повторяющееся: времена HH:MM"},
            "days": {"type": "array", "items": {"type": "string"},
                     "description": "дни недели mon..sun / пн..вс; пусто = каждый день"},
            "notes": {"type": "string"}},
           ["title"]),
        fn("list_reminders", "Показать активные напоминания."),
        fn("cancel_reminder", "Отменить напоминание по его номеру (id).",
           {"id": {"type": "integer"}}, ["id"]),
        fn("remember_fact",
           "Запомнить факт/предпочтение в долговременную память.",
           {"text": {"type": "string"}}, ["text"]),
        fn("recall", "Найти в памяти, что известно по теме или человеку.",
           {"query": {"type": "string"}}, ["query"]),
        fn("forget_fact", "Удалить факт из памяти по его номеру (id).",
           {"id": {"type": "integer"}}, ["id"]),
        fn("health_overview",
           "Обзор здоровья: последние анализы (с пометкой вне нормы) и ближайшие визиты."),
        fn("lab_trend",
           "Динамика одного показателя анализов во времени (тренд + норма).",
           {"marker": {"type": "string", "description": "название показателя, напр. «витамин D», «холестерин»"}},
           ["marker"]),
        fn("add_lab_result",
           "Добавить ОДИН показатель анализа вручную (когда называют числом, без бланка).",
           {"marker": {"type": "string"},
            "value": {"type": "number", "description": "числовое значение, если есть"},
            "value_text": {"type": "string", "description": "если значение не число: «отрицательно», «<0.5»"},
            "unit": {"type": "string"},
            "taken_on": {"type": "string", "description": "дата сдачи ГГГГ-ММ-ДД или ДД.ММ.ГГГГ; пусто = сегодня"},
            "ref_low": {"type": "number"}, "ref_high": {"type": "number"}},
           ["marker"]),
        fn("research_drug",
           "Ресёрч препарата/добавки: что это, как принимать, побочки и взаимодействия "
           "с текущими препаратами босса. Не медицинский совет.",
           {"query": {"type": "string"}}, ["query"]),
        fn("add_visit",
           "Записать визит к врачу (план).",
           {"date": {"type": "string", "description": "дата визита ГГГГ-ММ-ДД или ДД.ММ.ГГГГ"},
            "specialty": {"type": "string", "description": "кардиолог/стоматолог…"},
            "doctor": {"type": "string", "description": "ФИО/клиника, если назвали"},
            "reason": {"type": "string", "description": "повод"},
            "followup_date": {"type": "string", "description": "когда повторно, если известно"}}),
        fn("list_visits", "Показать визиты к врачам.",
           {"upcoming_only": {"type": "boolean", "description": "только предстоящие"}}),
        fn("complete_visit",
           "Закрыть визит как состоявшийся: что назначили и когда повторно.",
           {"id": {"type": "integer"}, "outcome": {"type": "string"},
            "followup_date": {"type": "string"}}, ["id"]),
        fn("add_contact", "Добавить человека в контакты.",
           {"name": {"type": "string"},
            "relation": {"type": "string", "description": "кто это: партнёр/друг/семья/клиент…"},
            "circle": {"type": "string", "enum": ["core", "close", "work", "extended"]},
            "birthday": {"type": "string", "description": "ГГГГ-ММ-ДД или ДД.ММ"},
            "interests": {"type": "string"},
            "language": {"type": "string", "description": "язык/национальность, напр. русский"},
            "touch_days": {"type": "integer", "description": "желаемый ритм касания, дней"},
            "notes": {"type": "string"}}, ["name"]),
        fn("find_contact", "Найти человека и показать карточку.",
           {"query": {"type": "string"}}, ["query"]),
        fn("update_contact",
           "Изменить данные существующего контакта (язык, отношение, круг, интересы, ритм, ДР, заметку).",
           {"query": {"type": "string", "description": "имя/ФИО для поиска"},
            "language": {"type": "string"}, "relation": {"type": "string"},
            "circle": {"type": "string", "enum": ["core", "close", "work", "extended"]},
            "interests": {"type": "string"}, "touch_days": {"type": "integer"},
            "birthday": {"type": "string"}, "notes": {"type": "string"}}, ["query"]),
        fn("list_contacts", "Показать список контактов."),
        fn("write_greeting", "Сгенерировать личное поздравление для человека.",
           {"name": {"type": "string"}, "occasion": {"type": "string"}}, ["name"]),
        fn("note_contacted", "Отметить, что сегодня общались с человеком.",
           {"name": {"type": "string"}}, ["name"]),
        fn("meeting_last",
           "Последняя разобранная встреча/переговоры в нужном формате (по её транскрипту).",
           {"format": {"type": "string",
                       "enum": ["protocol", "negotiation", "tasks", "email", "tldr"],
                       "description": ("protocol=протокол, negotiation=переговоры "
                                       "(кто что пообещал/договорённости/риски), "
                                       "tasks=задачи, email=письмо-итог, tldr=кратко")}}),
        fn("meeting_ask",
           "Ответить на вопрос по последней встрече (опираясь на её расшифровку).",
           {"question": {"type": "string"}}, ["question"]),
    ]


async def dispatch(services, name: str, args: dict, chat_id: int) -> str:
    try:
        if name == "neuro_bio_agent":
            return await neuro_bio.run(services, question=args.get("question"))
        if name == "decision_support_agent":
            return await decision_support.run(services, mode="adhoc", question=args.get("question", ""))
        if name == "medication_schedule":
            return await medication.schedule_text(services)
        if name == "calendar_today":
            from integrations import calendar
            return await calendar.schedule_text(services)
        if name == "esoteric_today":
            from agents import esoteric
            return await esoteric.day_quality(services)
        if name == "set_birth":
            # 🔒 Защита: натальные данные босса из чата НЕ меняем (была случайная перезапись).
            return ("Натальные данные босса меняются только командой /birth — это защита от "
                    "случайной перезаписи. Скажи Ане ввести: /birth ДД.ММ.ГГГГ ЧЧ:ММ Город.")
        if name == "save_daily_state":
            fields = {}
            for src, dst in (("energy", "energy_subjective"),
                             ("focus", "focus_subjective"),
                             ("mood", "mood_subjective")):
                if args.get(src) is not None:
                    fields[dst] = int(args[src])
            for src, dst in (("workout", "workout_done"),
                             ("massage", "massage_done"),
                             ("alcohol", "alcohol")):
                if args.get(src) is not None:
                    fields[dst] = bool(args[src])
            day = datetime.now(services.config.tz).date()
            await crud.upsert_daily_health(services.db, day, **fields)
            return "Сохранил состояние: " + ", ".join(f"{k}={v}" for k, v in fields.items())
        if name == "add_medication":
            days = _parse_days(args.get("days"))
            med = await crud.add_medication(
                services.db, name=args["name"], dosage=args.get("dosage"),
                schedule_times=args.get("times", []), days_of_week=days,
                with_food=args.get("with_food"),
                is_critical=bool(args.get("is_critical", False)))
            times = ", ".join(t.strftime("%H:%M") for t in med["schedule_times"]) or "без времени"
            when = ", ".join(_RU_DAYS[d] for d in days) if days else "каждый день"
            return f"Добавил: {med['name']} — {when} в {times}."
        if name == "add_reminder":
            dt = None
            raw = args.get("datetime")
            if raw:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
                    try:
                        dt = datetime.strptime(raw, fmt)
                        break
                    except ValueError:
                        pass
            days = _parse_days(args.get("days"))
            rem = await crud.add_reminder(
                services.db, title=args["title"], due_at=dt,
                schedule_times=args.get("times"), days_of_week=days, notes=args.get("notes"))
            if rem["due_at"]:
                return f"Поставил напоминание #{rem['id']}: {rem['title']} — {rem['due_at'].strftime('%d.%m %H:%M')}."
            if rem["schedule_times"]:
                t = ", ".join(x.strftime("%H:%M") for x in rem["schedule_times"])
                when = ", ".join(_RU_DAYS[d] for d in days) if days else "каждый день"
                return f"Поставил напоминание #{rem['id']}: {rem['title']} — {when} в {t}."
            return f"Поставил напоминание #{rem['id']}: {rem['title']} (уточни, когда напомнить)."
        if name == "list_reminders":
            from agents import reminders as _reminders
            return await _reminders.list_text(services)
        if name == "cancel_reminder":
            await crud.deactivate_reminder(services.db, int(args["id"]))
            return f"Отменил напоминание #{args['id']}."
        if name == "remember_fact":
            await crud.add_fact(services.db, args["text"], source="аня")
            return "Запомнил."
        if name == "recall":
            facts = await crud.search_facts(services.db, args.get("query", ""), limit=10)
            if not facts:
                return "В памяти ничего по этому запросу."
            return "🧠 ПОМНЮ:\n" + "\n".join(f"#{f['id']} {f['text']}" for f in facts)
        if name == "forget_fact":
            await crud.deactivate_fact(services.db, int(args["id"]))
            return f"Забыл #{args['id']}."
        if name == "add_contact":
            c = await crud.add_contact(
                services.db, name=args["name"], relation=args.get("relation"),
                circle=args.get("circle"), birthday=args.get("birthday"),
                interests=args.get("interests"), touch_days=args.get("touch_days"),
                language=args.get("language"), notes=args.get("notes"))
            extra = f" (ДР {c['birthday']})" if c.get("birthday") else ""
            return f"Добавил контакт: {c['name']}{extra}."
        if name == "update_contact":
            c = await crud.get_contact_by_name(services.db, args.get("query", ""))
            if not c:
                return f"Не нашёл контакт «{args.get('query','')}» — сначала добавь его (add_contact)."
            upd = await crud.update_contact(
                services.db, c["id"], language=args.get("language"),
                relation=args.get("relation"), circle=args.get("circle"),
                interests=args.get("interests"), touch_days=args.get("touch_days"),
                birthday=args.get("birthday"), notes=args.get("notes"))
            return f"Обновил контакт: {upd['name']}." if upd else "Нечего обновлять — укажи, что изменить."
        if name == "find_contact":
            cs = await crud.find_contacts(services.db, args.get("query", ""), 3)
            return "\n\n".join(network.card(c) for c in cs) if cs else "Не нашёл такого контакта."
        if name == "list_contacts":
            return await network.list_text(services)
        if name == "write_greeting":
            c = await crud.get_contact_by_name(services.db, args["name"])
            if not c:
                return f"Не нашёл контакт «{args['name']}»."
            return await network.write_greeting(services, c, args.get("occasion") or "день рождения")
        if name == "note_contacted":
            c = await crud.get_contact_by_name(services.db, args["name"])
            if not c:
                return f"Не нашёл контакт «{args['name']}»."
            await crud.set_last_contact(
                services.db, c["id"], datetime.now(services.config.tz).date().isoformat())
            return f"Отметил: сегодня общались с {c['name']}."
        if name == "health_overview":
            return await health.overview_text(services)
        if name == "lab_trend":
            return await health.trend_text(services, args.get("marker", ""))
        if name == "add_lab_result":
            taken = parse_date(args.get("taken_on")) or \
                datetime.now(services.config.tz).date().isoformat()
            panel_id = await crud.add_lab_panel(services.db, taken_on=taken, source="manual")
            rec = await crud.add_lab_result(
                services.db, panel_id, taken, args["marker"],
                value=args.get("value"), value_text=args.get("value_text"),
                unit=args.get("unit"), ref_low=args.get("ref_low"), ref_high=args.get("ref_high"))
            return "Записал анализ: " + health.result_line(rec)
        if name == "research_drug":
            return await health.research_drug(services, args.get("query", ""))
        if name == "add_visit":
            v = await crud.add_visit(
                services.db, visit_date=parse_date(args.get("date")),
                doctor=args.get("doctor"), specialty=args.get("specialty"),
                reason=args.get("reason"), followup_date=parse_date(args.get("followup_date")))
            return "Записал визит #%d:\n%s" % (v["id"], health.visit_line(v))
        if name == "list_visits":
            return await health.visits_text(services, upcoming_only=bool(args.get("upcoming_only")))
        if name == "complete_visit":
            await crud.update_visit(
                services.db, int(args["id"]), status="done",
                outcome=args.get("outcome"), followup_date=parse_date(args.get("followup_date")))
            return f"Визит #{args['id']} закрыт."
        if name == "meeting_last":
            return await communication.last_meeting_text(
                services, chat_id, fmt_key=args.get("format", "protocol"))
        if name == "meeting_ask":
            return await communication.ask_last_meeting(services, chat_id, args.get("question", ""))
        return f"Неизвестный инструмент: {name}"
    except Exception as e:
        log.error("Ошибка инструмента %s: %s", name, e)
        return f"Ошибка инструмента {name}: {e}"
