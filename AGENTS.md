# Universe Atlas repository guidance

Implement only the scope requested. Phase 1 provides a read-only local knowledge graph, not AI research. Never present curated seed content as discovered or verified by an agent. Do not deploy or push without explicit user instructions.

## Layout and dependency direction

- Python package: `services/intelligence/src`; run backend commands from `services/intelligence`.
- Domain imports only the Python standard library and other domain modules.
- Application depends on domain and repository Protocols in `application/ports`.
- Infrastructure implements ports structurally and maps ORM rows to domain entities.
- Presentation composes concrete repositories with FastAPI Depends and converts application results to dedicated API schemas.
- Next.js lives in `apps/web`. Server-only API client is `src/lib/api.ts`; transport types are `src/lib/contracts.ts`; graph UI boundary is `src/components/Atlas.tsx`.

Use constructor injection, explicit meaningful Protocols, composition, Python type hints and strict TypeScript. Do not introduce BaseService/BaseAgent, generic repository frameworks, microservices, external auth, cloud storage, or unused future dependencies.

## Graph semantics

Universes are graphs, never trees. IDs are UUIDs. Slugs are lowercase hyphenated value objects. `None` continuity means explicitly shared knowledge; it is not a license to merge adaptations. Before persisting a relationship, call `validate_endpoints` with the actual nodes. Two scoped endpoints must share a continuity, and a scoped endpoint requires its edge to use that continuity. Cross-universe relationships are prohibited and defended by composite database foreign keys. New write use cases must validate these rules within their transaction.

Enums are application vocabulary stored as strings, not native PostgreSQL enums. Add enum members deliberately in domain and transport contracts; handle unknown historical values explicitly in any future import pipeline. Never silently coerce an unknown type to a different meaning.

## Persistence

Use SQLAlchemy async APIs; one session and transaction per request, closed through a yield dependency. Repositories never commit. Do not share an AsyncSession between concurrent tasks. Caller owns seed transactions. Backend Alembic migrations are the only runtime schema mechanism; do not call `create_all` at startup. Migration files must remain self-contained and never import mutable current ORM metadata. Add indexes and downgrade behavior for schema changes.

Seed IDs are deterministic, illustrative, and limited to early Re:Zero anime content. Preserve existing data and user edits. Run seeds serially. Never erase or reset developer volumes to fix a routine configuration issue.

## Checks

Backend (from `services/intelligence`, using root `.venv`):

```powershell
..\..\.venv\Scripts\python -m ruff check .
..\..\.venv\Scripts\python -m ruff format --check .
..\..\.venv\Scripts\python -m mypy -p src
..\..\.venv\Scripts\python -m pytest -q
```

Frontend (from root): `npm run lint --prefix apps/web`, `npm run typecheck --prefix apps/web`, `npm run build --prefix apps/web`.

Default tests use in-memory SQLite or fake repositories. PostgreSQL tests require an explicit `TEST_DATABASE_URL` ending in `_test` and a unique schema; never fall back to `DATABASE_URL`. Verify actual migration upgrade/downgrade and `alembic check` when touching persistence. Backend dependency resolution is recorded in `requirements-dev.lock`; npm versions are locked in `package-lock.json`. Update locks intentionally after meaningful checks.

Keep credentials out of Git. Local `.env` files are ignored; update examples when settings change. Maintain loading, error, empty, not-found, keyboard and responsive states. Do not embed sample data in React. Prefer simple local state until cross-component state actually requires a store.

Report exact checks, failures and blockers. Consult `docs/verification.md` for the last implementation verification; rerun only relevant checks for subsequent changes.
