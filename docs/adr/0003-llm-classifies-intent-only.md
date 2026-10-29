# 0003 — LLM classifies intent only; answers come from the database

**Status:** Accepted

## Context
HR wants to ask pay questions in plain English, with a local model (Ollama, llama3.2 3B).
Common approaches are text-to-SQL, RAG over rows, or letting the model write the answer.
All of them let the model produce or influence numbers, and a wrong pay figure in front of
HR is worse than no answer.

## Decision
- The model only maps a question to a whitelisted `QueryIntent`
  (`org_summary | country_stats | job_title_stats | department_stats | unsupported` plus
  optional country / job title / department), using structured output and temperature 0.
- Its entities are untrusted. `IntentResolver` reads entities from the question text
  first; a model value is kept only if it is a known value and grounded in the question.
- `AnswerComposer` renders the answer from `InsightsService` results using templates.
- The UI shows the interpreted intent so the user can check what was answered.
- No RAG (the data is structured; retrieval cannot compute aggregates) and no agent loop
  (single-shot is faster, cheaper and predictable).

## Consequences
- ✅ No hallucinated figures, no SQL injection surface, fully unit-testable with a fake LLM.
- ✅ Model outages degrade one feature (HTTP 503), not the app.
- ❌ Only supported question shapes can be answered; others get a helpful hint.
- Evidence: real-model failures (dropped and invented entities) are pinned by regression
  tests; see docs/AI_USAGE.md.
