# Salary Management — Requirements (one page)

## Goal
Replace ACME's spreadsheet-based salary management with a web application that lets the
**HR Manager** (a) maintain salary data for ~10,000 employees across multiple countries and
(b) answer "how do we pay people?" questions in seconds instead of pivot tables.

**Success looks like:** the HR manager can find any employee in under 5 seconds, change a
salary with an audit trail, and answer common pay questions (by country, role, department)
without exporting to Excel.

## Users & key jobs
| Persona | Job to be done |
|---|---|
| HR Manager | "Find an employee and update their salary, knowing it's recorded." |
| HR Manager | "What do we pay a Software Engineer in India vs Germany?" |
| HR Manager | "Which countries / departments cost the most? Where are the outliers?" |

## Scope & features (in)
1. **Employee directory** — paginated list (10k rows), search by name/email, filter by
   country, department, job title; sortable by name / salary / hire date.
2. **Employee CRUD** — add, edit, remove employees, with server-side validation
   (supported country, positive salary, unique email).
3. **Salary changes with history** — every salary change is recorded (old → new, reason,
   timestamp) and viewable per employee. HR's #1 compliance need when leaving spreadsheets.
4. **Multi-currency correctly** — salaries are stored in the employee's *local currency*
   (derived from country). Cross-country comparisons are converted to USD using a single,
   explicit FX table so numbers are never silently mixed.
5. **Pay insights**
   - Org summary: headcount, total annual payroll (USD), average salary (USD).
   - Per country: headcount, min / max / average / median salary (local + USD).
   - Per job title within a country: min / max / average salary.
   - Per department: headcount and average salary (USD), optionally per country.
6. **Ask in plain English (AI, via local Ollama)** — e.g. *"average salary of data analysts
   in Germany"*. The LLM only **interprets** the question into a structured query; all
   numbers are computed by the backend from the database. If the model is unavailable the
   rest of the app keeps working and the UI says so.
7. **Seed script** — deterministic generation of 10,000 realistic employees from
   `first_names.txt` × `last_names.txt`.

## Deliberately left out (and why)
| Left out | Reasoning |
|---|---|
| Authentication / RBAC | Single persona (HR Manager); would be SSO in real life. Designed so an auth dependency can be added at the API layer without touching services. |
| Live FX rates | Static, versioned rates keep reports reproducible and tests deterministic. Swap-in point is one module. |
| Payroll processing, tax, bonuses, equity | Different problem (payroll engine) — the brief is about *managing* and *understanding* pay. |
| Bulk Excel import/export | Valuable next step for migration; the seed script proves bulk ingest. Deferred to keep core quality high. |
| LLM generating SQL or answer numbers | Hallucinated pay figures are worse than no answer. Intent → whitelisted query only. |
| Multi-tenant, org charts, performance reviews | Out of the stated problem. |
| Postgres / caching layer | SQLite with indexes answers aggregations over 10k rows in milliseconds; repository layer keeps Postgres a config change. |

## Non-functional requirements
- List & insight endpoints respond in < 200 ms on 10k employees (indexed columns, SQL aggregates).
- Seeding 10k employees in < 5 s (bulk inserts, single transaction).
- Unit tests fast (< 10 s total) and deterministic (seeded RNG, fake LLM, in-memory DB).
- Validation errors return clear, field-level messages (HTTP 422); not-found → 404; conflicts → 409.
