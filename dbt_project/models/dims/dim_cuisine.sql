with distinct_cuisines as (
    select distinct cuisine
    from {{ source('staging', 'stg_restaurant_cuisines') }}
    where cuisine is not null
)

select
    row_number() over (order by cuisine) as cuisine_id,
    cuisine
from distinct_cuisines
