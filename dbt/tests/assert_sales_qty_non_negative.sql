-- Satış adedi negatif olamaz.
select *
from {{ ref('fct_sales_daily') }}
where sales_qty < 0
