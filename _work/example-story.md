---
# Copy this file to start a story, then delete it once real stories exist.
# The URL comes from `slug`, not the filename, but keep them identical so the
# two can never drift apart.
slug: "example-story"
title: "Example story"
summary: "One sentence shown on the home-page row and under the story title."
category: "supply"          # one lowercase word: supply, demand, identity
order: 1                    # global reading order; drives the eyebrow number,
                            # home-page position, and prev/next
role: "TODO your role"
team: "TODO e.g. 12 engineers, 2 data scientists, 3 solution engineers"
partners: "TODO e.g. Top-40 publishers, 60+ demand partners"
timeframe: "TODO e.g. 18 months"
chips:                      # 2-3 short mono tags on the home-page card
  - "18 months"
  - "eng 12"
hero_image: "/assets/img/example-story-hero.png"
hero_caption: "TODO what the diagram shows."
# card_image defaults to hero_image; set it only when the card differs.
# card_image: "/assets/img/example-story-card.png"
# image: overrides the site-wide share card for this story only.
# image: "/assets/og/example-story.png"

# Tradeoff tables are data, not a Markdown table, so the chosen column is
# identified by name and the marker can never land on the wrong column.
# This is a LIST: a story needing more than ~5 dimensions adds a second table
# for a second decision rather than a taller one.
tradeoffs:
  - rejected: "Router in front"
    chosen: "One decision service"
    rows:
      - dimension: "Time to first ship"
        rejected: "One quarter"
        chosen: "Three quarters"

# Set `published: false` to keep a story in the repo but out of the built site.
# This is Jekyll's own flag: an unpublished story drops out of the home list,
# the sitemap, and prev/next automatically.
published: true
---

Chapter headings carry an explicit anchor in braces. That anchor is what keeps a
shared link such as `/work/example-story/#situation` working after the heading
text is reworded. The rail on the left is generated from these headings, so
omitting a chapter that does not apply is fine -- delete the section and its rail
entry goes with it.

## The situation    {#situation}

TODO

## Constraints I was handed    {#constraints}

TODO

## The call I made    {#the-call}

TODO

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

## What shipped    {#shipped}

TODO

## What I'd redo    {#redo}

TODO
