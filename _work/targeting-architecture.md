---
slug: "targeting-architecture"
title: "Rebuilding how publishers target their inventory"
summary: "Publishers had to describe their inventory placement by placement, which meant maintaining thousands of configurations to express something simple. The cheaper option was to leave it alone and let them absorb the work. I argued for rebuilding the targeting model instead."
# One line, shown on the home-page row under the summary. A trim of this
# story's own "What I would redo" chapter, approved as written.
lesson: "Treat the customer experience of a transition as part of the design, not as something that follows it."
category: "supply"
order: 1
role: "PM, Prebid Server Premium. Owned roadmap and outcome."
team: "Customers, support, design, multiple eng teams"
partners: "1P and 3P publishers, demand partners, support and services"
timeframe: "Over a year, scoping to GA"
chips:
  - "over a year"
  - "GA in stages"
# No hero_image for v1 -- the site ships without diagrams. Adding one here is
# the only change needed to bring the hero and home-page card back.
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

Customers were direct with me about how prohibitive this overhead was. They had given the same feedback before, and the design had not changed in response. There were other friction points for both customers and the teams supporting them, but this one was the piece that had to be solved. The tension was that the platform worked. The argument against fixing it was that we would be re-architecting something that already functioned, which made it easy to keep deferring.

## Constraints I was handed    {#constraints}

1. The existing model was live and carrying real publisher revenue, so nothing could break for anyone already running on it.
2. The only alternative on the table was making no investment at all and letting first-party and third-party publishers keep absorbing the friction.
3. Ownership of the core targeting logic was genuinely unsettled between engineering teams, and engineering leadership had to settle it before the work could be assigned.

## The call I made    {#the-call}

The expected option was to leave it. Prebid Server Premium functioned, the bulk tools we had were rudimentary but they existed, and the complaints were coming from customers rather than from any internal metric. I argued for rebuilding the targeting model so publishers could express intent at whatever level actually matched how they sell, from run of site all the way down to an individual placement, with geographic, device, segment, and key-value targeting alongside it. That meant re-architecting something that already worked, and asking multiple engineering teams to commit to more than a year of work on the strength of customer complaints.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

I made the case with three kinds of evidence together, because no single one was enough. Qualitative customer feedback established that the problem was real and specific. Comparison against competitor platforms established that our model was the outlier. Internal data on configurations, revenue, and usage established the scale. On its own each was arguable. Together they were hard to set aside.

## What shipped    {#shipped}

Publishers now express targeting at whatever granularity matches how they actually sell, with geographic, device, segment, and key-value dimensions available alongside it. The average number of active configurations a publisher maintains fell by about a third, comparing the state before the work began to two months after general availability, and revenue grew through the transition. The rollout went through publishers on the API first to prove out architecture, reliability, and performance, then through the interface with a deliberately vocal group of customers, then to general availability, with both models available in parallel afterward and remaining customers migrated by script so the old architecture could be fully retired.

The configuration count is the visible proxy. The substance is that publishers can now say what they mean once, instead of restating it placement by placement.

## What I would redo    {#redo}

At general availability my instinct was to let both models coexist for a while, undefined but not indefinite, so publishers could move at their own pace. The team working directly with customers told me almost immediately that having both options visible was causing confusion and churn. What looked like optionality to me looked like ambiguity to a publisher deciding which one to use. The technical rollout had been staged carefully; the customer-facing transition had not been staged with the same rigor, and the gap was communication and education before launch rather than anything in the software. I reversed the decision, built a migration plan and a communications plan with engineering and services, and moved everyone. The lesson I took is to treat the customer experience of a transition as part of the design, not as something that follows it.
