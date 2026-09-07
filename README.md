# pdiggins.com

Source for Pat Diggins's personal site, published with GitHub Pages and Jekyll.

The current design is the Soda Fountain portfolio: three product case studies
presented as studio-rendered ice cream pints, a separate About page, and a shared
editorial case-page system.

## Pages

- `/` — interactive pint gallery
- `/about/` — About Pat
- `/work/targeting-architecture/` — Publisher Pistachio
- `/work/testing-the-fix/` — Evidence Espresso
- `/work/personal-finance-tools/` — Compound Caramel
- `/404.html` — not-found page

The previous site is preserved byte-for-byte under `archive/v1/site/`.
`archive/v1/README.md` records its source commit and comparison commands.
The root Jekyll configuration excludes `archive/`, so snapshots do not publish.

## Local build

From the repository root in PowerShell:

```powershell
$env:TZ = "UTC"
jekyll build --destination temp/_site
python -m http.server 4000 --directory temp/_site
```

Open `http://127.0.0.1:4000/`.

GitHub Pages publishes from `main`. Keep review and validation local; push only
after the full change is ready.

## Structure

- `_layouts/default.html` — metadata, shared masthead, main landmark, footer,
  and page-specific scripts
- `_layouts/story.html` — shared case-page structure
- `_includes/tradeoffs.html` — accessible tradeoff comparison
- `_includes/result.html` — case outcome callout
- `_work/*.md` — case metadata and approved prose
- `about.html` — About page
- `assets/css/style.scss` — complete visual system
- `assets/js/pint-gallery.js` — progressive-enhancement pint interaction
- `assets/js/chapter-rail.js` — visible current-chapter highlighting
- `assets/img/pints/<flavor>/frame-00..30.webp` — production rotation frames
- `assets/img/pints/<flavor>/still-800/` — native 800x1200 front/back stills
- `assets/img/pints/<flavor>/motion-600/` — 600x900 intermediate rotation frames
- `_originals/` — source imagery that Jekyll does not publish
- `_tools/` — local validation and asset scripts
- `archive/v1/` — ignored-by-Jekyll historical source snapshot

## Story front matter

Each published `_work/*.md` file needs:

- `slug`, `title`, `description`, `summary`, `lesson`, `category`, and `order`
- `date` and `last_modified_at`
- `role`, `team`, `timeframe`; `partners` when applicable
- `flavor` and `pint_id`
- `home_title_lines`
- `fact_problem` and `fact_approach`
- `tradeoffs`
- `published: true`

Body chapters are Markdown `h2` headings with explicit IDs, for example:

```markdown
## The situation    {#situation}
```

Those IDs drive both deep links and the generated chapter rail. Story prose is
owner-authored; do not rewrite it without explicit approval.

## Pint interaction

The front frame and case link work without JavaScript. With JavaScript:

- pointer hover and keyboard focus rotate to the back;
- the Turn pint button pins or resets the view;
- the first touch on a front-facing pint turns it, while the separate case link
  always navigates;
- Read label opens selectable Problem, Approach, and Lesson text in a native
  dialog;
- every standard-motion turn uses the complete frame sequence, including the
  first interaction;
- on the one-pint mobile layout, the next visible pint warms as it approaches
  the viewport so the first turn can animate without loading every pint;
- reduced-motion users load only the requested endpoint and get an instant
  swap;
- decode failure preserves the front image and all case navigation.

Only the front frame is required for the initial render. Standard-motion turns
wait for the complete sequence rather than snapping to an endpoint. Mobile
prewarming is viewport-led; reduced-motion users continue to fetch only the
requested endpoint.

Front/back stills use 400w/800w `srcset` candidates. On the home page, the original
responsive poster stays mounted for layout, accessibility and no-JS fallback.
After interaction, decoded frames are drawn into one persistent opaque 2D canvas
over that poster. It is mounted only after its first successful draw and never
cleared, resized or replaced between frames. Slow/failed decoding leaves the last
good pixels visible, rather than exposing an empty image or compositor layer.
Source selection happens on detached images: endpoints use responsive candidates,
motion uses its single selected tier, and repeated ticks for the same rounded frame
are deduplicated. Interrupted turns cannot commit stale decoded frames. Endpoint
selection refreshes after viewport resize without reallocating the canvas.
High-DPI or wider-than-400px pints use the 600x900 intermediate sequence and
800x1200 endpoints. A sequence's tier is fixed when the gallery initializes;
responsive endpoint selection continues adapting to viewport changes.
Save-Data and detected 2G connections use the lean 400x600 sequence and
skip speculative mobile prewarming. Browsers without Network Information use
the normal width/DPR path. Reduced motion remains endpoint-only at either size.
The browser may request an initial responsive still before JavaScript applies
the constrained-connection preference; no guarantee of zero high-res initial
requests is implied. No new runtime dependency or scroll-triggered turn is added.

## Assets and licenses

DM Sans and Fraunces are self-hosted as Latin WOFF2 files. Their unmodified SIL
Open Font License texts ship beside them.

Each pint publishes 31 lean WebPs, 29 retina motion WebPs, and two retina still
WebPs. Runtime selects a sequence; it does not preload both complete tiers.
Canvas backing stores are fixed at 800x1200 (400x600 on constrained connections),
about 3.7MiB (0.9MiB) of RGBA pixels per interacted pint, excluding browser overhead
and image decode/cache memory. No complete array of decoded images is retained.
PNG render intermediates and Blender working files stay outside the published
asset tree.

To regenerate both tiers from approved native 800x1200 PNG masters:

```powershell
python _tools/encode_pints.py PATH_TO_MASTERS
```

The masters directory contains `publisher/`, `evidence/`, and `compound/`, each
with `frame-00.png` through `frame-30.png`. These are rendered at 64 Cycles samples
from the approved shared-camera scene, not upscaled from delivered WebPs.
The encoder also regenerates the lean tier from those same masters (quality 90
endpoints, 75 motion), writes retina quality 92 endpoints and quality 85 motion,
and records source hashes beside the masters. Validation
budgets are under 800KB for all lean frames and 2MB for all retina frames.

The shared 1200x630 social card is `assets/og/default.jpg`. Its source composite
is `_originals/site-v2/soda-fountain-family-front.png`; regenerate it with:

```powershell
python _tools/make_og_card.py --write
```

## Validation

The frame-presentation regression test runs without a browser or dependencies:
`node _tools/test_pint_presentation.cjs`. It covers delayed/out-of-order decoding,
interrupted turns, safe failure, repeated adjacent turns, and the guarantee that
the visible surface is not cleared/resized/replaced or painted with an undecoded
frame. Live hover/pixel checks remain necessary, with diagnostics disabled.
The gallery exposes `data-renderer="persistent-canvas-v3"` on `.pint-shelf` so a
review can verify the actually executing code, not merely the served file. Bump
the gallery/CSS version query in `_layouts/default.html` on a renderer update;
normal reloads can retain stale browser assets.

For the full optional browser suite, use an environment with Playwright and Edge
already installed, start the local build, then run `node _tools/test_site_browser.cjs`.
It checks all six pages at 15 widths, touch/keyboard/reduced-motion behavior,
constrained connections, failed-image/canvas fallback, and uninstrumented adjacent
hover crossings followed by exact canvas-pixel checks. `SITE_URL` overrides the
default `http://127.0.0.1:8812`; `QA_OUTPUT` overrides `temp/browser-qa`; and
`PLAYWRIGHT_MODULE` can point to an existing external Playwright installation.
These are development-only tools, not dependencies loaded by the site.

```powershell
$env:TZ = "UTC"
jekyll build --destination temp/_site
python _tools/check_dates.py
python _tools/check_v2.py temp/_site
node --check assets/js/pint-gallery.js
node --check assets/js/chapter-rail.js
```

Also review the built site at 320, 360, 390, 412, 430, 600, 768, 900, 1000,
and 1200px. Test keyboard focus, touch/no-hover behavior, the label dialog,
Escape, chapter highlighting, reduced motion, horizontal overflow, and the
tablet tradeoff layout before publishing.

## Repository policy

The repository is all rights reserved. Do not add an open-source license, public
email address, contact form, hosted resume, analytics, tracking, or new external
runtime dependencies without an explicit owner decision.
