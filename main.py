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
    logging.getLogger("httpx").setLevel(logging.WARNING)  # не светим секретные URL в логах

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

    from aiogram.types import ErrorEvent

    @dp.errors()
    async def _on_error(event: ErrorEvent):
        # Любая необработанная ошибка: пишем в лог и мягко отвечаем пользователю,
        # чтобы кнопка не «висела», а в чате не было тишины.
        log.exception("Ошибка обработки апдейта: %s", event.exception)
        upd = event.update
        try:
            if getattr(upd, "callback_query", None):
                await upd.callback_query.answer("Что-то пошло не так. Попробуй ещё раз.")
                if upd.callback_query.message:
                    await upd.callback_query.message.answer("⚠️ Не получилось. Попробуй ещё раз.")
            elif getattr(upd, "message", None):
                await upd.message.answer("⚠️ Ой, что-то пошло не так. Попробуй ещё раз или напиши иначе.")
        except Exception:
            pass
        return True

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
