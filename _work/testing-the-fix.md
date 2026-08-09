---
slug: "testing-the-fix"
title: "Testing a fix before we built it"
# Header breadcrumb label on this story's page ("work / <crumb>"). Approved comp
# copy, not a trim of `title` -- the full title is too long for that slot.
crumb: "testing the fix"
# Shown under the title on the STORY PAGE, and read by jekyll-seo-tag as the
# meta description. It no longer renders on the home-page row -- that is a
# template decision in index.html, not a reason to drop the key. The key must
# be `description`: with any other name seo-tag falls back to page.excerpt,
# which is the first block of the body -- the opening `## ` heading. Search and
# link previews then read that heading instead.
description: "Two engineering leaders proposed a fix they believed would hold. I had doubts, so I spent a weekend testing it. The design would have left 14% of revenue exposed."
# One line, and the only prose on the home-page row now that the description
# does not render there. Owner-supplied, and deliberately shorter than this
# story's "What I would redo" chapter, which makes the same point at length.
lesson: "Repeated partial fixes are a sign the problem is not understood yet."
category: "platform"
order: 2
# Publication date of this page, not the date of the work it describes. Without
# it Jekyll falls back to BUILD time, so datePublished and the sitemap lastmod
# move on every deploy and re-announce the story as new. Set once, then leave it.
date: 2026-08-04
role: "PM. Built the analysis independently."
team: "Two eng leaders, plus the implementing teams"
partners: "Publishers with uncommon inventory setups"
timeframe: "A weekend, against a year of partial fixes"
chips:
  - "one weekend"
  - "14% revenue exposed"
# Order matters: this story's opening paragraph refers to case 1 as "the
# previous case study". Reordering requires a copy edit.
tradeoffs:
  - rejected: "Defer to the proposal"
    chosen: "Build the analysis first"
    rows:
      - dimension: "Time to ship"
        rejected: "Immediate start; implementation begins right away"
        chosen: "A weekend of analysis before anyone writes production code"
      - dimension: "What it fixes"
        rejected: "The cases the proposal covers, with the gaps unknown until they surface in production"
        chosen: "Establishes actual coverage before committing, so the design can be chosen against real data"
      - dimension: "Cost of being wrong"
        rejected: "An implemented solution that silently misses a meaningful share of inventory, discovered by customers"
        chosen: "A weekend spent confirming engineering was right, and a small delay"
published: true
---

## The situation    {#situation}

We found that a category of targeting was not being respected in Prebid Server Premium. It was a consequence of the architecture migration described in the previous case study: during that transition, this particular behavior was overlooked. Our testing had not caught it, because the gap only appears in setups that differ from how most publishers actually use the product, and most of our validation reflected common usage.

Through late 2025 and early 2026 we tried several fixes. Each one closed part of the problem and left edge cases uncovered. Eventually two engineering leaders came to me with a proposal built on a lower level of the media hierarchy, and made the case that it would give the broadest and most reliable coverage. The tension was that I had a hunch they were wrong, and a hunch is not a reason to spend engineering time.

## Constraints I was handed    {#constraints}

- The proposal came from two engineering leaders who had thought about it carefully and were confident in it.
- My doubt was anecdotal, based on patterns I had noticed in customer setups, and there was no existing analysis that could confirm or refute it.
- Several partial fixes had already been spent on this, so proposing another delay needed to be worth it.
{: role="list"}

## The call I made    {#the-call}

The expected move was to defer. Engineering owned the code, they had thought about it carefully, and I had a feeling. Instead I decided the disagreement was worth resolving with evidence rather than seniority, and that if I wanted evidence I would have to produce it myself. I spent a weekend building a tool that evaluated every publisher's inventory across every relevant combination of media settings, pulled real bid requests for active inventory, and ran hundreds of debug auctions to observe how that inventory was actually treated in practice. It was an analysis I had done manually before, but never at anything close to that scale.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

What mattered as much as the finding was how I brought it. I sent the leaders the evidence framed as a potential gap rather than a conclusion, shared the code and the full details so they could critique the method itself, and said plainly that my results could be wrong. Then I asked for their read and offered to talk it through. They put their own measurement in place, confirmed the finding independently, and we agreed on a direction together. None of it was contentious, and I think that is because I gave them something to verify instead of something to concede.

## What shipped    {#shipped}

The analysis changed the direction. Had the proposed design been implemented, approximately 14% of Prebid Server Premium revenue would have been exposed to the targeting gap it was meant to close. That design was never built. What was built instead evaluates the full set of media information present on both the inventory and the bid request, which closed the gap properly rather than narrowing it again.

## What I would redo    {#redo}

The gap went through several rounds of partial fixes before anyone characterized the problem properly, and I was part of that. Each attempt addressed the edge cases we could see, and I did not appreciate how many we could not. We were iterating on solutions to a problem none of us had mapped. What I would change is the order: describe the full shape of the problem before designing against it. The honest complication is that the analysis which finally did that was not practical by hand at the scale required, and only became feasible in 2026 with agentic tooling. So the lesson I take is narrower and more useful. When repeated fixes keep leaving edge cases behind, that is a signal the problem is not understood yet, and the next move is to go characterize it instead of designing again.
