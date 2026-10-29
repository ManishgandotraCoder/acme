# Video demo — shot list (~6 minutes)

Record locally with `make docker-up` (http://localhost:8000) so the assistant has Ollama. The
hosted Render copy needs a Claude or OpenAI key for the assistant; use it to show deployment.

| # | Time | Show | Say |
|---|---|---|---|
| 1 | 0:00 | README, top of the page | The problem: HR runs pay for 10,000 people in 10 countries from spreadsheets. Two capabilities: salary management and salary intelligence. |
| 2 | 0:20 | docs/REQUIREMENTS.md: scope, "Deliberately left out", success criterion | Written before any code. In, out and why: no auth (single persona), static FX rates, no RAG, the LLM never produces numbers. Success = 10 business questions answered accurately and reproducibly. |
| 3 | 0:50 | Home page: employee directory | 10k seeded employees. Search `patel` (trigram index). Filter level = Principal, currency = EUR, min salary 150,000: the range is in EUR because one currency is chosen, otherwise USD. |
| 4 | 1:20 | Edit an employee: new salary, reason, effective date in the past; open salary history | Every change is recorded with when it takes effect and who made it. Backdated changes land in the right place. |
| 5 | 1:45 | Change their country to one with another currency | The app requires a new salary, because an amount means nothing in a new currency. |
| 6 | 2:00 | Chat: "Which department has the highest median salary?" | The model only picks an allow-listed operation; the number comes from SQL. Chart, the table behind it, and the scope: USD at fixed FX rates as of a date. |
| 7 | 2:25 | Chat: "What is the salary gap between job levels?" | Like for like, same title and country. The org-wide medians would mislead: Principal looks lower than Lead because of where Principals work. |
| 8 | 2:50 | Chat: "Which employees earn significantly more or less than peers?" | Peers = same title, level and country, so local currency. Names need permission: restart with `SALARY_ACTOR_PERMISSIONS=[]` to show the refusal and hidden small groups (or narrate it). |
| 9 | 3:20 | Chat: "How have salaries changed over the last 12 months?", then "How much do engineers make?" | Trends by effective month. A vague role gets a clarifying question with one-click options. |
| 10 | 3:45 | Chat: "What's the weather tomorrow?"; then the model picker (if a key is set) | Off-topic questions are declined with examples. Ollama is the private default; Claude or OpenAI change understanding, never the numbers. |
| 11 | 4:10 | Terminal: `make benchmark-llm` | 11 predefined questions against the real model: 11/11 understood. |
| 12 | 4:30 | Terminal: `make check`; `tests/benchmark/test_salary_questions.py` | 314 tests on real PostgreSQL in seconds. The benchmark checks every answer against values recomputed from the seed generator. Query-plan tests keep every read path indexed. |
| 13 | 5:00 | `git log --oneline --reverse` | Test-first slices; `fix:` commits record what running the real system revealed. |
| 14 | 5:20 | docs/AI_USAGE.md, "Where AI output was wrong" and "Second round" | How AI was used, and how its mistakes were caught: real runs, screenshots, regression tests, CLAUDE.md rules. |
| 15 | 5:45 | Render URL | Deployed from render.yaml: same Docker image, PostgreSQL on Neon. |
