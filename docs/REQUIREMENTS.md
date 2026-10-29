# Salary Management — Requirements (one page)

## Goal
Replace ACME's spreadsheet-based salary management with a web application that lets the
**HR Manager** (a) maintain salary data for ~10,000 employees across multiple countries and
(b) answer "how do we pay people?" questions in seconds instead of pivot tables.

The application has two core capabilities: **Salary Management** and **Salary Intelligence**
(asking questions of the HR data in plain English). The second is a first-class feature, not
a set of dashboard charts.

**Success looks like:** the HR manager can find any employee in under 5 seconds, change a
salary with an audit trail (who, when, effective from), and get accurate, reproducible answers
to at least **10 predefined business questions**, verified against known seeded data.

## Users & key jobs
| Persona | Job to be done |
|---|---|
| HR Manager | "Find an employee and update their salary, knowing it's recorded." |
| HR Manager | "What do we pay a Software Engineer in India vs Germany?" |
| HR Manager | "Which countries / departments cost the most? Where are the outliers?" |

## Scope & features (in)
1. **Employee directory** — paginated list (10k rows), search by name/email, filter by
   country, department, job title, job level, currency and salary range; sortable by name /
   salary / hire date.
2. **Employee CRUD** — add, edit, remove employees, with server-side validation
   (supported country, positive salary, unique email).
3. **Salary changes with history** — every salary change is recorded (old → new, reason,
   **effective date**, **who made it** and when) and viewable per employee. HR's #1 compliance
   need when leaving spreadsheets.
4. **Multi-currency correctly** — salaries are stored in the employee's *local currency*
   (derived from country). Cross-country comparisons are converted to USD using a single,
   explicit FX table so numbers are never silently mixed.
5. **Pay insights**
   - Org summary: headcount, total annual payroll (USD), average salary (USD).
   - Per country: headcount, min / max / average / median salary (local + USD).
   - Per job title within a country: min / max / average salary.
   - Per department: headcount and average salary (USD), optionally per country.
6. **Natural-Language Salary Intelligence ("Ask Salary Data")** — the HR manager can ask
   questions in plain English about organizational compensation, including averages, medians,
   salary distributions, department and country comparisons, historical changes, and potential
   pay disparities. The system translates supported questions into validated analytics
   operations, retrieves results from the database, and presents evidence-based answers with
   appropriate charts or tables. Unsupported or ambiguous questions receive a clear explanation
   or a request for clarification. Sensitive individual-level results respect authorization and
   privacy controls.

   | Category | Example question |
   |---|---|
   | Salary overview | What are the average and median salaries across the organization? |
   | Department analysis | Which department has the highest median salary? |
   | Country analysis | How does compensation differ across countries? |
   | Pay equity | What is the salary gap between job levels? |
   | Outliers | Which employees earn significantly more or less than peers in comparable roles? |
   | Trends | How have salaries changed over the last 12 months? |
   | Distribution | How many employees fall into each salary band? |

   **Pipeline:** question → the LLM *selects* one allow-listed analytics operation and its
   parameters (structured output) → parameters are validated against known values → a
   read-only, parameterized SQL aggregate runs → the answer is rendered from a template with a
   table, a chart where useful, and the data scope. The LLM never writes SQL, never sees salary
   rows and never writes the numbers. Cross-country figures are converted to USD only through
   the static, dated FX table. Model provider: **Ollama by default**, Claude or OpenAI when
   configured, chosen per question; everything else works with no model at all.
7. **Seed script** — deterministic generation of 10,000 realistic employees from
   `first_names.txt` × `last_names.txt`.

## Deliberately left out (and why)
| Left out | Reasoning |
|---|---|
| Authentication / RBAC | Single persona (HR Manager); would be SSO in real life. One `Actor` seam already records who changed a salary and gates individual-level answers by permission; SSO would fill it. |
| Live FX rates | Static, versioned rates keep reports reproducible and tests deterministic. Swap-in point is one module. |
| Payroll processing, tax, bonuses, equity | Different problem (payroll engine) — the brief is about *managing* and *understanding* pay. |
| Bulk Excel import/export | Valuable next step for migration; the seed script proves bulk ingest. Deferred to keep core quality high. |
| LLM generating SQL or answer numbers | Hallucinated pay figures are worse than no answer. Intent → whitelisted query only. |
| LLM-written answer prose | Even "explaining" verified results lets a model restate a number wrongly. Answers are templates filled from query results; the model only classifies. |
| RAG over HR documents | Every in-scope question is quantitative and answered by SQL. RAG earns its place only if policy documents (salary-revision rules, band guidelines) come into scope. |
| Multi-tenant, org charts, performance reviews | Out of the stated problem. |
| Caching layer | PostgreSQL with targeted indexes answers every list and insight query in milliseconds even at 20× today's data (ADR 0006); a cache would add invalidation complexity for no gain. |

## Non-functional requirements
- List & insight endpoints respond in < 200 ms on 10k employees (indexed columns, SQL aggregates).
- Seeding 10k employees in < 5 s (bulk inserts, single transaction).
- Unit tests fast (< 10 s total) and deterministic (seeded RNG, fake LLM, each test in a
  rolled-back PostgreSQL transaction).
- Validation errors return clear, field-level messages (HTTP 422); not-found → 404; conflicts → 409.
