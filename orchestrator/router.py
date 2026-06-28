"""Эвристический роутер — запасной вариант, когда OpenAI не настроен.
Когда LLM доступен, маршрутизацию делает сам оркестратор через function calling."""

_RULES = [
    (("таблет", "препарат", "лекарств", "приём", "прием", "витамин", "добавк"), "medication"),
    (("состоян", "готов", "устал", "энерг", "сон", "readiness", "нагрузк"), "neuro_bio"),
    (("стоит ли", "совет", "реши", "стратег", "анализ", "встреч"), "decision_support"),
]


def heuristic_route(text: str) -> str:
    low = (text or "").lower()
    for keys, target in _RULES:
        if any(k in low for k in keys):
            return target
    return "decision_support"
