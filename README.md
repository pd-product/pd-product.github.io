# Personal site

Static site published by GitHub Pages at https://pd-product.github.io/

Publishing source is **Deploy from a branch** (`main`, root). GitHub runs Jekyll on its side, so
there is no build step to run locally and no CI workflow to maintain. Pushing to `main` publishes;
allow a few minutes.

## Page set

`/` is the whole site apart from the stories. About and contact are anchored blocks on the home
page (`/#about`, `/#contact`), not separate pages. Stories live at `/work/<slug>/`.

## Adding a story

Copy `_work/example-story.md`. Set `slug` (keep the filename identical to it), `title`, `category`,
and `order`. Everything else is optional and is simply not rendered when absent.

`order` is the global reading position. It drives three things at once: the zero-padded eyebrow
number, the row's place on the home page, and prev/next on the story page. No index needs editing.

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

## Assets

Diagrams and cards are committed at final size; there is no build-time image processing. Story
share cards are an authoring step, not a build step: `image:` in a story's front matter overrides
the site-wide default in `_config.yml`, so nothing is ever missing a card.

- `assets/img/` -- diagrams, exported at the dimensions the design calls for.
- `assets/og/` -- share cards at 1200x630. `default.png` is the site-wide fallback; per-story cards
  override it. TODO: add `default.png`.
- `assets/fonts/` -- self-hosted woff2. IBM Plex Mono is under the SIL Open Font License, which
  requires the license text to travel with the font, so commit `OFL.txt` alongside the woff2 files;
  this repo is public and therefore redistributes them. TODO: add the woff2 files and `OFL.txt`.

Do not put a `README.md` inside these folders. The site-wide `defaults` block in `_config.yml`
gives front matter to every markdown file, which turns a stray note into a published, indexed page.
Placeholder folders are held by `.gitkeep`, which Jekyll ignores because it starts with a dot.

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
