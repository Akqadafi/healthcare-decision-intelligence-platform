import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score

from healthcare_di.tract_models import FEATURES, cohort, fit, passes_rules


def test_cohort_preserves_excluded_rows_and_reasons():
    frame = pd.DataFrame({feature: [10.0, 20.0, 30.0] for feature in FEATURES})
    frame["tractfips"] = ["04001942600", "04001942700", "04001942800"]
    frame["B01003_E001_numeric"] = [100, 100, 0]
    frame.loc[1, "poverty_pct"] = np.nan
    result = cohort(frame)
    assert len(result) == 3
    assert result.eligible.tolist() == [True, False, False]
    assert result.exclusion_reason.tolist() == [
        "", "poverty_pct", "nonpositive_or_missing_population"
    ]


@pytest.mark.parametrize("method", ["kmeans", "ward"])
def test_separated_groups_recovered_and_scaling_refitted(method):
    rng = np.random.default_rng(23)
    values = np.r_[rng.normal(-10, 0.1, (20, 3)), rng.normal(10, 0.1, (20, 3))]
    labels, scaled = fit(values, method, 2)
    assert adjusted_rand_score([0] * 20 + [1] * 20, labels) == 1
    assert np.allclose(scaled.mean(axis=0), 0)
    _, rescaled = fit(values[:25], method, 2)
    assert np.allclose(rescaled.mean(axis=0), 0)
    assert not np.allclose(scaled[:25].mean(axis=0), 0)


@pytest.mark.parametrize("values", [[[1, np.nan], [2, 3], [4, 5]],
                                     [[1, np.inf], [2, 3], [4, 5]]])
def test_fit_rejects_nonfinite_features(values):
    with pytest.raises(ValueError):
        fit(values, "kmeans", 2)


def test_silhouette_alone_cannot_pass_project_rules():
    row = {"silhouette": 0.8, "minimum_share": 0.2, "subsample_ari_median": 0.95,
           "subsample_ari_p10": 0.9, "omit_feature_ari_min": 0.2}
    assert not passes_rules(row)
    row["omit_feature_ari_min"] = 0.7
    assert passes_rules(row)
