# VALIDATION_EVIDENCE

## Alcance y resultado

Ejecución final del código corregido: **121 assertions PASS, 2 NOT RUN, 0 FAIL**, exit0 del runner en modo explícito **embedded diagnostic**. No constituye aceptación nativa. `native_sql_acceptance=false` y `full_bootstrap_acceptance=false` quedaron en el resultado. El dictamen global sigue **NOT READY**.

No se ejecutó Docker/PowerShell/PostgreSQL 16 real. No se usó una base local del usuario ni se insertaron datos requeridos fuera del contrato del proyecto. Los datos adversos y assertions están en el runner/fixtures versionables. Bases/directorios usados fueron temporales de auditoría. Se preservaron ZIP y hashes de79 archivos originales.

## Entorno y dependencias

| Componente | Ejecutado / límite |
|---|---|
| Sistema | Linux x86_64, glibc2.39, Ubuntu24.04; entorno Work administrado |
| Python | 3.12.14 |
| dbt Core / adapter | 1.12.5 / dbt-postgres 1.11.0 |
| psycopg / dotenv | 3.3.6 / python-dotenv 1.2.2 |
| pathspec / PyYAML | 1.0.4 / 6.0.3 |
| Build backend | setuptools 80.9.0 pinneado y usado por build aislado; no paquete runtime instalado |
| SQL auxiliar | PGlite 0.5.8, PostgreSQL 18.3, un backend, DBT_THREADS=1 |
| Objetivo no ejecutado | postgres:16.15-bookworm; Docker Compose v2; PowerShell 5.1/7 |
| Binario nativo auxiliar | PostgreSQL 16.14 encontrado; initdb falló al ejecutarse como root. No cluster nativo iniciado |

PGlite/Node y el servicio socket fueron infraestructura auxiliar de auditoría, fuera del proyecto/ZIP y no requisitos de ejecución de AgriDax. Ignoran autenticación normal y no implementan sesiones independientes representativas: se excluyeron pruebas nativas en vez de declararlas aprobadas.

## Comandos ejecutados

Se usaron intérpretes de venv separados; estos comandos se muestran relativos al working-tree root, sin rutas temporales ni credenciales:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q agridax data_generator scripts tests
.venv/bin/python -m agridax.preflight
.venv/bin/python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic
```

Además se creó una **copia limpia independiente** sólo con archivos publicables: sin .env, profile del usuario, target/logs/caches. Nuevo venv y instalación literal `python -m pip install -r requirements.txt -c requirements-py312.lock.txt`: exit0; pip check exit0;9 unit tests exit0; preflight exit0. El lock contiene61 distribuciones/resolución Linux 3.12 y excluye la ruta/package editable local. Los source finales de hooks/whitespace se sincronizaron antes del smoke de storage nuevo; no se reutilizó un venv del autor.

El runner ejecutó las llamadas siguientes desde source/config repo-local, con UUID distinto y directorio target por run:

```bash
python -m agridax.pipeline --initialize --seed-baseline
python -m agridax.pipeline --seed-baseline
python -m agridax.pipeline --full-refresh
python -m agridax.pipeline --skip-publish
python -m agridax.pipeline --backfill-start <ISO-offset> --backfill-end <ISO-offset>
python -m agridax.pipeline --simulate-failure-after-copy 2
python -m agridax.inspect_dbt debug
```

No todas son invocaciones de shell literales: la aceptación llama `run_pipeline(...)` con esos argumentos equivalentes para retener/examinar run IDs. El coordinator sí ejecuta dbt CLI real: debug, build y source freshness con perfiles locales. Para bounds,10 invocaciones `dbt compile --select stg_field_event_winners stg_weather_observation_winners --vars <JSON>` cubrieron UTC, offset no UTC, missing start/end, equal/reverse, malformed/no timezone, texto de SQL y full-refresh. Exit codes se contrastan con éxito/fracaso previsto; no son casts accidentales enviados a PostgreSQL.

`python -m agridax.acceptance --docker` se intentó: **exit1, Docker unavailable**. No se invocó PowerShell ni compose up exitosamente. No se afirma que una instalación Python limpia equivalga a clean-volume Docker.

## Resultados de build, snapshot, freshness y publicación

| Verificación | Resultado observado |
|---|---|
| Input ZIP sin cambios | 22models+1 snapshot+174 tests; build197 PASS |
| Input NaN | NaN de quantity/temperature/rain/wind llegó a facts con 174 tests verdes; defecto confirmado |
| Input undated retry | Corrección3000 → 3200 por delivery sin source_updated_at, con 174 tests verdes; defecto confirmado |
| Final build válido | 23 models+1 snapshot+258 data tests+1hook =283 PASS, WARN 0/ERROR 0/SKIP 0 en última release |
| Unit tests | 9 PASS; includes bounds/config/preflight y cleanup que preserva CommitOutcomeUnknown por inyección cliente |
| Snapshot | Current esperado, awareness timestamptz, same-update changes e ingest-only retry sin nueva versión PASS |
| Freshness final | 5 sources PASS; defaults diferenciados. Overrides weather1/2 generaron ERROR y preservaron release sin modificar RAW |
| Empty source | Build vacío puede terminar; freshness bloquea y ops.releases sigue0 |
| Publicación | Release `808b7561-33d6-42e4-9dea-8ef063723b7e`, status `published` |
| Ledger final funcional | 34 runs:22 published,10 failed intencionales,2 validated skip-publication |
| Target vacío | Ambos canonical recuperaron todas las keys; scanlower congeladoNULL y progress monotónico |
| Equivalencia | JSONB completo de canonical event/weather y fct events histórico igual tras RAW rebuild y empty-target recovery |

Build invocation `989cfa07-8d66-4436-b16e-b35f92ab6fac`, run_results SHA-256 `149e159525fc909697cbc964fe7aaa82f2b704ab054f0c849058002286def04c`. Freshness invocation `76863381-675e-484b-a9f7-2e63cafeb906`, sources SHA-256 `830c3eb054216d40c92ba6005a08ba81a5202c3f8d1e684f57a9dee08060fdf1`. Artefactos frescos llevan env run_id y se validan contra manifest completo; su hash no se toma de un target anterior.

| Mart de la última release adversa válida | Rows | MD5 contenido (control local, no firma) |
|---|---:|---|
| dim_farms | 3 | `f622e12de217636a4f9aac22218cb59a` |
| dim_fields | 4 | `e8107b476fdae98ce74ce30ce08e0981` |
| fct_crop_cycles | 4 | `662c19ade98874000d8249182a352f44` |
| fct_field_events | 20 | `4a862f6e7fa84c3f0b9bafb47dc791ab` |
| fct_field_daily_performance | 10 | `80931d41c5fafeb2a6ba85b139de0a38` |

Estos valores corresponden a fixtures del run, no a datos productivos ni a un benchmark. El último delivery FUTURE_INGESTION fue intencional y **no** se promovió. Checkpoints/scans de última recuperación: field_events: 39 deliveries/30 keys; weather: 19 deliveries/14 keys, ambos lower NULL por target vacío. Evidencia de scans no procede de winners.

## Comprobaciones adversas decisivas

- Winner fechado antiguo reentregado DESPUÉS de avance global no reemplaza raw_record_id/contexto del winner nuevo en ambos streams. Una ventana histórica sobre la entrega perdedora tampoco lo hace.
- First full scan de fixtures conocidos: eventos11 deliveries/8 keys; weather6 deliveries/5 keys. Normal lower es checkpoint anterior menos lookback. Backfill captura1 delivery perdedor/1 key en cada stream, sin mover progreso normal. Target vacío congela lower NULL antes del insert; post-hook no cambia esa evidencia.
- Canonical valid→invalid retiene nueva identidad/reason y trusted/fact desaparece; valid posterior recupera; physical quarantine antigua persiste. Cantidades negativas/NaN, keys espacios/tabs/newlines, humedad<0/>100, lluvia/viento negativos y NaN weather quedan excluidos.
- Daily: irrigation0 y fuente weather ausente producen0/NULL/activity_only; weather rain0 con temperatureNULL conserva0/NULL/weather_only. El microsegundo previo a00:00UTC y la misma frontera expresada en offset-03 se agrupan en fechasUTC correctas.
- Same-update field correction y eventos antes/exactamente en boundary obtienen wheat/corn correctos; field futuro no se convierte en current. Área histórica0/NaN bloquea el test preciso, luego nueva revisión válida recupera. Evento antes del primer state bloquea matching; corrección legítima lo recupera.
- Primer harvest420000 kg,120.50 ha: yield≈3485.4771784232365145 y duración2 h/24 h≈0.0833333333days, esperados por literales independientes. Segunda cosecha100000 y orphan100 no alteran first harvest; assignment los reconcilia. Planting sucesivo→superseded/open; simultáneo→test específico falla y no cambia release.
- Simulated publication después decopy 2 hace rollback de5 marts/hashes/OIDs; promoción posterior conserva view/index/check/comment/reader grant. Trigger que modifica quantity durante copia también se detecta y revierte. Tamper candidate antes de promoción y validated run sin writer vivo son rechazados.

## Fallos encontrados durante la propia remediación

El primer fixture blank logical ID también tenía event_id blank y esperaba la razón incorrecta; se corrigió el fixture para aislar la condición, conservando prioridad de rechazo. Se corrigieron usos iniciales no soportados de dbt debug/exports Jinja antes de la ejecución final.

La revisión final encontró N06: un hook evaluado al parsear había resuelto source como target y lower NULL, dando counts canónicos. Se comprobó en manifest/ops; se sustituyó por hook diferido, boundary transaction-local pre-DML y RAW en post-hook. Pilot baseline/rerun y assertions físicas de aceptación confirmaron la corrección. No se usa aquel build verde como prueba de F10.

N07 fue reproducido añadiendo test_whitespace_key_rejection: **FAIL5** antes del arreglo, con tabs/newlines. La aceptación endurecida detectó que un build fallido no era el tamper esperado, en lugar de declararlo PASS. Macro blank compartida + fixtures integradas corrigieron el problema; el test permanece en el proyecto final. No se suprimió el error ni se eliminaron las condiciones adversas.

## Operaciones destructivas de test y exclusiones

El runner resetó sólo schemas published/analytics/snapshots/ops/raw de su base PGlite auxiliar, expresamente marcada embedded; recreó RAW/control desde source. DROP analytics/snapshots y TRUNCATE canonical fueron experimentos aislados de reconstrucción. Los RAW adversos no se borraron para pasar assertions: corrections se hicieron con nuevas versiones. Publication/normal bootstrap no usan DROP SCHEMA/CASCADE/reset.

NOT RUN: sesiones/auth/negative permissions reales, segundo writer/ingesta concurrente/lector MVCC, imagen16.15/Compose health/clean volume y PowerShell/bootstrap/rerun nativos. No se probó red perdida durante COMMIT, host crash, backup restore ni performance/escala. El resultado SQL18 no convierte estas exclusiones en PASS. La suite native Docker completa falla si falta PowerShell.

## Registro completo de acceptance assertions

| Assertion | Resultado |
|---|---|
| `engine_scope` | PASS |
| `isolated_empty_database_initialized` | PASS |
| `authenticated_tcp_complete_raw_contract` | PASS |
| `incompatible_raw_readiness_rejected` | PASS |
| `source_preflight` | PASS |
| `first_run_backfill_rejected` | PASS |
| `empty_source_freshness_blocks_release` | PASS |
| `empty_source_has_no_release` | PASS |
| `baseline_raw_counts` | PASS |
| `baseline_fact_events` | PASS |
| `freshness_override_error` | PASS |
| `freshness_does_not_mutate_raw` | PASS |
| `freshness_failure_preserves_release` | PASS |
| `idempotent_rerun_data_and_oid` | PASS |
| `idempotent_snapshot` | PASS |
| `inspection_debug_from_dotenv_outside_root` | PASS |
| `repository_correction_then_old_retry` | PASS |
| `repository_late_arrival` | PASS |
| `repository_invalid_observable` | PASS |
| `repository_invalid_not_in_fact` | PASS |
| `repository_candidate_waits_for_promotion` | PASS |
| `repository_fixture_reruns_no_duplicate_batches` | PASS |
| `compile_bounds_utc` | PASS |
| `compile_bounds_offset` | PASS |
| `compile_bounds_missing_end` | PASS |
| `compile_bounds_missing_start` | PASS |
| `compile_bounds_equal` | PASS |
| `compile_bounds_reversed` | PASS |
| `compile_bounds_malformed` | PASS |
| `compile_bounds_missing_zone` | PASS |
| `compile_bounds_sql_literal` | PASS |
| `compile_bounds_full_refresh` | PASS |
| `processing_full_scan_counts_physical_deliveries` | PASS |
| `stale_event_full_identity` | PASS |
| `stale_weather_full_identity` | PASS |
| `non_winner_advances_processing` | PASS |
| `processing_normal_lower_uses_previous_checkpoint` | PASS |
| `backfill_preserves_winner` | PASS |
| `backfill_does_not_rewind_or_advance_checkpoint` | PASS |
| `processing_backfill_counts_raw_losing_revision` | PASS |
| `undated_does_not_replace_dated_event` | PASS |
| `undated_does_not_replace_dated_weather` | PASS |
| `valid_to_invalid_event` | PASS |
| `invalid_winner_retained` | PASS |
| `valid_to_invalid_weather` | PASS |
| `invalid_to_valid_event` | PASS |
| `physical_quarantine_history` | PASS |
| `weather_recovery_retains_physical_quarantine` | PASS |
| `event_quarantine_16` | PASS |
| `invalid_event_not_in_fact_16` | PASS |
| `event_quarantine_17` | PASS |
| `invalid_event_not_in_fact_17` | PASS |
| `event_quarantine_18` | PASS |
| `invalid_event_not_in_fact_18` | PASS |
| `event_quarantine_19` | PASS |
| `invalid_event_not_in_fact_19` | PASS |
| `event_quarantine_20` | PASS |
| `invalid_event_not_in_fact_20` | PASS |
| `event_quarantine_21` | PASS |
| `invalid_event_not_in_fact_21` | PASS |
| `event_quarantine_22` | PASS |
| `invalid_event_not_in_fact_22` | PASS |
| `event_quarantine_23` | PASS |
| `invalid_event_not_in_fact_23` | PASS |
| `event_quarantine_24` | PASS |
| `invalid_event_not_in_fact_24` | PASS |
| `weather_quarantine_11` | PASS |
| `weather_quarantine_12` | PASS |
| `weather_quarantine_13` | PASS |
| `weather_quarantine_14` | PASS |
| `weather_quarantine_15` | PASS |
| `weather_quarantine_16` | PASS |
| `weather_quarantine_17` | PASS |
| `weather_quarantine_18` | PASS |
| `zero_vs_missing_weather` | PASS |
| `weather_zero_and_null_measurement` | PASS |
| `business_date_uses_utc_boundary` | PASS |
| `post_state_event` | PASS |
| `same_update_current_correction` | PASS |
| `temporal_half_open_boundary` | PASS |
| `corrected_historical_context` | PASS |
| `snapshot_observation_is_aware` | PASS |
| `physical_field_retry_is_current` | PASS |
| `ingestion_only_retry_does_not_version_snapshot` | PASS |
| `historical_area_zero_blocks_release` | PASS |
| `historical_area_zero_specific_test` | PASS |
| `historical_area_zero_preserves_release` | PASS |
| `historical_area_nan_blocks_release` | PASS |
| `historical_area_nan_specific_test` | PASS |
| `historical_area_nan_preserves_release` | PASS |
| `event_before_first_state_blocks_release` | PASS |
| `unmatched_temporal_state_specific_test` | PASS |
| `unmatched_temporal_state_preserves_release` | PASS |
| `first_harvest_metrics` | PASS |
| `first_harvest_not_total_production` | PASS |
| `harvest_reconciliation_statuses` | PASS |
| `superseded_and_open_cycles` | PASS |
| `ambiguous_simultaneous_plantings_rejected` | PASS |
| `simultaneous_plantings_specific_test_failed` | PASS |
| `invalid_pairing_preserves_release` | PASS |
| `publication_rollback_after_copy2` | PASS |
| `rollback_all_five_marts_data_oid` | PASS |
| `successful_promotion_preserves_objects` | PASS |
| `published_metadata_preserved` | PASS |
| `reader_select_grant` | PASS |
| `consumer_trigger_changed_copy_rejected` | PASS |
| `consumer_trigger_failure_preserves_release` | PASS |
| `candidate_tamper_rejected` | PASS |
| `tamper_preserves_release` | PASS |
| `stale_validation_without_live_writer_refused` | PASS |
| `standalone_publisher_refused` | PASS |
| `unmanaged_dbt_mutation_refused` | PASS |
| `raw_rebuild_canonical_equivalence` | PASS |
| `raw_rebuild_weather_canonical_equivalence` | PASS |
| `raw_rebuild_historical_fact_equivalence` | PASS |
| `empty_targets_recover_without_checkpoint_reset` | PASS |
| `empty_weather_target_recovery` | PASS |
| `processing_empty_target_preserves_full_scan_evidence` | PASS |
| `native_login_role_isolation` | NOT RUN |
| `native_writer_ingest_reader_concurrency` | NOT RUN |
| `future_ingestion_metadata_blocks_release` | PASS |
| `future_metadata_preserves_release` | PASS |
| `functional_suite_complete` | PASS |

## Huellas de evidencia capturada

Las huellas identifican salidas reales de auditoría. Logs/target/bases privadas no se incluyen en el ZIP de source, como se solicitó. Los escenarios y assertions que produjeron esta evidencia sí están codificados en el proyecto.

| Evidencia capturada | SHA-256 |
|---|---|
| `acceptance_final_complete.log` | 01886fcb071b23f0c5d8b018e14e48ee193499464acaf4113be10d6c0abb1c1b |
| `acceptance_verified.json` | ab563c12676a49ea26dd53a3f7048878d4863a1a0773fcffc01a4d5d5e265881 |
| `verified_catalog_release.json` | 0d34333b55cd3b27b9f97c4848511879b6d0f1dd7dad0bdbe46ceff0b81005dd |
| `clean_clone_0.log` | 05225b4c3cbd6a3f34cc898b83a18b852c182255bc5b5bac04842aafcad1d6d8 |
| `clean_clone_1.log` | 9261363b733079a641c2e4cc9bc46ffa1d8336945a87f807b6cf68847dbc9b09 |
| `clean_clone_2.log` | 29801cce9f4608f2d998342a8b9a2128c79fcbf62b4161aab052450319fcca18 |
| `clean_clone_3.log` | 648f0d53e478306dcf3c6a20e44bc502bae494d3b447dbae64b1f3a111aa6f86 |
| `native_docker_unavailable.log` | 2800c283b41525140b964b0559f99ef418c14b2c58dc42048382e34a28c20709 |
| `input_nan_build.log` | 255ce808033f714366b7d9679ad23d8f26e3786bae47d4e589974eb4981cf209 |
| `input_undated_retry_build.log` | 14e57cfb7bdd24734376dfdb9709be6af844f1185a7a5253fa20902de2637efd |
| `acceptance_final_verified.log` | fd0224359db185b417364927e3bef227346339b63a7632fa316382647515c344 |
| `scan_hook_pilot.log` | 8844fc5d7b2cce9e77d31302fec6cd2f396ec07c5ea4d561daeaec3479de31a4 |

No se ejecutó git add/commit/remote/push/PR. `--staged` no se usó porque no se creó un índice para esta tarea; se probó el escáner de contenido y los ignores sin mutar Git.

## Smoke de copia limpia y almacenamiento SQL nuevo

La copia independiente con venv nuevo y `.env` privado generado desde source completó el flujo Python sobre un directorio de datos PGlite 18 nuevo. First run `5293f17e-e8ba-45e9-a54e-b46417ef1a8b` y rerun `92978a65-6807-400a-80d1-81fcc219421c` publicados; los fingerprints completos/columnas de los cinco marts fueron iguales. Baseline produjo farms 3, fields 4, crop_cycles 1, daily 4, events 4. Ambas builds283 PASS; wrapper debug/parse/compile PASS. Se ejecutó la ruta initialize/seed/build/freshness/promote desde recursos del paquete editable de esa copia, sin tablas del primer entorno ni inserts manuales.

Esto es almacenamiento auxiliar SQL18 limpio, **no clean-volume Docker 16**. El servicio auxiliar aplicó DDL RAW desde la copia; no se probó el entrypoint Docker ni autenticación nativa. El archivo privado generado no se incluye en el entregable. La smoke usó DBT_THREADS=4 por default, sobre backend auxiliar único; no prueba paralelismo nativo.

Log smoke SHA-256 `5ed3ac5f0bfd3a132e329c466e34b43391334118bc67b99f2f8675b8f56609c7`.
