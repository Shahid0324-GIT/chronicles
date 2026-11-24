# Romance Dawn · Luffy’s Origin

The controlled run retained three distinct rescue transitions from the existing reviewed development plan. The stricter event-frame review admitted no frames, so the result below is a partial reconstruction of the source account. The clause relationships have their own verification history. Their presence cannot qualify the actor and action frames on either end.

## Rescue progression carried forward from the development plan

| Clause transition | Supported reading | Archive references |
| --- | --- | --- |
| `4.7 → 4.8` · `link-12` | Benn Beckman overpowers the bandits. Higuma escapes with Luffy and takes him out to sea. The account presents those actions before Higuma sends Luffy into the water. | F, `2938–3255`. H, `4206–4237` and `4257–4316`. |
| `4.8 → 4.9` · `link-11`, `link-14` | The Sea King first approaches Higuma, then turns toward Luffy. Shanks intervenes to save Luffy. These are two records of the same clause transition. | F, `3088–3362`. H, `4487–4581`. |
| `4.9 → 4.10` · `link-13` | The account describes the rescue before Luffy reacts to Shanks losing his arm. The second reference names Shanks as the injured character. The review retained chronology and did not promote a specific causal mechanism. | F, `3256–3472`. H, `4656–4716`. |

The report uses half-open character offsets in the archived source. F is archive passage `67fd9486-2ccb-5f20-bad4-8f9abe9a5d40` in the supplied Romance Dawn reference. H is archive passage `cbb5369e-0541-53fb-9a0a-561e1879fff2` in the chapter-one review. The machine-readable audit lists the exact evidence IDs, passage hashes, and individual spans for each link. [Romance Dawn structural reference](https://onepiece.fandom.com/wiki/Romance_Dawn_Arc) · [Chapter-one review](https://healthydoseofanime.blogspot.com/2018/10/one-piece-chapter-1-review-romance-dawn.html) · [Archived evidence mapping](origin-audit.json)

## Unresolved scenes

| Development | Gate result |
| --- | --- |
| Roger’s execution and the Great Pirate Era | The reviewer returned ordinary frame decisions without passing both attribution controls. The proposed frames were withheld. |
| The Red Hair Pirates’ arrival and Luffy’s aspiration | The binder rejected a completed frame drawn from a non-completed clause without an exact excerpt for a separate action. The remaining review failed qualification. |
| The tavern conflict and Devil Fruit revelation | The first pass wrongly assigned the tavern exit to Higuma. The stricter review failed qualification, so neither the tavern scene nor the speaker and experiencer frames for the rubber-body revelation reached composition. |
| The Sea King and rescue | The earlier clause links above remain available. Separate action frames for the Sea King, Shanks’ intervention, and Shanks’ injury remained unqualified. |
| Promise, hat, and departure | Qualification failed before the final review batch. The run reached its configured ceiling. |

## Article status

**Withheld before composition.** Chronicles generated no new Markdown article. Alignment, prose grounding, coverage, originality, and editorial review had no draft to assess. The existing spoiler-bounded FastAPI endpoint returned HTTP 200 with `article: null`. First Voyage was held behind the Origin publication requirement.

## Benchmark record

The two passes shared one 30-call budget and the same frozen set of 54 evidence units. The second pass reused automatic extraction checkpoints. The first pass charged 18 calls and provisionally admitted 54 frames before spot checks exposed attribution and modality errors. The stronger pass charged the remaining 12 calls and superseded those accepts. Returned batches sometimes omitted both control IDs, omitted role and modality observations, or described incidental missing details as core gaps. Individual scene connectivity and archive permissions remained enforced.

The follow-up changes use uniform numbered review items and check the order of separately aligned claims within a scene. The owned tests exercise these changes. The shared provider budget was exhausted before a live run of the numbered response format.

Frame participants can link to uniquely named accepted character records. Unlinked names remain source-local and ambiguous canonical matches are held. The frame stage has yet to demonstrate canonical alias resolution or an article that preserves action order through composition and publication.

The benchmark reuses the archived plan with `python -m src.benchmark_621 origin --original --autonomous --scene --relationships --recovery --handoff --verified-frames` from `services/intelligence`. `--resume-review` replaces `--original` to reuse the existing budget and saved batch outputs. The controlled harness writes diagnostics locally. The backend API reads the existing database separately.

Actual calls used Groq `openai/gpt-oss-120b` and local Ollama `qwen3.5:4b`. Groq recorded 15 successful responses, two invalid-output responses and six rate-limit responses. Ollama recorded seven successful responses. Reported usage was 51,554 input tokens and 12,504 output tokens. These results exercise fixed-archive reconstruction. They establish no new web evidence or canonical publication. [Run audit](origin-audit.json)
