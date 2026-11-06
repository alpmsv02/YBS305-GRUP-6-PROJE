#!/usr/bin/env bash
# dbt → DuckDB → Superset yayın adımı. Dosya atomik olarak değiştirilir (mv), Superset'in açık bağlantıları bozulmaz.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/dbt"
"$ROOT/.venv/bin/dbt" seed --profiles-dir .
"$ROOT/.venv/bin/dbt" run  --profiles-dir .
"$ROOT/.venv/bin/dbt" test --profiles-dir .
"$ROOT/.venv/bin/dbt" docs generate --profiles-dir .
cp "$ROOT/data/warehouse/build/dc_planning.duckdb" "$ROOT/data/warehouse/.dc_planning.tmp"
chmod 644 "$ROOT/data/warehouse/.dc_planning.tmp"
mv -f "$ROOT/data/warehouse/.dc_planning.tmp" "$ROOT/data/warehouse/dc_planning.duckdb"
echo "published: $ROOT/data/warehouse/dc_planning.duckdb"
cp "$ROOT/dbt/target/index.html" "$ROOT/dbt/target/manifest.json" "$ROOT/dbt/target/catalog.json" "$ROOT/superset/dbt-docs/"
echo "dbt docs published to superset/dbt-docs/"
