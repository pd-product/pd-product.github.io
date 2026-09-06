---
slug: "personal-finance-tools"
title: "The spreadsheet that became a toolkit"
flavor: "Compound Caramel"
pint_id: "compound"
home_title_lines:
  - "The spreadsheet that became a toolkit"
fact_problem: "A rebalancing spreadsheet was too tedious to maintain."
fact_approach: "Keep existing aggregation; build the missing Python tools."
# Header breadcrumb label on this story's page ("work / <crumb>"). Approved comp
# copy, not a trim of `title` -- the full title is too long for that slot.
crumb: "personal finance tools"
# Shown under the title on the STORY PAGE, and read by jekyll-seo-tag as the
# meta description. It does not render on the home-page row -- that is a
# template decision in index.html, not a reason to drop the key. The key must
# be `description`: with any other name seo-tag falls back to page.excerpt,
# which is the first block of the body -- the opening `## ` heading. Search and
# link previews then read that heading instead.
description: "I set out to rebalance our portfolio in a spreadsheet, realized how tedious it would be to maintain, and decided to find out what I could build instead. It turned into a suite of tools, and a lesson about scope."
# One line, and the only prose on the home-page row now that the description
# does not render there. Owner-supplied, and deliberately shorter than this
# story's "What I would redo" chapter, which makes the same point at length.
lesson: "When building feels cheap, skipped planning becomes expensive."
category: "Personal tools"
order: 3
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
last_modified_at: 2026-09-06
role: "Sole author, with AI coding tools"
team: "None. A planner validated the strategy separately."
timeframe: "Ongoing since early 2026"
# `partners` is deliberately omitted -- it does not apply to a personal
# project, and an omitted field drops its rail entry rather than printing
# "not applicable".
chips:
  - "ongoing"
  - "python"
tradeoffs:
  - rejected: "Spreadsheet or off-the-shelf"
    chosen: "Build around the product I use"
    rows:
      - dimension: "Time to ship"
        rejected: "Immediate; the spreadsheet already existed"
        chosen: "Slower; nothing is usable until it is built"
      - dimension: "What it fixes"
        rejected: "Handles the common case, and diverges from how I actually run these decisions"
        chosen: "Fits my approach, and lets me run the analysis whenever a decision calls for it"
      - dimension: "Cost of being wrong"
        rejected: "Low; abandon it and go back to manual work"
        chosen: "Real; anything I build I maintain myself, and a bad structure compounds"
published: true
---

## How it started    {#situation}

Early in 2026 I spent a while researching investment and tax strategy to revamp our portfolios, then hired a financial planner for a short engagement to pressure-test what I had come up with. That left me with several jobs that would recur indefinitely, the most tedious being portfolio rebalancing and estimated tax payments. Both are the kind of work that is straightforward in principle and miserable in practice, because doing them properly means holding a lot of interacting rules in your head at once.

I started the rebalancing model in a spreadsheet, but it quickly became clear that it would be too tedious to maintain. At the same time I was learning what agentic coding tools could do at work, so I decided to see what I could build instead. The obvious solution was the one I would end up avoiding.

## Constraints I set myself    {#constraints}

- The inputs are personal financial information, so nothing could be handled carelessly or sent anywhere it did not need to be.
- Nobody else would maintain it, so every layer of complexity would be mine to carry.
- Tax work needed income information that rebalancing did not, so the data model would not stay simple.
{: role="list"}

## The call I made    {#the-call}

The expected option was a spreadsheet or a product that handled some of this. I already use Monarch, which aggregates accounts well. I kept it for what it does well and built only the parts where my approach does not match how that product thinks about the problem. That meant writing requirements first, treating a personal project like a product with a defined scope, and building against them.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

Monarch remained the aggregator and exporter—the part it does better than anything I would write—and my tools consumed its export. That boundary kept me from rebuilding aggregation. The tools now cover rebalancing, estimated tax payments, spend analysis, and budgeting.

## What I built    {#shipped}

A suite of Python tools now covers rebalancing, estimated tax payments, spend analysis, and budgeting. They save manual work, but the benefit I did not anticipate is that I can run each exercise as often as I want, with more accuracy and depth. The real gain is reaching analysis I would otherwise have skipped—the same value I found using these tools at work.

{% include result.html value="4" copy="recurring workflows now covered: rebalancing, estimated taxes, spend analysis, and budgeting." %}

## What I would redo    {#redo}

I should have returned to planning when the scope changed. The project began as a rebalancing tool with clear requirements. Then tax work needed richer income data, which led to consolidating ingestion and building document processing with personal information stripped out. Each step followed sensibly from the last, but none was in the plan. On a work project, a conversation with an engineer would have forced a re-plan. Working alone with tools that made each feature feel almost free, I skipped that step and paid for it in refactoring. The lesson generalizes: when building feels cheap, skipped planning becomes expensive.
