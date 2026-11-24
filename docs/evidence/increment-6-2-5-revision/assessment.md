# Romance Dawn revision replay

The controlled replay used the previously qualified Romance Dawn scene frames and the saved whole-section first draft. It did not rerun extraction, assemble the story by hand, or acquire fresh sources.

The latest [generated revision](luffy-origin.md) gives Higuma's escape and the encounter at sea clearer sentence boundaries. It still claims that Luffy was aboard the pirates' ship when they arrived at Foosha Village, and it drops his request to join Shanks. The saved first draft includes that request but also implies the pirates brought Luffy to the village.

The [archived scene reconstruction](../increment-6-2-5-recovery/origin-reconstruction.md) identifies the independent arrival and request clauses as `2.1` and `2.4`. It records the escape and intervention as `4.7–4.9`, the unresolved injury attribution as `4.10`, and the hat gift and request to return it as `5.3`. The departure preparation and Luffy's declaration remain unresolved in this writing input. The edit moves straight from the rescue to the hat gift, so a first-time reader still lacks the setup for the farewell.

The comparison reviewer noticed that the request disappeared but returned frame objects where numbered IDs were required. It also returned an empty unsupported-claims list despite the ship arrival. The revision gate rejected that response and retained the first draft for further checks. The alignment checkpoint retained the three valid rows from its first response, retried the two missing rows in that batch, and eventually mapped all 14 spans in the retained draft. These mappings were eligible for review.

Grounding then stopped on incomplete or duplicate sentence IDs. The unaligned diagnostic review of the revision independently surfaced the ship-arrival and invented retreat details, but some batches contained malformed IDs and some reasons contradicted the supplied frames. Editorial and originality checks did not finish. The [writer audit](writer-audit.json) preserves the drafts, gate results, and real provider usage. The replay recorded 15 successful Ollama responses, one Ollama invalid-output response, and one Groq rate-limit response.

The backend returned HTTP 200 with `status: pending` and `article: null` at the manga chapter 7 spoiler boundary. The writer-only replay is a diagnostic and does not persist a publication.
