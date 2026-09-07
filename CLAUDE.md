# Working in this repository

Read `README.md` first. It describes the current Soda Fountain design,
story contract, assets, interaction model, and validation commands.

## Owner decisions

Do not re-propose these without a new owner request:

- The primary domain is `pdiggins.com`; secondary domains remain reversible
  302 redirects.
- No contact form, public email link, hosted resume, analytics, tracking,
  dark-mode toggle, or new runtime library.
- The repository is all rights reserved. Do not replace `LICENSE` with an
  open-source license.
- All pages share one social card rather than per-story cards.
- The public role label is Product Manager.
- The approved case flavors and order are Publisher Pistachio, Evidence
  Espresso, and Compound Caramel.
- The approved case prose is the current reduced text in `_work/*.md`.
  Do not rewrite it without explicit approval.
- The Soda Fountain visual system is teal, cream, peach tile, Fraunces display
  type, DM Sans body/UI type, and the approved studio pint renders.

## Load-bearing behavior

- Keep the global and per-page `noindex` checks in the default layout.
- Keep the home-page ProfilePage/Person JSON-LD separate from the SEO tag.
- Keep `image:` defaults as bare paths. The layout emits dimensions and alt
  text only for the shared default card.
- Keep explicit `role="list"` where CSS removes list markers.
- Keep explicit heading IDs in case Markdown; the chapter rail depends on them
  and `kramdown.auto_ids` is deliberately false.
- The front pint image and every case link must work without JavaScript.
- Essential navigation and facts must not require hover. Touch, keyboard, and
  reduced-motion states are part of the interaction contract in README.
- `archive/` must remain excluded from Jekyll. Historical source snapshots are
  repository references, not alternate published sites.
- Never add `.nojekyll`; doing so disables the layouts, collection, includes,
  Sass, and SEO tag.

## Source and asset rules

- Keep full-resolution photo and share-card inputs under `_originals/`.
- Publish WebP rotation frames only, not PNG render intermediates or Blender
  working files.
- Keep the unmodified OFL text beside each redistributed font.
- Do not add front matter to files under `_originals/` or `_tools/`.
- Keep scratch output under ignored `temp/`.

## Verification

Build with UTC so dates match GitHub Pages:

```powershell
$env:TZ = "UTC"
jekyll build --destination temp/_site
python _tools/check_dates.py
python _tools/check_v2.py temp/_site
node --check assets/js/pint-gallery.js
node --check assets/js/chapter-rail.js
```

Inspect the built output, not only the successful build message. Confirm that
`archive/` and Markdown notes did not publish, internal links and assets
resolve, and the home, About, and three case pages work at 320, 360, 390, 412,
430, 600, 768, 900, 1000, and 1200px. The widths between CSS breakpoints are
part of the contract: verify zero horizontal overflow and readable tradeoff
columns rather than checking only named device presets.

Pushing `main` publishes. Finish local review before the first push.
