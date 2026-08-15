# ADR 0001: Use an explainable weighted index for the MVP

- **Status:** Accepted
- **Date:** 2026-08-15

## Context

Healthcare resource allocation requires traceability, and the first release has only 15 Arizona
county observations. A supervised model would lack a defensible outcome label and enough samples.

## Decision

Use within-state percentile ranks, explicit domain weights, rule-based recommendations, and a
documented uncertainty treatment for missing ratings.

## Consequences

Leadership can inspect every input and calculation. The scores are relative to Arizona and cannot
be interpreted as probabilities or causal effects. Weight sensitivity and community validation
are required before operational use.
