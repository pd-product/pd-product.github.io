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
- `assets/js/chapter-rail.js` — current-chapter state
- `assets/img/pints/<flavor>/frame-00..30.webp` — production rotation frames
- `_originals/` — source imagery that Jekyll does not publish
- `_tools/` — local validation and asset scripts
- `archive/v1/` — ignored-by-Jekyll historical source snapshot

## Story front matter

Each published `_work/*.md` file needs:

- `slug`, `title`, `description`, `lesson`, `category`, and `order`
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
- reduced-motion users get an instant endpoint swap;
- decode failure preserves the front image and all case navigation.

Only the front frame loads initially. The remaining frames for a pint load on
first intent.

## Assets and licenses

DM Sans and Fraunces are self-hosted as Latin WOFF2 files. Their unmodified SIL
Open Font License texts ship beside them.

The 31 WebP frames per pint are the only render frames published. PNG render
intermediates and Blender working files stay outside the published asset tree.

The shared 1200x630 social card is `assets/og/default.jpg`. Its source composite
is `_originals/site-v2/soda-fountain-family-front.png`; regenerate it with:

```powershell
python _tools/make_og_card.py --write
```

## Validation

```powershell
$env:TZ = "UTC"
jekyll build --destination temp/_site
python _tools/check_dates.py
python _tools/check_v2.py temp/_site
node --check assets/js/pint-gallery.js
node --check assets/js/chapter-rail.js
```

Also review the built site at desktop, tablet, and 360px. Test keyboard focus,
touch/no-hover behavior, the label dialog, Escape, and reduced motion before
publishing.

## Repository policy

The repository is all rights reserved. Do not add an open-source license, public
email address, contact form, hosted resume, analytics, tracking, or new external
runtime dependencies without an explicit owner decision.
