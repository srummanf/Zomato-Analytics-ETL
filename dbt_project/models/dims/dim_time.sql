select
    hour as hour_id,
    hour as hour_of_day,
    case
        when hour between 6 and 10 then 'Breakfast'
        when hour between 11 and 15 then 'Lunch'
        when hour between 16 and 18 then 'Evening Snacks'
        when hour between 19 and 22 then 'Dinner'
        else 'Late Night'
    end as time_period
from generate_series(0, 23) as hour
