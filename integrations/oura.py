"""Клиент Oura Ring API v2. Ошибки сети не валят бота — возвращаем то, что есть."""
import logging

import httpx

log = logging.getLogger("los.oura")

BASE = "https://api.ouraring.com/v2/usercollection"


class OuraClient:
    def __init__(self, token: str):
        self.token = token

    async def _get(self, path: str, params: dict):
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{BASE}/{path}", params=params, headers=headers)
            r.raise_for_status()
            return r.json()

    async def _latest(self, path: str, date_iso: str):
        try:
            data = await self._get(path, {"start_date": date_iso, "end_date": date_iso})
            items = data.get("data") or []
            return items[-1] if items else None
        except Exception as e:
            log.warning("Oura %s недоступен: %s", path, e)
            return None

    async def snapshot(self, day) -> dict:
        """Сводка за день: readiness, sleep, hrv, чсс. Пустые поля = нет данных."""
        date_iso = day.isoformat() if hasattr(day, "isoformat") else str(day)
        out = {}
        readiness = await self._latest("daily_readiness", date_iso)
        if readiness:
            out["readiness_score"] = readiness.get("score")
            contrib = readiness.get("contributors") or {}
            out["hrv_balance"] = contrib.get("hrv_balance")
        sleep = await self._latest("daily_sleep", date_iso)
        if sleep:
            out["sleep_score"] = sleep.get("score")
        return out
