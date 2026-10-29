# How AI was used

AI shows up in two places: as a **development collaborator** (an agentic coding assistant,
Claude Code) and as a **product feature** (a local Ollama model behind *Ask AI*). In both
cases the rule was the same: AI proposes, tests and real runs decide.

## 1. AI as a development collaborator

### Initial instruction
> Complete this assignment (docs/ASSIGNMENT.md) using TDD. Front end React + TypeScript,
> backend Python on uvicorn, AI via Ollama. Emphasise production quality, OO design,
> testing (TDD), simple/maintainable/scalable systems, Git hygiene and judgment over AI output.

### Workflow
1. **Requirements first** — one-page doc committed before any code.
2. **Inside-out, test-first slices** — domain (countries/FX) → repository → service →
   insights → AI → HTTP → seed → UI. For each slice: write tests, run them and watch them
   fail (red), implement the minimum to pass (green), lint/format, commit.
3. **Run the real thing** — after the backend was green, it was seeded with 10k rows, timed,
   and asked real questions through the real model. Two of the most important fixes came
   from this step, not from unit tests.
4. **Incremental commits** with messages explaining *why*.

### Where AI output was wrong — and how it was caught

| What happened | Caught by | Resolution |
|---|---|---|
| A commit was made while tests were failing: the shell chain `pytest | tail && git commit` checked `tail`'s exit code, not pytest's | Reading the output before moving on | Fixed, amended that local commit, and used `set -o pipefail` for every later commit command |
| Repository method named `list` shadowed the builtin, breaking `-> list[str]` annotations in the class body | Test collection error | Renamed to `search` (clearer anyway) |
| Test fixtures used `@acme.test` emails, which `email-validator` correctly rejects (reserved TLD) | Failing schema tests | Switched to `example.com` |
| `useMutation({ mutationFn: api.ask })` — React Query v5 passes a second argument, leaking into the API call | Failing UI test (`toHaveBeenCalledWith`) | Wrapped: `(q) => api.ask(q)` |
| **LLM hallucinations** in Ask AI (see below) | Running real questions against llama3.2 | Grounding design + regression tests |
| **Salary sort compared raw local amounts** — JPY/INR employees ranked as "highest paid" | End-to-end smoke test reading the actual data | Sort by USD equivalent in SQL + test + clearer UI label |

## 2. AI as a product feature (Ask AI)

### Design principle
The model is used **only to classify** a question into a whitelisted intent
(`org_summary | country_stats | job_title_stats | department_stats | unsupported` plus
optional country / job title / department). The backend runs the matching insight query and
renders the answer from a template. The model never sees salary data, never writes SQL and
never produces a number.

### Prompt (system)
Built at request time from live data so the model can only pick real values:
```
You translate HR questions about employee salaries into a JSON query. Reply with JSON only.

Choose "metric":
- "org_summary": overall headcount, total payroll or average pay for the whole company.
- "country_stats": pay statistics (min/max/average/median) for a country or comparing countries.
- "job_title_stats": pay for a job title / role, optionally within a country.
- "department_stats": pay or headcount per department, optionally within a country.
- "unsupported": the question is not about employee pay or headcount.

Set "country", "job_title" and "department" ONLY when the question explicitly names one;
otherwise leave them out. Use the exact spelling from these lists:
Countries: Australia, Brazil, ...
Job titles: Accountant, Account Executive, ...
Departments: Data, Engineering, ...
```
Sent with Ollama **structured outputs** (`format` = the intent's JSON schema) and
`temperature: 0`.

### What the real model got wrong (first run, llama3.2 3B)

| Question | Model output | Problem |
|---|---|---|
| "average salary of data analysts **in Germany**" | `job_title: Data Analyst` (no country) | Dropped an entity → answered for all countries |
| "software engineers in India" | `department: "IT/Software Development"` | Invented an unknown value → whole question rejected |
| "**which** department has the highest average pay?" | `department: "Marketing"` | Invented a filter → answered the wrong question |
| "What's the weather tomorrow?" | `org_summary` | No way to decline |

### Fix: trust the model for *what*, verify *which*
- Entities are first read **deterministically from the question** (known values,
  plural-tolerant, longest match wins, `US`/`UK`/`America` aliases).
- A model-supplied entity is kept only if it maps to a **known value** *and* shares a word
  with the question. Invented filters and unknown values are dropped.
- `unsupported` was added so the model can decline.

After the fix all 8 benchmark questions resolved correctly, each failure is pinned by a
regression test in `tests/unit/test_ask_service.py`, and those tests use a fake LLM, so they
stay fast and deterministic.

### Failure handling
If Ollama is down or slow, `/api/ask` returns **503** with a clear message. The UI explains it
and points to *Pay insights*, which needs no model. Nothing else depends on the LLM.
