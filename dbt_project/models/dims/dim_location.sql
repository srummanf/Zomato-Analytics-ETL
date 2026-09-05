with distinct_areas as (
    select distinct area
    from {{ source('staging', 'stg_restaurants') }}
    where area is not null
)

select
    row_number() over (order by area) as location_id,
    area
from distinct_areas
