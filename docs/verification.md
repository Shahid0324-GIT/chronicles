# Phase 1 verification

Verified locally on Windows 11 on 12 November 2026 (Asia/Calcutta).

## Environment and resolved packages

- Python 3.14.3; Node.js 24.13.0; npm 11.11.0; Docker Engine/CLI 29.8.2.
- PostgreSQL 18 via Docker Compose; healthy loopback-bound container.
- FastAPI 0.162.5, Pydantic 2.14.3, SQLAlchemy 2.0.57, Alembic 1.20.1, asyncpg 0.32.0.
- Next.js 16.4.6, React 19.3.1, TypeScript 6.0.3, Tailwind 4.3.5.
- Exact Python environment in `services/intelligence/requirements-dev.lock`; npm resolution in `apps/web/package-lock.json`.

## Successfully executed

Commands were run from the locations documented in README. Virtual-environment Python was invoked directly.

| Check | Result |
| --- | --- |
| Backend editable installation with dev dependencies | Installed successfully |
| `python -m pip check` | No broken requirements |
| `docker compose up -d --wait` | PostgreSQL healthy |
| `python -m alembic upgrade head` | Initial migration applied to local development database |
| `python -m src.infrastructure.persistence.seed` twice | 1 universe, 1 continuity, 10 nodes, 12 edges; no duplicates |
| `python -m alembic check` | No new upgrade operations detected |
| `python -m pytest -q` with explicit test URL | 21 passed; includes real PostgreSQL migration/API test |
| `python -m mypy -p src` | No issues in 23 source files |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | Passed |
| `npm ci` with final exact-version lockfile | Fresh installation succeeded |
| `npm run format:check` | Passed |
| `npm run lint` | Passed, no warnings after PostCSS config cleanup |
| `npm run typecheck` | Passed |
| `npm run build` | Next.js production compilation passed |
| `npm audit --omit=dev` | Zero production dependency vulnerabilities reported |
| Live HTTP queries to all five API routes | Correct persisted responses |
| Browser catalog and atlas | Correct rendering and interactive traversal |

The PostgreSQL integration test uses `universe_atlas_test`, a randomly named test schema, the actual Alembic upgrade and downgrade, and two seed runs. The default suite was also exercised without a PostgreSQL URL: the PostgreSQL case skips explicitly. No default test connects to the development database.

## End-to-end story

The catalog requests FastAPI records through the Next.js server, the API reads PostgreSQL through injected use cases/repositories, and opening a world renders the returned graph in Atlas.

| Boundary | Evidence |
| --- | --- |
| UI catalog | Browser showed one Re:Zero atlas from API data |
| API connectivity | `/api/health`: `status=ok`, `database=ready` |
| PostgreSQL → API graph | `/api/universes/re-zero/graph`: 10 nodes, 12 edges, one continuity |
| API node details | UUID lookup returned the persisted Emilia node and incident edges |
| Response → UI | Overview displayed matching counts and continuity information |
| Interaction | Following Subaru from Emilia changed the selected node and relationship list |
| Empty state | Unmatched search showed zero entries and a useful empty view |
| Continuity | Selecting anime continuity retained the correct scoped entries |
| Responsive layout | Checked at 390px width; document content fit without horizontal overflow |
| Browser console | No warnings or errors observed after rendering |

The navigation loading boundary was observed in the browser. Missing records and database failure responses are tested through the API; the frontend error and not-found components compiled. Browser error/offline scenarios and comprehensive accessibility audits were not exhaustively exercised. A full-page browser screenshot API was unavailable; a viewport screenshot was saved using the supported screenshot method instead. [Catalog screenshot](atlas-preview.jpg).

## Diagnosed environment failures and remaining limitations

- Windows sandbox blocked `ensurepip` temporary-directory writes, registry DNS, Docker named-pipe access, and stalled an async SQLite test run. Workspace-local temp paths plus approved host execution resolved installation/testing. Pip was subsequently installed into the venv. The stalled sandbox process was stopped; the host suite passed.
- An initial mypy command from the root could not discover `src`. Running from `services/intelligence`, as documented, passed.
- ESLint 10 is available, but Next's current React/import/accessibility plugins declare compatibility through ESLint 9. The final lock uses the newest compatible ESLint 9 release (9.39.5), whose npm metadata marks it deprecated. No forced incompatible upgrade was retained.
- Full npm audit reports seven moderate findings in the development-only TypeScript ESLint/minimatch dependency chain (GHSA-g3hv-75wg-m249). `npm audit fix` was attempted and did not resolve them with the mutually compatible packages. No vulnerable production dependencies were reported. Recheck upstream plugin compatibility before upgrading; no unsupported major transitive override was forced.
- The graph endpoint returns the entire graph and has no pagination. The API is intentionally read-only. No AI/research integration or large-graph renderer is included.
- Checks used the listed Windows/Python/Node versions; other operating systems and Python versions were not exercised.

Verification FastAPI/Next.js servers were stopped after browser checks. PostgreSQL and the seeded development database remain available locally. No remote push, deployment or Git commit was performed.
