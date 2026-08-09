# Working in this repository

Read `README.md` first -- it is the authoring surface and covers how to add a story, what the story
prose supports, and the front-matter contract. This file holds only what the code and the README
cannot say: settled decisions, and prohibitions that look like improvements.

Most durable constraints live as comments next to the rule they govern -- the accent bar in
`assets/css/style.scss`, the ARIA roles in `_includes/tradeoffs.html`, the `image:` and `social:`
keys in `_config.yml`. Read the comment before changing the line.

## Settled, not pending

These are owner decisions. They are recorded here so they are not re-proposed as improvements. Do
not raise them again unprompted.

- **The secondary domains redirect at 302 and stay there.** A 301 would consolidate search signals
  into the primary, but it is cached hard by browsers and search engines and is painful to reverse.
  This is a settled position, not an optimisation waiting to be taken.
- **No contact form.** Not merely unavailable on a static host -- declined. A form that silently
  fails to send is worse than a link. Contact is links only.
- **No public email link and no hosted resume PDF.** Both keys are deliberately absent from
  `_config.yml`; see the comments there. Restoring either is an owner decision, not a gap to fill.
- **No licence from GitHub's picker.** The repository is all rights reserved and the `LICENSE` file
  is deliberately not an open-source licence. Adopting a recognised one to make GitHub's label
  tidier would grant rights the owner withholds.
- **No analytics, JS libraries, CDN dependencies, or dark/light toggle.** Dark and light are pure
  `prefers-color-scheme`. There are exactly two executable JavaScript assets -- the chapter-rail
  reading state and the Off hours reveal -- both vanilla, both progressive enhancement, and both of
  which must stay optional. (The `<script type="application/ld+json">` blocks in
  `_layouts/default.html` and from `{% seo %}` are structured data, not behaviour, and are not
  counted here.) The bar for a third is that the page is complete and correct without it. For the
  reveal that means the hidden state is applied FROM the script and never from the stylesheet, so
  no JavaScript means no animation rather than no content.

## Do not "clean these up"

Each of these looks like redundancy or an obvious simplification, and each is load-bearing. The
failure mode in every case is silent.

- **`role="list"` on lists, and the explicit ARIA roles on the tradeoff table.** A CSS display value
  that changes an element's implicit role has to be answered with an explicit role. Removing them
  costs nothing visible and drops the semantics for screen readers.
- **The breadcrumb's first crumb must stay visible at narrow widths.** Do not reintroduce a rule
  that hides it: that leaves a labelled `Breadcrumb` landmark with nothing to navigate to.
- **The `.story-prose > table` containment guard.** Do not simplify it to
  `display: block; overflow-x: auto` -- that leaves the page itself scrolling horizontally, which is
  the WCAG reflow failure the guard exists to prevent. The child combinator is also deliberate; a
  descendant selector would reach the designed tradeoff table and break its cell text mid-word.
- **Never add `.nojekyll`.** It is a common suggested fix when Pages assets 404, and here it would
  bypass Jekyll entirely -- layouts, includes, the `_work` collection and the SEO tag all stop
  working at once. If an asset 404s, the cause is almost always missing front matter on a file that
  needs it.
- **The site-wide `noindex` switch in `_config.yml`.** It is the withdrawal mechanism: flipping it
  to `true` is the only centralised, non-destructive way to pull the whole site from search. Keep
  the flag even while it is `false`. Any future layout that does not inherit from `default.html`
  must emit the tag itself, or it silently opts out of the switch.

## House rules

- **Story prose in `_work/*.md` is verbatim and is not reworded** -- including phrasing that reads
  oddly to you. These are the owner's own words about their own work. Front matter is editable;
  bodies are not, absent an explicit instruction to change one.
- **ASCII only in source files.** HTML entities in markup, CSS escapes in stylesheets.
  `assets/fonts/OFL-IBMPlexMono.txt` is the single exempt file -- it carries a UTF-8 copyright
  sign -- and must travel unaltered. `assets/fonts/OFL-SpaceGrotesk.txt` is ASCII already and is
  equally unalterable, for the licence's reasons rather than this convention's.
- **No in-source change logs.** Comment the durable CONSTRAINT, never the change that introduced it.
  If a comment addresses a past session or a document outside this repo, it is handoff apparatus and
  should be removed rather than preserved.
- **A design proposal is a proposal, not a spec.** Evaluate it against the real markup before
  landing it. A proposal can carry sound intent and a faulty premise, and implementing one
  faithfully is not a defence.

## Known and accepted

A story page is clean down to 275px and scrolls horizontally at 270px and below: `.site-nav` runs
past the right edge, giving `scrollWidth` 272 against `clientWidth` 270. That is well below the
320px narrowest common device, so it is accepted rather than outstanding.

THE BREADCRUMB IS NOT THE CAUSE, and this is worth stating because it is the thing that looks like
it. The gap between the crumb and the nav holds at a constant 24px at every width down to 270 -- the
crumb truncates as designed and never reaches the nav. It is the nav row itself that will not fit.

The fix, if it is ever wanted, is the header wrap the home page and 404 already have: those two
carry `.site-header-wordmark`, which below 640px is free to drop the nav onto its own row at
whatever width it stops fitting, and they are therefore clean down to 250px. Story pages
deliberately do not get that rule -- `flex-wrap: wrap` moves an over-long crumb to the next line
INSTEAD of shrinking it, which defeats the truncation the crumb depends on; the scope is explained
on the rule in `assets/css/style.scss` and in `_includes/nav.html`. So the fix is a wrap or stack
that story pages can take without losing the ellipsis, not re-hiding the first crumb, for the
reason above.

## Verifying

Check the built page, not the build status -- a green build will happily serve a stray markdown note
as a page. After adding or editing a story, load it and confirm:

- the `<meta name="description">` is the story's `description`, not its opening heading
- the chapter rail lists every `h2` on the page
- `datePublished` in the JSON-LD is the story's `date`, not today
- the page loads at its `/work/<slug>/` URL and the home row links to it

Pushing to `main` publishes. There is no staging environment and no CI.

A local `jekyll build` is a useful witness, and `_config.yml` pins the two things that would
silently make it disagree with production: the Sass output style, and `temp/`. Build with `TZ=UTC`
for the
third -- Jekyll stamps dates in the build machine's zone, so without it `datePublished`,
`dateModified`, `article:published_time` and the sitemap's `lastmod` all carry the local offset
instead of the `+00:00` every deployed date has. The zone is passed to the build rather than set in
`_config.yml`; the comment on that decision is beside the `sass:` block.

Even then it is NOT the same build. GitHub Pages force-enables ten plugins on top of whatever
`plugins:` lists, and a local build loads only what `plugins:` lists. Five of those ten can publish
or retitle content: `jekyll-optional-front-matter`, `jekyll-readme-index`,
`jekyll-titles-from-headings`, `jekyll-default-layout` and `jekyll-relative-links`.

All five are inert here today, which is why local output otherwise matches deployed byte for byte.
They stop being inert the moment a front-matter-less `.md` or a directory `README.md` reaches a
publishable location -- the exact hazard README.md warns about. THAT CLASS FAILS SILENTLY LOCALLY:
the file is copied as a static asset by a local build and becomes a live indexed URL on Pages. A
local build cannot clear it; only the deployed site can.
