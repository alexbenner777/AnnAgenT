"""Базовый помощник для агентов: один вызов Claude с системным промтом.
Возвращает None, если Claude не настроен — тогда агент использует свой fallback.

NB: Opus 4.8 не принимает temperature/top_p/budget_tokens — параметры не передаём."""
from __future__ import annotations

import logging

log = logging.getLogger("los.agent")


async def chat(services, system: str, user: str, max_tokens: int = 1000) -> str | None:
    if not services.anthropic:
        return None
    try:
        resp = await services.anthropic.messages.create(
            model=services.config.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")
    except Exception as e:
        log.error("Claude ошибка: %s", e)
        return None
