# Story packs (draft worlds)

A story pack is one JSON file holding an arc's events (cast, places, causes), deep entry
pages and lore threads, each citing archived sources. It is AI-drafted, reviewed by you,
and loaded into its own `<world>-draft` world. It is never canonical or verified.

Run from `services/intelligence`.

1. Draft it from the local archive. Replies are cached, so rerunning resumes.

```powershell
..\..\.venv\Scripts\python -m src.build_story_pack --world <world> --arc <arc> --subject "<name>"
```

2. Read `story-packs/<arc>.md`. Put corrections in `story-packs/<arc>.edits.json`;
   they are reapplied whenever the draft is regenerated (editing the pack file directly is
   overwritten by the next generation). Corrections are keyed by event and entry keys:
   `events` (title, summary, label, sources, `after` to move), `chapter_labels`, `rename`,
   `merge` (from into), `drop`, `introductions`, `drop_statements` (exact text) and
   `drop_links` ("cause-event>effect-event").

3. Check and load it. Loading replaces only the draft world.

```powershell
..\..\.venv\Scripts\python -m src.import_story_pack ..\..\story-packs\<arc>.json --check
```

```powershell
..\..\.venv\Scripts\python -m src.import_story_pack ..\..\story-packs\<arc>.json
```

4. Start the API and web app, then pick the draft world in the world switcher.

## Rules

- Every event, cause, statement and discovery cites a source; unknown references are rejected.
- A cause is listed only when a cited sentence supports it. Order alone is not a cause.
- The chapter boundary hides events, pages, sections and lore from later chapters.
- Source filtering is not supported for draft worlds.
- `story-packs/` is git-ignored because it quotes source text.

## Story library (new path)

`library/<world>/world.json` names the world, its medium, its position word and its arcs.
Each arc keeps saved pages in `library/<world>/<arc>/sources/*.json` with `url`, `title`,
`position`, `text`, `licence` and `cloud_allowed`. See `samples/lantern-marsh/`. The library
is git-ignored. Run from `services/intelligence`:

```powershell
..\..\.venv\Scripts\python -m src.chronicle check lantern-marsh the-search --library ..\..\samples
```

`build <world> <arc>` drafts `pack.json` and `review.md` in the arc folder (corrections go in
`edits.json`). `load <world>` merges every drafted arc into the one draft world.
`samples/glass-orchard/` is a longer owned story for judging the article.

## From the app

Open **New story** (`/new`) with the API and web app running:

1. Name the story, the arc and its kind.
2. Paste a link to the wiki page about it. "Suggest wikis" offers AI guesses; none is
   contacted until you check it.
3. "Check this site" reads that page within the site's rules and shows its name, licence and
   headings. You confirm the terms allow automated reading, and decide whether its text may
   go to cloud models.
4. Review the proposed page list: untick pages and correct their order (at least three).
5. The build runs in the background; progress is saved in `<arc>/job.json`. A failed or
   interrupted build can be resumed. Finished replies and saved pages are reused.

One build runs at a time. Only MediaWiki wikis work. Sites known to forbid automated reading
are refused, and a bot check is never worked around. The checks cannot read a site's terms
for you. A second arc of a story appears in the same world, chosen with the arc picker.

Writes to `/api/builds` need the `X-Chronicles-Local: 1` header, so other websites cannot
start builds. The API is meant for this computer only; do not expose it.

## Scout: finding sources

`scout` reads wikis you approve, finds the pages that tell an arc and saves their story
sections. Approve a site in `world.json`:

```json
"sites": [{"pages": "https://www.khwiki.com/", "cloud_allowed": true}],
"arcs": [{"key": "first-journey", "title": "Sora's First Journey",
          "sections": ["story / kingdom hearts"]}]
```

- Give `api` (a MediaWiki `api.php`) or `pages` (the address article titles are added to),
  whichever the site's robots rules allow. `sections` names the story headings; a name with
  `/` is an exact heading path.
- `cloud_allowed` stays false unless you decide that site's text may go to cloud models.

```powershell
..\..\.venv\Scripts\python -m src.chronicle scout <world> <arc> --start "<overview page>" --about "<what to cover>"
```

The chosen pages are listed in `<arc>/pages.json`. Edit it and run `scout` again to correct
the choice; saved pages are not fetched twice (delete a source file to refetch it).

Rules it follows:

- Only approved hosts, within each site's robots rules and requested delay.
- A site that answers with a bot check is left alone. Never work around one.
- Check a site's terms before approving it. Some forbid automated reading even where robots
  rules do not (Fandom's terms, checked 2026-11-27).
- Each saved page keeps its link, revision and stated licence. Keep credit, and note that
  share-alike and non-commercial licences also cover what you make from them.
- A model picks only among titles the site returned. It can pick wrongly, so read the list.

## Story order

Pages organised by place or person tell return visits and endings beside first events.
Before reading, `build` asks a model which paragraphs belong elsewhere and moves only those
whose own words show it; the quoted words must be in the moved paragraph.

- Every move is listed under "Check these" in `review.md`. A quoted clue shows the move has
  support, not that the new place is right.
- A paragraph moved later belongs to that later part. One moved earlier stays behind the
  spoiler boundary of the page that told it.
- Only whole paragraphs move. One without a quoted clue moves only as the continuation of
  the paragraph before it, and a page's first paragraph never moves.
- Set `"reorder": false` on an arc whose sources are already in order.

## Entry pages

- Names are judged in small groups beside the sentences that first mention them. Generic
  words get no page; a name the story keeps using is always kept.
- Spellings merge only when they are variants of one name, such as a surname or a shorter
  place name. Anything else stays apart and is listed under "Check these"; use `merge` in
  `edits.json` when they are the same.
- An introduction uses only the subject's first appearance, so it does not spoil later
  events.
- The most mentioned subjects get a deep page drawn from across the whole arc
  (`build --pages 12`; `--subject` adds one).
- Each page also lists who the subject appears alongside and its events; event pages list
  who is there, where, and what led to and from it. These are assembled, not written.

## The journey page

A pack also tells the arc as an article: an opening paragraph, then headed sections of prose
tied to events and sources. The app opens a told arc as a journey:

- a full opening with the story's title and artwork;
- a tree (React Flow) of stops, one per chapter or place, where the chosen stop grows its
  moments and the stated causes between them;
- reading stop by stop or straight through, with names opening their entry page;
- a spoiler limit set from the map: hidden stops are revealed only after you confirm.

Each story has its own look. The model picks a background, two colours, a heading style and
a motif; code derives the rest and adjusts colours until text passes contrast. Override it
in `edits.json` with `"theme": {...}`. A pack without a theme gets a steady default of its
own. A new story is built from the **New story** screen.

### How the article is written

- The writer gets a few events and all their source sentences per section, so its length
  follows the sources. A section much shorter than its sources, or one that skips an event,
  is asked for once more and then listed under "Check these".
- A second model pass checks each section against its sources. It only points at sentences:
  the writer then rewrites the section once, and each finding is listed under "Check
  these". The checker can be wrong and can miss things.
- Paragraphs without a cited sentence are dropped. Citations show that a paragraph has
  support, not that every phrase in it is correct, so read the article before trusting it.
- Correct wording in `edits.json` with `"story_text": {"exact text": "replacement"}`; an
  empty replacement removes the text.
- Names link by entry name, alias or unshared first name, once per section.
- A section partly hidden by the spoiler boundary loses its heading.
