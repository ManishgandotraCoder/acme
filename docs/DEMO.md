# Video demo — shot list (~5 minutes)

Record locally with `make docker-up` (http://localhost:8000) so the pay assistant has Ollama.
The hosted Render copy has no model; use it only to show that the app is deployed.

| # | Time | Show | Say |
|---|---|---|---|
| 1 | 0:00 | README, top of the page | The problem: HR runs pay for 10,000 people in 10 countries from spreadsheets. One app to manage salaries and answer pay questions. |
| 2 | 0:20 | docs/REQUIREMENTS.md, "Deliberately left out" | Written before any code. What's in, what's out and why: no auth (single persona), static FX rates, the LLM never produces numbers. |
| 3 | 0:45 | Home page: employee directory | 10k seeded employees. Type `patel` in search (instant, trigram index). Filter country = India, sort by salary. |
| 4 | 1:15 | Sort by salary with no filter | Salaries are stored in local currency, so the sort compares USD equivalents. Otherwise JPY and INR would rank first. |
| 5 | 1:35 | Add an employee with a duplicate email, then a negative salary | Field-level validation in the browser and on the server (409 for the duplicate). |
| 6 | 2:00 | Edit an employee: change the salary, enter a reason, open salary history | Every change is recorded (old → new, reason, time): the compliance need when leaving spreadsheets. |
| 7 | 2:25 | Change their country to one with another currency | The app requires a new salary, because an amount means nothing in a new currency. |
| 8 | 2:45 | Pay insights page | Org totals in USD; per-country min/median/average/max in local currency and USD; job titles within Germany; departments. |
| 9 | 3:15 | Pay assistant: "What do data analysts earn in Germany?" then "What's the weather tomorrow?" | The model only classifies the question; numbers come from the database. It declines off-topic questions. |
| 10 | 3:45 | Stop Ollama, ask again | The assistant reports itself unavailable; the rest of the app is unaffected. |
| 11 | 4:00 | Terminal: `make check`; then `git log --oneline --reverse` | 195 tests (150 backend on real PostgreSQL, 45 frontend) in seconds; architecture, migration-drift and query-plan tests. Commit history shows test-first slices. |
| 12 | 4:30 | docs/AI_USAGE.md, "Where AI output was wrong" | How AI was used, and how its mistakes were caught: real runs, regression tests, CLAUDE.md rules. |
| 13 | 4:50 | Render URL | Deployed from render.yaml: same Docker image, managed Postgres. |
