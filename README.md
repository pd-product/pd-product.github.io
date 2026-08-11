# Personal site

Static site published by GitHub Pages at https://pdiggins.com

`pd-product.github.io` still resolves and 301s here. That redirect is GitHub's own behaviour for the
default Pages host once a custom domain is set, not something this repo configures.

## Copyright

Copyright (c) 2026 Patrick Diggins. All rights reserved. **No license is granted** to reproduce,
distribute, adapt, or create derivative works from the contents of this repository. Viewing and
forking within GitHub, per GitHub's Terms of Service, are permitted; no other rights are granted.
See [LICENSE](LICENSE).

This is deliberate, not an oversight. Third-party assets keep their own licenses.

Publishing source is **Deploy from a branch** (`main`, root). GitHub runs Jekyll on its side, so
there is no build step to run locally and no CI workflow to maintain. Pushing to `main` publishes;
allow a few minutes.

## Page set

`/` is the whole site apart from the stories. Everything else is an anchored block on the home page
rather than a separate page: `/#work`, `/#path-here`, `/#off-hours`, `/#about`, `/#contact`. Four of
those five are in the nav; `#path-here` deliberately is not, and `_config.yml` says why. Stories
live at `/work/<slug>/`.

## The two data-driven home sections

Off hours and The path here are edited in `_data/`, not in `index.html`, for the same reason the
nav is: adding, dropping or reordering an entry is a data edit and the template does not change.
Each file carries its own constraints at the top -- read them, because both have one that is not
obvious from the markup:

- `off-hours.yml` has no `numeral` key. The displayed `01`, `02` comes from position in the list,
  as everything numbered on this site does, so reordering renumbers itself.
- `path-here.yml` describes a career whose **third stop is current**. The fourth is a change in how
  the work is done, not a job.

Both files carry HTML entities in some strings -- `&amp;`, `&gt;`, `&middot;` -- to keep the source
ASCII, and both are printed without the `escape` filter for that reason. Adding an entry means
writing the entity, not the character. Escaping them renders the entity text on the page.

The same rule governs authored PROSE anywhere in the repo -- `_data` entries, story front matter,
tradeoff option names -- and it has two halves: **write entities, and expect them to survive.** No
template escapes one on its way into element content. Where such a value also lands in an
ATTRIBUTE, the template applies `escape_once` rather than `escape`: it escapes a bare `&` and the
double quote that would end the attribute early, and leaves a well-formed entity alone. Plain
`escape` would double it, and a value that prints in both places would then disagree with itself.
`_layouts/story.html` and `_includes/tradeoffs.html` each pair an attribute with content this way;
the comments on those lines own the detail.

**URLs and paths are not prose and do not take this rule.** Slugs, `hero_image`, nav `url` values
and the two contact links are written raw, carry no entities, and mostly reach their attributes
through `relative_url`. The contact pair keeps plain `escape`, which is right for an href: an `&`
in a query string has to become `&amp;` there. So do not write an entity into a URL -- an authored
`&amp;` in a `mailto:` would be escaped again and send the wrong address.

Grid shape is why the counts are what they are: six Off hours entries fill a 3-up and a 2-up grid
exactly, and four path stops fill a 4-up and a 2-up. A seventh or a fifth leaves a gap at a
breakpoint, which is a design question rather than only a data one.

## Adding a story

Copy `_work/example-story.md`. It carries `published: false`, so it is a template rather than a
page: it stays out of the built site, the home list, prev/next and the sitemap until a copy sets
`published: true`.

Required: `slug` (keep the filename identical to it), `title`, `category`, `order`, `description`,
`date` and `last_modified_at`.

**`date` and `last_modified_at` answer different questions and both are required.** `date` is when
the story was published and never moves. `last_modified_at` is when its content last changed, and
it is the only field here you have to remember to update: revise a story and it needs the new date,
by hand. Both `jekyll-seo-tag` and `jekyll-sitemap` read that one key, so it drives the JSON-LD
`dateModified` and the sitemap's `lastmod` together.

Leave it unset and neither is absent -- both silently fall back to `date`, so a revised story
reports itself unrevised in two places that agree with each other, which is what makes it look
right. Search engines are then told there is nothing to re-read, and the description they show
stays the old one. Do not bump it for a comment or a formatting edit; only for something a reader
would see. `_tools/check_dates.py` is what catches a forgotten update, and it knows the difference.

The rest are presentational -- `partners`, `chips`, `hero_image` and friends -- and a story that
omits one renders without it. Two carry a fallback rather than nothing: `crumb` falls back to
`title`, and `hero_alt` falls back to `title`, which is a weak image description rather than a
visible failure, so set it whenever you set `hero_image`.

Nothing guards `category`, `description` or `date`, and each fails differently. `category` and
`description` leave something visibly wrong on the page; `date` is the only one that fails with no
sign at all:

- `category` leaves an empty eyebrow on the home row and a dangling `01 /` on the story page when
  it is missing. It also drops the story-header field tint, since that is keyed to the value.
- `description` does not render on the home row, but it is still required: it is the line under the
  story title AND the page's meta description. Omitting it visibly removes that summary line from
  the story page, and silently corrupts the metadata -- `jekyll-seo-tag` falls back to the page
  excerpt, which is the first block of the body, so the story goes to search results and link
  previews described by its own opening heading. Only the second half is quiet.
- `date` has a silent WRONG default rather than an absent one. Without it Jekyll stamps build time,
  so `datePublished` and the sitemap's `lastmod` move on every deploy and re-announce the story as
  new. Use the date the story was published, not the date you are editing.

`order` is the global reading position and is required. It is a **sort key only**: the zero-padded
number is derived from the story's position in the sorted list, not from the value itself, so
duplicate, missing, zero, or negative values cannot render a duplicate number, a blank, `00`, or
`0-1`. The home row prints it as the large display numeral and the story page prints it inside the
eyebrow, but both derive it the same way and therefore always agree. Use unique
integers anyway -- ties have no defined order. No index needs editing.

Set `published: false` to keep a story in the repo but out of the built site. That is Jekyll's own
flag, so an unpublished story drops out of the home list, prev/next, and the sitemap together.

## Chapters

Each chapter is an `h2` with an explicit anchor:

```
## The situation    {#situation}
```

The rail is generated from those headings, so a story may omit a chapter that does not apply or add
one -- delete the section and its rail entry goes with it. The explicit anchor is what keeps a shared
deep link such as `/work/<slug>/#situation` working after the heading is reworded.

Chapters are numbered `01`, `02` by CSS, in the prose and in the rail. Do not write the number into
the heading text: the two counters walk the same set of headings in the same order, so adding or
dropping a chapter renumbers both and nothing needs editing. A hand-written number would survive
that renumbering and disagree with the rail.

Standard anchors: `#situation`, `#constraints`, `#the-call`, `#shipped`, `#redo`.

**`#redo` must stay the last chapter.** The accent bar down that chapter is a sibling selector that
claims every element after the `#redo` heading, so a chapter added below it inherits the accent and
reads as a bug. Adding one means rewriting that rule as a wrapper first -- see the comment on the
rule in `assets/css/style.scss`. Neither widening nor narrowing the selector fixes it.

The anchor is **required**, not optional. Kramdown's `auto_ids` is disabled in `_config.yml`, so a
heading without `{#id}` gets no id at all and drops out of the rail -- visibly, on the page. That is
deliberate: with `auto_ids` on, a forgotten anchor appears to work while minting an id from the
heading text, and every shared deep link then breaks the next time that heading is reworded.

Only the `{#id}` form is matched. The `{: .class #id}` form renders the class attribute first and
the chapter will be missing from the rail.

Authoring guidance, not enforced by the template: 3-8 rail entries is the comfortable range, and
heading text under about 24 characters avoids wrapping in the rail.

## Tradeoff tables

Declared in front matter, not as a Markdown table, so the chosen column is identified by name and
its marker can never land on the wrong column. Place it in the body where it belongs:

```
{% include tradeoffs.html tradeoffs=page.tradeoffs %}
```

`tradeoffs` is a list even with one table. Target 3 rows, 5 is the ceiling -- a story needing more
dimensions should add a second table for a second decision rather than a taller one.

Per table: `rejected` and `chosen` name the two options and head the two columns, and `rows`
carries one entry per dimension, each with its own `dimension`, `rejected` and `chosen`. A fourth
key, `title`, is optional and draws a caption above the table; omit it and the table has none.
Nothing else is read, and nothing errors. Omit `rejected` and its column head is blank; omit
`chosen` and the head keeps the check mark with no option name beside it; omit `rows` and the table
body is empty. In the first two the sub-640px stacked view loses that column's label as well, since
it is drawn from the same value.

**The include line is required and fails silently without it.** Declaring `tradeoffs:` in front
matter renders nothing on its own: the include is placed by hand, and `{% for table in nil %}`
iterates zero times without complaining. A story with a fully authored table and no include line
builds clean and ships without it.

## What the story prose supports

`.story-prose` styles `h2`, `p`, `ul`, `ol`, `figure`, `figcaption` and `a`. That is the whole list.

Anything else gets browser defaults inside a stylesheet that has already zeroed the margins on
`h1, h2, h3, p, dl, dd, dt, figure, table`. Measured on the built site, the two an author is most
likely to reach for are both worse than "unstyled" -- and neither looks like a mistake in the
source, only on the page:

- An **`h3`** renders as browser-default bold 18.72px with no margin at all. At 1280 that is just
  jammed against its neighbours. **At 390 it INVERTS the hierarchy**: the story `h2` drops to 18px
  at that breakpoint while the unstyled `h3` stays at 18.72px, so a subheading renders LARGER than
  the chapter heading above it.
- A **Markdown table** is unstyled next to the designed tradeoff table it will be compared with.
  It is also the one authoring slip that can take the page out of conformance: measured at 390, a
  bare five-column table pushes the document to `scrollWidth` 461 against `clientWidth` 390, giving
  the whole page a horizontal scrollbar and clipping every line of body prose at the right edge --
  a WCAG 1.4.10 reflow failure. `.story-prose > table` carries a containment guard so that cannot
  happen. **The guard is not support.** It keeps the page conformant and makes the table look
  cramped and wrong, which is the intended signal.

So: chapters are `h2`, and everything under them is paragraphs, lists and figures. A story that
genuinely needs an `h3`, a blockquote, code, a rule or a Markdown table needs those styles designed
first -- it is not an authoring decision to make mid-story.

Both list forms are styled and neither takes a marker in the source. An unordered list gets an
accent square, which is what the constraints chapter uses. An ordered list is numbered by CSS, so
author it as a plain markdown ordered list and let the counter supply `01`, `02`. Add
`{: role="list"}` after a list, as the existing stories do: the `list-style: none` reset drops the
implicit list role in Safari with VoiceOver.

## Assets

Diagrams and cards are committed at final size; there is no build-time image processing. Every page
shares one card, `default.png`, drawn by `_tools/make_og_card.py` -- see CLAUDE.md for why there are
no per-story cards. Nothing is ever missing a card because the site-wide default in `_config.yml`
covers every page.

- `assets/img/` -- the about photo, plus diagrams when they arrive, exported at the dimensions the
  design calls for. Full-resolution originals are kept in `_originals/`, which Jekyll does not
  publish; re-derive from there rather than upscaling a shipped file when a display size grows.
- `assets/og/` -- the share card at 1200x630. `default.png` serves every page. A story CAN override
  it with `image:` in its front matter, and none does.

  If one ever should, keep `image:` a **bare path**, never a hash. seo-tag will emit
  `og:image:width/height/alt` from a
  hash, but its JSON-LD drop then forwards every key into the structured data and hardcodes
  `"@type": "imageObject"` in lowercase -- and Schema.org type names are case-sensitive, so that is
  not a real type, and `alt` is not a Schema.org property. The dimensions come from `og_image:` in
  `_config.yml` and are printed by `_layouts/default.html` instead. A story that sets its own
  `image:` gets no dimension tags, deliberately: they would describe the wrong file.
- `assets/fonts/` -- two families, both self-hosted as woff2 and both **subset**, which is what
  keeps each file at 11-12KB instead of the 46KB the complete face weighs. Regenerate with
  `fonttools subset` if a character set
  ever needs to grow: adding a character the subset lacks makes that one glyph silently fall back
  to another font. `_tools/check_subset_coverage.py` is what finds that.

  Re-subsetting means reproducing the CURRENT subset from the same upstream release first, and
  proving it by comparing every decompressed table byte for byte rather than a chosen list of
  fields. A same-codepoint rebuild matches all 17 tables exactly, bar `head`'s checksum and build
  timestamp; anything less is a changed face.

  **IBM Plex Mono** Regular and Medium, subset to the 108 codepoints the site renders, declared in
  CSS as `"Site Mono"`. The rename is required: the SIL OFL reserves the name "Plex" and forbids a
  modified version from presenting a reserved name, and a subset is a modified version.

  **Space Grotesk** Regular and Medium, subset to printable ASCII plus five characters a display
  string could reach for, declared under its own name. Its OFL reserves no name -- the notice is
  "Copyright 2020 The Space Grotesk Project Authors" with nothing specified after it -- so the
  clause that forced the Plex rename does not apply and the upstream name records are untouched.
  Do not copy the Plex precedent onto a third family without reading that family's own licence.

  The copyright notice is retained inside all four files. The SIL Open Font License requires its
  text to travel with the font, and this repo is public and therefore redistributes it, so each
  family ships its own: `OFL-IBMPlexMono.txt` and `OFL-SpaceGrotesk.txt`. The Plex one is the one
  file exempt from the ASCII-only convention -- it carries a UTF-8 copyright sign. Space Grotesk's
  is already pure ASCII, but both must travel unaltered either way.

v1 ships without diagrams by design decision. No story sets `hero_image`, so the hero figure and
home-page card do not render; the CSS for both is written and inert, so adding one later needs no
CSS change.

When a story does set `hero_image`, set `hero_alt` alongside it. `hero_alt` describes the image for
someone who cannot see it; `hero_caption` is the visible caption everyone reads. They are separate
fields because they say different things -- using one for both makes a screen reader announce the
same sentence twice. Omitting `hero_alt` falls back to the story title, which is a weak description
rather than a broken page, so the failure is quiet.

Do not put a `README.md` inside these folders. Any `.md` in a publishable location becomes a page,
so a stray note turns into a published, indexed URL. Placeholder folders are held by `.gitkeep`,
which Jekyll ignores because it starts with a dot.

(The `defaults` blocks in `_config.yml` are both scoped to a `type`, which is what keeps them from
reaching a stray file. The advice stands on its own either way: Jekyll publishes markdown it can
reach, defaults or no defaults.)

## Tools

`_tools/` holds five committed scripts. None runs at build or deploy time -- Pages runs Jekyll and
nothing else -- and the site builds and serves without them. They exist because each checks
something that cannot be checked by reading the source.

**The leading underscore is load-bearing.** Jekyll skips entries starting with `_`, which is why
`_tools/` needs no entry in `exclude:` the way `temp/` does. Renamed to `tools/`, every script in
it would deploy as a live URL on pdiggins.com.

Each script's own docstring is its living record; this is the map. Two of them ask about the
rendered page and drive a headless Chrome to get the answer; two do not need it:

| Script | Chrome | Server on 8731 |
|---|---|---|
| `make_og_card.py` | yes, with `--disable-lcd-text` | its own font fixture |
| `check_subset_coverage.py` | yes | a built site |
| `resubset_mono.py` | no | no, but one network fetch |
| `probe_card_gates.py` | no | no |
| `check_dates.py` | no | no |

The two that want Chrome expect it on port 9351, and neither starts it:

```
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new \
  --remote-debugging-port=9351 --remote-allow-origins='*' --no-first-run \
  --user-data-dir='C:/Users/pbd/AppData/Local/Temp/cdp' about:blank
```

`--remote-allow-origins` is not optional; without it every connection hangs. Nor are the forward
slashes in that path cosmetic -- bash eats the backslashes in an unquoted `C:\Users\...` and Chrome
silently receives `C:UserspbdAppData...`. Add `--disable-lcd-text` for the card generator, which
gates on it; the checker reads the DOM and never a pixel, so it is indifferent and one browser
carrying the flag serves both.

Python needs `fonttools`, `websocket-client`, and, for the card, `pillow` and `numpy`.

### `make_og_card.py` -- draws `assets/og/default.png`

The share card is a picture of text, so rewording the h1 leaves every shared link previewing the old
claim. This draws the whole card from values rather than editing the previous PNG, and refuses copy
that does not fit instead of shrinking it.

It renders through a fixture of the four font files and no site markup, so it needs no Jekyll build.
It writes that fixture itself; serve it, then draw:

```
python -m http.server 8731 --directory temp/og-fixture
python _tools/make_og_card.py            # draws and gates; installs nothing
python _tools/make_og_card.py --write    # installs a card that MATCHES the committed one
python _tools/make_og_card.py --replace  # installs a card that DIFFERS from the committed one
```

Two things about it are easy to get wrong. It needs Chrome launched with `--disable-lcd-text`, or
the small type comes back with colour fringes that no geometry check can see and that ship in the
PNG. And a redraw that changes the card needs `--replace`: that comparison against the committed
card is the only check that catches a wrong design VALUE, because every per-element check predicts
from the same constants it drew from.

### `check_subset_coverage.py` -- finds characters the faces do not carry

Both self-hosted families are subset. A character outside the subset does not fail; the browser
drops to the next family in the stack, so one glyph arrives mid-word in a different typeface at a
different width. This walks the built site and names any character that reaches a face lacking it.

```
python -m http.server 8731 --directory <a built site>
python _tools/check_subset_coverage.py
```

Only one of the two can hold 8731 at a time: this wants a built site there, the card generator wants
its font fixture.

Run it after adding a story, and after any copy that reaches past plain ASCII -- an arrow, a dash, a
quote mark, anything pasted. It exits non-zero on a finding, names the code point and the face, and
reports what Chrome painted instead.

The check is per face, not per site: the two subsets are different sets, so a character can be in
the mono face and absent from the display one. Body copy is exempt -- `--sans` is a system stack
with no subset, so nothing there can fall back this way.

### `resubset_mono.py` -- proves the shipped mono face reproduces from upstream

This is the procedure the Assets section above describes. Both mono faces are subsets, and a subset
cannot be checked by looking at it: it renders every character the site uses whether or not it came
from the release the design was measured against, and it is called "Site Mono" either way.

```
python _tools/resubset_mono.py                       # prove the shipped face reproduces
python _tools/resubset_mono.py --add U+20AC          # also build one with a codepoint added
python _tools/resubset_mono.py --add U+20AC --write  # install the grown face
```

With no `--add` it builds nothing installable. That run is still the point: it rebuilds the current
108 codepoints from upstream and compares all 17 decompressed tables with the shipped file. A
same-codepoint rebuild matches every one of them, bar `head`'s checksum and build timestamp.

The complete upstream faces are **not committed** -- they are third-party OFL binaries and this
repository is all rights reserved. The script fetches IBM Plex Mono 2.004 from a pinned `@ibm/plex`
release, checks it against a recorded SHA-256, and caches it under `temp/`. That needs network
access once. A digest mismatch stops the run rather than warning: it means the release no longer
serves the bytes the shipped subset was built from, and the pin must not be updated to match
without rebuilding and re-proving the subset.

### `probe_card_gates.py` -- checks that the card generator's gates have teeth

Feeds `make_og_card.py` values that are wrong and reports any it accepts, then feeds it the values
the card actually ships and reports if those are refused. Both halves are the check: a gate that
refuses everything passes a probe suite with no controls.

```
python _tools/probe_card_gates.py
```

It needs no Chrome and no server -- it reads the font files and `_config.yml` directly, and writes
only into `temp/`. `_config.yml` itself is never edited; the `check_alt` probes run against a
doctored copy.

Run it after changing any constant the card gates on, which is the case it exists for: a checker
that passed before a value moved says nothing about the value that replaced it.

### `check_dates.py` -- finds pages that misreport when they last changed

`last_modified_at` is the one field here that has to be updated by hand, and forgetting it is
silent. This compares what each page declares against what its content actually did, taken from git
history.

```
python _tools/check_dates.py
```

Run it before publishing a revision. It exits non-zero and names the commit that moved the content.

It knows the difference between a content change and a touch: comments, both YAML and Liquid,
HTML comments and whitespace are stripped before comparison, so rewording a comment raises nothing.
A checker that cried wolf on every formatting edit would be ignored within a week, which would be
worse than not having it. It also reads the WORKING TREE, not just committed history -- the moment
you need it is before you commit a revision, when git has not seen the change yet.

The home page's sources are not just `index.html`. It prints both `_data` files and each story's
title, lesson and category, so revising a story dates the home page too, and the check follows that.

## Layout

```
_config.yml      site metadata, contact links, nav list, collection config, share-card default
_layouts/        default.html (page shell), story.html (story page)
_includes/       nav.html, footer.html, chapter-rail.html, tradeoffs.html
_data/           off-hours.yml, path-here.yml -- the two data-driven home sections
_work/           one file per story
_tools/          five committed authoring scripts; not part of the build, not published
assets/css/      style.scss compiles to /assets/css/style.css
assets/js/       chapter-rail.js, off-hours.js -- both optional, both vanilla
assets/fonts/    self-hosted woff2, two families, each with its own license
assets/img/      diagrams
assets/og/       share cards
```
