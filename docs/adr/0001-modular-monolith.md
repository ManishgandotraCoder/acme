# 0001 — Modular monolith with enforced module boundaries

**Status:** Accepted

## Context
One HR team, one product, ~10k employees and a handful of concurrent users. The domain has
three clear capabilities: managing employees, analysing pay, and answering questions in
plain English. The first version was organised by technical layer (`api/`, `services/`,
`repositories/`), which scatters each capability across the tree and lets any file import
any other.

## Decision
A single deployable organised by **business module**:

```
app/core/      infrastructure (config, database, DI, errors, logging, ops)
app/shared/    shared kernel (countries, currencies, FX)
app/modules/   employees · insights · assistant — each owns models, schemas,
               repository/service, router, errors
app/main.py    composition root
```

Rules, enforced by `tests/unit/test_architecture.py`:
- `core` and `shared` never import `modules`.
- A module may import another module only if declared:
  `insights → employees`, `assistant → employees, insights`.

## Consequences
- ✅ A feature lives in one folder; ownership and change impact are obvious.
- ✅ Coupling becomes a reviewed decision (the test fails until it's declared).
- ✅ A module could be extracted into a service later along an existing seam.
- ❌ Microservices were rejected: network hops, distributed transactions and extra
  operations for no benefit at this scale.
- ⚠️ `insights` reads the `employees` table directly (a read model) instead of going
  through an API. Acceptable inside one process and database; revisit if split.
