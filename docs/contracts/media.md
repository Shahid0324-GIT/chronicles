# Proposed media contract (not implemented in FastAPI)

Media is separate from knowledge facts. The frontend registry maps stable universe/node UUIDs to local artwork. MediaArtwork supports alt text, credit, focal positioning, missing entries and failed loads. Sigma uses the same registry; semantic node color remains visible if a texture fails.

A future backend media array or separate resource should include:

    interface EntityMedia {
      id: string;
      entity_id: string;
      role: "portrait" | "location" | "event" | "cover";
      local_url: string;
      alt: string;
      width: number;
      height: number;
      focal_point?: { x: number; y: number };
      attribution: string;
      license: string;
      source_url?: string;
      continuity_id: string | null;
      interpretation: "canonical-reference" | "interpretive" | "fallback";
    }

The backend must validate local paths, media types, ownership, license and provenance. Do not assume art applies across adaptations. Source URLs document rights/provenance; they do not authorize arbitrary hotlinking. Resolve the preferred role and continuity, then fall back to the original compass. Retain credits and label interpretive media honestly.

The current original SVGs have a CC0 notice in their directory. Replace or supplement them with licensed, adaptation-specific imagery through this contract. No backend media fields or migrations are added in Phase 2.
