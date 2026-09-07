---
slug: "targeting-architecture"
title: "Rebuilding targeting around how publishers sell"
flavor: "Publisher Pistachio"
pint_id: "publisher"
home_title_lines:
  - "Rebuilding targeting around how publishers sell"
fact_problem: "Publishers maintained thousands of placement-level configurations."
fact_approach: "Rebuild targeting around how publishers sell."
# Concise search/share description. `summary` below preserves the approved,
# longer on-page introduction without forcing it into search-result snippets.
description: "How I rebuilt publisher targeting around the way customers sell, reducing active configurations by 33% while revenue grew."
summary: "Publishers had to describe their inventory placement by placement, which meant maintaining thousands of configurations to express something simple. The cheaper option was to leave it alone and let them absorb the work. I argued for rebuilding the targeting model instead."
# One line, shown on the home-page row. A trim of this story's own "What I
# would redo" chapter, approved as written; the full sentence stays in that
# chapter and this is deliberately the shorter form.
lesson: "Treat the customer experience of a transition as part of the design."
category: "Platforms"
order: 1
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
role: "PM, Prebid Server Premium. Owned roadmap and outcome."
team: "Customers, support, design, multiple eng teams"
partners: "1P and 3P publishers, demand partners, support and services"
timeframe: "Over a year, scoping to GA"
tradeoffs:
  - rejected: "Leave the model alone"
    chosen: "Rebuild the targeting model"
    rows:
      - dimension: "Time to ship"
        rejected: "Nothing to ship; the friction continues"
        chosen: "Over a year from scoping to general availability"
      - dimension: "What it fixes"
        rejected: "Nothing structurally; the bulk tools reduce the symptom slightly"
        chosen: "Lets publishers express intent at the level that matches how they sell, and unlocks better inventory-to-demand matching"
      - dimension: "Cost of being wrong"
        rejected: "Publishers keep absorbing overhead we already knew was prohibitive"
        chosen: "A long investment, plus migrating every existing publisher off a live model without disrupting revenue"
published: true
---

## The situation    {#situation}

Configurations in Prebid Server Premium, Microsoft's server-side header bidding platform for publishers, determine what inventory a publisher sends to which demand partners. Historically that was expressed at the placement level, so a publisher describing their full offering had to create and maintain thousands of individual configurations. For larger publishers it reached into the tens of thousands.

Customers were direct with me about how prohibitive this overhead was. They had given the same feedback before, and the design had not changed. There were other friction points, but this was the piece that had to be solved. The platform worked, which made rebuilding it easy to keep deferring.

## Constraints I was handed    {#constraints}

- The existing model carried real publisher revenue, so nothing could break for anyone already using it.
- The only alternative was making no investment and leaving first-party and third-party publishers to absorb the friction.
- Ownership of the core targeting logic was unsettled between engineering teams; engineering leadership had to resolve it before work could be assigned.
{: role="list"}

## The call I made    {#the-call}

The expected option was to leave it. Prebid Server Premium worked, rudimentary bulk tools existed, and the pressure was coming from customers rather than an internal metric. I argued for rebuilding the model so publishers could express intent at the level that matched how they sell—from run of site to an individual placement, with geographic, device, segment, and key-value targeting alongside it. That meant asking multiple engineering teams to re-architect a live system over more than a year on the strength of customer complaints.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

I made the case with three forms of evidence: customer feedback established that the problem was real and specific; competitor comparison showed that our model was the outlier; and internal configuration, revenue, and usage data established the scale. Each was arguable on its own. Together they were hard to set aside.

## What shipped    {#shipped}

Publishers now express targeting at the granularity that matches how they sell, with geographic, device, segment, and key-value dimensions alongside it. Active configurations per publisher fell by about a third from before the work began to two months after general availability, while revenue grew. We rolled out first to API publishers to prove architecture, reliability, and performance; then to a deliberately vocal group using the interface; then to general availability. Both models ran in parallel until remaining customers were migrated by script and the old architecture retired.

The configuration count is the visible proxy. The substance is that publishers can now say what they mean once, instead of restating it placement by placement.

{% include result.html value="33%" copy="fewer active configurations per publisher two months after general availability, while revenue grew through the transition." %}

## What I would redo    {#redo}

At general availability, I wanted both models to coexist for a while so publishers could move at their own pace. The team working directly with customers quickly reported that having both options visible caused confusion and churn: what looked like optionality to me looked like ambiguity to a publisher. We had staged the technical rollout carefully, but not the customer transition; the gap was communication and education, not software. I reversed the decision, built migration and communications plans with engineering and services, and moved everyone.
