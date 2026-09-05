with distinct_dates as (
    select distinct order_date
    from {{ source('staging', 'stg_orders') }}
    where order_date is not null
)

select
    order_date as date_id,
    order_date as full_date,
    extract(year from order_date)::int as year,
    extract(quarter from order_date)::int as quarter,
    extract(month from order_date)::int as month,
    to_char(order_date, 'Month') as month_name,
    extract(day from order_date)::int as day,
    extract(isodow from order_date)::int as day_of_week,
    to_char(order_date, 'Day') as day_name,
    extract(isodow from order_date) in (6, 7) as is_weekend
from distinct_dates
