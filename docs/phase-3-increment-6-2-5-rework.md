# Evidence-to-narrative rework

The saved Origin audit establishes two separate failures. The reviewer accepted Roger’s reported claim as an occurrence, while model-output and role-string mismatches prevented other scenes from qualifying. The zero-frame recovery condition also prevented a second attempt on the scenes most in need of one. The last run exhausted the reconstruction allocation and preserved the review reserve. Its published article was empty.

## Before

`prepare_developments` → normalized development clauses → `reconstruct_arc` → loose participant strings → per-batch controls and role-string comparison → `frame_notes` → sequential prose → model-calculated character offsets → grounding, relationship and editorial review → publication.

Some audit findings describe older behavior. The current frame reviewer already preserves independently valid rows in a malformed batch. An optional gap does not by itself make `Reconstruction.ready` false. The repeated controls and coarse classification of essential clauses still affect throughput and readiness. `frame_notes` is not the writer’s primary input, but it still collapses roles in the downstream review and repair contract.

## Intended call graph

`prepare_developments` retains scope, the evidence allowlist and reviewed connections. `reconstruct_arc` supplies direct archive spans and bounded neighboring context for extraction. It binds stable scoped participants, qualifies atomic propositions against their permitted evidence, and recovers recoverable missing actions. `build_discourse` preserves verified connections and source presentation lanes. The writer uses qualified frames and rolling reader context. Code makes spans and the model associates them with frame IDs. Archive-based entailment and publication gates remain independent.

Provider failures leave a gap and preserve earlier qualified frames. Extractor output never changes the canonical graph, source permissions, or spoiler scope. Existing API projections remain the publication boundary. A controlled benchmark demonstrates the frozen archive rather than autonomous source acquisition.

## Implemented changes and remaining boundaries

| Boundary | Current behavior |
| --- | --- |
| Evidence to frame | The extractor gets the direct licensed spans, their source offsets, and bounded neighboring and parallel passages. A paraphrased clause can bind to an exact excerpt from the original archive. A neighboring passage cannot supply a new primary action. |
| Frame review | The reviewer observes role IDs, modality and negation from evidence independently of the candidate assignment. Rows are assessed individually. Malformed decisions remain unavailable and do not erase accepted siblings. The synthetic attribution probes were removed from live frame batches. |
| Recovery | Empty scenes are eligible for the bounded extraction retry. Missing decisions get a review retry, while an unavailable reviewer does not prompt another extraction of the same evidence. |
| Writing and alignment | Qualified frames carry their roles, modality and outcomes into the writer and semantic grounding. The internal projection contains only citation bindings. Python segments the prose and the aligner returns numbered associations. The old independent note extractor and scene writer have no active callers and were removed. |
| Publication | The existing archive-based factual, relationship, coverage, editorial and originality checks are still required. The retained review and development-plan safeguards have separate purposes. A pre-existing fallback for sections with no development plan remains for compatibility. |

Source-local IDs currently stay stable for the same accepted display name within a section. Canonical links still require a unique scoped match. The extraction prompt asks the model to use one name for each referent within a scene. Different names across source windows still need stronger evidence-bound alias resolution. The rework retains the existing broad coverage policy and verified plan links. It does not add a second relationship graph or automatically invent action-level links for gaps.
