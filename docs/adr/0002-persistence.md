# ADR 0002: Local PostgreSQL, async SQLAlchemy and backend-owned migrations

Status: Accepted

## Context

A media-independent atlas requires a directed cyclic graph with scoped continuities, arbitrary node metadata and stable relational integrity. All services must run locally on Windows. The frontend must not own database credentials or schema changes.

## Decision

Run PostgreSQL 18 in Docker Compose, bound to loopback with a persistent named volume. Use asyncpg and SQLAlchemy 2 async sessions. Use Alembic for explicit self-contained schema migrations. Use UUID keys, timezone-aware timestamps and JSONB metadata. Index universe, continuity and edge endpoint lookups.

Store node/relationship vocabulary as strings instead of native PostgreSQL enums, validating through domain enums at the adapter boundary. Composite foreign keys ensure endpoints and continuity belong to the edge's universe. Domain endpoint validation enforces additional continuity semantics. Preserve adaptation boundaries instead of inferring event identity.

The deterministic sample seed inserts missing records and preserves edits in one caller-owned transaction. It is idempotent for serial runs, not a concurrent import system.

Tests use isolated SQLite by default and a separately configured PostgreSQL test database with a unique temporary schema for actual migrations. They never infer a test URL from normal configuration.

## Consequences

No graph database or extra infrastructure is needed for the small initial graph. SQL joins and filters remain accessible. Schema changes are reviewed in backend migrations. New enum members need coordinated code/transport changes but no native enum DDL. Cross-continuity semantics cannot be fully represented by nullable composite foreign keys and must be checked in future write use cases. SQLite cannot prove JSONB behavior or PostgreSQL migrations; the opt-in PostgreSQL test covers that boundary. Large graph retrieval, ingestion concurrency and vector storage remain future work.
