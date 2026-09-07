---
slug: "testing-the-fix"
title: "Testing a fix before we built it"
flavor: "Evidence Espresso"
pint_id: "evidence"
home_title_lines:
  - "Testing a fix before we"
  - "built it"
fact_problem: "Repeated fixes left targeting edge cases uncovered."
fact_approach: "Test the proposed design against real inventory and auctions."
# Concise search/share description. `summary` below preserves the approved,
# longer on-page introduction without forcing it into search-result snippets.
description: "How a weekend analysis showed a proposed fix would leave 14% of revenue exposed—and changed the architecture before engineering began."
summary: "Two engineering leaders proposed a fix they believed would hold. I had doubts, so I spent a weekend testing it. The design would have left 14% of revenue exposed."
# One line, and the only prose on the home-page row now that the description
# does not render there. Owner-supplied, and deliberately shorter than this
# story's "What I would redo" chapter, which makes the same point at length.
lesson: "Repeated partial fixes are a sign the problem is not understood yet."
category: "Investigation"
order: 2
# Publication date of this page, not the date of the work it describes. Without
# it Jekyll falls back to BUILD time, so datePublished and the sitemap lastmod
# move on every deploy and re-announce the story as new. Set once, then leave it.
date: 2026-08-04
# When this story's CONTENT last changed, which is a DIFFERENT question from
# `date` above and has to be updated by hand when you revise it. Both
# jekyll-seo-tag and jekyll-sitemap read this one key, so it fixes the JSON-LD
# `dateModified` and the sitemap `lastmod` together. Leave it unset and both
# quietly answer with `date`, so a revised story reports itself unrevised in two
# places that agree with each other. Do NOT bump it for a comment or a
# formatting edit -- only for something a reader would see.
# `_tools/check_dates.py` is what catches a forgotten update.
last_modified_at: 2026-09-07
role: "PM. Built the analysis independently."
team: "Two eng leaders, plus the implementing teams"
partners: "Publishers with uncommon inventory setups"
timeframe: "A weekend, against a year of partial fixes"
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

We found that a category of targeting was not being respected in Prebid Server Premium, a consequence of the architecture migration in the previous case study. The behavior had been overlooked because the gap appeared only in setups that differed from how most publishers used the product, while our validation reflected common usage.

Through late 2025 and early 2026, several fixes closed part of the problem but left edge cases uncovered. Two engineering leaders eventually proposed a solution lower in the media hierarchy that they believed would provide the broadest and most reliable coverage. I suspected they were wrong, but a hunch was not a reason to spend engineering time.

## Constraints I was handed    {#constraints}

- Two engineering leaders had considered the proposal carefully and were confident in it.
- My doubt was anecdotal, based on customer patterns I had noticed, with no existing analysis to confirm or refute it.
- Several partial fixes had already consumed time, so another delay had to be worth it.
{: role="list"}

## The call I made    {#the-call}

The expected move was to defer: engineering owned the code and had confidence; I had a feeling. Instead, I decided the disagreement was worth resolving with evidence rather than seniority, and that I would have to produce the evidence myself. Over a weekend I built a tool that evaluated every publisher's inventory across relevant combinations of media settings, pulled real bid requests for active inventory, and ran hundreds of debug auctions to observe how it was treated. I had done the analysis manually before, but never at this scale.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

How I brought the finding mattered as much as the result. I framed the evidence as a potential gap rather than a conclusion, shared the code and details so the leaders could critique the method, and said plainly that I could be wrong. I asked for their read. They built their own measurement, confirmed the finding independently, and we agreed on a direction together. It stayed noncontentious because I gave them something to verify rather than something to concede.

## What shipped    {#shipped}

The analysis changed the direction. The proposed design would have left approximately 14% of Prebid Server Premium revenue exposed to the gap it was meant to close, so it was never built. Instead, the implemented design evaluates the full set of media information on both the inventory and the bid request, closing the gap rather than narrowing it again.

{% include result.html value="14%" copy="of revenue would have remained exposed under the proposed design. The analysis prevented it from being built." %}

## What I would redo    {#redo}

The gap went through several partial fixes before anyone characterized the problem properly, and I was part of that. We addressed the edge cases we could see without appreciating how many we could not. We were designing against a problem none of us had mapped. I would change the order: describe the full shape of the problem before designing against it. The complication is that this analysis was impractical by hand at the required scale and only became feasible in 2026 with agentic tooling. The narrower lesson is more useful: when repeated fixes keep leaving edge cases behind, stop designing and characterize the problem.
