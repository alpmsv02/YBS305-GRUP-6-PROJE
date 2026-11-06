-- Dış kaynak: haftalık dizel fiyatı (USD/galon) bölge bazında.
select
    region,
    series_id,
    cast(week_date as date)                 as week_date,
    cast(price_usd_gal as decimal(6, 3))    as price_usd_gal
from {{ source('external', 'diesel_prices') }}
