"""Configuration and data contracts used throughout the platform."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshots"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

CDC_DATASET_ID = "i46a-9kgh"
CDC_API_URL = f"https://data.cdc.gov/resource/{CDC_DATASET_ID}.json"
CMS_DATASET_ID = "xubh-q36u"
CMS_API_URL = (
    f"https://data.cms.gov/provider-data/api/1/datastore/query/{CMS_DATASET_ID}/0"
)
CENSUS_ACS_YEAR = 2024
CENSUS_PROFILE_URL = f"https://api.census.gov/data/{CENSUS_ACS_YEAR}/acs/acs5/profile"

CDC_COLUMNS = [
    "stateabbr",
    "countyname",
    "countyfips",
    "totalpopulation",
    "access2_crudeprev",
    "checkup_crudeprev",
    "obesity_crudeprev",
    "diabetes_crudeprev",
    "bphigh_crudeprev",
    "phlth_crudeprev",
    "mhlth_crudeprev",
    "foodinsecu_crudeprev",
    "lacktrpt_crudeprev",
    "geolocation",
]

INTERVENTION_COSTS = {
    "Mobile clinic day": 25_000,
    "Community health worker team": 60_000,
    "Benefits navigation campaign": 18_000,
    "Behavioral health outreach": 35_000,
    "Hospital quality partnership": 45_000,
}
