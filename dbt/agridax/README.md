# AgriDax dbt project

The repository-local profiles.yml resolves environment credentials and fixes schema analytics. Use the installed coordinator (`python -m agridax.pipeline`) for mutating build/run/snapshot operations. It holds the single-writer boundary and supplies managed invocation identity, horizon and unique targets. Direct mutation without that identity fails.

Use `python -m agridax.inspect_dbt debug` (or parse/compile/test/source-freshness/ls) for inspection. The wrapper loads private dotenv configuration and fixes the repository-local profile; direct dbt does not load .env automatically. Such artifacts do not authorize promotion. Business history comes from RAW states; snap_fields is warehouse-observed current-state history. See the root README and docs/recovery.md.
