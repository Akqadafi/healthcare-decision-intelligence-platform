# Modeling plan after reliability fixes

## Current evidence and limits

The app compares 15 Arizona counties using bundled public aggregate releases.
Release years do not establish a consistent longitudinal dataset. There are no
observed intervention, participation, cost, savings, or program-outcome labels.
The priority score is a deterministic planning rule, not a predicted outcome.

## 1. Sensitivity and allocation comparisons

Extend the existing missing-rating comparison with editable domain weights and
cost scenarios. Display rank shifts, weighted contribution bars, counties selected,
and budget remaining. Preserve the baseline and show all changed assumptions.
Accept when default outputs match the baseline and perturbation tests explain
every changed result. This requires no learned model.

## 2. Illustrative cost and ROI scenarios

Collect intervention units, fixed/variable costs, assumed participation, and
assumed monetized benefits over an explicit time horizon. Show cost per assumed
participant, total cost, net benefit, ROI, and break-even participation/benefit.
ROI = (assumed benefit - cost) / cost, only when cost is positive.
Use low/base/high scenarios and break-even charts. Defaults must be labeled
hypothetical with no claim of realized savings, causal benefit, or clinical value.
Do not derive program capacity from the current 2%-of-population heuristic.

## 3. Obtain data for one prediction question

Choose a measurable outcome, prediction date, unit of observation, and intended
use first. County-level forecasting requires comparable historical observations
and documented changes in source definitions. Program completion classification
requires actual program-level completion labels and approved access; the current
county snapshots do not contain them. Do not construct labels from our own
priority tiers and present learned tiers as new evidence.

## 4. Baseline models and evaluation

For a binary observed outcome, evaluate regularized logistic regression against
a simple prevalence baseline. Use linear regression or a time-series baseline
for an appropriate continuous target. Fit imputation/scaling on training data
only inside a scikit-learn Pipeline. Split by time and/or location when that
matches the proposed use, preventing records from the same unit leaking across
partitions. Data adequacy, class counts, and dependence determine whether modeling
is feasible; do not assume 15 counties are adequate for predictive validation.

Report held-out error, calibration and uncertainty, not accuracy alone. Inspect
performance across relevant groups/locations with sufficient observations.
Features available after the prediction date are excluded. Predictive association
does not establish intervention effectiveness or causal financial returns.

## 5. Deployment and visuals

Train outside Streamlit. Version the validated dataset, split definitions, feature
schema, fitted pipeline, dependency versions, model card, and evaluation report.
The app loads an approved artifact; it does not retrain on each visit. Compare
baseline vs model, predicted vs observed values, calibration curves and residuals.
Keep current rule-based planning accessible. No prediction feature is published
until data and evaluation support its stated purpose.
