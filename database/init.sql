CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.dim_county (
    county_fips CHAR(5) PRIMARY KEY,
    county_name TEXT NOT NULL,
    state CHAR(2) NOT NULL,
    population INTEGER NOT NULL CHECK (population > 0),
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6)
);

CREATE TABLE IF NOT EXISTS analytics.mart_community_priority (
    county_fips CHAR(5) PRIMARY KEY REFERENCES analytics.dim_county(county_fips),
    health_burden_score NUMERIC(5, 2) NOT NULL CHECK (health_burden_score BETWEEN 0 AND 100),
    sdoh_score NUMERIC(5, 2) NOT NULL CHECK (sdoh_score BETWEEN 0 AND 100),
    access_score NUMERIC(5, 2) NOT NULL CHECK (access_score BETWEEN 0 AND 100),
    hospital_gap_score NUMERIC(5, 2) NOT NULL CHECK (hospital_gap_score BETWEEN 0 AND 100),
    total_priority_score NUMERIC(5, 2) NOT NULL CHECK (total_priority_score BETWEEN 0 AND 100),
    priority_tier TEXT NOT NULL,
    primary_drivers TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
