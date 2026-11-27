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
