"""Постоянное хранилище на SQLite (aiosqlite). Один файл, без сервера, переживает
перезапуск. Postgres — задел на будущее (через DATABASE_URL), пока не используется."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("los.db")

try:
    import aiosqlite
except Exception:
    aiosqlite = None


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = None

    @property
    def enabled(self) -> bool:
        return self.conn is not None

    async def connect(self):
        if aiosqlite is None:
            log.error("aiosqlite не установлен — данные не будут сохраняться!")
            return
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.commit()
        log.info("SQLite подключён: %s", self.path)

    async def init_schema(self, sql_path: str):
        if not self.enabled:
            return
        sql = Path(sql_path).read_text(encoding="utf-8")
        await self.conn.executescript(sql)
        await self.conn.commit()

    async def execute(self, q, *args):
        """INSERT/UPDATE/DELETE. Возвращает lastrowid (для вставок)."""
        cur = await self.conn.execute(q, args)
        await self.conn.commit()
        rid = cur.lastrowid
        await cur.close()
        return rid

    async def fetchone(self, q, *args):
        cur = await self.conn.execute(q, args)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, q, *args):
        cur = await self.conn.execute(q, args)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None
