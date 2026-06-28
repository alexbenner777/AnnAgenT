"""Ночная рефлексия — «учится во сне».
Раз в сутки перечитывает реплики дня и сам вытаскивает стойкие факты/предпочтения
в долговременную память, чтобы Ане не нужно было каждый раз говорить «запомни»."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from database import crud

log = logging.getLogger("los.reflection")

SYSTEM = """Ты — модуль памяти LOS. Из реплик за день вытащи СТОЙКИЕ факты и
предпочтения, которые полезно помнить в будущем (о боссе, людях, здоровье, работе,
привычках). Игнорируй разовое/сиюминутное и то, что уже известно.
Категории: preference / health / relationship / work / other.
Верни ТОЛЬКО JSON-массив: [{"text": "...", "category": "..."}]. Нечего — верни []."""


def _parse_array(s: str) -> list:
    s = s.strip()
    i, j = s.find("["), s.rfind("]")
    if i == -1 or j == -1:
        return []
    try:
        data = json.loads(s[i:j + 1])
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def reflect(services) -> int:
    """Возвращает число добавленных фактов."""
    if not services.anthropic:
        return 0
    db = services.db
    since = (datetime.now(services.config.tz) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    rows = await db.fetchall(
        "SELECT role, content FROM conversation_episodes WHERE created_at >= ? ORDER BY id", since)
    if not rows:
        return 0

    convo = "\n".join(f"{r['role']}: {r['content']}" for r in rows)[:12000]
    known = [f["text"] for f in await crud.list_facts(db, 100)]
    known_lower = {k.lower() for k in known}
    known_str = "\n".join(f"- {k}" for k in known) or "(пусто)"

    try:
        resp = await services.anthropic.messages.create(
            model=services.config.anthropic_model, max_tokens=1000,
            system=SYSTEM,
            messages=[{"role": "user",
                       "content": f"УЖЕ ИЗВЕСТНО:\n{known_str}\n\nРЕПЛИКИ ЗА ДЕНЬ:\n{convo}"}])
        txt = "".join(b.text for b in resp.content if b.type == "text")
    except Exception as e:
        log.error("reflect LLM: %s", e)
        return 0

    added = 0
    for f in _parse_array(txt):
        t = (f.get("text") or "").strip() if isinstance(f, dict) else ""
        if t and t.lower() not in known_lower:
            await crud.add_fact(db, t, category=f.get("category"), source="рефлексия")
            known_lower.add(t.lower())
            added += 1
    log.info("Рефлексия: добавлено фактов: %d", added)
    return added
