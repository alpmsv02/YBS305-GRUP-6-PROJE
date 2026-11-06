select * 
from {{ ref('fct_route') }} 
where distance_km <= 0