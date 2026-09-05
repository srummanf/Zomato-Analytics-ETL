select
    rc.restaurant_id,
    c.cuisine_id
from {{ source('staging', 'stg_restaurant_cuisines') }} rc
join {{ ref('dim_cuisine') }} c on c.cuisine = rc.cuisine
