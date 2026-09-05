select
    delivery_id,
    order_id,
    delivery_partner_id,
    delivery_time_minutes,
    delivery_status
from {{ source('staging', 'stg_deliveries') }}
