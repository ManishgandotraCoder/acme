# 0002 — Store salaries in local currency; convert via one FX table

**Status:** Accepted

## Context
Employees are paid in 10 countries. HR thinks and contracts in local currency, but
questions like "highest paid" or "average across the org" compare countries.

## Decision
- `annual_salary` is stored as an integer in the employee's local currency; `currency` is
  derived from `country`, never entered by hand.
- All cross-country maths goes through `app/shared/countries.py` (static, dated FX rates,
  shown in the UI as "as of …").
- Aggregations group by country *first* and convert after, so mixed currencies are never
  summed. Sorting by salary uses the USD equivalent in SQL.
- Moving an employee to a country with a different currency requires a new salary.

## Consequences
- ✅ Numbers match payslips; reports are reproducible; tests are deterministic.
- ✅ One place to swap in a live FX provider.
- ❌ Static rates drift from the market; reports state their FX date.
- Lesson: a smoke test caught salary sorting by raw local amount (JPY first). Any new
  query touching salary must respect this ADR.
