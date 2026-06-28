"""Геокодинг города → координаты + таймзона (open-meteo, бесплатно, без ключа).
Нужен один раз при вводе данных рождения."""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger("los.geocode")


async def geocode(city: str):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://geocoding-api.open-meteo.com/v1/search",
                            params={"name": city, "count": 1, "language": "ru"})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        log.warning("geocode '%s': %s", city, e)
        return None
    res = data.get("results") or []
    if not res:
        return None
    g = res[0]
    return {
        "lat": g["latitude"], "lon": g["longitude"],
        "tz": g.get("timezone", "UTC"),
        "city": g.get("name", city),
        "country": g.get("country", ""),
    }
