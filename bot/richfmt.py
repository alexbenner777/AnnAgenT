"""Лёгкий markdown → Telegram-HTML (ограниченный набор тегов) + сворачиваемая
заметка через <blockquote expandable> — современная «фишка» Telegram, без сторонних
пакетов. Заметки по встречам приходят от Claude в markdown; здесь превращаем их
в аккуратный вид для телефона."""
from __future__ import annotations

import html
import re

_DIVIDER = re.compile(r"^[-—–*_=]{3,}$")          # строка-разделитель: ---, ***, ===
_HEADER = re.compile(r"^#{1,6}\s+(.*)$")           # ## Заголовок
_BULLET = re.compile(r"^[-*+]\s+(.*)$")            # - пункт / * пункт
_NUM = re.compile(r"^(\d+)\.\s+(.*)$")             # 1. пункт
_CHECK = re.compile(r"^\[([ xX])\]\s*(.*)$")       # [ ] / [x] чекбокс


def _inline(s: str) -> str:
    """Экранируем HTML, затем включаем безопасные **жирный** и `код`."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md_to_tg_html(md: str) -> str:
    """markdown → HTML, который понимает обычное сообщение Telegram (parse_mode=HTML).
    Заголовки → <b>, списки → «• », чекбоксы → ☐/☑, разделители опускаем."""
    out: list[str] = []
    for raw in (md or "").split("\n"):
        line = raw.rstrip()
        s = line.strip()
        if not s:
            out.append("")
            continue
        if _DIVIDER.match(s):
            continue
        h = _HEADER.match(s)
        if h:
            out.append(f"<b>{_inline(h.group(1))}</b>")
            continue
        indent = "  " * ((len(line) - len(line.lstrip())) // 2)
        b = _BULLET.match(s)
        if b:
            content = b.group(1)
            chk = _CHECK.match(content)
            if chk:
                box = "☑" if chk.group(1).lower() == "x" else "☐"
                out.append(f"{indent}{box} {_inline(chk.group(2))}")
            else:
                out.append(f"{indent}• {_inline(content)}")
            continue
        n = _NUM.match(s)
        if n:
            out.append(f"{indent}{n.group(1)}. {_inline(n.group(2))}")
            continue
        out.append(_inline(s))
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def expandable_note(header: str, body_md: str) -> str:
    """Свёрнутая заметка: тапнул — раскрылась. header виден всегда (первая строка)."""
    body = md_to_tg_html(body_md)
    inner = f"<b>{html.escape(header)}</b>\n{body}" if header else body
    return f"<blockquote expandable>{inner}</blockquote>"
