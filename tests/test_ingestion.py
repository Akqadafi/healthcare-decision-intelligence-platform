import pandas as pd

from healthcare_di.ingestion import aggregate_cms


def test_cms_aggregation_preserves_missing_ratings() -> None:
    hospitals = pd.DataFrame(
        [
            {
                "facility_id": "1",
                "countyparish": "TEST",
                "hospital_overall_rating": "Not Available",
                "emergency_services": "Yes",
                "meets_criteria_for_birthing_friendly_designation": "Y",
            },
            {
                "facility_id": "2",
                "countyparish": "TEST",
                "hospital_overall_rating": "4",
                "emergency_services": "No",
                "meets_criteria_for_birthing_friendly_designation": "",
            },
        ]
    )
    result = aggregate_cms(hospitals).iloc[0]
    assert result["hospital_count"] == 2
    assert result["rated_hospital_count"] == 1
    assert result["average_hospital_rating"] == 4
    assert result["emergency_hospital_count"] == 1
