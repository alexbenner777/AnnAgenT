"""Общий контейнер зависимостей (DB, OpenAI, Oura, Mem0, bot, scheduler).

Создаётся один раз в main.py и передаётся агентам/инструментам/хендлерам —
чтобы не плодить глобальные переменные.
"""
import logging
import os

from config import Config
from database.db import Database
from memory.mem0_client import Mem0Memory
from integrations.oura import OuraClient

log = logging.getLogger("los.services")

try:
    from anthropic import AsyncAnthropic
except Exception:
    AsyncAnthropic = None

try:
    from openai import AsyncOpenAI
except Exception:  # пакет может быть не установлен на этапе каркаса
    AsyncOpenAI = None


class Services:
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.mem0 = Mem0Memory(config)
        self.oura = OuraClient(config.oura_access_token) if config.has_oura else None

        # «Мозги» — Claude (Anthropic)
        self.anthropic = None
        if config.has_anthropic and AsyncAnthropic is not None:
            # timeout + retries: если сервис медлит/перегружен — не виснем навсегда,
            # а ждём максимум 60с и до 3 раз повторяем (бот не «замирает»).
            self.anthropic = AsyncAnthropic(
                api_key=config.anthropic_api_key, timeout=60.0, max_retries=3)

        # OpenAI — только для Whisper (голос)
        self.openai = None
        if config.has_openai and AsyncOpenAI is not None:
            self.openai = AsyncOpenAI(api_key=config.openai_api_key)

        # выставляются позже в main.py
        self.bot = None
        self.scheduler = None
        self.orchestrator = None

    async def startup(self):
        await self.db.connect()
        if self.db.enabled:
            schema = os.path.join(os.path.dirname(__file__), "database", "schema_sqlite.sql")
            try:
                await self.db.init_schema(schema)
            except Exception as e:
                log.error("Ошибка инициализации схемы БД: %s", e)
        self._log_status()

    def _log_status(self):
        log.info(
            "LOS интеграции: Claude=%s | Voice/Whisper=%s | DB=%s | Oura=%s | Mem0=%s",
            "on" if self.anthropic else "OFF",
            "on" if self.openai else "OFF",
            self.config.db_path if self.db.enabled else "OFF",
            "on" if self.oura else "OFF",
            "on" if self.mem0.enabled else "OFF",
        )

    async def shutdown(self):
        try:
            if self.bot:
                await self.bot.session.close()
        except Exception:
            pass
        await self.db.close()
