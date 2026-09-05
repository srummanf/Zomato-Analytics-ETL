select
    o.order_id,
    o.customer_id,
    o.restaurant_id,
    r.location_id,
    o.order_date as date_id,
    o.order_hour as hour_id,
    o.party_size,
    o.order_total,
    o.order_status
from {{ source('staging', 'stg_orders') }} o
left join {{ ref('dim_restaurant') }} r on r.restaurant_id = o.restaurant_id
