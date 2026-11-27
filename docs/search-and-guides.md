# Search and guide pages

The home page is one search box. A model reads what was typed and says which of these it
is; the reader can correct it before anything is read.

| Asked for | Result |
|---|---|
| A whole story | Not built. The reader is offered a summary, an arc or a character |
| A summary | Premise, the story so far, main cast and supporting cast |
| An arc | How it begins, what happens, how it ends |
| A character | Overview, background, personality, powers, role by arc, relationships, latest status |

A section the sources say nothing on is shown as not found. It is never filled in.

## Sources

Wikipedia only, in English, Japanese and Chinese (CC BY-SA). The app reads ordinary
article pages, which Wikipedia's robots rules allow; it does not use the API. Starting a
page is the approval to read them and to send their text to the cloud models, and nothing
is fetched without it. Fandom is not used: its terms forbid automated reading.

1. The story's English page is found by name, or from a link the reader pastes. It is
   refused if it does not name the story.
2. A model picks up to four related pages from that page's own links, and the Japanese and
   Chinese pages are reached through its language links.
3. Passages are chosen (a character's list entries and own page; plot sections; the arc's
   passages and episode summaries), within a size limit per language that keeps a page
   inside the free allowances.
4. Japanese and Chinese passages are translated to English, spelling names as the English
   pages do. A reply much shorter than its original is dropped.
5. Passages are sorted into sections, each section is written from its own passages, and
   a second call removes sentences it cannot find support for, after one rewrite.

Every paragraph lists its sources. Opening one shows the English text, the original when
it was translated, and the page link.

## Files and API

Pages are saved in `library/_guides/` (git-ignored) as `<key>.job.json` and
`<key>.guide.json`, with model replies cached beside them, so resuming repeats little.
Asking for the same thing again opens the saved page.

- `POST /api/guides/understand` reads a search.
- `POST /api/guides` starts a page; `POST /api/guides/{key}/resume` resumes one.
- `GET /api/guides` and `GET /api/guides/{key}` read them.

Writes need the `X-Chronicles-Local` header.

## Limits

- Wikipedia is much thinner than a fan wiki. Later arcs and minor characters get little.
- Machine translation can be wrong, especially about who did what.
- The check that removes sentences can miss errors and can remove true statements; the
  notes at the foot of a page list what was removed.
- There is no chapter-by-chapter spoiler limit, only a warning before the page is shown.
- Story names that Wikipedia titles differently may need the page link pasted.
- Wikimedia asks automated readers to give a contact address in their identification;
  the app currently sends only its name, and reads a few pages at a time.
