-- The Python scoring engine is authoritative in the MVP. This dbt model exposes
-- the resulting mart in warehouses where the CSV is loaded into analytics.
select *
from {{ source('analytics', 'community_priority_score') }}
