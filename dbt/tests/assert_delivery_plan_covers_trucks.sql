-- Seçilen planda sefer sayısı haftalık adedi taşımaya yetmeli.
select p.*
from {{ ref('mart_delivery_plan') }} p, (select max(case when param='truck_capacity_units' then value end) cap from {{ ref('cost_params') }}) c
where p.trips_per_week * c.cap < p.weekly_qty
