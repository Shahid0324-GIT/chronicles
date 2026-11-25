# Romance Dawn research integration

## Frozen evidence

The [complete generated draft](luffy-origin.md) includes the confrontation, the Devil Fruit revelation, the kidnapping, the rescue, and the farewell. It still repeats the opening, attributes some transitions without clear support, and leaves the injury attribution ambiguous. The farewell declaration is also truncated. The draft was withheld.

The first run mapped 15 of 21 sentences. The later batches received out-of-batch sentence numbers from the model. Batch-local identifiers let the continuation map all 21 while retaining the original 15 mappings. The subsequent factual review available to the gate covered five sentences. The fallback reviewer did not qualify for the remaining decisions. The attempted factual repair returned the whole section instead of the requested target paragraph. A saved editorial response had 13 issues and exceeded the assessment contract's 12-item limit. The report now bounds the public diagnostic list while retaining the editorial veto and the raw checkpoint.

## Online research

The actual chapter-7 Origin job ran through the existing LangGraph worker as job `efd9d030-58e1-49bb-b98e-13e8fbfdfd6c`. It submitted six discovery queries and recorded five results that yielded no eligible evidence. The permitted registry supplied two archived sources. Two other URLs were rejected because their robots policy was unavailable. The worker reached verification and expired with `job_duration_exceeded` before promotion. This run ended before a second research round could be demonstrated with newly accepted evidence.

The archived chapter-one review explicitly names Shanks as the person whose arm was bitten off while saving Luffy. Its evidence had not entered the canonical dossier at the end of that job. [Archived review source](https://healthydoseofanime.blogspot.com/2018/10/one-piece-chapter-1-review-romance-dawn.html) · [Second archived source](https://www.binderpirates.com/story/volumes/1)

The archive-only follow-up ran as job `229614a7-a35a-4d9f-806a-cc87157b8b8f` with web discovery disabled. It reached the narrative builder. The verifier supported the rescue candidate, but the identity decision claimed a match without identifying the target record. The token budget blocked remaining verification. The job recorded eight unresolved candidates and zero promotions. The chapter-7 API returned HTTP 200 with a withheld article and zero validated sections. No enriched article was published, and First Voyage was deferred. [Benchmark audit](benchmark-audit.json)

## Workflow changes

Focused online arc jobs can use evidence questions from a validated development plan as inputs for another pass through the existing research graph. Planning and reviewer errors stay in diagnostics. Follow-up work requires new eligible evidence or canonical developments and unresolved evidence questions under the original job budget. Verification now checkpoints exact per-claim decisions, and sentence grounding can reuse decisions whose scoped evidence and surrounding prose are identical.
