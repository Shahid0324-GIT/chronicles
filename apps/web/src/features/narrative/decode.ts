import type { NarrativeCatalog } from "./contracts";

type RecordValue = Record<string, unknown>;
const object = (v: unknown): v is RecordValue =>
  !!v && typeof v === "object" && !Array.isArray(v);
const text = (v: unknown): v is string =>
  typeof v === "string" && v.length <= 20000;
const id = (v: unknown): v is string => text(v) && /^[0-9a-f-]{36}$/i.test(v);
const list = (v: unknown, check: (item: unknown) => boolean) =>
  Array.isArray(v) && v.length <= 500 && v.every(check);
const ids = (v: unknown) => list(v, id);
const hint = (v: unknown) =>
  object(v) &&
  ids(v.relatedNodeIds) &&
  ids(v.relationshipIds) &&
  (v.focusRatio === undefined ||
    (typeof v.focusRatio === "number" &&
      Number.isFinite(v.focusRatio) &&
      v.focusRatio >= 0.25 &&
      v.focusRatio <= 3));
const scoped = (v: RecordValue) =>
  id(v.id) && id(v.universeId) && id(v.continuityId);
const step = (v: unknown) =>
  object(v) &&
  id(v.id) &&
  id(v.eventNodeId) &&
  text(v.title) &&
  text(v.body) &&
  (v.detailedRecap === undefined || text(v.detailedRecap)) &&
  (v.underlyingEventIds === undefined || ids(v.underlyingEventIds)) &&
  (v.presentationStatus === undefined ||
    ["validated", "unavailable"].includes(String(v.presentationStatus))) &&
  text(v.episodeLabel) &&
  ids(v.sourceIds) &&
  ids(v.loreThreadIds) &&
  hint(v.presentation) &&
  (v.presentationState === undefined ||
    (object(v.presentationState) &&
      text(v.presentationState.status) &&
      text(v.presentationState.reason))) &&
  (v.participantRoles === undefined ||
    list(
      v.participantRoles,
      (r) =>
        object(r) &&
        id(r.nodeId) &&
        ["actor", "recipient", "witness", "opponent"].includes(String(r.role)),
    ));

const section = (v: unknown) =>
  object(v) &&
  text(v.heading) &&
  list(
    v.paragraphs,
    (p) =>
      object(p) &&
      ids(p.eventNodeIds) &&
      ids(p.sourceIds) &&
      list(
        p.segments,
        (s) =>
          object(s) && text(s.text) && (s.nodeId === undefined || id(s.nodeId)),
      ),
  );

export function decodeNarrative(value: unknown): NarrativeCatalog {
  if (
    !object(value) ||
    value.schemaVersion !== 1 ||
    (value.reconstruction !== undefined &&
      !(
        object(value.reconstruction) &&
        text(value.reconstruction.status) &&
        text(value.reconstruction.readingExplanation) &&
        object(value.reconstruction.coverage) &&
        [
          "verifiedSegments",
          "candidateTransitions",
          "causallyExplainedTransitions",
          "unexplainedTransitions",
          "segmentsWithParticipants",
          "segmentsWithLocations",
        ].every(
          (k) =>
            Number.isInteger(
              (value.reconstruction as RecordValue).coverage &&
                ((value.reconstruction as RecordValue).coverage as RecordValue)[
                  k
                ],
            ) &&
            Number(
              ((value.reconstruction as RecordValue).coverage as RecordValue)[
                k
              ],
            ) >= 0,
        ) &&
        list(
          value.reconstruction.segments,
          (s) =>
            object(s) &&
            id(s.id) &&
            ids(s.eventNodeIds) &&
            text(s.title) &&
            text(s.statement),
        ) &&
        list(
          value.reconstruction.transitions,
          (t) =>
            object(t) &&
            id(t.fromId) &&
            id(t.toId) &&
            text(t.explanation) &&
            text(t.sourceOrder) &&
            text(t.narrativeOrder) &&
            text(t.chronology),
        )
      )) ||
    (value.researchScopes !== undefined &&
      !list(
        value.researchScopes,
        (s) =>
          object(s) &&
          id(s.id) &&
          text(s.title) &&
          Number.isInteger(s.firstPosition) &&
          Number.isInteger(s.lastPosition) &&
          Number(s.firstPosition) >= 1 &&
          Number(s.lastPosition) >= Number(s.firstPosition) &&
          list(s.references, (r) => text(r) && r.startsWith("https://")),
      )) ||
    (value.researchState !== undefined &&
      !(
        object(value.researchState) &&
        text(value.researchState.status) &&
        (value.researchState.jobId === null || id(value.researchState.jobId)) &&
        (value.researchState.error === null ||
          text(value.researchState.error)) &&
        (value.researchState.coverage === undefined ||
          value.researchState.coverage === null ||
          text(value.researchState.coverage))
      )) ||
    (value.unorderedMilestones !== undefined &&
      !list(value.unorderedMilestones, step)) ||
    (value.coverage !== undefined &&
      !(
        object(value.coverage) &&
        text(value.coverage.status) &&
        [
          "acceptedEvents",
          "validatedMilestones",
          "entries",
          "orderingGaps",
        ].every(
          (k) =>
            Number.isInteger(
              value.coverage && (value.coverage as RecordValue)[k],
            ) && Number((value.coverage as RecordValue)[k]) >= 0,
        )
      )) ||
    (value.relations !== undefined &&
      !list(
        value.relations,
        (edge) =>
          object(edge) &&
          id(edge.id) &&
          id(edge.source) &&
          id(edge.target) &&
          text(edge.type),
      )) ||
    (value.entryIndex !== undefined &&
      !list(
        value.entryIndex,
        (e) => object(e) && id(e.id) && text(e.displayTitle),
      )) ||
    !list(
      value.sources,
      (s) =>
        object(s) &&
        id(s.id) &&
        text(s.title) &&
        text(s.url) &&
        /^https?:\/\//.test(s.url) &&
        text(s.locator) &&
        !!s.locator.trim(),
    ) ||
    !list(
      value.journeys,
      (j) =>
        object(j) &&
        scoped(j) &&
        text(j.title) &&
        text(j.introduction) &&
        (j.presentationState === undefined ||
          (object(j.presentationState) &&
            text(j.presentationState.status) &&
            text(j.presentationState.reason))) &&
        (j.overview === undefined || text(j.overview)) &&
        text(j.spoilerScope) &&
        object(j.ordering) &&
        [
          "broadcast-presentation",
          "manga-chapter",
          "story-position",
          "unresolved",
        ].includes(String(j.ordering.basis)) &&
        text(j.ordering.explanation) &&
        ids(j.ordering.sourceIds) &&
        list(j.steps, step) &&
        (j.story === undefined || list(j.story, section)) &&
        (j.positionWord === undefined || text(j.positionWord)),
    ) ||
    !list(
      value.loreThreads,
      (t) =>
        object(t) &&
        scoped(t) &&
        id(t.conceptNodeId) &&
        text(t.title) &&
        text(t.introduction) &&
        text(t.spoilerScope) &&
        ids(t.discoveryIds) &&
        id(t.initialDiscoveryId) &&
        hint(t.presentation),
    ) ||
    !list(
      value.discoveries,
      (d) =>
        object(d) &&
        id(d.id) &&
        id(d.threadId) &&
        id(d.nodeId) &&
        text(d.title) &&
        text(d.explanation) &&
        ["established", "interpretation", "unresolved"].includes(
          String(d.classification),
        ) &&
        ids(d.sourceIds) &&
        ids(d.relatedDiscoveryIds) &&
        hint(d.presentation),
    )
  ) {
    throw new Error("The generated story response has an invalid structure.");
  }
  // All fields used by the existing renderer are checked above; backend extras stay outside it.
  return value as unknown as NarrativeCatalog;
}
