# Phase 2 verification

Verified locally on Windows 11, 12 November 2026, with Node 24.13.0, Python 3.14.3, Next.js 16.4.6 and PostgreSQL 18.

## Successful checks

| Command / check | Result |
| --- | --- |
| npm dependency installation | Sigma 4.0.6, Graphology 0.26.0, image layer 4.0.2, GSAP 3.15.1, React integration 2.1.2, Zustand 5.1.0 installed with exact lockfile versions |
| npm run test --prefix apps/web | 23 unit tests passed across five suites |
| npm run test:e2e --prefix apps/web | Three Playwright tests passed in installed Google Chrome against actual seeded PostgreSQL/FastAPI |
| npm run lint --prefix apps/web | Passed |
| npm run typecheck --prefix apps/web | Passed |
| npm run format:check --prefix apps/web | Passed; generated Next environment declarations excluded |
| npm run build --prefix apps/web | Optimized production build passed, including browser-only Sigma boundary and API forwarding route |
| npm audit --omit=dev --prefix apps/web | Zero production vulnerabilities reported |
| Backend pytest with explicit TEST_DATABASE_URL | All 21 existing tests passed, including PostgreSQL migration/API coverage |
| Backend alembic check | No new upgrade operations detected |
| Backend source/API-contract diff | No changes |
| Final whitespace/diff review | No whitespace errors |

Unit tests cover node/edge mapping, direction, multi-edges, cycles, invalid links, deterministic/preserved coordinates, continuity/layer filtering, store isolation, camera focus commands, stale universe loads/failures, retries, explicit-order journeys, missing media, edge selection and incremental consumer guards.

Playwright exercises actual WebGL rendering, selecting Emilia, following Subaru, minimizing/resetting the panel, searching for Puck, entering/exiting unsupported Guided mode, failed-image fallback, continuity/layer filtering, reloading the active universe without route navigation, and reduced-motion keyboard use at 390px width. The narrow-screen test checks focus restoration and horizontal overflow. The same suite passed against the production server after the relationship-detail change.

Browser review additionally inspected original artwork, selection dimming, directed labels and desktop/mobile composition. The final spacing adjustment keeps lower entries above floating map controls. Screenshots are visual evidence, not claims of exhaustive usability or accessibility certification.

## Honest limits

- The current Re:Zero graph has no supported chronology. Guided mode intentionally reports that ordering is unavailable. Progression is exercised with explicit synthetic test sequences, never fake story data in app components.
- Only one universe is seeded. Actual browser coverage reloads that universe; two-universe switching and out-of-order load protection are covered with isolated unit fixtures.
- Artwork is original and interpretive, with a local CC0 notice. It is not official or verified character/location imagery.
- No SSE transport, research execution or AI simulation is implemented. The store consumer and documented contracts prepare that boundary.
- Large-graph performance, live event volume, touch-device behavior on physical phones and comprehensive assistive-technology audits remain future work.
- The previously documented seven moderate development-only TypeScript ESLint/minimatch audit findings remain. Production audit is clean; no unsupported transitive major override was forced.

## Diagnosed issues during implementation

Windows intermittently rejected the packaged default shell inside the sandbox. Direct patches and an explicit Windows PowerShell/approved-host execution path completed the work; no system installation was changed. Initial React lint failures were fixed by deferring context-safe handlers until events and receiving renderer failures via a lifecycle-cleaned animation-frame callback. Sigma image attributes were explicitly bound, a temporary text-encoding issue in glyph definitions was corrected, and compact labels were reduced to avoid crowding.

An initial Playwright cold-start wait expired during development compilation. The test now waits on rendered UI with a bounded 15-second assertion timeout; all three tests passed afterward. No arbitrary sleep or fake API response was added.

See [the implementation guide](phase-2-atlas.md), [media](contracts/media.md), [journeys](contracts/journeys.md) and [event consumer](contracts/atlas-events.md). Source changes were left local for review; no Phase 2 commit, remote push or deployment was made.

Final screenshots: [overview](phase-2-overview.jpg) and [focused story](phase-2-preview.jpg). Temporary verification servers were stopped after capture; the seeded PostgreSQL service and data remain intact.
