# Veri Sözlüğü

Tüm tablolar DuckDB dosyasında (`data/warehouse/dc_planning.duckdb`), şema `main_staging` ve `main_marts`.
Kapsam: CA, TX, WI (10 mağaza), 24.05.2014 – 22.05.2016.

## Ham kaynaklar (`data/raw`, `data/external`, `dbt/seeds`)

| Dosya | Satır | Açıklama |
|---|---|---|
| `calendar.csv` | 1.969 | Gün başına: `date`, `d` (d_1..d_1969), `wm_yr_wk`, `weekday`, `event_name_1/2`, `event_type_1/2`, `snap_CA/TX/WI` |
| `sales_train_evaluation.csv` | 30.490 | SKU × mağaza satırları; `d_1..d_1941` sütunları günlük satış adedi |
| `sell_prices.csv` | 6.841.121 | `store_id`, `item_id`, `wm_yr_wk`, `sell_price` (USD) |
| `weather.csv` | 7.810 | Open-Meteo: `store_id`, `city`, `date`, `temp_max/min/mean` (°C), `precipitation_mm` |
| `routes.csv` | 182 | OSRM: `origin_id`, `dest_id`, `distance_km`, `duration_min`, `method` (osrm / haversine yedek) |
| `diesel_prices.csv` | 624 | FRED/EIA: `region` (US, CA, TX, WI), `series_id`, `week_date`, `price_usd_gal` |
| `store_locations.csv` (seed) | 10 | Mağaza → varsayılan şehir, enlem, boylam |
| `dc_locations.csv` (seed) | 4 | HUB + 3 bölgesel DC: ad, Walmart DC numarası, şehir, koordinat, kaynak notu |
| `cost_params.csv` (seed) | 6 | Maliyet parametreleri: ATRI $/mil, yakıt $/mil, mpg, tır kapasitesi, stok taşıma oranı, elleçleme günü |

## Staging

### `stg_calendar` (1.969 satır)
| Sütun | Tip | Açıklama |
|---|---|---|
| date_day | DATE | Takvim günü (tekil) |
| day_key / day_idx | VARCHAR / INT | M5 gün anahtarı `d_N` / N |
| wm_yr_wk | INT | Walmart yıl-hafta kodu (ör. 11613); hafta Cumartesi başlar |
| weekday_name / weekday_num | VARCHAR / INT | Gün adı; 1 = Cumartesi … 7 = Cuma (M5 kuralı) |
| is_weekend, is_event, event_name, event_type | | Hafta sonu ve etkinlik bayrakları (Sporting, Cultural, National, Religious) |
| is_snap_ca / is_snap_tx / is_snap_wi | BOOL | Eyalette SNAP (gıda yardımı) kullanım günü |

### `stg_sales_long` (22.257.700 satır) — `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`, `day_key`, `sales_qty` (≥ 0, sıfırlar dahil)
### `stg_prices` — `store_id`, `item_id`, `wm_yr_wk`, `sell_price` DECIMAL(10,2)
### `stg_weather` — `store_id`, `city`, `date_day`, `temp_max_c`, `temp_min_c`, `temp_mean_c`, `precipitation_mm`, `is_rainy` (≥ 1 mm)
### `stg_routes` — `origin_id`, `dest_id`, `distance_km`, `distance_miles`, `duration_min`, `leg_type` (HUB_TO_DC / DC_TO_STORE / OTHER)
### `stg_diesel_prices` — `region`, `series_id`, `week_date`, `price_usd_gal`

## Marts

### `dim_product` (3.049) — `item_id` (PK), `dept_id`, `cat_id`
### `dim_store` (10) — `store_id` (PK), `dc_id` (= eyalet), `state_id`, `city`, `latitude`, `longitude` (varsayılan şehirler)
### `dim_dc` (4) — `dc_id` (HUB, CA, TX, WI), `dc_name`, `dc_level` (HUB / RDC), `walmart_dc_number`, `city`, `state_id`, `latitude`, `longitude`, `source_note`

### `fct_sales_daily` (22.257.700 satır) — ayrıntı düzeyi (grain): SKU × mağaza × gün
| Sütun | Tip | Açıklama |
|---|---|---|
| date_day, wm_yr_wk | DATE, INT | |
| dc_id, state_id, store_id, item_id, dept_id, cat_id | VARCHAR | dc_id = mağazanın bağlı olduğu bölgesel DC |
| sales_qty | INT | Satış adedi |
| sell_price | DECIMAL | O haftaki fiyat; ürün henüz listelenmemişse NULL |
| revenue | DECIMAL(12,2) | sales_qty × sell_price |
| weekday_name, weekday_num, weekday_label | | `weekday_label` = "1. Cumartesi" … "7. Cuma" (sıralama ön ekli) |
| is_weekend, is_event, event_type, event_name, is_snap | | Takvim bayrakları; `is_snap` mağazanın eyaletine göre |
| temp_mean_c, precipitation_mm, is_rainy | | Hava durumu (dış kaynak) |

### `fct_sales_weekly` (3.201.450) — ayrıntı düzeyi: SKU × mağaza × hafta
`wm_yr_wk`, `week_start`, `dc_id`, `state_id`, `store_id`, `item_id`, `dept_id`, `cat_id`, `units`, `revenue`, `zero_days`, `days_in_week`,
`is_complete_week` (7 gün = tam hafta; mart pencereleri yalnızca tam haftaları kullanır)

### `fct_route` (13) — ayrıntı düzeyi: bacak (origin → dest); yalnızca HUB_TO_DC ve DC_TO_STORE
| Sütun | Açıklama |
|---|---|
| distance_km, distance_miles, duration_min, duration_hours | OSRM yol mesafesi ve sürüş süresi (tek yön) |
| lead_time_days | ⌈sürüş saati / 24⌉ + DC elleçleme günü (1) |
| diesel_usd_gal | Varış bölgesinin satış dönemi sonundaki haftalık dizel fiyatı |
| cost_per_mile_usd | (ATRI toplam − ATRI yakıt) + dizel / mpg |
| round_trip_cost_usd | 2 × mil × cost_per_mile_usd |

### `mart_sku_abc_xyz` (12.196) — ayrıntı düzeyi: depo seviyesi × SKU; pencere: son 52 tam hafta
| Sütun | Açıklama |
|---|---|
| dc_id, dc_name | HUB (tüm ağ toplamı) veya CA / TX / WI (bölgesel DC toplamı) |
| units_52w, revenue_52w | 52 haftalık toplam adet ve ciro |
| active_weeks, avg_weekly_units, cv_weekly | Ürünün listede olduğu hafta sayısı; ortalama haftalık adet ve değişkenlik katsayısı (σ/μ) — yalnızca listede olduğu haftalar üzerinden |
| zero_day_share | Sıfır satış günü oranı (0–1) |
| cum_revenue_share | Depo içinde ciroya göre sıralı kümülatif pay |
| picking_rank | Depo içinde adede göre toplama sırası (1 = en hızlı dönen) |
| abc_class | A: kümülatif ciro ≤ %80, B: ≤ %95, C: kalan |
| xyz_class | X: CV < 0,5 (düzenli), Y: CV < 1,0, Z: ≥ 1,0 (düzensiz) |
| abc_xyz, warehouse_zone, zone_label | **HOT**: AX, AY · **WARM**: AZ, BX, BY · **COLD**: BZ, C*; `zone_label` = "1. HOT" / "2. WARM" / "3. COLD" (sıralama ön ekli; HOT = rampaya yakın hızlı bölge, COLD = uzak raf) |

### `mart_store_replenishment` (30.490) — ayrıntı düzeyi: SKU × mağaza; pencere: son 13 tam hafta
| Sütun | Açıklama |
|---|---|
| avg_weekly_units, std_weekly_units, max_weekly_units, units_13w | Haftalık talep istatistikleri |
| avg_unit_price | 13 haftalık ciro / adet |
| safety_stock | Emniyet stoku: ⌈1,65 × σ⌉ (%95 hizmet seviyesi, tedarik süresi 1 hafta) |
| recommended_weekly_qty | ⌈μ + 1,65 σ⌉ — önerilen haftalık sevkiyat |
| abc_class, xyz_class, warehouse_zone | Mağazanın bağlı olduğu bölgesel DC'nin sınıfı |

### `mart_delivery_options` (50) — ayrıntı düzeyi: mağaza × teslimat sıklığı (1, 2, 3, 5, 7 / hafta)
| Sütun | Açıklama |
|---|---|
| weekly_qty, weekly_value_usd | Mağazanın haftalık sevkiyat adedi ve değeri (Σ recommended_weekly_qty × avg_unit_price) |
| trips_per_week | k × ⌈weekly_qty / (k × tır kapasitesi)⌉ |
| transport_cost_week_usd | trips_per_week × round_trip_cost_usd |
| holding_cost_week_usd | weekly_value / (2k) × yıllık taşıma oranı / 52 (ortalama stok maliyeti) |
| total_cost_week_usd | Taşıma + stok taşıma |

### `mart_delivery_plan` (10) — ayrıntı düzeyi: mağaza; toplam maliyeti en küçükleyen seçenek
`optimal_deliveries_per_week`, `schedule_label` ("Haftada 3 (Pzt-Çrş-Cum)" vb.), `trips_per_week`, `weekly_qty`, `distance_km`, `duration_hours`,
`round_trip_cost_usd`, `transport_cost_week_usd`, `holding_cost_week_usd`, `total_cost_week_usd`, `transport_cost_per_unit_usd`

### `mart_hub_supply_plan` (3) — ayrıntı düzeyi: bölgesel DC
| Sütun | Açıklama |
|---|---|
| weekly_qty, weekly_value_usd, n_stores | DC'nin mağaza planlarının toplamı |
| distance_km, duration_hours, lead_time_days | Hub → DC (OSRM) |
| trucks_per_week | ⌈weekly_qty / tır kapasitesi⌉ |
| transport_cost_week_usd, transport_cost_per_unit_usd | Haftalık hub → DC taşıma maliyeti |
| pipeline_stock_units | Yoldaki stok: günlük ihtiyaç × tedarik süresi |

### `mart_calendar_effects` (123) — ayrıntı düzeyi: DC × kategori × gün tipi × hava tipi
| Sütun | Açıklama |
|---|---|
| day_type | "1. Hafta içi", "2. Hafta sonu", "3. SNAP hafta içi", "4. Spor etkinliği", "5. Kültürel etkinlik", "6. Ulusal bayram", "7. Dinî bayram" |
| weather_type | Kuru / Yağışlı (≥ 1 mm) |
| n_days, avg_units_per_sku | Gün sayısı; SKU başına ortalama günlük adet |
| baseline_units, lift_vs_baseline | Kuru hafta içi ortalaması; avg / baseline − 1 |
