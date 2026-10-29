"""Answer plain-English pay questions.

Pipeline: build a grounded prompt -> LLM classifies the question (structured output) ->
``IntentResolver`` verifies it -> ``AnswerComposer`` answers from the database. The LLM can
never invent a salary figure or run arbitrary queries.
"""

from sqlalchemy.orm import Session

from app.modules.assistant.answers import AnswerComposer
from app.modules.assistant.intent import IntentResolver, Vocabulary
from app.modules.assistant.llm import LLMClient
from app.modules.assistant.prompt import build_system_prompt
from app.modules.assistant.schemas import AskResult, ModelIntent
from app.modules.employees.repository import EmployeeRepository
from app.modules.insights.service import InsightsService
from app.shared.countries import SUPPORTED_COUNTRIES


class AskService:
    def __init__(self, session: Session, llm: LLMClient) -> None:
        repo = EmployeeRepository(session)
        self._llm = llm
        self._vocabulary = Vocabulary(
            countries=[c.name for c in SUPPORTED_COUNTRIES],
            job_titles=repo.distinct_job_titles(),
            departments=repo.distinct_departments(),
        )
        self._resolver = IntentResolver(self._vocabulary)
        self._composer = AnswerComposer(InsightsService(session), self._vocabulary.countries)

    def ask(self, question: str) -> AskResult:
        raw = self._llm.complete_json(
            build_system_prompt(self._vocabulary), question, ModelIntent.model_json_schema()
        )
        intent = self._resolver.resolve(raw, question)
        answer, data = self._composer.compose(intent)
        return AskResult(question=question, answer=answer, intent=intent, data=data)
