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

`/` is the whole site apart from the stories. About and contact are anchored blocks on the home
page (`/#about`, `/#contact`), not separate pages. Stories live at `/work/<slug>/`.

## Adding a story

Copy `_work/example-story.md`. It carries `published: false`, so it is a template rather than a
page: it stays out of the built site, the home list, prev/next and the sitemap until a copy sets
`published: true`.

Required: `slug` (keep the filename identical to it), `title`, `category`, `order`, `description`
and `date`.

The rest are presentational -- `partners`, `chips`, `hero_image` and friends -- and a story that
omits one renders without it. Two carry a fallback rather than nothing: `crumb` falls back to
`title`, and `hero_alt` falls back to `title`, which is a weak image description rather than a
visible failure, so set it whenever you set `hero_image`.

Nothing guards `category`, `description` or `date`, and each fails silently rather than visibly:

- `category` renders a dangling `01 /` in the eyebrow, on both the home row and the story page,
  when it is missing.
- `description` is also the page's meta description. Omit it and `jekyll-seo-tag` falls back to the
  page excerpt -- the first block of the body -- so the story goes to search results and link
  previews described by its own opening heading.
- `date` has a silent WRONG default rather than an absent one. Without it Jekyll stamps build time,
  so `datePublished` and the sitemap's `lastmod` move on every deploy and re-announce the story as
  new. Use the date the story was published, not the date you are editing.

`order` is the global reading position and is required. It is a **sort key only**: the zero-padded
eyebrow number is derived from the story's position in the sorted list, not from the value itself,
so duplicate, missing, zero, or negative values cannot render a duplicate number, a blank, `00`, or
`0-1`. Home row and story page derive it the same way and therefore always agree. Use unique
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
  It also used to break the page: at 390 a five-column table pushed the document to `scrollWidth`
  461 against `clientWidth` 390, giving the whole page a horizontal scrollbar and clipping every
  line of body prose at the right edge -- a WCAG 1.4.10 reflow failure, from one authoring slip.
  `.story-prose > table` now carries a containment guard so that cannot happen. **The guard is not
  support.** It keeps the page conformant and makes the table look cramped and wrong, which is the
  intended signal.

So: chapters are `h2`, and everything under them is paragraphs, lists and figures. A story that
genuinely needs an `h3`, a blockquote, code, a rule or a Markdown table needs those styles designed
first -- it is not an authoring decision to make mid-story.

Both list forms are styled and neither takes a marker in the source. An unordered list gets an
accent square, which is what the constraints chapter uses. An ordered list is numbered by CSS, so
author it as a plain markdown ordered list and let the counter supply `01`, `02`. Add
`{: role="list"}` after a list, as the existing stories do: the `list-style: none` reset drops the
implicit list role in Safari with VoiceOver.

## Assets

Diagrams and cards are committed at final size; there is no build-time image processing. Story
share cards are an authoring step, not a build step: `image:` in a story's front matter overrides
the site-wide default in `_config.yml`, so nothing is ever missing a card.

- `assets/img/` -- the about photo, plus diagrams when they arrive, exported at the dimensions the
  design calls for. Full-resolution originals are kept in `_originals/`, which Jekyll does not
  publish; re-derive from there rather than upscaling a shipped file when a display size grows.
- `assets/og/` -- share cards at 1200x630. `default.png` is the site-wide fallback; per-story cards
  override it via `image:` in the story front matter.

  Keep `image:` a **bare path**, never a hash. seo-tag will emit `og:image:width/height/alt` from a
  hash, but its JSON-LD drop then forwards every key into the structured data and hardcodes
  `"@type": "imageObject"` in lowercase -- and Schema.org type names are case-sensitive, so that is
  not a real type, and `alt` is not a Schema.org property. The dimensions come from `og_image:` in
  `_config.yml` and are printed by `_layouts/default.html` instead. A story that sets its own
  `image:` gets no dimension tags, deliberately: they would describe the wrong file.
- `assets/fonts/` -- IBM Plex Mono Regular and Medium, self-hosted as woff2 and **subset** to the
  ~107 glyphs the site renders, which cut each file from about 46KB to about 11.6KB. They are
  declared in CSS as `"Site Mono"`: the SIL OFL reserves the name "Plex" and forbids a modified
  version from presenting a reserved name, and a subset is a modified version. The IBM copyright
  notice is retained inside both files. Regenerate with `fonttools subset` if the character set
  ever needs to grow -- adding a character the subset lacks makes that one glyph silently fall back
  to another font.
  The SIL Open Font License requires its text to travel with the font, and this repo is public and
  therefore redistributes it. `OFL.txt` is the one file exempt from the ASCII-only convention.

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

(The `defaults` blocks in `_config.yml` are no longer the mechanism -- both are scoped to a `type`,
which is the fix for exactly this problem. The advice stands on its own: Jekyll publishes markdown
it can reach, defaults or no defaults.)

## Layout

```
_config.yml      site metadata, contact links, nav list, collection config, share-card default
_layouts/        default.html (page shell), story.html (story page)
_includes/       nav.html, footer.html, chapter-rail.html, tradeoffs.html
_work/           one file per story
assets/css/      style.scss compiles to /assets/css/style.css
assets/fonts/    self-hosted woff2 + its license
assets/img/      diagrams
assets/og/       share cards
```
