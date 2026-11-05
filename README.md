# YBS305 – Bölgesel Dağıtım Merkezinde Talep Odaklı Depo Yerleşimi ve Mağaza Dağıtım Planlaması

Это мой 


**Ders:** YBS305 İş Zekâsı ve Veri Madenciliği (2026–2027 Güz)
**Öğretim Elemanı:** Ece Dalpolat
**Grup:** 6

## Ekip

| Ad Soyad | GitHub | Sorumluluk |
|---|---|---|
| NURASYL UTEPBERGEN | alpmsv02 | Dokümantasyon, GitHub |
| IBROKHIMKHUJA ASKARKHONOV | - | dbt / ETL |
| MUKHAMMADAMIN YULDASHEV | yuldoshevm22 | Dashboard |

## Proje Amacı

Bölgesel bir dağıtım merkezinde mağaza taleplerini analiz ederek depo yerleşimine ve mağazalara sevkiyat planlamasına karar desteği sağlamak.

İki temel soru:
1. Hangi ürünler yüksek ve istikrarlı talep görüyor, depoda hızlı erişilebilir bölgede hangileri durmalı?
2. Mağazalara hangi ürün gruplarından ne kadar sevkiyat yapılmalı?

## Veri Kaynakları

- **NovaPerakende** veri seti (`perakende_satis`, `müşteri`, `sepet`)
- **M5 Forecasting (Walmart)**, Kaggle: günlük satış (`sales_train_validation.csv`), takvim (`calendar.csv`), fiyat (`sell_prices.csv`)

> Ham veri dosyaları boyutları nedeniyle depoya eklenmemiştir. Kaggle'dan indirip `data/` klasörüne koyunuz.

## Kullanılan Araçlar

| Aşama | Araç |
|---|---|
| Veri ambarı | DuckDB |
| ETL | dbt Core + dbt-duckdb |
| Dashboard | Apache Superset |
| Sürüm kontrolü | Git + GitHub |

**Neden Superset?** Açık kaynaklıdır, SQL tabanlıdır ve DuckDB ile bağlanabilir. Kullanımı öğretim elemanı tarafından onaylanmıştır.

## Proje Yapısı

```
data/       # ham veriler (depoya eklenmez)
dbt/        # dbt projesi (staging ve mart katmanları, testler)
superset/   # Superset kurulumu, ekran görüntüleri, dashboard dışa aktarımı
docs/       # dokümantasyon
```

## Kurulum ve Çalıştırma

```bash
pip install dbt-duckdb
cd dbt
dbt run
dbt test
dbt docs generate
dbt docs serve
```

Superset kurulumu için `superset/README.md` dosyasına bakınız.

## Bölüm 1 Teslim Listesi

- [ ] dbt projesi (staging ve mart modelleri, en az 3 test)
- [ ] Dashboard (en az 3 KPI, 3 görsel, 1 filtre)
- [ ] Veri sözlüğü
- [ ] dbt docs
- [ ] Ekran görüntüleri ve dashboard dışa aktarımı

## İş Çıkarımları

_Dashboard tamamlandıktan sonra buraya 3 kısa öneri eklenecek._

## Veri Sözlüğü

_Eklenecek (docs/veri_sozlugu.md)._
