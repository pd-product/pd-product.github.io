---
# Unpublished authoring template. Copy, rename, and set published: true.
published: false
slug: "example-story"
title: "The full case title"
crumb: "short breadcrumb"
description: "The situation, the call, and what it cost."
lesson: "The one sentence to remember."
category: "Category"
order: 99
date: 2026-01-01
last_modified_at: 2026-01-01

flavor: "Example Flavor"
pint_id: "example"
home_title_lines:
  - "The first title line"
  - "The second title line"
fact_problem: "The concise problem shown in the label dialog."
fact_approach: "The concise approach shown in the label dialog."

role: "Your role and ownership."
team: "Who you worked with."
partners: "External or cross-org partners, when applicable."
timeframe: "How long it ran."

tradeoffs:
  - rejected: "The expected option"
    chosen: "What you did"
    rows:
      - dimension: "Time to ship"
        rejected: "Expected option"
        chosen: "Chosen option"
      - dimension: "What it fixes"
        rejected: "Expected option"
        chosen: "Chosen option"
      - dimension: "Cost of being wrong"
        rejected: "Expected option"
        chosen: "Chosen option"
---

## The situation    {#situation}

Opening context.

## Constraints I was handed    {#constraints}

- Constraint one.
- Constraint two.
- Constraint three.
{: role="list"}

## The call I made    {#the-call}

The decision.

{% include tradeoffs.html tradeoffs=page.tradeoffs %}

The evidence or reasoning.

## What shipped    {#shipped}

The outcome.

{% include result.html value="00" copy="What the result means." %}

## What I would redo    {#redo}

The retrospective.
