---
slug: "personal-finance-tools"
title: "The spreadsheet that became a toolkit"
# Header breadcrumb label on this story's page ("work / <crumb>"). Approved comp
# copy, not a trim of `title` -- the full title is too long for that slot.
crumb: "personal finance tools"
# Shown under the title on the STORY PAGE, and read by jekyll-seo-tag as the
# meta description. It no longer renders on the home-page row -- that is a
# template decision in index.html, not a reason to drop the key. The key must
# be `description`: with any other name seo-tag falls back to page.excerpt,
# which is the first block of the body -- the opening `## ` heading. Search and
# link previews then read that heading instead.
description: "I set out to rebalance our portfolio in a spreadsheet, realized how tedious it would be to maintain, and decided to find out what I could build instead. It turned into a suite of tools, and a lesson about scope."
# One line, and the only prose on the home-page row now that the description
# does not render there. Owner-supplied, and deliberately shorter than this
# story's "What I would redo" chapter, which makes the same point at length.
lesson: "When building feels cheap, skipped planning becomes expensive."
category: "personal"
order: 3
# Publication date of this page, not the date of the work it describes. Without
# it Jekyll falls back to BUILD time, so datePublished and the sitemap lastmod
# move on every deploy and re-announce the story as new. Set once, then leave it.
date: 2026-08-04
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

I started building the rebalancing model in a spreadsheet. Fairly early on it became clear that it would be too tedious and time consuming to maintain. This was the same period I was learning what agentic coding tools could actually do at work, so I decided to find out what I could build instead. The tension was mundane and familiar: the obvious solution was the one I would end up avoiding.

## Constraints I set myself    {#constraints}

- The inputs are personal financial information, so nothing could be handled carelessly and no real figures could go anywhere they did not need to be.
- Nobody else was going to maintain this, so complexity I added was complexity I would carry myself.
- The tax work depended on income information that the rebalancing work did not need, so the data the tools required was not going to stay simple.
{: role="list"}

## The call I made    {#the-call}

The expected option was a spreadsheet, or paying for a product that does some of this. I already subscribe to Monarch, which aggregates accounts well. The call I made was to keep it for what it does well and build only the parts where my approach does not match how that product thinks about the problem. That meant writing a short requirements document first, treating a personal project like a product with a defined scope, and then building against it.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

I kept Monarch for aggregating and exporting the data, which is the part it does better than anything I would write, and built tools that consume that export. That boundary meant I never had to rebuild aggregation. The tools now cover rebalancing, estimated tax payments, spend analysis, and budgeting.

## What I built    {#shipped}

A suite of Python tools covering rebalancing, estimated tax payments, spend analysis, and budgeting. The obvious benefit is that they save me the manual work. The one I did not anticipate is that they let me run each exercise as often as I want, more accurately and in more depth than I otherwise would. That turned out to be the actual value, and it matches what I found using the same tools at work. The real gain was reaching analysis I would otherwise have skipped.

## What I would redo    {#redo}

I would have gone back to planning when the scope changed, and I did not. The project started as a rebalancing tool with a clear requirements document. Then the tax work needed richer income data, which made me want to consolidate how all the tools ingested data, which led to building document processing with personal information stripped out. Each step followed sensibly from the last and none of them were in the original plan. I would never have let that happen on a work project, because a conversation with an engineer would have forced a re-plan. Building alone with tools that make the next feature feel almost free, I skipped that step, and I paid for it in refactoring that cost more than the planning would have. The lesson generalizes past this project: when building feels cheap, skipped planning becomes expensive.
