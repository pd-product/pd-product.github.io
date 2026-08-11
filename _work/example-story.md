---
# TEMPLATE, not a page. `published: false` keeps it out of the built site, the
# home list, prev/next and the sitemap. Copy this file, rename it to match the
# slug you choose, then set published: true. Do NOT set it true here.
published: false

# --- Required ---------------------------------------------------------------
# Keep the filename identical to the slug: /work/<slug>/ is built from it.
slug: "example-story"
title: "The full title, as long as it needs to be"
# Renders in the eyebrow as "01 / <category>". Nothing guards it -- omit it and
# the eyebrow renders a dangling "01 /".
category: "supply"
# Global reading position. A SORT KEY ONLY: the displayed number comes from the
# story's position in the sorted list, so a duplicate or a gap cannot render a
# wrong number. Use unique integers anyway; ties have no defined order.
order: 99

# --- Strongly recommended ---------------------------------------------------
# Shown under the title on the STORY PAGE, and used as the meta description.
# It does not render on the home row -- still required, still what a search
# result and a pasted link show. Omit it and jekyll-seo-tag falls back to the
# page excerpt, which is the first block of the body -- your opening "## "
# heading. Google truncates near 155 characters, so put the point first.
description: "One or two sentences: the situation, the call, and what it cost. This is what a search result and a pasted link both show."
# Publication date of the page, not of the work it describes. Without it Jekyll
# uses BUILD time, so the date moves on every deploy. Set once, then leave it.
date: 2026-01-01

# --- Optional; omitted fields simply do not render ---------------------------
# Header breadcrumb label ("work / <crumb>"). Falls back to `title`, which is
# usually too long for the slot.
crumb: "example story"
# One line, and the only prose the home row shows. Usually a trim of this
# story's own "What I would redo" chapter.
lesson: "The one sentence you would want someone to remember."
role: "Your role, and what you owned."
team: "Who you worked with."
partners: "External or cross-org counterparties."
timeframe: "How long it ran."
# Small labels on the home row. Two or three; they are not tags.
chips:
  - "one weekend"
  - "staged rollout"
# Set both together. hero_alt describes the image for someone who cannot see it;
# hero_caption is the visible caption everyone reads. They say different things.
# hero_alt falls back to the title, which is a weak description rather than a
# broken page -- so forgetting it is quiet.
# hero_image: "/assets/img/example-diagram.png"
# hero_alt: "What the diagram shows."
# hero_caption: "Caption printed under the figure."
# Per-story share card, overriding the site-wide default in _config.yml.
# image:
#   path: "/assets/og/example-story.png"
#   width: 1200
#   height: 630
#   alt: "Transcribe the card's own text here."

# A LIST of tables even with one table. Target 3 rows; 5 is the ceiling. A
# second decision wants a second table, not a taller one. The chosen column is
# named rather than positional, so its marker cannot land on the wrong column.
tradeoffs:
  - rejected: "The expected option"
    chosen: "What you actually did"
    # Optional caption above the table. Omitted, the table has none.
    # title: "What the decision was between"
    rows:
      - dimension: "Time to ship"
        rejected: "What the expected option cost in time"
        chosen: "What yours cost in time"
      - dimension: "What it fixes"
        rejected: "What the expected option would and would not solve"
        chosen: "What yours solved"
      - dimension: "Cost of being wrong"
        rejected: "The downside if the expected option was wrong"
        chosen: "The downside if yours was"
---

## The situation    {#situation}

The anchor is REQUIRED. `auto_ids` is off in _config.yml, so a heading without
`{#id}` gets no id at all and drops out of the chapter rail -- visibly. Only the
`{#id}` form is matched; `{: .class #id}` renders the class first and the
chapter goes missing from the rail.

Prose is paragraphs, lists and figures. `.story-prose` styles h2, p, ul, ol,
figure, figcaption and a -- nothing else. See the README before reaching for an
h3, a blockquote, code or a Markdown table.

## Constraints I was handed    {#constraints}

- Author ordered lists as plain markdown; the CSS supplies the `01`, `02`.
- Keep them short -- they sit beside the prose measure, not inside it.
- The `role="list"` line below is not decoration: the `list-style: none` reset
  drops the implicit list role in Safari with VoiceOver.
{: role="list"}

## The call I made    {#the-call}

Declaring `tradeoffs:` in front matter renders nothing by itself. The include
below is placed by hand, and a missing one fails silently -- `{% for table in
nil %}` iterates zero times and the page builds clean without the table.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

## What shipped    {#shipped}

What actually went out, and how you know it worked.

## What I would redo    {#redo}

This chapter carries the only accent rule in the prose, and it must stay LAST.
The rule claims every sibling after `#redo`, so a chapter added below it would
be swallowed into the accent bar. Rail entries are comfortable at 3-8, and
heading text under about 24 characters avoids wrapping in the rail.
