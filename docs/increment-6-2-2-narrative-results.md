# Increment 6.2.2 narrative results

## Luffy’s origin

The controlled run produced five paragraphs. Chronicles withheld the section. Draft structure and citation references passed deterministic checks. Human inspection rejected specific factual and editorial choices, and model grounding did not complete within the run budget. [Complete generated draft](evidence/increment-6-2-2/origin-rejected.md)

## First voyage

The origin acceptance gate remained unmet. The first-voyage benchmark was therefore deferred under the execution order for this increment. Its existing controlled evidence remains available. [First-voyage baseline](evidence/increment-6-2-1/voyage.md)

## Evidence and grounding

Each paragraph maps to scoped clause IDs, frozen reference assertions, archived passage IDs, source revisions and document offsets. These are secondary source references as used by the controlled benchmark. No canonical records were written. [Paragraph evidence appendix](evidence/increment-6-2-2/origin-evidence.md) · [Full mapping and validation outcomes](evidence/increment-6-2-2/origin-assessment.json)

## Narrative quality

- **Comprehension and context.** The draft explains why Luffy wanted to join Shanks, why Shanks refused, and how Higuma’s dispute and subsequent kidnapping led to the rescue. The opening starts with Roger’s announcement and provides a time transition to Foosha Village. Some names appear during the confrontation with little context.
- **Flow and detail.** The bar scene moves naturally from Shanks’s refusal to fight to Luffy’s reaction and the discovery of his altered body. The rescue paragraph covers the kidnapping, confrontation, escape, and rescue in one dense block. The departure paragraph repeats the crew’s decision to leave at its end.
- **Factual support.** Paragraph two says Luffy “proved his toughness.” The reference describes his goal in cutting himself. The sentence does not establish that he proved anything. Paragraph four leaves the owner of the lost arm ambiguous. The separate archived chapter-one account explicitly attributes the injury to Shanks, and the generated sentence should have used a supported name or omitted the detail. The evidence appendix records what the model cited for both claims.
- **Source fidelity and originality.** The developmental order is readable and the conflict has a resolution. Several sentences track the wording of the source closely. The writer needs to synthesize each scene more independently while retaining the same claim citations. The output has encyclopedia-like coverage but does not yet meet the publication standard.

After the benchmark, the composer gained a pre-review originality check for exact runs of 18 or more normalized words from an archived source unit. A zero-inference replay flagged paragraphs 1 through 4 of the saved draft. This checks verbatim reuse. Editorial review is still needed to judge close paraphrase and flow.

## Implementation and provider usage

The 6.2.1 origin plan was reconstructed from its saved artifact. The prior request sent every development and all evidence to one semantic reviewer. It ended with provider request failures and incomplete local structured responses. The voyage baseline also exposed a caption anchor. The new path reviews batches of up to three developments. Python verifies each clause-ID partition, rejects inconsistent decisions, checks that an anchor refers to a supported clause, rebuilds separate source orders, and carries unresolved developments into coverage. It defers cross-development story relations for explicit evidence review. Multi-actor developments are reviewed clause by clause.

The reviewer selected a caption for the rescue despite the prompt. Reconciliation rejected adjacent repeated labels as action anchors, retaining the original evidence references. The rescue anchor moved from document offset 2144 to 2202 and the Roger development moved from 42 to 100. The first prose request then failed at both provider adapters. The successful compact request sent each accepted clause once and included additional cited context only where it differed from the clause text.

Six provider attempts comprised two successful Groq development reviews, two rejected composition requests, one successful Groq composition request, and one successful Groq reviewer qualification response. The next grounding call was blocked by the benchmark budget. Providers reported 7,687 input and 7,714 output tokens across successful responses. The generated draft remains available in the pending-review artifact. No frontend files were changed during this increment. [Measured provider outcomes](evidence/increment-6-2-2/origin-assessment.json)

The isolated backend and PostgreSQL suite passed 312 tests with one skip before the final originality check. After that change, 32 focused tests passed. Ruff, formatting, mypy and Alembic checks passed. The browser fixture was left out to preserve the frontend freeze.
