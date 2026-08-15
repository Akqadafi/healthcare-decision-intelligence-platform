# Model card: Community Priority Score v1.0

## Summary

A deterministic weighted index that ranks Arizona counties for outreach and access investment.
It is not machine learning, a clinical score, or a forecast.

## Intended use

- Portfolio and planning demonstrations.
- Starting conversations about mobile clinics, outreach, benefits navigation, and partnerships.
- Comparing relative need within the same state and snapshot.

## Out-of-scope use

- Individual care, diagnosis, eligibility, or adverse action.
- Measuring program impact or claiming causality.
- Automated funding decisions without local review and community input.
- Comparing scores across states without recalibration.

## Inputs and weights

Health burden 35%, social need 25%, care access 25%, hospital gap 15%. Social need includes
Census poverty and median income plus CDC food insecurity and insurance. Inputs and internal domain
weights are defined in `src/healthcare_di/scoring.py` and summarized in the README.

## Missing data

A missing county average CMS rating receives a hospital-gap value of 60/100 and an explicit
`Insufficient rating data` flag. This reflects planning uncertainty and is not a quality judgment.

## Validation

Automated checks verify schema, county coverage, unique FIPS, score bounds, and recommendation
completeness. Before operational adoption, add stakeholder weight review, sensitivity analysis,
geographic fairness assessment, current local capacity data, and outcome validation.

## Known limitations

- PLACES values are model-based small-area estimates.
- County averages can hide within-county inequity.
- Hospital count is an access proxy, not provider capacity or travel time.
- The allocation reach estimate is illustrative.
- The current snapshot does not yet include HRSA shortage designations.
