"""Inline-клавиатуры: меню, ввод состояния (1–10 / да-нет), действия по препаратам."""
from datetime import datetime

from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton, WebAppInfo)

B = InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="📋 Брифинг", callback_data="menu:briefing"),
         B(text="🔋 Статус", callback_data="menu:status")],
        [B(text="💊 Таблетки", callback_data="menu:meds"),
         B(text="⏰ Напоминания", callback_data="menu:reminders")],
        [B(text="📅 Календарь", callback_data="menu:calendar"),
         B(text="👥 Люди", callback_data="menu:contacts")],
        [B(text="📝 Состояние", callback_data="menu:state"),
         B(text="❤️ Здоровье", callback_data="menu:health")],
        [B(text="❓ Помощь", callback_data="menu:help")],
    ])


# Главная ПОСТОЯННАЯ reply-панель (всегда внизу). Пары (подпись, action);
# action совпадает с menu:<action>, чтобы кнопка-текст и старое инлайн-меню
# вели в одно и то же место. Подписи — единственный источник правды.
MAIN_BUTTONS = [
    ("☀️ Брифинг", "briefing"), ("✍️ Состояние", "state"),
    ("❤️ Здоровье", "health"), ("⏰ Напоминания", "reminders"),
    ("📅 Календарь", "calendar"), ("👥 Люди", "contacts"),
    ("🔮 Качество дня", "day"), ("🌙 Итог дня", "digest"),
    ("🎙 Встречи", "meeting"), ("❓ Помощь", "help"),
]
MAIN_BUTTON_ACTIONS = {label: action for label, action in MAIN_BUTTONS}

# === Минимальная панель: 3 кнопки-ГРУППЫ. Внутри каждой — (подпись, action),
# где action понимает run_menu_action в handlers. Нажал группу → инлайн-подменю.
GROUPS = {
    "health": ("❤️ Здоровье", [
        ("✍️ Состояние", "state"),
        ("❤️ Анализы и здоровье", "health"),
        ("💊 Таблетки", "meds"),
    ]),
    "day": ("☀️ Мой день", [
        ("🔮 Качество дня", "day"),
        ("🌙 Итог дня", "digest"),
    ]),
    "work": ("📌 Дела и люди", [
        ("⏰ Напоминания", "reminders"),
        ("📅 Календарь", "calendar"),
        ("🎙 Встречи", "meeting"),
        ("👥 Люди", "contacts"),
    ]),
}
GROUP_BY_LABEL = {label: key for key, (label, _) in GROUPS.items()}

# Прямые кнопки панели (не группы): подпись → action для run_menu_action в handlers.
TASKS_BTN = "📋 Задачи"
DIRECT_ACTIONS = {TASKS_BTN: "now"}


def main_reply_kb() -> ReplyKeyboardMarkup:
    # Ряд 1 — Задачи (инбокс «что сейчас»); ряд 2 — Здоровье + Мой день; ряд 3 — Дела и люди.
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TASKS_BTN)],
            [KeyboardButton(text=GROUPS["health"][0]), KeyboardButton(text=GROUPS["day"][0])],
            [KeyboardButton(text=GROUPS["work"][0])],
        ],
        resize_keyboard=True, is_persistent=True,
        input_field_placeholder="Напиши или скажи голосом…")


def group_kb(group_key: str) -> InlineKeyboardMarkup:
    """Инлайн-подменю группы: её кнопки (по 2 в ряд) + «⬅️ Назад»."""
    _, items = GROUPS[group_key]
    rows, row = [], []
    for lbl, action in items:
        row.append(B(text=lbl, callback_data=f"grp:{action}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([B(text="⬅️ Назад", callback_data="grp:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def health_hub_kb() -> InlineKeyboardMarkup:
    """Под-меню домена «Здоровье»: таблетки и визиты (анализы — фото/PDF присылаются)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [B(text="💊 Таблетки на сегодня", callback_data="menu:meds")],
        [B(text="🩺 Визиты к врачам", callback_data="menu:visits")],
    ])


def scale_kb(field: str) -> InlineKeyboardMarkup:
    row1 = [B(text=str(i), callback_data=f"st:{field}:{i}") for i in range(1, 6)]
    row2 = [B(text=str(i), callback_data=f"st:{field}:{i}") for i in range(6, 11)]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def yesno_kb(field: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        B(text="✅ Да", callback_data=f"st:{field}:yes"),
        B(text="❌ Нет", callback_data=f"st:{field}:no")]])


def med_action_kb(med_id: int, scheduled: datetime) -> InlineKeyboardMarkup:
    ts = scheduled.strftime("%Y%m%d%H%M")
    return InlineKeyboardMarkup(inline_keyboard=[[
        B(text="✅ Принял", callback_data=f"med:taken:{med_id}:{ts}"),
        B(text="⏭ Пропустить", callback_data=f"med:skip:{med_id}:{ts}"),
        B(text="💤 +15м", callback_data=f"med:snooze:{med_id}:{ts}")]])


def esoteric_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        B(text="🔍 Расшифровка (почему так)", callback_data="eso:facts")]])


def morning_prompt_kb(web_app_url: str | None = None) -> InlineKeyboardMarkup:
    """Утренний промпт: кнопка открывает мини-апп на форме заполнения брифа."""
    rows = []
    if web_app_url:
        rows.append([B(text="📋 Заполнить бриф", web_app=WebAppInfo(url=web_app_url))])
    rows.append([B(text="✍️ Внести состояние вручную", callback_data="menu:state")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def briefing_kb(web_app_url: str | None = None) -> InlineKeyboardMarkup:
    """Под готовым брифом: открыть форму в мини-аппе + расшифровка качества дня."""
    rows = []
    if web_app_url:
        rows.append([B(text="📋 Открыть в мини-аппе", web_app=WebAppInfo(url=web_app_url))])
    rows.append([B(text="✍️ Внести состояние", callback_data="menu:state")])
    rows.append([B(text="🔍 Расшифровка (почему так)", callback_data="eso:facts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_action_kb(rem_id: int, scheduled: datetime) -> InlineKeyboardMarkup:
    ts = scheduled.strftime("%Y%m%d%H%M")
    return InlineKeyboardMarkup(inline_keyboard=[[
        B(text="✅ Сделал", callback_data=f"rem:taken:{rem_id}:{ts}"),
        B(text="⏭ Пропустить", callback_data=f"rem:skip:{rem_id}:{ts}"),
        B(text="💤 +15м", callback_data=f"rem:snooze:{rem_id}:{ts}")]])


def meeting_kb(meeting_id: int) -> InlineKeyboardMarkup:
    """Кнопки под разобранной встречей: форматы заметки + дела в напоминания + транскрипт."""
    from agents.communication import FORMATS
    items = list(FORMATS.items())
    rows, row = [], []
    for key, (label, _) in items:
        row.append(B(text=label, callback_data=f"comm:fmt:{key}:{meeting_id}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([B(text="🕵️ Разбор переговоров", callback_data=f"comm:nego:{meeting_id}")])
    rows.append([B(text="📌 Дела → напоминания", callback_data=f"comm:tasks:{meeting_id}")])
    rows.append([B(text="📄 Скачать транскрипт", callback_data=f"comm:tr:{meeting_id}")])
    rows.append([B(text="📤 Поделиться с участниками", callback_data=f"comm:share:{meeting_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
