"""Master Orchestrator — ReAct через Claude (Anthropic tool use).
Думает → вызывает инструмент(ы) агентов → анализирует → отвечает Ане по-русски.

NB: Opus 4.8 не принимает temperature/top_p/budget_tokens — не передаём.
block.input у Anthropic уже распарсен в dict (json.loads не нужен)."""
import logging
from datetime import datetime

from database import crud
from memory import episodic
from orchestrator import tools as toolmod
from orchestrator.router import heuristic_route

log = logging.getLogger("los.orchestrator")

SYSTEM = """Ты — Master Orchestrator системы LOS (Life Operating System).
Получаешь запросы от Ани (Chief of Staff) и координируешь специализированных агентов.

ПРИНЦИПЫ:
1. Работай по ReAct: думай → вызови инструмент → проанализируй → реши следующий шаг.
2. Решение всегда за человеком. Ты анализируешь и рекомендуешь.
3. Отвечай ТОЛЬКО на русском. Конкретно: вместо «возможно» — «рекомендую».
4. Используй контекст из памяти, если он передан.

МАРШРУТИЗАЦИЯ (через инструменты):
- состояние/расписание/энергия → neuro_bio_agent
- стратегия/«стоит ли»/анализ ситуации → decision_support_agent
- таблетки/препараты: показать график → medication_schedule, добавить → add_medication
- встречи/календарь/«что у меня сегодня» → calendar_today
- напомнить о чём угодно / «напомни …» → add_reminder; показать → list_reminders; отменить → cancel_reminder
- ввод состояния (энергия/фокус/настроение) → save_daily_state
- «запомни …» → remember_fact; «что ты знаешь про …»/вспомнить → recall; забыть → forget_fact
- контакты/люди/дни рождения/поздравления → add_contact / find_contact / list_contacts / write_greeting / note_contacted
- качество дня/астрология/нумерология/матрица → esoteric_today; данные рождения → set_birth
- здоровье/анализы (обзор) → health_overview; динамика показателя → lab_trend; один показатель числом → add_lab_result; про препарат/витамин/взаимодействия → research_drug
- визиты к врачам: записать → add_visit, показать → list_visits, закрыть с итогом → complete_visit
- переговоры → communication_agent (Фаза 2)
ВАЖНО: бланк анализов присылают фото/PDF — он разбирается отдельно, не через тебя; ты по тексту даёшь обзор/тренд/ресёрч и пишешь про визиты.

ФОРМАТ: кратко, структурно, максимум 3-4 абзаца, без «Конечно!».
При критическом алерте — сначала алерт, потом детали."""

MAX_STEPS = 5


class MasterOrchestrator:
    def __init__(self, services):
        self.services = services

    async def handle(self, user_text: str, chat_id: int) -> str:
        s = self.services
        if not s.anthropic:
            return await self._fallback(user_text)

        now_local = datetime.now(s.config.tz).strftime("%Y-%m-%d %H:%M (%A)")
        system = (SYSTEM + f"\n\nСЕЙЧАС (МСК): {now_local}. От этого считай «через N минут/часов», "
                  "«завтра», «в субботу» → конкретные дата-время для add_reminder.")
        facts = await crud.recall_for_context(s.db, user_text, limit=8)
        if facts:
            system += "\n\nЧТО Я ЗНАЮ (память):\n" + "\n".join(f"- {f}" for f in facts)

        messages = [{"role": "user", "content": user_text}]
        tools = toolmod.tool_specs()

        for _ in range(MAX_STEPS):
            try:
                resp = await s.anthropic.messages.create(
                    model=s.config.anthropic_model,
                    max_tokens=s.config.max_tokens,
                    system=system,
                    messages=messages,
                    tools=tools,
                )
            except Exception as e:
                log.error("Claude ошибка оркестратора: %s", e)
                return "⚠️ Ошибка обращения к Claude. Попробуй ещё раз позже."

            if resp.stop_reason == "refusal":
                return "Не могу помочь с этим запросом."

            if resp.stop_reason == "tool_use":
                # вернуть ассистентский ход (с tool_use-блоками) и результаты инструментов
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        result = await toolmod.dispatch(s, block.name, block.input or {}, chat_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)[:6000],
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            # финальный ответ
            text = "".join(b.text for b in resp.content if b.type == "text")
            await episodic.log_turn(s, "user", user_text)
            await episodic.log_turn(s, "assistant", text or "")
            return text or "…"

        return "Не удалось собрать ответ за несколько шагов — переформулируй запрос."

    async def _fallback(self, user_text: str) -> str:
        """Без Claude: простая эвристическая маршрутизация."""
        from agents import neuro_bio, medication, decision_support
        target = heuristic_route(user_text)
        if target == "medication":
            return await medication.schedule_text(self.services)
        if target == "neuro_bio":
            return await neuro_bio.run(self.services)
        if target == "decision_support":
            return await decision_support.run(self.services, mode="adhoc", question=user_text)
        return ("⚠️ Claude не настроен — понимаю только команды: "
                "/briefing, /status, /meds, /state.\n"
                "Добавь ANTHROPIC_API_KEY в .env для свободного текста и голоса.")
