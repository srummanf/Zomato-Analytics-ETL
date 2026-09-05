select
    order_item_id,
    order_id,
    item_name,
    item_price
from {{ source('staging', 'stg_order_items') }}
