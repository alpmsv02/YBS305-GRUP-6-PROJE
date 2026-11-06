select * 
from {{ ref('mart_sku_abc_xyz') }} 
where zero_day_share < 0 or zero_day_share > 1