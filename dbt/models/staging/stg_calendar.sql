-- Takvim boyutu: her satır bir gün. Walmart haftası, hafta sonu, etkinlik ve SNAP bayrakları.
select
    cast(date as date)                              as date_day,
    d                                               as day_key,
    cast(replace(d, 'd_', '') as integer)           as day_idx,
    cast(wm_yr_wk as integer)                       as wm_yr_wk,
    weekday                                         as weekday_name,
    cast(wday as integer)                           as weekday_num,
    cast(month as integer)                          as month_num,
    cast(year as integer)                           as year_num,
    weekday in ('Saturday', 'Sunday')               as is_weekend,
    event_name_1                                    as event_name,
    event_type_1                                    as event_type,
    event_name_1 is not null                        as is_event,
    cast(snap_CA as integer) = 1                    as is_snap_ca,
    cast(snap_TX as integer) = 1                    as is_snap_tx,
    cast(snap_WI as integer) = 1                    as is_snap_wi
from {{ source('m5', 'calendar') }}
