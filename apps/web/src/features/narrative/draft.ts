/** Story packs load only into "-draft" worlds; their wording must never claim verification. */
export const isDraftWorld = (slug: string | null | undefined) =>
  !!slug?.endsWith("-draft");

/** Curated notes describe one opening; generated worlds can cover any story. */
export const discoveryLabels = (generated: boolean) =>
  generated
    ? {
        established: "Stated in a cited source",
        interpretation: "Interpretation",
        unresolved: "Unresolved in these sources",
      }
    : {
        established: "Established in the opening",
        interpretation: "Editorial interpretation",
        unresolved: "Unresolved in this scope",
      };

export const DRAFT_NOTE =
  "AI draft that cites its sources. It is not verified, so check it against them.";
