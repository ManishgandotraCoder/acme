from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# The allow-list of analytics operations the model may choose from.
Metric = Literal[
    "org_summary",
    "country_stats",
    "job_title_stats",
    "department_stats",
    "level_stats",
    "salary_bands",
    "outliers",
    "above_department_average",
    "salary_trends",
]
MetricChoice = Literal[Metric, "unsupported"]
Statistic = Literal["average", "median"]
AnswerKind = Literal["answer", "clarification", "unsupported", "forbidden"]


class QueryIntent(BaseModel):
    """A validated, allow-listed query. The only thing the LLM is allowed to influence."""

    metric: MetricChoice
    countries: list[str] = []
    job_titles: list[str] = []
    departments: list[str] = []
    statistic: Statistic = "average"


class ModelIntent(BaseModel):
    """The JSON the model must produce. Strict (every field required, nothing extra) so every
    provider's structured-output mode accepts its schema."""

    model_config = ConfigDict(extra="forbid")

    metric: MetricChoice
    countries: list[str]
    job_titles: list[str]
    departments: list[str]
    statistic: Statistic


class ParsedIntent(BaseModel):
    """Lenient parse of what the model actually returned; the resolver verifies the rest."""

    metric: MetricChoice
    countries: list[str] = []
    job_titles: list[str] = []
    departments: list[str] = []


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: Annotated[str, Field(min_length=3, max_length=500)]
    # Which configured model provider classifies the question; the default when omitted.
    provider: str | None = None


class Column(BaseModel):
    key: str
    label: str
    # usd / local: money (local uses the row's "currency"); percent: signed change.
    format: Literal["text", "number", "usd", "local", "percent"] = "text"


class Table(BaseModel):
    columns: list[Column]
    rows: list[dict]


class Chart(BaseModel):
    type: Literal["bar"] = "bar"
    x: str
    y: str
    label: str


class AskResult(BaseModel):
    question: str
    kind: AnswerKind
    answer: str
    intent: QueryIntent
    table: Table | None = None
    chart: Chart | None = None
    # What the numbers cover: population, currency basis, FX date, privacy rules applied.
    scope: str | None = None
    # Follow-up questions the assistant can answer (clarification options, alternatives).
    suggestions: list[str] = []
    provider: str | None = None
