# Tract study modeling decisions

Written before fitting the first models, October 24, 2026.

Use diabetes, frequent mental distress, uninsured adults, poverty, and no-vehicle
households, all expressed as percentages. Omit income from the primary model because
poverty already represents economic resources. Compare replacement of poverty with
income on the same complete subset as a sensitivity analysis. All five concepts
receive equal weight after standardization. Correlation remains present; equal
feature weights do not guarantee equal concept weights.

Use tracts with complete primary features, positive ACS population, and matching
2023 polygons. No imputation, population weighting, or geographic coordinates in
the distance calculation. Keep excluded rows with reasons. These restrictions can
underrepresent unusual tracts; publish county coverage and population summaries.

Fit StandardScaler and compare K-means (30 initializations, seed 20261024) with
agglomerative Ward clustering for k=2 through 6. All comparisons use Euclidean
distance in standardized feature space. Ward has no random initialization.

For each candidate, save silhouette, cluster sizes, and 20 deterministic 80%
subsample comparisons. Refit scaling and clustering within each subsample; compare
its labels to the full fit restricted to those same rows using adjusted Rand index
(ARI). This tests perturbation stability, not out-of-sample predictive accuracy.
Also refit after omitting each feature, swapping income for poverty on common rows,
using RobustScaler, and leaving out each county. Report these separately from
sampling stability. Counties are not independent trials, and this is not a causal
or clinical validation. K-means seed sensitivity uses five additional full fits.

Before viewing results, use the following **project heuristics**, not established
scientific certification thresholds: silhouette >=0.25, smallest group >=5% of
eligible tracts, median subsample ARI >=0.80, tenth-percentile subsample ARI >=0.65,
and minimum leave-one-feature-out ARI >=0.60. A display candidate is the highest
silhouette solution among those meeting all these heuristics. If none pass, display
the best silhouette solution only as an exploratory example and explicitly state
that no candidate met the project's stability rules. Report every candidate.

ACS component margins of error and PLACES intervals remain available in source
outputs. Derived-rate margins of error are explicitly omitted in this first study;
do not interpret its perturbation scores as uncertainty propagation. Health estimates
are crude (age composition can influence groups) and modeled using ACS inputs;
apparent health/social associations are not independent validation.

References: [scikit-learn clustering guide](https://scikit-learn.org/stable/modules/clustering.html)
and [Census cartographic boundaries](https://www.census.gov/geographies/mapping-files/2023/geo/carto-boundary-file.html).
