-- Haftalık satış fiyatları, yalnızca kapsamdaki eyaletin mağazaları.
select
    store_id,
    item_id,
    cast(wm_yr_wk as integer)      as wm_yr_wk,
    cast(sell_price as decimal(10, 2)) as sell_price
from {{ source('m5', 'sell_prices') }}
where split_part(store_id, '_', 1) in ({% for s in var('states') %}'{{ s }}'{% if not loop.last %}, {% endif %}{% endfor %})
