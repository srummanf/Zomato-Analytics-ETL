select distinct
    delivery_partner_id,
    delivery_partner_name
from {{ source('staging', 'stg_deliveries') }}
where delivery_partner_id is not null
