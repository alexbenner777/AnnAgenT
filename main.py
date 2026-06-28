"""Точка входа LOS: поднимает сервисы, Telegram-бот (polling) и планировщик."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from services import Services
from bot.handlers import build_router
from scheduler.jobs import setup_scheduler


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("los")

    if not config.telegram_bot_token:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN не задан. Заполни .env (см. .env.example).")

    services = Services(config)
    await services.startup()

    bot = Bot(token=config.telegram_bot_token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    services.bot = bot

    from orchestrator.master import MasterOrchestrator
    services.orchestrator = MasterOrchestrator(services)

    dp = Dispatcher()
    dp.include_router(build_router(services))

    scheduler = setup_scheduler(services)
    services.scheduler = scheduler
    scheduler.start()

    log.info("✅ LOS запущен. Жду сообщений в Telegram…")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await services.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
