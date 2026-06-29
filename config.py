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
    # 🎙 Communication: транскрипция встреч. ElevenLabs Scribe лучше понимает русский;
    # если ключа нет — откат на OpenAI Whisper (он уже есть для голоса).
    elevenlabs_api_key: str = field(default_factory=lambda: _get("ELEVENLABS_API_KEY"))
    transcription_provider_raw: str = field(default_factory=lambda: _get("TRANSCRIPTION_PROVIDER"))

    # Постоянное хранилище: файл SQLite (переживает перезапуск, без сервера)
    db_path: str = field(default_factory=lambda: _get("LOS_DB_PATH", "los_data.db"))

    # Google Календарь — секретная iCal-ссылка (можно задать командой /calendar)
    gcal_ics_url: str = field(default_factory=lambda: _get("GOOGLE_CALENDAR_ICS_URL"))

    # Локальный Bot API сервер (для записей встреч >20МБ, до 2ГБ). Нужны api_id/api_hash
    # с my.telegram.org И запущенный telegram-bot-api (Docker). Пока creds сохранены,
    # но сервер не поднят → telegram_api_base пуст → бот работает на облачном API (лимит 20МБ).
    telegram_api_id: str = field(default_factory=lambda: _get("TELEGRAM_API_ID"))
    telegram_api_hash: str = field(default_factory=lambda: _get("TELEGRAM_API_HASH"))
    telegram_api_base: str = field(
        default_factory=lambda: (_get("TELEGRAM_API_BASE") or "").rstrip("/"))
    telegram_local_mode: bool = field(default_factory=lambda: _get("TELEGRAM_LOCAL_MODE") == "1")

    # чат для проактивных сообщений (необязательно)
    proactive_chat_id: int = field(
        default_factory=lambda: int(_get("LOS_CHAT_ID")) if _get("LOS_CHAT_ID") else None
    )

    # 🔒 Владелец(ы): Telegram user id через запятую — бот пускает ТОЛЬКО их.
    # Свой id можно узнать у @userinfobot. Если пусто — берём из LOS_CHAT_ID.
    owner_ids_raw: str = field(default_factory=lambda: _get("LOS_OWNER_IDS"))

    # --- модели ---
    # «Мозги» оркестратора и агентов — Claude. Точный ID Opus 4.8: claude-opus-4-8.
    anthropic_model: str = field(default_factory=lambda: _get("ANTHROPIC_MODEL", "claude-opus-4-8"))
    whisper_model: str = "whisper-1"            # голос → текст, OpenAI
    openai_transcribe_model: str = field(default_factory=lambda: _get("OPENAI_TRANSCRIBE_MODEL", "whisper-1"))
    elevenlabs_stt_model: str = field(default_factory=lambda: _get("ELEVENLABS_STT_MODEL", "scribe_v1"))
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
    def owner_ids(self) -> set:
        """Допущенные Telegram id. Источник: LOS_OWNER_IDS (+ LOS_CHAT_ID как запасной).
        Пусто = бот закрыт для всех (fail-closed)."""
        ids = set()
        if self.owner_ids_raw:
            for part in self.owner_ids_raw.replace(";", ",").split(","):
                part = part.strip()
                if part.lstrip("-").isdigit():
                    ids.add(int(part))
        if self.proactive_chat_id:
            ids.add(int(self.proactive_chat_id))
        return ids

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def has_local_api(self) -> bool:
        """Поднят ли локальный Bot API сервер (тогда можно качать файлы до 2 ГБ)."""
        return bool(self.telegram_api_base)

    @property
    def transcription_provider(self) -> str:
        """Какой движок распознавания речи для встреч. Авто: ElevenLabs, если есть
        ключ (лучше для русского), иначе OpenAI Whisper."""
        if self.transcription_provider_raw:
            return self.transcription_provider_raw.strip().lower()
        return "elevenlabs" if self.has_elevenlabs else "openai"

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
