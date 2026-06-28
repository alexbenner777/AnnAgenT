"""Конфигурация LOS: читает переменные окружения (.env локально / Secrets на Replit)."""
import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv не обязателен в проде
    pass


def _get(name: str, default=None):
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass
class Config:
    # --- секреты ---
    telegram_bot_token: str = field(default_factory=lambda: _get("TELEGRAM_BOT_TOKEN"))
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))  # «мозги»
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY"))        # только Whisper (голос)
    oura_access_token: str = field(default_factory=lambda: _get("OURA_ACCESS_TOKEN"))
    database_url: str = field(default_factory=lambda: _get("DATABASE_URL"))  # задел под Postgres
    mem0_api_key: str = field(default_factory=lambda: _get("MEM0_API_KEY"))

    # Постоянное хранилище: файл SQLite (переживает перезапуск, без сервера)
    db_path: str = field(default_factory=lambda: _get("LOS_DB_PATH", "los_data.db"))

    # Google Календарь — секретная iCal-ссылка (можно задать командой /calendar)
    gcal_ics_url: str = field(default_factory=lambda: _get("GOOGLE_CALENDAR_ICS_URL"))

    # чат для проактивных сообщений (необязательно)
    proactive_chat_id: int = field(
        default_factory=lambda: int(_get("LOS_CHAT_ID")) if _get("LOS_CHAT_ID") else None
    )

    # --- модели ---
    # «Мозги» оркестратора и агентов — Claude. Точный ID Opus 4.8: claude-opus-4-8.
    anthropic_model: str = field(default_factory=lambda: _get("ANTHROPIC_MODEL", "claude-opus-4-8"))
    whisper_model: str = "whisper-1"            # голос → текст, OpenAI
    max_tokens: int = 1500
    # ВАЖНО: Opus 4.8 не принимает temperature / top_p / budget_tokens (вернёт 400) — не передаём.

    # --- ритм и пороги (из ТЗ §9) ---
    timezone_name: str = field(default_factory=lambda: _get("LOS_TIMEZONE", "Europe/Moscow"))
    morning_briefing_time: str = "07:00"
    evening_digest_time: str = "22:00"
    readiness_low_threshold: int = 65
    readiness_critical_threshold: int = 50
    medication_repeat_minutes: int = 15
    medication_max_reminders: int = 3
    medication_supply_low_days: int = 5

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_db(self) -> bool:
        return bool(self.database_url)

    @property
    def has_oura(self) -> bool:
        return bool(self.oura_access_token)

    @property
    def has_mem0(self) -> bool:
        return bool(self.mem0_api_key)


config = Config()
