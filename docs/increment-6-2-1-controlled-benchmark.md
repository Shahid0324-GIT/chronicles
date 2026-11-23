# Increment 6.2.1 controlled reconstruction benchmark

The controlled run used fixed, permitted archive spans. The scope was selected by section boundary, with no handwritten story order or prose. Source units retained their document and passage hashes and archive offsets. A second chapter-one reference supplied rescue and departure context for the origin test. The first-voyage test used the supplied reference section through the Alvida confrontation. The source accounts are secondary material. Their text placement establishes reference presentation order, and in-world dates require separate evidence.

| Controlled section | Frozen units | Planned developments | Reference integrity | Structural review | Editorial review |
| --- | ---: | ---: | --- | --- | --- |
| Luffy’s Origin and Devil Fruit Acquisition | 54 | 5 | Passed | Unavailable after malformed responses and provider rejection | Pending |
| Luffy’s First Voyage and Meeting Koby | 20 | 4 | Passed | Blocked by a caption anchor and missing context | Pending |

The origin proposal groups the opening context, arrival and refusal, bar confrontation and rubber revelation, bandit conflict and rescue, and the farewell. Its structure is provisional. The voyage proposal reached a real Groq structural review, which did not approve the selected anchors. The first provider run also exposed an output mismatch in which the planner named anchors outside a clause’s evidence. The fixed-input adapter now derives anchor references from source units already assigned to clauses. It feeds the same validation and composition services as the graph-backed path.

Both controlled runs stopped before prose. The earlier live baseline still has 26 accepted assertions and zero validated article sections. These results isolate evidence organization and structural assessment as a bottleneck under fixed input. Successful autonomous acquisition and a successful end-to-end article remain unverified in this increment. The preserved plans do not establish that all context needed for the finished prose was selected.

Development iterations used 17 provider attempts across the two sections, including rate limits and failed structured responses. Origin recorded 9 attempts with 9,108 returned input tokens and 3,917 output tokens. Voyage recorded 8 attempts with 12,207 returned input tokens and 6,588 output tokens. Those totals are measured only for responses that returned token usage. There were no composition or editorial calls, web requests or canonical graph writes. The runner now carries the attempt count forward when resuming a saved plan.

The production plan includes stable development IDs, source evidence, clause modalities, negation and source-specific partial orders. It separates reference order from proposed chronology and other relationships. A structurally blocked plan stops the writer. Pending prose that passes deterministic checks can be resumed using its stored review artifact. The controlled benchmark uses the same composer with isolated presentation storage.

## Reproducing the benchmark

Run from `services/intelligence` with the existing selected source archives and provider configuration. `--freeze` records or verifies the input hash without inference. Running a section without a flag generates and assesses the plan. `--resume-review` reuses the saved plan when review was unavailable. `--compose` reads the saved decision and runs only when both plan checks passed. Review the development plan before invoking composition.

```powershell
..\..\.venv\Scripts\python -m src.benchmark_621 origin --freeze
..\..\.venv\Scripts\python -m src.benchmark_621 voyage --freeze
```

Full local artifacts are under `.tmp/benchmark621`. Public inspection copies retain original source coordinates and clause hashes in place of archived source text. The Markdown files record the withheld outcome.

- [Origin Markdown](evidence/increment-6-2-1/origin.md) · [Development plan, evidence mapping and usage](evidence/increment-6-2-1/origin.json)
- [Voyage Markdown](evidence/increment-6-2-1/voyage.md) · [Development plan, evidence mapping and usage](evidence/increment-6-2-1/voyage.json)
- [Reproduced live baseline](increment-6-2-1-baseline.md)
