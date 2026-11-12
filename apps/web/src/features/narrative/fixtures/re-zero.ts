import type { NarrativeCatalog } from "../contracts";
import { RE_ZERO as N, RE_ZERO_EDGES as E } from "./re-zero-ids";
const threadId = "re-zero-return-by-death";
const fact = "official-opening";
const premiere = "broadcaster-introduction";
const returnSource = "episode-two-synopsis";
/** Manual editorial presentation. Entities/relationships are resolved exclusively from FastAPI. */
export const RE_ZERO_NARRATIVE: NarrativeCatalog = {
  schemaVersion: 1,
  sources: [
    {
      id: fact,
      title: "Official anime story guide",
      url: "https://re-zero-anime.jp/tv/story/tv1r.html",
      locator:
        "Original TV season 1, episodes 1–2 only; the page also contains later-story spoilers.",
    },
    {
      id: premiere,
      title: "TV Tokyo introduction",
      url: "https://www.tv-tokyo.co.jp/anime/re-zero/story/",
      locator:
        "Opening premise: Subaru arrives, receives help, and joins the search.",
    },
    {
      id: returnSource,
      title: "Licensed episode 2 synopsis",
      url: "https://tv.apple.com/us/episode/episode-2/umc.cmc.60smxe7gvy3ak446dw2trjhhk",
      locator:
        "Season 1, episode 2: repeated returns and Subaru naming the phenomenon.",
    },
  ],
  journeys: [
    {
      id: "re-zero-introduction",
      universeId: N.universe,
      continuityId: N.anime,
      title: "A stranger, a promise, a return",
      introduction:
        "Enter the opening through Subaru's experience. Four moments introduce a world whose beginning can be encountered again.",
      spoilerScope:
        "Original TV anime · episodes 1–2 · death and return spoilers",
      ordering: {
        basis: "broadcast-presentation",
        explanation:
          "An editorial route through the original broadcast's presentation, not a single linear in-world timeline. Repeated attempts are acknowledged, not merged.",
        sourceIds: [fact, premiere, returnSource],
      },
      steps: [
        {
          id: "arrival",
          eventNodeId: N.arrival,
          title: "A world without a welcome",
          body: "Subaru arrives without understanding where he is. The capital is unfamiliar, and the help he receives becomes his first connection.",
          episodeLabel: "EPISODE 01 · THE ARRIVAL",
          sourceIds: [premiere, fact],
          loreThreadIds: [],
          presentation: {
            relatedNodeIds: [N.subaru, N.capital],
            relationshipIds: [E.arrivalPlace, E.arrivalParticipant],
            focusRatio: 0.9,
          },
        },
        {
          id: "promise",
          eventNodeId: N.search,
          title: "A promise in an unfamiliar city",
          body: "A silver-haired girl helps Subaru. He joins her search for the stolen insignia, turning a chance encounter into a shared purpose.",
          episodeLabel: "EPISODE 01 · THE FIRST SEARCH",
          sourceIds: [premiere, fact],
          loreThreadIds: [threadId],
          presentation: {
            relatedNodeIds: [N.subaru, N.emilia, N.insignia, N.capital],
            relationshipIds: [
              E.searchParticipant,
              E.emiliaSearch,
              E.searchObject,
              E.searchPlace,
            ],
            focusRatio: 0.92,
          },
        },
        {
          id: "return",
          eventNodeId: N["first-return"],
          title: "An ending that leads back",
          body: "The initial search ends in a fatal encounter at the loot house. Subaru then finds himself back in the capital; this is a return, not the next ordinary day.",
          episodeLabel: "EPISODE 01 · THE FIRST RETURN",
          sourceIds: [fact, returnSource],
          loreThreadIds: [threadId],
          presentation: {
            relatedNodeIds: [
              N.subaru,
              N["loot-house"],
              N.capital,
              N["return-by-death"],
            ],
            relationshipIds: [
              E.returnParticipant,
              E.returnLoot,
              E.returnPlace,
              E.returnPhenomenon,
            ],
            focusRatio: 0.92,
          },
        },
        {
          id: "recognition",
          eventNodeId: N.recognition,
          title: "Giving the impossible a name",
          body: "After repeated deaths and returns, Subaru identifies the pattern as Return by Death. This introduction ends with that recognition, leaving its cause open.",
          episodeLabel: "EPISODE 02 · RECOGNITION",
          sourceIds: [fact, returnSource],
          loreThreadIds: [threadId],
          presentation: {
            relatedNodeIds: [
              N.subaru,
              N["return-by-death"],
              N["return-origin"],
            ],
            relationshipIds: [
              E.recognitionParticipant,
              E.revealsReturn,
              E.phenomenonMystery,
            ],
            focusRatio: 0.92,
          },
        },
      ],
    },
  ],
  loreThreads: [
    {
      id: threadId,
      universeId: N.universe,
      continuityId: N.anime,
      conceptNodeId: N["return-by-death"],
      title: "Return by Death",
      introduction:
        "Trace an observed pattern, the name Subaru gives it, and the question the opening leaves unanswered.",
      spoilerScope: "Original TV anime · episodes 1–2 only",
      initialDiscoveryId: "the-return",
      discoveryIds: [
        "the-return",
        "recognizing-the-pattern",
        "a-reading-of-second-chances",
        "the-open-question",
      ],
      presentation: {
        relatedNodeIds: [
          N.subaru,
          N["first-return"],
          N.recognition,
          N["return-origin"],
        ],
        relationshipIds: [
          E.returnPhenomenon,
          E.revealsReturn,
          E.phenomenonSubaru,
          E.phenomenonMystery,
        ],
        focusRatio: 1,
      },
    },
  ],
  discoveries: [
    {
      id: "the-return",
      threadId,
      nodeId: N["first-return"],
      title: "The impossible return",
      explanation:
        "A fatal encounter does not end Subaru's experience. He finds himself back where his encounter with this world began.",
      classification: "established",
      sourceIds: [fact, returnSource],
      relatedDiscoveryIds: ["recognizing-the-pattern", "the-open-question"],
      presentation: {
        relatedNodeIds: [
          N.subaru,
          N["return-by-death"],
          N.capital,
          N["loot-house"],
        ],
        relationshipIds: [
          E.returnParticipant,
          E.returnPhenomenon,
          E.returnPlace,
          E.returnLoot,
        ],
      },
    },
    {
      id: "recognizing-the-pattern",
      threadId,
      nodeId: N.recognition,
      title: "Recognizing a repeated beginning",
      explanation:
        "Subaru can compare the repeated attempts. By episode 2, he recognizes the returns and calls the phenomenon Return by Death.",
      classification: "established",
      sourceIds: [fact, returnSource],
      relatedDiscoveryIds: [
        "the-return",
        "a-reading-of-second-chances",
        "the-open-question",
      ],
      presentation: {
        relatedNodeIds: [N.subaru, N["return-by-death"]],
        relationshipIds: [E.recognitionParticipant, E.revealsReturn],
      },
    },
    {
      id: "a-reading-of-second-chances",
      threadId,
      nodeId: N.subaru,
      title: "A second chance is still a burden",
      explanation:
        "An interpretive reading: repeating a beginning changes the meaning of choice and responsibility. This is an editorial lens, not an additional rule of the ability.",
      classification: "interpretation",
      sourceIds: [premiere, returnSource],
      relatedDiscoveryIds: ["recognizing-the-pattern", "the-open-question"],
      presentation: {
        relatedNodeIds: [N["return-by-death"], N["first-return"]],
        relationshipIds: [E.phenomenonSubaru, E.returnParticipant],
      },
    },
    {
      id: "the-open-question",
      threadId,
      nodeId: N["return-origin"],
      title: "What causes the return?",
      explanation:
        "This introductory scope does not establish the cause. Keep the question open rather than turning an unanswered point into a confirmed explanation.",
      classification: "unresolved",
      sourceIds: [fact, returnSource],
      relatedDiscoveryIds: ["the-return", "recognizing-the-pattern"],
      presentation: {
        relatedNodeIds: [N["return-by-death"]],
        relationshipIds: [E.phenomenonMystery],
      },
    },
  ],
};
