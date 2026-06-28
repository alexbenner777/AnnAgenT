"""Обёртка над Mem0 (семантическая память). Полностью опциональна:
если ключа нет или пакет не установлен / версия не та — все методы no-op.
"""
import logging

log = logging.getLogger("los.mem0")

USER_ID = "boss_1"


class Mem0Memory:
    def __init__(self, config):
        self.enabled = False
        self.client = None
        if not config.has_mem0:
            return
        try:
            from mem0 import AsyncMemoryClient
            self.client = AsyncMemoryClient(api_key=config.mem0_api_key)
            self.enabled = True
            log.info("Mem0 подключён.")
        except Exception as e:
            log.warning("Mem0 недоступен (%s) → память отключена.", e)

    async def add(self, text: str, role: str = "user"):
        if not self.enabled:
            return
        try:
            await self.client.add(messages=[{"role": role, "content": text}], user_id=USER_ID)
        except Exception as e:
            log.warning("Mem0.add: %s", e)

    async def search(self, query: str, limit: int = 5) -> list:
        if not self.enabled:
            return []
        try:
            res = await self.client.search(query=query, user_id=USER_ID, limit=limit)
            # нормализуем разные форматы ответа в список строк
            items = res.get("results", res) if isinstance(res, dict) else res
            out = []
            for it in items or []:
                if isinstance(it, dict):
                    out.append(it.get("memory") or it.get("text") or str(it))
                else:
                    out.append(str(it))
            return out
        except Exception as e:
            log.warning("Mem0.search: %s", e)
            return []
