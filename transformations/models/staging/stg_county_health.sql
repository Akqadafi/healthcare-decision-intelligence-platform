select
    cast(county_fips as varchar(5)) as county_fips,
    county_name,
    state,
    cast(population as integer) as population,
    cast(obesity_rate as numeric) as obesity_rate,
    cast(diabetes_rate as numeric) as diabetes_rate,
    cast(hypertension_rate as numeric) as hypertension_rate,
    cast(uninsured_rate as numeric) as uninsured_rate,
    cast(food_insecurity_rate as numeric) as food_insecurity_rate,
    cast(transportation_barrier_rate as numeric) as transportation_barrier_rate
from {{ source('public_health', 'cdc_places_county') }}
