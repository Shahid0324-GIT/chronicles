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
  (v.participantRoles === undefined ||
    list(
      v.participantRoles,
      (r) =>
        object(r) &&
        id(r.nodeId) &&
        ["actor", "recipient", "witness", "opponent"].includes(String(r.role)),
    ));

export function decodeNarrative(value: unknown): NarrativeCatalog {
  if (
    !object(value) ||
    value.schemaVersion !== 1 ||
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
        (j.overview === undefined || text(j.overview)) &&
        text(j.spoilerScope) &&
        object(j.ordering) &&
        j.ordering.basis === "broadcast-presentation" &&
        text(j.ordering.explanation) &&
        ids(j.ordering.sourceIds) &&
        list(j.steps, step),
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
