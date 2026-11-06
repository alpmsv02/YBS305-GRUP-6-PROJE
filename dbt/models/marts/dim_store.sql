-- Mağaza boyutu: hangi bölgesel DC'ye bağlı olduğu ve varsayılan konumu.
select
    store_id,
    state_id                  as dc_id,
    state_id,
    city,
    cast(latitude as double)  as latitude,
    cast(longitude as double) as longitude
from {{ ref('store_locations') }}
