-- Dış kaynak: OSRM yol mesafesi/süresi. Tek yön; bacak tipi: HUB→DC, DC→STORE, diğerleri (analiz için saklanır).
select
    origin_id,
    origin_type,
    dest_id,
    dest_type,
    cast(distance_km as decimal(8, 1))      as distance_km,
    cast(duration_min as decimal(8, 1))     as duration_min,
    cast(distance_km / 1.609344 as decimal(8, 1)) as distance_miles,
    method,
    case
        when origin_id = 'HUB' and dest_type = 'DC' then 'HUB_TO_DC'
        when origin_type = 'DC' and origin_id <> 'HUB' and dest_type = 'STORE'
             and split_part(dest_id, '_', 1) = origin_id then 'DC_TO_STORE'
        else 'OTHER'
    end as leg_type
from {{ source('external', 'routes') }}
