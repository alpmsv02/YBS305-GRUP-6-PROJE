-- Dış kaynak: Open-Meteo günlük hava durumu (mağaza başına varsayılan şehir).
select
    store_id,
    city,
    cast(date as date)                          as date_day,
    cast(temp_max as decimal(5, 1))             as temp_max_c,
    cast(temp_min as decimal(5, 1))             as temp_min_c,
    cast(temp_mean as decimal(5, 1))            as temp_mean_c,
    cast(precipitation_mm as decimal(6, 1))     as precipitation_mm,
    cast(precipitation_mm as double) >= 1.0     as is_rainy
from {{ source('external', 'weather') }}
