"""Эпизодическая память — лог реплик в conversation_episodes. Best-effort."""
import logging

log = logging.getLogger("los.episodic")


async def log_turn(services, role: str, content: str, agent: str = None):
    db = services.db
    if not db.enabled:
        return
    try:
        from datetime import datetime
        ts = datetime.now(services.config.tz).strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            """INSERT INTO conversation_episodes(role, content, agent_involved, created_at)
               VALUES(?,?,?,?)""", role, content, agent, ts)
    except Exception as e:
        log.debug("episodic.log_turn: %s", e)


async def recent_turns(services, limit: int = 8) -> list:
    """Последние реплики диалога (краткосрочная память оркестратора), в хронологии."""
    db = services.db
    if not db.enabled:
        return []
    try:
        rows = await db.fetchall(
            "SELECT role, content FROM conversation_episodes ORDER BY id DESC LIMIT ?", limit)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    except Exception as e:
        log.debug("episodic.recent_turns: %s", e)
        return []
