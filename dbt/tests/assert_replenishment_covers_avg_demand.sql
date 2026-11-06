-- Önerilen sevkiyat miktarı ortalama haftalık talebin altında olamaz.
select *
from {{ ref('mart_store_replenishment') }}
where recommended_weekly_qty < avg_weekly_units
