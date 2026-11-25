# Arc-first Romance Dawn benchmark

## Artifacts

- [Partial Arc Dossier](dossier.md) is a readable audit assembled from actual API assertions, with references. It is not generated reader prose.
- [Previous generated Origin draft](../increment-6-2-5-research-integration/luffy-origin.md) is the last complete Markdown draft from the earlier frozen-evidence iteration. The publication gate withheld it. This iteration did not reuse it to represent the new arc article.

## Live arc-wide research

Job `a17853be-710d-400a-a97c-923b303b97cd` surveyed the original manga's chapter 1–7 scope before scene qualification. Its four sections covered Origin, First Voyage and Koby, Zoro and Morgan, and the resolution. It started with 43 accepted assertions. Two SearXNG queries returned no results. Permitted registry retrieval supplied these records.

| Source | Indexed chapter | Result |
| --- | ---: | --- |
| [Healthy Dose of Anime chapter-one review](https://healthydoseofanime.blogspot.com/2018/10/one-piece-chapter-1-review-romance-dawn.html) | 1 | Existing selection refreshed |
| [Binder Pirates, volume one](https://www.binderpirates.com/story/volumes/1) | 3 | Existing selection refreshed |
| [Grand Line Wiki manga reference](https://grandlinewiki.net/eastbluearcM.html) | 7 | New scoped archive record |
| [Aaron Ngo's chapters 1–7 review](https://www.aaronngo.com/blogthread/2021/2/5/one-piece-east-blue-saga-romance-dawn-arc-chapters-1-through-7-manga-review) | 7 | New scoped archive record |

The worker restarted from the saved research checkpoint and reused two extraction responses and eight embeddings. The verifier supported six of 19 candidates. Publication retained two events and recorded zero new relationships. One event describes Higuma taking Luffy hostage (`45f60d78-c054-5eb7-863d-9564de43c9c4`). The other describes Luffy using his rubber arm to defeat the sea creature (`89ba72d6-cc28-5e56-ac1c-36dc44ce5ae8`). The dossier grew to 45 accepted assertions. These additions serve different parts of the progression and do not establish an ordered or causal link between the events.

The arc endpoint returned HTTP 200 with a partial dossier, a withheld article, and zero validated sections. Origin's plan included a clause that did not match its accepted assertion span. The API had also materialized the default inference policy as if it were supplied by the caller, so the other sections ran into the configured stage cap. The measured research run used Ollama `qwen3.5:4b` throughout. Its ledger reported 36 calls including one incomplete reservation, two cache hits, and 83,154 measured input and 4,667 measured output tokens.

## Production Origin follow-ups

Job `b75863a7-d7be-4bb0-a097-c845c2709133` ran with the corrected default policy. The full archive was too noisy for a single section's detailed plan: one Groq request failed schema validation, another was rate-limited, and the Ollama replies omitted required anchor or clause fields. The worker withheld the section before composition.

Job `9439dbc0-520a-491a-a2f4-2b48d570ecac` used the compact whole-arc assignment. Ollama returned a complete assignment, grouping 16 accepted assertions for Origin, eight for First Voyage, eight for the Morgan conflict, and six for the resolution. Some assertions appeared in more than one section. Twelve IDs had explicit omissions. Groq returned a detailed Origin proposal after two schema failures on assignment. That proposal cited a source outside the accepted sources for one of its assertions. Binding rejected it.

Job `be0694fe-7662-4b27-b19d-aa1042d93e75` reused the saved assignment with explicit per-assertion evidence options. Groq was rate-limited and Ollama supplied a proposal. Binding rejected a rewritten assertion that did not match the accepted text. The planner now selects accepted assertions by ID and derives their text from those records. The existing source and semantic review gates still apply.

The final continuation, `de784cfb-d2f3-4a44-8c53-69281f87ce29`, cleared that text mismatch. The local fallback still chose evidence outside the accepted sources for one setup assertion. The verifier withheld the section before scene reconstruction. It generated no new article Markdown. The production API returned HTTP 200, a partial dossier, and zero validated sections. First Voyage was not run as a standalone publication benchmark because Origin had not qualified.

Manual pauses use the existing checkpoint and the `pause` and `resume` research job endpoints. Automatic provider deferral keeps the job queued with a recorded cause and next attempt time. Waiting does not consume active execution time. No timed provider pause fired in the completed live runs above. Groq's rate-limited attempt fell back to Ollama.
