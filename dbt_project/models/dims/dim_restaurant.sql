select
    r.restaurant_id,
    r.restaurant_name,
    r.url,
    r.address,
    l.location_id,
    r.restaurant_type,
    r.meal_type,
    r.rating,
    r.vote_count,
    r.avg_cost_for_two,
    r.online_order_enabled,
    r.table_booking_enabled
from {{ source('staging', 'stg_restaurants') }} r
left join {{ ref('dim_location') }} l on l.area = r.area
