# ADR 0001: Explicit ports and constructor-injected use cases

Status: Accepted

## Context

The local knowledge graph must remain independent of HTTP, ORM implementation and future research orchestration. Tests need meaningful substitutions without real inference or a shared database. Small foundations are easy to burden with speculative service hierarchies.

## Decision

Use domain dataclasses/value objects and exceptions; application repository Protocols and focused use cases; SQLAlchemy infrastructure adapters; and FastAPI presentation dependencies. Dependencies point inward. Use structural Protocols only at repository boundaries, constructor injection in use cases, and explicit response mapping. Keep graph semantics and continuity compatibility in domain methods.

The FastAPI composition root owns request sessions and transactions. Repositories query and map, never commit. Engines live in application lifespan. Default tests substitute repositories or the session dependency. Async operations sharing a session are sequential.

## Consequences

Domain and use-case tests need no framework or database. Future adapters can substitute behind existing ports. Some mapping is intentionally explicit and repetitive, making boundaries reviewable. New mutation paths must invoke domain invariants; simply writing ORM rows is not an application use case. There are no generic base services, agent classes, containers or runtime plugin registries.
