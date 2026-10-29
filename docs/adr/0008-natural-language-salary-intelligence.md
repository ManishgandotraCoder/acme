# 0008 — Natural-language salary intelligence over allow-listed analytics

**Status:** Accepted. Extends [0003](0003-llm-classifies-intent-only.md).

## Context
Answering "how does the org pay people?" is one of the two core capabilities, not an add-on
to CRUD (docs/REQUIREMENTS.md). HR asks about overviews, departments, countries, pay equity
between levels, outliers, trends and distributions, and needs answers they can verify and
reproduce. The questions are quantitative; the data holds personal salaries.

Options considered:
- **Text-to-SQL**: flexible, but the model writes queries against personal data, results
  can't be reproduced or reviewed, and a wrong join is a confident wrong number.
- **LLM explains verified results** (aggregates sent back to the model for prose): reads
  well, but lets the model restate or round a number wrongly in the final answer.
- **RAG**: suited to documents (salary-revision policy, band guidelines), none of which is
  in scope; it adds an index and an embedding model for no in-scope question.
- **Allow-listed analytics operations** (chosen).

## Decision
- The model only **selects** one of nine operations (`org_summary`, `country_stats`,
  `job_title_stats`, `department_stats`, `level_stats`, `salary_bands`, `outliers`,
  `above_department_average`, `salary_trends`) and its entity lists, via a strict JSON
  schema. It never sees salary rows, never writes SQL and never writes the answer.
- **Parameters are verified** against known values; entities named in the question win over
  the model's, a span of text names one value, and "median" is read from the question.
- Each operation is a **read-only SQL aggregate** in the insights module, index-backed and
  covered by the query-plan tests.
- **Answers are templates** filled from results, returned with the rows as a typed table, a
  chart spec for comparisons, the **data scope** (population, currency basis, FX date, rules)
  and follow-up suggestions. Ambiguous questions get a **clarifying question**; unsupported
  ones a decline with examples.
- **Comparable means comparable.** Cross-country figures use the stored USD equivalent at
  the dated FX rate. Level gaps compare the same job title in the same country one level
  apart (an org-wide median per level mostly measures which countries each level is in).
  Outliers are measured against peers with the same title, level and country, in local
  currency.
- **Privacy.** Operations that name individuals require the `view_individual_pay`
  permission (403 / a "forbidden" answer without it). Without it, pay for groups smaller than
  3 people is hidden, because the average of one person is their salary. The actor comes from
  one seam (`app/core/actor.py`) that SSO would fill.
- **Providers.** Ollama (local, nothing leaves the machine) is the default; Claude and OpenAI
  are offered when their API key is configured and can be chosen per question. The provider
  changes understanding quality, never the numbers.
- **Success criterion is executable.** `tests/benchmark` verifies 11 predefined questions
  against an oracle computed from the seed generator's output; `make benchmark-llm` checks a
  real model selects the expected operations.

## Consequences
- ✅ Every number is reproducible and traceable to a SQL aggregate; hallucinated figures are
  impossible by construction. Swapping or adding a model provider can't change an answer.
- ✅ New question types are a reviewed change: an operation, a template, a plan test and a
  benchmark question.
- ❌ Questions outside the nine operations get "unsupported", even if SQL could answer them.
  That's the price of reproducibility; the decline lists what *can* be asked.
- ❌ Templated prose is plainer than model-written prose.
- ⚠️ Small models make new mistakes on new questions. Each one found on real runs is pinned by
  a regression test (docs/AI_USAGE.md); `make benchmark-llm` re-checks understanding per
  provider.
