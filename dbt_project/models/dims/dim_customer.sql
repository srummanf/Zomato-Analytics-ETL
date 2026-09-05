select
    customer_id,
    name,
    email,
    phone,
    signup_date,
    customer_order_count
from {{ source('staging', 'stg_customers') }}
