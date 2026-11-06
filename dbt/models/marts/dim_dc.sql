-- Dağıtım merkezi boyutu: merkez hub ve 3 bölgesel DC (gerçek Walmart DC konumları; hub ataması varsayımdır).
select
    dc_id,
    dc_name,
    dc_level,
    cast(walmart_dc_number as varchar) as walmart_dc_number,
    city,
    state_id,
    cast(latitude as double)  as latitude,
    cast(longitude as double) as longitude,
    source_note
from {{ ref('dc_locations') }}
