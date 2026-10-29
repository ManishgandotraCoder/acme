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
5. **Restructure under test:** when asked to structure the code like a senior architect, the
   agent moved to a modular monolith in behaviour-preserving steps (pure move, then error
   hierarchy, assistant split, migrations, observability), with the full suite green after
   each step. It then added architecture tests so the structure can't erode.
6. **Standing instructions** for the agent live in [CLAUDE.md](../CLAUDE.md), built from the
   mistakes below.

### Where AI output was wrong — and how it was caught

| What happened | Caught by | Resolution |
|---|---|---|
| A commit was made while tests were failing: the shell chain `pytest | tail && git commit` checked `tail`'s exit code, not pytest's | Reading the output before moving on | Fixed, amended that local commit, and used `set -o pipefail` for every later commit command |
| Repository method named `list` shadowed the builtin, breaking `-> list[str]` annotations in the class body | Test collection error | Renamed to `search` (clearer anyway) |
| Test fixtures used `@acme.test` emails, which `email-validator` correctly rejects (reserved TLD) | Failing schema tests | Switched to `example.com` |
| `useMutation({ mutationFn: api.ask })` — React Query v5 passes a second argument, leaking into the API call | Failing UI test (`toHaveBeenCalledWith`) | Wrapped: `(q) => api.ask(q)` |
| **LLM hallucinations** in Ask AI (see below) | Running real questions against llama3.2 | Grounding design + regression tests |
| **Salary sort compared raw local amounts** — JPY/INR employees ranked as "highest paid" | End-to-end smoke test reading the actual data | Sort by USD equivalent in SQL + test + clearer UI label |
| Two hidden boundary violations after the restructure (`core` importing the assistant's `LLMClient` and the employee models) | The new architecture tests, on their first run | LLM DI moved into the assistant module; table registration moved to the composition root |
| SQLite WAL/SHM sidecar files had been committed (`.gitignore` covered `*.db` only) | Reviewing `git status` during the restructure | Untracked and ignored |
| **Pay gap between levels compared org-wide medians**: on seeded data, Principals "earned 1.5% less" than Leads, because a level's median mostly reflects which countries its people are in | Running the new analytics on the 10k seed and reading the numbers | Like-for-like gaps (same title and country, one level apart) + a regression test with the confounded case |
| Seed data too clean: nobody far from their peers (outlier question always "nobody") and Principal salaries capped at the band top | Same real run | Evenly spaced level bands, ~1% off-band salaries, tests on both |
| A role question about "wizards" in Germany was answered as "Data Analyst in Germany: …" because Germany has one title, as if a role had been matched | A regression test written for the dropped-title case | The single-role format only applies when the question named a role |
| Query-plan check passed or failed depending on test order: `enable_sort=off` doesn't disable *incremental* sorts, and dead rows from another test's rolled-back insert changed the planner's size estimates | The new benchmark running before the plan tests | Disable incremental sorts too + a regression test that reproduces the bloat |
| Anthropic SDK 2.x runs on `httpx2`; the test fakes used `httpx` | `TypeError` in the adapter tests | Fakes built with `httpx2.MockTransport` (per the SDK's upgrade notes) |
| The level chart plotted org-wide medians (Principal below Lead) under a headline saying every level earns more; key columns scrolled off the chat table | Screenshots of the real UI in Chrome | Chart the like-for-like gap; key columns first |
| Chat charts pulled recharts into every page's bundle (280 kB gzipped, from 170 kB) | Measuring the build output while updating a docs claim | Lazy-load the chart view |

## 2. AI as a product feature (Ask Salary Data)

### Design principle
The model is used **only to select** one of nine allow-listed analytics operations
(`org_summary`, `country_stats`, `job_title_stats`, `department_stats`, `level_stats`,
`salary_bands`, `outliers`, `above_department_average`, `salary_trends`, or `unsupported`)
plus the countries / departments / job titles the question names. The backend verifies them,
runs the matching read-only SQL aggregate and renders the answer from a template, with the
table behind it, a chart and the data scope. The model never sees salary data, never writes
SQL and never produces a number or the answer's wording
([ADR 0008](adr/0008-natural-language-salary-intelligence.md)).

Not used, on purpose: **text-to-SQL** (unreviewable queries on personal data), **LLM-written
explanations of the results** (a model can restate a number wrongly), and **RAG** (no in-scope
question needs documents; it would earn its place for salary-policy documents).

### Providers
Ollama (llama3.2, local) is the default; Claude (`claude-opus-5-5`) and OpenAI are used when
their API key is configured and can be chosen per question in the chat. All three get the same
prompt and a strict JSON schema (structured outputs). Claude runs at low effort (it's a
classification) with server-side fallback on refusals; a refusal from any provider becomes
"unsupported". The Claude and OpenAI adapters are tested over mocked HTTP; they have not yet
been run against the live APIs (no keys on the development machine). `make benchmark-llm
provider=anthropic` is the check to run once a key is set.

### Prompt (system)
Built at request time from live data so the model can only pick real values
(`app/modules/assistant/prompt.py`):
```
You translate an HR manager's question about employee pay into a JSON query. You only choose
the operation and its filters; the system computes every number. Reply with JSON only.

Choose "metric" (the operation):
- "org_summary": overall headcount, total payroll, average or median pay for the whole company.
- "country_stats": pay in a country, or comparing countries.
- "job_title_stats": pay for a job title / role, optionally in a country.
- "department_stats": pay or headcount by department, comparing departments, or which
  department pays most.
- "level_stats": pay by job level (Junior to Principal), the salary gap between levels,
  pay equity between comparable roles and levels.
- "salary_bands": how many employees fall into each salary band / the salary distribution.
- "outliers": employees paid significantly more or less than peers in comparable roles.
- "above_department_average": employees earning above their department's average.
- "salary_trends": how salaries changed over time / raises over the last 12 months.
- "unsupported": anything that is not about employee pay or headcount.

Fill "countries", "job_titles" and "departments" ONLY with values the question explicitly
names (several when it compares them); otherwise use empty lists. Use the exact spelling from:
Countries: Australia, Brazil, ...
Job titles: Accountant, Account Executive, ...
Departments: Data, Engineering, ...
Set "statistic" to "median" if the question asks for a median, otherwise "average".
```

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

### Second round: the salary-intelligence questions (llama3.2)

| Question | Model output | Problem |
|---|---|---|
| "What is the average salary **in Engineering**?" | `job_title_stats`, job title *Engineering Manager* | A role guessed from the department's name: grounded because it shares the word "engineering" |
| "Compare Engineering and Sales salaries" | `job_title_stats` with two departments | Asked for clarification instead of comparing |
| "How much do **engineers** make?" | two of the four *Engineer* titles | A guess skipped the clarifying question and produced a 20-row listing |

Fixes, each pinned by a regression test in `tests/unit/assistant/test_service.py`:
- a span of the question names **one** value ("data analysts" is a role, not also the Data
  department), and model guesses are grounded only in words **no explicit mention claimed**;
- a role question that names only departments **becomes a department question**;
- only a role the question names explicitly skips the **clarifying question** for vague words;
- "median" vs "average" is read from the question, not the model.

Result: `make benchmark-llm` (11 predefined questions, one per category and more) is
**11/11 with llama3.2**, ~1 s per question; the numbers for the same 11 questions are checked
against values recomputed from the seed generator in `tests/benchmark`.

### Failure handling
If the chosen model is down or slow, `/api/ask` returns **503** naming the provider. The UI
explains it and points to *Pay insights*, which needs no model. Nothing else depends on the
LLM.
