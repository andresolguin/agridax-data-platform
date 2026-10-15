# CHANGES

## Fuente y alcance

Comparación por bytes/SHA-256 con `agridax-data-platform-current.zip` (79 archivos). Sólo se modificó la copia de remediación; los79 hashes originales permanecieron iguales. **50 archivos añadidos, 44 modificados, 4 removidos del paquete, 31 conservados sin cambios.** No Git add/commit/remote/push/PR.

Los archivos ya remediados manualmente en el ZIP se retuvieron cuando la garantía se sostuvo: no se atribuye la historia RAW o los canonical/trusted split originales exclusivamente a este trabajo. La lista refleja diferencias actuales, no una reescritura ficticia de todo el sistema.

## Añadidos

| Archivo | Motivo |
|---|---|
| `.gitattributes` | Política de finales de línea para el futuro repositorio. |
| `CHANGES.md` | Inventario exacto de diferencias respecto al ZIP actual original. |
| `FINAL_AUDIT.md` | Auditoría adversarial final, scores, readiness y B01. |
| `REMEDIATION_REPORT.md` | F01–F24, evidencias/limitaciones y defectos adicionales. |
| `VALIDATION_EVIDENCE.md` | Entorno/comandos/resultados/exclusiones y huellas de salidas. |
| `agridax/__init__.py` | Namespace de paquete para instalación/imports reproducibles. |
| `agridax/acceptance.py` | Runner aislado y assertions de todos los layers; gates nativos explícitos. |
| `agridax/acceptance_fixtures.py` | Fixtures parametrizadas adversas reproducibles, sin datos productivos ocultos. |
| `agridax/admin.py` | Init/migrations checksum/roles/grants/ownership y readiness. |
| `agridax/config.py` | Configuración compartida estándar dotenv con precedencia/validación/roles. |
| `agridax/database.py` | Conexiones/UTC/timeouts, límites RAW y single-writer; cleanup preserva COMMIT incierto. |
| `agridax/fixtures.py` | Anchor explícito y arrival DB después del lock. |
| `agridax/inspect_dbt.py` | Inspección con dotenv/perfil local, paths fijos, sin habilitar publicación. |
| `agridax/pipeline.py` | Identidad, horizonte, build completo/freshness/quality/evidence y promoción coordinada. |
| `agridax/preflight.py` | Inspección heurística de archivos/staged content sin mutación Git. |
| `agridax/publication.py` | RR, validación viva/fingerprints, stable DML, metadata y comprobación de copia. |
| `agridax/raw_contract.py` | Shape de63 columnas/PK/identity antes de bootstrap. |
| `agridax/time_contract.py` | ISO offset/UTC/cronología y combinaciones inseguras antes de SQL. |
| `data_generator/__init__.py` | Namespace de paquete para instalación/imports reproducibles. |
| `dbt/agridax/macros/business_text_is_blank.sql` | Blank NULL/empty/POSIX whitespace incluyendo tabs/newlines. |
| `dbt/agridax/macros/normalized_raw.sql` | Normalización compartida para modelos/reconciliación/quarantine. |
| `dbt/agridax/models/intermediate/int_harvest_cycle_assignment.sql` | Diagnóstico closing/additional/orphan y reconciliación de harvests. |
| `dbt/agridax/tests/generic/finite.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/generic/non_blank.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_crop_cycle_window.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_daily_source_presence.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_farm_country_format.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_field_history_positive_intervals.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_field_history_reconciles_states.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_field_history_unique_grain.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_fields_expected_current.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_harvest_assignment_reconciliation.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_no_simultaneous_plantings.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_snapshot_current_matches_fields.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_weather_quarantine_not_in_trusted.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_whitespace_key_rejection.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `docs/adr/0001_processing_and_single_writer.md` | Decisión local/target y trade-offs explícitos sin cloud desplegado. |
| `docs/adr/0002_temporal_states_and_revisions.md` | Decisión local/target y trade-offs explícitos sin cloud desplegado. |
| `docs/adr/0003_stable_publication.md` | Decisión local/target y trade-offs explícitos sin cloud desplegado. |
| `docs/adr/0004_crop_and_metric_scope.md` | Decisión local/target y trade-offs explícitos sin cloud desplegado. |
| `docs/adr/0005_bigquery_target.md` | Decisión local/target y trade-offs explícitos sin cloud desplegado. |
| `docs/fixtures.md` | Contrato/runbook/runtime/fixtures consistente con implementación y evidencia. |
| `docs/recovery.md` | Contrato/runbook/runtime/fixtures consistente con implementación y evidencia. |
| `docs/runtime_and_dependencies.md` | Contrato/runbook/runtime/fixtures consistente con implementación y evidencia. |
| `infra/postgres/migrations/001_processing_control.sql` | Ledger/scans/checkpoints/releases, guards y índices normalizados. |
| `pyproject.toml` | Paquete editable, Python 3.12/direct/backend pins y CLI operativo/inspect/acceptance/preflight. |
| `requirements-py312.lock.txt` | 61 distribuciones de resolución Linux 3.12; sin ruta editable. |
| `scripts/configure_env.py` | Generación privada sin sobrescritura ni salida de credenciales. |
| `scripts/run_pipeline.py` | Façade del coordinator instalado. |
| `tests/test_config_and_backfill.py` | Pruebas de bounds/config/preflight y error operacional sin ocultar COMMIT unknown. |

## Modificados

| Archivo | Motivo |
|---|---|
| `.env.example` | Cinco identidades privadas y opciones; placeholders inoperables, sin secreto real. |
| `.gitignore` | Variantes dotenv/profile/backups/keys y artefactos de runtime excluidos. |
| `README.md` | Guía específica ejecutable, alcance local/target y límites de evidencia. |
| `data_generator/scenario_duplicate_delivery.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_field_state_change.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_harvest_event.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_invalid_record.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_late_arrival.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_post_change_event.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_publication_candidate.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/scenario_source_correction.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `data_generator/seed_initial_data.py` | Config/límites compartidos, clock controlable/arrival real, precondiciones/reruns y mensajes correctos. |
| `dbt/agridax/README.md` | Guía específica ejecutable, alcance local/target y límites de evidencia. |
| `dbt/agridax/dbt_project.yml` | Versión y managed guard de mutaciones dbt. |
| `dbt/agridax/macros/field_event_rejection_reason.sql` | Validación compartida de negocio, cero/negativos/finite y keys blank consistentes. |
| `dbt/agridax/macros/incremental_ingestion_predicate.sql` | Bounds/horizon, guards, deferred hooks y lower congelado antes del target write. |
| `dbt/agridax/macros/weather_observation_rejection_reason.sql` | Validación compartida de negocio, cero/negativos/finite y keys blank consistentes. |
| `dbt/agridax/models/intermediate/int_field_crop_cycles.sql` | Superseded/first-harvest explícitos y cycle hash estructural. |
| `dbt/agridax/models/intermediate/intermediate.yml` | Contrato/grain/columnas/descripciones/tests reconciliados con DDL y SQL. |
| `dbt/agridax/models/marts/marts.yml` | Contrato/grain/columnas/descripciones/tests reconciliados con DDL y SQL. |
| `dbt/agridax/models/staging/quarantine_field_events.sql` | Conservar comportamiento corregido y coherencia con el nuevo contrato operacional. |
| `dbt/agridax/models/staging/quarantine_weather_observations.sql` | Conservar comportamiento corregido y coherencia con el nuevo contrato operacional. |
| `dbt/agridax/models/staging/sources.yml` | Contrato/grain/columnas/descripciones/tests reconciliados con DDL y SQL. |
| `dbt/agridax/models/staging/staging.yml` | Contrato/grain/columnas/descripciones/tests reconciliados con DDL y SQL. |
| `dbt/agridax/models/staging/stg_farms.sql` | Conservar comportamiento corregido y coherencia con el nuevo contrato operacional. |
| `dbt/agridax/models/staging/stg_field_event_winners.sql` | Global revisions, dated-first, schema fail y scans transaccionales correctos. |
| `dbt/agridax/models/staging/stg_field_state_winners.sql` | Conservar comportamiento corregido y coherencia con el nuevo contrato operacional. |
| `dbt/agridax/models/staging/stg_fields.sql` | Current por mayor effective_from no posterior al horizon. |
| `dbt/agridax/models/staging/stg_sustainability_practices.sql` | Conservar comportamiento corregido y coherencia con el nuevo contrato operacional. |
| `dbt/agridax/models/staging/stg_weather_observation_winners.sql` | Mismas garantías para weather y checkpoint separado. |
| `dbt/agridax/profiles.yml` | Roles/workload/secret env/analytics/timeouts e identidad administrada. |
| `dbt/agridax/snapshots/snap_fields.sql` | Observación aware por check; ingested-only retry no genera historia. |
| `dbt/agridax/tests/test_stg_field_events_matches_canonical_winner.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_stg_field_events_matches_deterministic_winner.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_stg_field_state_winners_match_raw.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_stg_weather_observation_winners_match_raw.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `dbt/agridax/tests/test_stg_weather_observations_matches_canonical_winner.sql` | Regresión de grain/contexto/finite/whitespace/current/history/crop/quarantine, manteniendo checks útiles. |
| `docker-compose.yml` | Patch/distribución PostgreSQL, loopback, health TCP autenticado y proyectos aislados. |
| `docs/raw_data_contracts.md` | Contrato/runbook/runtime/fixtures consistente con implementación y evidencia. |
| `docs/requirements.md` | Contrato/runbook/runtime/fixtures consistente con implementación y evidencia. |
| `infra/postgres/init/001_create_raw_schema.sql` | Comentario de llegada/progreso actualizado; baseline RAW se conserva. |
| `requirements.txt` | Dependencias directas explícitas y pinneadas; instalación editable. |
| `scripts/bootstrap.ps1` | Fail-fast/root/venv/Compose wait/timeout y configuración para test aislado. |
| `scripts/publish_marts.py` | Façade que rechaza promoción standalone insegura. |

## Removidos del paquete

| Archivo | Motivo |
|---|---|
| `dbt/agridax/.user.yml` | Artefacto generado de identidad/telemetría dbt; ahora ignorado. |
| `dbt/agridax/macros/.gitkeep` | Placeholder redundante en directorio con source real. |
| `dbt/agridax/snapshots/.gitkeep` | Placeholder redundante en directorio con source real. |
| `dbt/agridax/tests/.gitkeep` | Placeholder redundante en directorio con source real. |

## Conservados sin cambios de bytes

- `dbt/agridax/.gitignore`
- `dbt/agridax/analyses/.gitkeep`
- `dbt/agridax/models/intermediate/int_field_daily_activity.sql`
- `dbt/agridax/models/intermediate/int_field_daily_conditions.sql`
- `dbt/agridax/models/intermediate/int_field_daily_weather.sql`
- `dbt/agridax/models/intermediate/int_field_events_with_history.sql`
- `dbt/agridax/models/intermediate/int_field_history.sql`
- `dbt/agridax/models/intermediate/int_field_sustainability_metrics.sql`
- `dbt/agridax/models/marts/dim_farms.sql`
- `dbt/agridax/models/marts/dim_fields.sql`
- `dbt/agridax/models/marts/fct_crop_cycles.sql`
- `dbt/agridax/models/marts/fct_field_daily_performance.sql`
- `dbt/agridax/models/marts/fct_field_events.sql`
- `dbt/agridax/models/staging/stg_field_events.sql`
- `dbt/agridax/models/staging/stg_weather_observations.sql`
- `dbt/agridax/seeds/.gitkeep`
- `dbt/agridax/tests/test_fct_crop_cycles_yield_consistency.sql`
- `dbt/agridax/tests/test_fct_field_daily_performance_unique_grain.sql`
- `dbt/agridax/tests/test_fct_field_events_unique_logical_key.sql`
- `dbt/agridax/tests/test_field_event_quantity_zero_semantics.sql`
- `dbt/agridax/tests/test_int_field_crop_cycles_state_consistency.sql`
- `dbt/agridax/tests/test_int_field_daily_conditions_unique_grain.sql`
- `dbt/agridax/tests/test_int_field_events_with_history_all_matched.sql`
- `dbt/agridax/tests/test_int_field_events_with_history_unique_logical_event.sql`
- `dbt/agridax/tests/test_int_field_history_no_overlapping_states.sql`
- `dbt/agridax/tests/test_quarantine_field_events_not_in_trusted.sql`
- `dbt/agridax/tests/test_snap_fields_one_current_record.sql`
- `dbt/agridax/tests/test_stg_field_events_unique_logical_key.sql`
- `dbt/agridax/tests/test_stg_fields_positive_area.sql`
- `dbt/agridax/tests/test_stg_sustainability_valid_dates.sql`
- `dbt/agridax/tests/test_stg_weather_observations_unique_logical_key.sql`

## Cambios de operación visibles

- Instalación editable declarada; nueva configuración de5 roles y passwords privados. No se prescribe un password público operable.
- Build/release por coordinator; inspección por wrapper dotenv. Name-only publisher y build/run/snapshot/seed fuera del run administrado son rechazados.
- Checkpoints no se calculan desde winners. Hook de scan diferido y lower pre-DML registra RAW físico real, incluso losing revisions/backfill/target vacío.
- Publicación mantiene objetos y usa DML/reconciliación en una TX RR. Schema/PK/ownership de volúmenes legados necesitan migración explícita; nunca CASCADE de consumidores.
- Recovery completo, bounds por ingestión y costo global explícito. No se alteran RAW receipts para rejuvenecer freshness.
- Blank incluye tabs/newlines, finite incluye NaN. First harvest/superseded/orphans y NULL/zero/presencia están documentados y probados.

No se añadieron LICENSE, despliegue GCP, orquestador, servicios cloud, benchmarks ni experiencias/SLA ficticios. Analyses/seeds vacíos permanecen deliberadamente con .gitkeep. `.env`, venv, target/logs/dbt_packages, caches/egg-info/IDE y bases/volúmenes auxiliares no forman parte del paquete.
