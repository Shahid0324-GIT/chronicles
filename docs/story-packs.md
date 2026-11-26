# Story packs (draft worlds)

A story pack is one JSON file holding an arc's events (cast, places, causes), deep entry
pages and lore threads, each citing archived sources. It is AI-drafted, reviewed by you,
and loaded into its own `<world>-draft` world. It is never canonical or verified.

Run from `services/intelligence`.

1. Draft it from the local archive. Replies are cached, so rerunning resumes.

```powershell
..\..\.venv\Scripts\python -m src.build_story_pack --world one-piece --arc romance-dawn --subject "Luffy" --subject "Shanks" --subject "Gomu Gomu no Mi"
```

2. Read `story-packs/romance-dawn.md`, then edit `story-packs/romance-dawn.json`.

3. Check and load it. Loading replaces only the draft world.

```powershell
..\..\.venv\Scripts\python -m src.import_story_pack ..\..\story-packs\romance-dawn.json --check
```

```powershell
..\..\.venv\Scripts\python -m src.import_story_pack ..\..\story-packs\romance-dawn.json
```

4. Start the API and web app, then pick the draft world in the world switcher.

## Rules

- Every event, cause, statement and discovery cites a source; unknown references are rejected.
- A cause is listed only when a cited sentence supports it. Order alone is not a cause.
- The chapter boundary hides events, pages, sections and lore from later chapters.
- Source filtering is not supported for draft worlds.
- `story-packs/` is git-ignored because it quotes source text.
