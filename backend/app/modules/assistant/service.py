"""Answer plain-English pay questions.

Pipeline: build a grounded prompt -> LLM selects an allow-listed analytics operation
(structured output) -> ``IntentResolver`` verifies its parameters -> ``AnswerComposer`` runs the
read-only query and renders the answer, table, chart and scope. The LLM can never invent a
salary figure, run arbitrary queries or see salary data.
"""

from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from app.core.actor import Actor
from app.modules.assistant.answers import AnswerComposer
from app.modules.assistant.intent import IntentResolver, Vocabulary
from app.modules.assistant.llm import LLMClient
from app.modules.assistant.prompt import build_system_prompt
from app.modules.assistant.schemas import AskResult, ModelIntent
from app.modules.employees.repository import EmployeeRepository
from app.modules.insights.service import InsightsService
from app.shared.countries import SUPPORTED_COUNTRIES

INTENT_SCHEMA = ModelIntent.model_json_schema()


class AskService:
    def __init__(
        self,
        session: Session,
        llm: LLMClient,
        *,
        actor: Actor,
        today: Callable[[], date] = date.today,
        provider: str | None = None,
    ) -> None:
        repo = EmployeeRepository(session)
        self._llm = llm
        self._provider = provider
        self._vocabulary = Vocabulary(
            countries=[c.name for c in SUPPORTED_COUNTRIES],
            job_titles=repo.distinct_job_titles(),
            departments=repo.distinct_departments(),
        )
        self._resolver = IntentResolver(self._vocabulary)
        self._composer = AnswerComposer(
            InsightsService(session), self._vocabulary, actor=actor, today=today
        )

    def ask(self, question: str) -> AskResult:
        raw = self._llm.complete_json(
            build_system_prompt(self._vocabulary), question, INTENT_SCHEMA
        )
        intent = self._resolver.resolve(raw, question)
        composed = self._composer.compose(intent, question)
        return AskResult(
            question=question,
            intent=intent,
            provider=self._provider,
            kind=composed.kind,
            answer=composed.answer,
            table=composed.table,
            chart=composed.chart,
            scope=composed.scope,
            suggestions=composed.suggestions,
        )
