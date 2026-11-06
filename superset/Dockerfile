FROM apache/superset:4.1.3
USER root
RUN pip install --no-cache-dir "duckdb==1.5.6" "duckdb-engine==0.15.0" psycopg2-binary
USER superset
