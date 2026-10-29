from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Metric = Literal["org_summary", "country_stats", "job_title_stats", "department_stats"]


class QueryIntent(BaseModel):
    """A validated, whitelisted query. The only thing the LLM is allowed to influence."""

    metric: Metric | Literal["unsupported"]
    country: str | None = None
    job_title: str | None = None
    department: str | None = None


class ModelIntent(QueryIntent):
    """Raw shape the model must produce; its JSON schema is sent to Ollama."""


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: Annotated[str, Field(min_length=3, max_length=500)]


class AskResult(BaseModel):
    question: str
    answer: str
    intent: QueryIntent
    data: list[dict]
