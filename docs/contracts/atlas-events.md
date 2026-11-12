# Future atlas event consumer

features/graph/events.ts defines a transport-independent AtlasEventConsumer. The Zustand store exposes consume(event). No EventSource connection, SSE route, agent simulator, polling loop or fake research producer is implemented.

All events carry universeId. Events for inactive universes are ignored:

| Type | Payload | Effect |
| --- | --- | --- |
| node.added | Full GraphNode | Insert a new known-universe/continuity record |
| node.updated | Full GraphNode | Replace an existing node |
| relationship.added | Full GraphEdge | Insert an eligible directed edge with valid endpoints |
| verification.changed | nodeId, unverified/verified/disputed status | Update node metadata |
| discovery.revealed | nodeId | Mark a known node for restrained reveal animation |
| research.progress | completed, total | Store bounded integer progress for future real progress UI |

Duplicate inserts are ignored by stable ID; updates never manufacture missing nodes. Edges with absent endpoints or incompatible scopes are rejected. Updated nodes retain known layout coordinates, and the renderer can reject newly inconsistent edges. Future transport must order endpoints before relationships and support snapshot resynchronization.

Before connecting SSE, add an envelope with schema version, event ID and per-universe sequence/revision. Validate unknown JSON at the transport boundary, deduplicate events, reject stale revisions, bound batch size/memory, support reconnect/Last-Event-ID, and resynchronize on gaps. Abort streams on universe changes. Verification updates need claim/evidence semantics before being described as researched facts.

Current graph-data changes replace immutable snapshots and rebuild Sigma while retaining known coordinates and camera pose. Selection/filter/camera changes reuse the renderer. High-volume transport should batch Graphology mutations rather than replaying whole snapshots. Transport and that optimization remain outside this phase.
