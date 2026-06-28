"""Inline-клавиатуры: меню, ввод состояния (1–10 / да-нет), действия по препаратам."""
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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


def reminder_action_kb(rem_id: int, scheduled: datetime) -> InlineKeyboardMarkup:
    ts = scheduled.strftime("%Y%m%d%H%M")
    return InlineKeyboardMarkup(inline_keyboard=[[
        B(text="✅ Сделал", callback_data=f"rem:taken:{rem_id}:{ts}"),
        B(text="⏭ Пропустить", callback_data=f"rem:skip:{rem_id}:{ts}"),
        B(text="💤 +15м", callback_data=f"rem:snooze:{rem_id}:{ts}")]])
