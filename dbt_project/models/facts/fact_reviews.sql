select
    row_number() over (order by restaurant_id) as review_id,
    restaurant_id,
    review_rating,
    review_text
from {{ source('staging', 'stg_reviews') }}
