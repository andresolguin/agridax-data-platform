# REMEDIATION_REPORT

## Resumen ejecutivo

**NOT READY para primer commit bajo los gates solicitados.** Se corrigió y verificó el comportamiento funcional del working tree, pero la evidencia nativa PostgreSQL 16 + Docker + PowerShell sigue pendiente. No se creó repositorio remoto, índice Git, commit, push ni PR.

Fuente primaria: `agridax-data-platform-current.zip`, SHA-256 `d11013333639bd5100a961bef1831fc697a188e66724f255b154a1b60c506636` (79 archivos, 181364 bytes descomprimidos). El ZIP original y sus 79 archivos extraídos conservaron sus hashes. Se trabajó sobre una copia separada; el informe original fue criterio de problemas, no fuente del código actual.

F01–F08 no se aceptaron por declaración. El snapshot actual se ejecutó primero sin cambios: 22 modelos + 1 snapshot + 174 tests, build197 PASS. Se reprodujeron además NaN de eventos/weather llegando a facts y una entrega sin source_updated_at revirtiendo una corrección fechada, ambos con tests verdes. La remediación añade rechazo finite y precedencia dated-first, además de los cambios operativos solicitados.

CLOSED significa comportamiento del componente reproducido en el entorno funcional observado y contrato/documentación reconciliados. No equivale a certificación de PostgreSQL 16/Windows. PARTIALLY CLOSED conserva explícitamente una aceptación necesaria no ejecutada. Todos los cierres se subordinan a B01 del FINAL_AUDIT; no se transforma PGlite 18 en evidencia nativa16.

| ID | Original | Estado final | Objeto |
|---|---|---|---|
| F01 | P1 | CLOSED | Configuración dbt reproducible |
| F02 | P1 | CLOSED | Winner global ante reentregas antiguas |
| F03 | P1 | CLOSED | Valid → invalid → valid |
| F04 | P1 | CLOSED | Historia business-effective desde RAW |
| F05 | P1 | CLOSED | Modos de backfill seguros |
| F06 | P1 | CLOSED | Keys no blank y weather inválido |
| F07 | P1 | CLOSED | Cero observado distinto de ausencia |
| F08 | P2 | CLOSED | Historia observada y clocks |
| F09 | P2 | CLOSED | Contrato cronológico de bounds |
| F10 | P2 | CLOSED | Checkpoint independiente de winners |
| F11 | P2 | PARTIALLY CLOSED | Single writer build + publicación |
| F12 | P2 | CLOSED | Objetos published estables |
| F13 | P2 | CLOSED | Procedencia validada y COMMIT incierto |
| F14 | P2 | PARTIALLY CLOSED | Bootstrap/readiness/lifecycle |
| F15 | P2 | CLOSED | Configuración dotenv centralizada |
| F16 | P2 | PARTIALLY CLOSED | Pruebas semánticas/operativas |
| F17 | P2 | CLOSED | Documentación y contratos consistentes |
| F18 | P2 | PARTIALLY CLOSED | Seguridad local/roles |
| F19 | P2 | CLOSED | Freshness vs salud del producto |
| F20 | P2 | CLOSED | Recovery y evolución de schema |
| F21 | P2 | CLOSED | Contrato de crop cycles |
| F22 | P2 | CLOSED | Higiene y secret preflight |
| F23 | P3 | CLOSED | Fixtures y aceptación reproducibles |
| F24 | P3 | CLOSED | Cierre de packaging |

## Resultado por hallazgo

### F01 — Configuración dbt reproducible

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** Profile ausente/externo en la auditoría original. El ZIP actual ya contenía profile local, pero debía verificarse su uso y la carga de dotenv.
- **Remediación:** Profile dev fija analytics y usa env_var; pipeline e inspección cargan configuración centralizada. Wrapper de inspección fija paths/perfil y funciona fuera del cwd del proyecto.
- **Archivos cambiados o inspeccionados:** dbt/agridax/profiles.yml; agridax/config.py; agridax/inspect_dbt.py; agridax/pipeline.py; scripts/bootstrap.ps1; README.md.
- **Comandos/tests/evidencia:** inspection_debug_from_dotenv_outside_root; dbt debug de cada release; instalación editable desde copia limpia. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Credenciales y sesiones reales PG 16/Windows pendientes en B01. Los comandos directos dbt requieren entorno exportado; el README usa el wrapper.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F02 — Winner global ante reentregas antiguas

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** Una ventana limitada de versiones podía reemplazar una corrección nueva por un delivery viejo.
- **Remediación:** Ventana descubre keys; winner se selecciona sobre TODAS sus revisiones RAW. Orden: source_updated_at DESC NULLS LAST, ingested_at DESC, raw_record_id DESC.
- **Archivos cambiados o inspeccionados:** dbt/agridax/models/staging/stg_field_event_winners.sql; dbt/agridax/models/staging/stg_weather_observation_winners.sql; dbt/agridax/macros/normalized_raw.sql; dbt/agridax/tests/test_stg_field_events_matches_deterministic_winner.sql; dbt/agridax/tests/test_stg_weather_observation_winners_match_raw.sql.
- **Comandos/tests/evidencia:** stale_event_full_identity; stale_weather_full_identity; backfill_preserves_winner; raw_rebuild_canonical_equivalence; raw_rebuild_weather_canonical_equivalence. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Requiere revisiones de fuente comparables. Todas las revisiones NULL conservan latest-arrival; no se promete ordenar retries sin información de revisión.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F03 — Valid → invalid → valid

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** Filtrar inválidos antes del incremental dejaba visible un trusted anterior.
- **Remediación:** Canonical conserva winner inválido con rejection_reason; trusted es vista filtrada. Corrección válida posterior recupera la key; quarantine sigue en grain físico.
- **Archivos cambiados o inspeccionados:** dbt/agridax/models/staging/stg_field_event_winners.sql; dbt/agridax/models/staging/stg_weather_observation_winners.sql; dbt/agridax/models/staging/stg_field_events.sql; dbt/agridax/models/staging/stg_weather_observations.sql; dbt/agridax/tests/test_stg_field_events_matches_canonical_winner.sql; dbt/agridax/tests/test_stg_weather_observations_matches_canonical_winner.sql.
- **Comandos/tests/evidencia:** valid_to_invalid_event; invalid_winner_retained; valid_to_invalid_weather; invalid_to_valid_event; weather_recovery_retains_physical_quarantine. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Invalidar una key no borra sus deliveries RAW ni su quarantine física. No hay tombstones/source-key supersession.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F04 — Historia business-effective desde RAW

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** La historia dependía de estados current observados por snapshots y perdía correcciones same-update.
- **Remediación:** Se retiene la solución del ZIP actual: canonical field/effective_from, precedencia updated_at/ingestion/id y LEAD de effective_from. Se refuerza reconciliación completa y grain histórico.
- **Archivos cambiados o inspeccionados:** dbt/agridax/models/staging/stg_field_state_winners.sql; dbt/agridax/models/staging/stg_fields.sql; dbt/agridax/models/intermediate/int_field_history.sql; dbt/agridax/models/intermediate/int_field_events_with_history.sql; dbt/agridax/tests/test_field_history_reconciles_states.sql; dbt/agridax/tests/test_field_history_unique_grain.sql.
- **Comandos/tests/evidencia:** same_update_current_correction; temporal_half_open_boundary; corrected_historical_context; raw_rebuild_historical_fact_equivalence; event_before_first_state_blocks_release. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Los estados persisten hasta el próximo inicio; no hay valid_to de fuente, intervalos explícitos sin estado, borrados ni bitemporalidad as-known. Cambiar effective_from cambia identidad.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F05 — Modos de backfill seguros

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** First run/full refresh ignoraban bounds y producían una reconstrucción no solicitada.
- **Remediación:** Rechazo explícito de primer backfill sin targets y bounded + full-refresh; ambos bounds obligatorios antes de SQL. Recovery normal de targets vacíos descubre todas las keys.
- **Archivos cambiados o inspeccionados:** agridax/time_contract.py; agridax/pipeline.py; dbt/agridax/macros/incremental_ingestion_predicate.sql; agridax/acceptance.py; docs/recovery.md.
- **Comandos/tests/evidencia:** first_run_backfill_rejected; compile_bounds_missing_start/end; compile_bounds_full_refresh; backfill_preserves_winner; empty_targets_recover_without_checkpoint_reset. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** El modo bounded requiere targets existentes; un target incompleto fuera de la ventana hace fallar reconciliación global. No se promueve un rebuild parcial.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F06 — Keys no blank y weather inválido

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** Keys vacías/ranges inválidos podían llegar a facts con build verde.
- **Remediación:** Macros compartidas rechazan blanks, rangos weather, negativos y valores no finitos. Canonical guarda rechazo; ambas quarantines tienen raw_record_id físico.
- **Archivos cambiados o inspeccionados:** dbt/agridax/macros/field_event_rejection_reason.sql; dbt/agridax/macros/weather_observation_rejection_reason.sql; dbt/agridax/tests/generic/non_blank.sql; dbt/agridax/tests/generic/finite.sql; dbt/agridax/models/staging/staging.yml; agridax/acceptance_fixtures.py.
- **Comandos/tests/evidencia:** event_quarantine_*; invalid_event_not_in_fact_*; weather_quarantine_*; weather_recovery_retains_physical_quarantine. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No se inventa rango de temperatura. Invalidez de referencias/contexto histórico bloquea validación; no se convierte automáticamente en quarantine de evento.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F07 — Cero observado distinto de ausencia

- **Severidad original / estado:** P1 / **CLOSED**.
- **Problema original:** quantity <= 0 rechazaba cero; faltaba una prueba integrada de cobertura.
- **Remediación:** Conserva quantity=0 y rechaza negativos. Agregaciones condicionadas y FULL OUTER preservan NULL/presencia; no se introduce COALESCE universal.
- **Archivos cambiados o inspeccionados:** dbt/agridax/macros/field_event_rejection_reason.sql; dbt/agridax/models/intermediate/int_field_daily_activity.sql; dbt/agridax/models/intermediate/int_field_daily_weather.sql; dbt/agridax/models/intermediate/int_field_daily_conditions.sql; dbt/agridax/models/marts/fct_field_daily_performance.sql.
- **Comandos/tests/evidencia:** zero_vs_missing_weather; weather_zero_and_null_measurement; business_date_uses_utc_boundary; event_quarantine_* negativo. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Eventos trusted requieren cantidad; weather permite medidas NULL. Sin ambas fuentes no se genera fila/calendario.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F08 — Historia observada y clocks

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Snapshot metadata se describía como observación aunque derivaba de tiempo de fuente.
- **Remediación:** Snapshot check sobre current state usa warehouse_observed_at timestamptz/current_timestamp de transacción y conserva source updated/ingested aparte. Ignora retries de sólo ingestión.
- **Archivos cambiados o inspeccionados:** dbt/agridax/snapshots/snap_fields.sql; dbt/agridax/models/staging/staging.yml; dbt/agridax/tests/test_snapshot_current_matches_fields.sql; docs/adr/0002_temporal_states_and_revisions.md.
- **Comandos/tests/evidencia:** snapshot_observation_is_aware; ingestion_only_retry_does_not_version_snapshot; idempotent_snapshot; rebuild histórico independiente. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Es observación de transacción, no instante de commit ni captura de todos los estados RAW. Borrar snapshots pierde observaciones irrecuperables.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F09 — Contrato cronológico de bounds

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Bounds no validaban rango, zona/calendario ni SQL seguro.
- **Remediación:** Parser Python y validación Jinja normalizan UTC, exigen segundos/Z u offset, aceptan hasta 6 decimales y rechazan igualdad/inversión/inputs malformed antes de ejecutar casts.
- **Archivos cambiados o inspeccionados:** agridax/time_contract.py; dbt/agridax/macros/incremental_ingestion_predicate.sql; tests/test_config_and_backfill.py; agridax/acceptance.py; docs/recovery.md.
- **Comandos/tests/evidencia:** 4 tests Python de bounds con subcasos; 10 compile_bounds_*; first_run_backfill_rejected. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** [start,end) filtra ingested_at. No limita todas las revisiones de keys afectadas ni costo downstream. No se afirma portabilidad BigQuery del literal PostgreSQL.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F10 — Checkpoint independiente de winners

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** max(ingested_at) del target omitía entregas inválidas/no winning como progreso.
- **Remediación:** ops ledger con horizon por run, scans físicos/keys y checkpoints por stream. Hooks renderizados en ejecución congelan lower antes de escribir target; post-hook lee RAW real y confirma scan/checkpoint junto al canonical. Backfill no avanza/retrocede checkpoint normal. No usa identity como orden de commit.
- **Archivos cambiados o inspeccionados:** infra/postgres/migrations/001_processing_control.sql; agridax/database.py; agridax/pipeline.py; dbt/agridax/macros/incremental_ingestion_predicate.sql; docs/adr/0001_processing_and_single_writer.md.
- **Comandos/tests/evidencia:** processing_full_scan_counts_physical_deliveries; processing_normal_lower_uses_previous_checkpoint; processing_backfill_counts_raw_losing_revision; processing_empty_target_preserves_full_scan_evidence; non_winner_advances_processing; backfill_does_not_rewind_or_advance_checkpoint; future_ingestion_metadata_blocks_release. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Protocolo cooperativo de timestamp después del lock; imports arbitrariamente antiguos requieren recovery. Un downstream fallido no revierte canonical ya confirmado. Seguridad temporal de sesiones nativas pendiente en F11/B01.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F11 — Single writer build + publicación

- **Severidad original / estado:** P2 / **PARTIALLY CLOSED**.
- **Problema original:** Una transacción aislada no coordina builds/publishers ni asegura la misma generación.
- **Remediación:** Coordinator mantiene locks de pipeline/RAW durante horizon, build, tests, freshness y publicación; dbt mutante exige run activo/token/locks. Timeouts acotados. Publisher usa REPEATABLE READ.
- **Archivos cambiados o inspeccionados:** agridax/database.py; agridax/pipeline.py; agridax/publication.py; infra/postgres/migrations/001_processing_control.sql; agridax/acceptance.py.
- **Comandos/tests/evidencia:** unmanaged_dbt_mutation_refused; stale_validation_without_live_writer_refused; checks funcionales de locks/procedencia; pruebas nativas codificadas. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional aprobado; aceptación indicada pendiente.
- **Limitación restante:** NOT RUN: dos sesiones autenticadas, segundo writer, espera de ingesta y lector MVCC. PGlite comparte un backend y NO prueba concurrencia PostgreSQL 16.
- **Primer commit / GitHub:** Sí, bloqueo de aceptación B01; no declarar cerrado el alcance nativo.

### F12 — Objetos published estables

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** CTAS + DROP/RENAME perdía OIDs/metadata y afectaba dependencias.
- **Remediación:** DELETE/INSERT transaccional en tablas estables, PK/schema verificados, reader grants dentro de TX, fingerprint publicado comparado. No DROP/CASCADE para promoción.
- **Archivos cambiados o inspeccionados:** agridax/publication.py; agridax/admin.py; docs/adr/0003_stable_publication.md; agridax/acceptance.py.
- **Comandos/tests/evidencia:** publication_rollback_after_copy2; rollback_all_five_marts_data_oid; successful_promotion_preserves_objects; published_metadata_preserved; reader_select_grant; consumer_trigger_changed_copy_rejected. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Objetos/metadatos verificados funcionalmente en PG 18/PGlite. Sesiones de lectores y locks nativos siguen pendientes F11. FKs externos arbitrarios no son parte del contrato.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F13 — Procedencia validada y COMMIT incierto

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Publisher aceptaba cinco nombres sin evidencia; podía prometer rollback ante COMMIT desconocido.
- **Remediación:** UUID/run vivo, target único, artefactos completos con invocation/hash/env ID, todos los gates, fingerprint candidate y copied content. Standalone se rechaza; error de conexión durante COMMIT se distingue como unknown; cleanup no lo oculta.
- **Archivos cambiados o inspeccionados:** agridax/pipeline.py; agridax/publication.py; agridax/database.py; scripts/publish_marts.py; tests/test_config_and_backfill.py.
- **Comandos/tests/evidencia:** candidate_tamper_rejected; tamper_preserves_release; standalone_publisher_refused; stale_validation_without_live_writer_refused; consumer_trigger_failure_preserves_release; test_lock_cleanup_preserves_commit_uncertainty. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No se simuló una pérdida de red real durante COMMIT. El test de cleanup es inyección de fallo cliente. No es attestation frente a un publisher/admin malicioso; MD5 es control local de cambios, no firma.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F14 — Bootstrap/readiness/lifecycle

- **Severidad original / estado:** P2 / **PARTIALLY CLOSED**.
- **Problema original:** Readiness socket y mantenimiento de volumen no protegían el flujo completo.
- **Remediación:** Compose health TCP autenticado; up --wait; validación Python de 5 tablas/63 columnas, tipos/nullability/identity/PK con deadline; script root-anchored fail-fast y Python explícito; init/migrations/rerun/reset separados.
- **Archivos cambiados o inspeccionados:** docker-compose.yml; scripts/bootstrap.ps1; agridax/admin.py; agridax/raw_contract.py; agridax/acceptance.py; docs/recovery.md.
- **Comandos/tests/evidencia:** authenticated_tcp_complete_raw_contract; incompatible_raw_readiness_rejected; baseline/rerun funcional; --docker ejecutado: fallo por Docker ausente. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional aprobado; aceptación indicada pendiente.
- **Limitación restante:** NOT RUN: pull/clean volume PG 16.15, Docker health real, PowerShell 5.1/7, bootstrap nativo y rerun del volumen. B01 bloquea aceptación final.
- **Primer commit / GitHub:** Sí, bloqueo de aceptación B01; no declarar cerrado el alcance nativo.

### F15 — Configuración dotenv centralizada

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Parsing split/strip difería de Compose/dbt y publisher dependía de generadores/sys.path.
- **Remediación:** python-dotenv directo, Settings compartido, proceso prevalece incluso vacío, validación de puerto/password/roles/timeouts; publisher independiente del generador; inspección usa mismo contrato.
- **Archivos cambiados o inspeccionados:** agridax/config.py; data_generator/*.py; scripts/configure_env.py; requirements.txt; pyproject.toml; agridax/inspect_dbt.py.
- **Comandos/tests/evidencia:** test_quoted_values_and_process_precedence; test_empty_process_value_does_not_fall_back; test_ports; inspection_debug_from_dotenv_outside_root. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** La configuración local contiene todas las credenciales; no aísla secretos frente al mismo usuario OS. Parsing/arranque Compose real queda en B01; no se promete equivalencia de cualquier extensión dotenv.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F16 — Pruebas semánticas/operativas

- **Severidad original / estado:** P2 / **PARTIALLY CLOSED**.
- **Problema original:** Tests de subconjuntos o fórmulas derivadas aparentaban cobertura más fuerte.
- **Remediación:** Comparaciones JSONB de contexto completo, historia/current esperado/grain, intervalos, integración/expectativas numéricas independientes, aceptación con error específico/SQLSTATE/artifact del test fallido y equivalencia RAW.
- **Archivos cambiados o inspeccionados:** dbt/agridax/tests/*.sql; dbt/agridax/tests/generic/*.sql; agridax/acceptance.py; agridax/acceptance_fixtures.py; tests/test_config_and_backfill.py.
- **Comandos/tests/evidencia:** 258 data tests por build final; 9 unit tests; batería funcional final; valor 420000/120.50 y duración2 h comprobados por literales independientes. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional aprobado; aceptación indicada pendiente.
- **Limitación restante:** Cobertura nativa login/locking/MVCC/PowerShell no ejecutada. Tests de reconciliation comparten normalización: integración adversa aporta contraste, no un oráculo universal independiente.
- **Primer commit / GitHub:** Sí, bloqueo de aceptación B01; no declarar cerrado el alcance nativo.

### F17 — Documentación y contratos consistentes

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Farms/fields/effective_from, raw IDs/grains, lluvia/prácticas/ADRs y scopes se contradecían.
- **Remediación:** Reescritura README/requirements/contracts/runbook, source YAML de DDL, rainfall_mm correcto, vocabulario clocks/grains preciso y 5 ADRs reales. Inspection commands cargan dotenv.
- **Archivos cambiados o inspeccionados:** README.md; docs/requirements.md; docs/raw_data_contracts.md; docs/recovery.md; docs/fixtures.md; docs/runtime_and_dependencies.md; docs/adr/*.md; dbt/agridax/models/**/*.yml; dbt/agridax/README.md.
- **Comandos/tests/evidencia:** Comparación literal automatizada 63 columnas/tipos/nullability DDL↔YAML↔contracts↔readiness; columnas documentadas contrastadas con catálogo; comandos inspect y enlaces/fences. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No se afirma GCP/producción ni SLA medido. Metadatos/yield de primer harvest/prácticas current/daily presencia y limitaciones de validación están explícitos.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F18 — Seguridad local/roles

- **Severidad original / estado:** P2 / **PARTIALLY CLOSED**.
- **Problema original:** Superuser para workloads, exposición amplia y placeholder público como configuración operable.
- **Remediación:** Loopback; generación de passwords privados; 5 identidades separadas; grants/revokes/ownership/default privileges; elevated roles existentes rechazados; RAW/ops owner admin; init explícito.
- **Archivos cambiados o inspeccionados:** docker-compose.yml; .env.example; scripts/configure_env.py; agridax/config.py; agridax/admin.py; infra/postgres/migrations/001_processing_control.sql; agridax/acceptance.py.
- **Comandos/tests/evidencia:** Revisión completa SQL/config; reader_select_grant de catálogo; tests dotenv/placeholder; pruebas de login/permisos negativas codificadas. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional aprobado; aceptación indicada pendiente.
- **Limitación restante:** NOT RUN: login real, password incorrecto rechazado, current_user real, permisos negativos/attrs/memberships por sesión. PGlite ignora autenticación; no se certifica least privilege efectivo.
- **Primer commit / GitHub:** Sí, bloqueo de aceptación B01; no declarar cerrado el alcance nativo.

### F19 — Freshness vs salud del producto

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Arrival aggregate y flags se interpretaban como salud/completitud total.
- **Remediación:** Política ERROR global/WARN elegible, thresholds por fuente, overrides sólo weather coherentes/registrados y counts quality por release; flags documentan presencia.
- **Archivos cambiados o inspeccionados:** dbt/agridax/models/staging/sources.yml; agridax/pipeline.py; dbt/agridax/models/marts/fct_field_daily_performance.sql; README.md; docs/requirements.md.
- **Comandos/tests/evidencia:** freshness_override_error; freshness_does_not_mutate_raw; freshness_failure_preserves_release; zero_vs_missing_weather; empty_source_freshness_blocks_release. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No hay completeness watermark/event coverage por productor/campo, calendario completo, alertas ni scheduler desplegados. Counts quality no equivalen a SLA.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F20 — Recovery y evolución de schema

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Bounds staging se anunciaban como recovery/costo acotado; selector parcial podía dejar descendants ausentes.
- **Remediación:** Única ruta mutante soportada: DAG completo. on_schema_change=fail; migraciones numeradas con checksum; lifecycle explícito; full RAW rebuild y target vacío comprobados.
- **Archivos cambiados o inspeccionados:** docs/recovery.md; agridax/admin.py; agridax/pipeline.py; infra/postgres/migrations/001_processing_control.sql; dbt/agridax/models/staging/stg_field_event_winners.sql; dbt/agridax/models/staging/stg_weather_observation_winners.sql.
- **Comandos/tests/evidencia:** raw_rebuild_canonical_equivalence; raw_rebuild_weather_canonical_equivalence; raw_rebuild_historical_fact_equivalence; empty_targets_recover_without_checkpoint_reset; empty_weather_target_recovery. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No es bounded end-to-end compute. Marts/checksums/reconciliation son completos; snapshot observado perdido no se puede recrear. Migraciones de volumen legado requieren evaluación explícita.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F21 — Contrato de crop cycles

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Primer harvest sin diagnóstico de adicionales/orphans; simultáneos/superseded ambiguos.
- **Remediación:** Primer harvest deliberado; superseded/open/closed precisos; simultáneos fallan; relación harvest→cycle con categorías y reconciliación; yield whole-field al planting.
- **Archivos cambiados o inspeccionados:** dbt/agridax/models/intermediate/int_field_crop_cycles.sql; dbt/agridax/models/intermediate/int_harvest_cycle_assignment.sql; dbt/agridax/models/marts/fct_crop_cycles.sql; dbt/agridax/tests/test_harvest_assignment_reconciliation.sql; dbt/agridax/tests/test_no_simultaneous_plantings.sql; docs/adr/0004_crop_and_metric_scope.md.
- **Comandos/tests/evidencia:** first_harvest_metrics; first_harvest_not_total_production; harvest_reconciliation_statuses; superseded_and_open_cycles; simultaneous_plantings_specific_test_failed; historical_area_*. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No suma producción total del ciclo ni calcula planted-area yield. Asociación biológica real, múltiples zonas y parcialidad de planting requieren contrato de fuente.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F22 — Higiene y secret preflight

- **Severidad original / estado:** P2 / **CLOSED**.
- **Problema original:** Variantes dotenv/profiles/backups no ignoradas y no había chequeo previo.
- **Remediación:** Ignore .env.* salvo example, profiles privados, keys/backups/caches/artefactos; preflight árbol y contenido staged read-only con regex/config checks; generated .user.yml removido.
- **Archivos cambiados o inspeccionados:** .gitignore; .gitattributes; agridax/preflight.py; tests/test_config_and_backfill.py; .env.example.
- **Comandos/tests/evidencia:** agridax.preflight en proyecto y copia limpia; test_secret_detection_does_not_print_values; inspección/allowlist del ZIP; original79 hashes intactos. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Heurístico, no prueba criptográfica de ausencia de secretos. --staged no ejecutado porque no se creó índice/commit; no se ejecutó git add. No protege archivos ya trackeados de forma retroactiva.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F23 — Fixtures y aceptación reproducibles

- **Severidad original / estado:** P3 / **CLOSED**.
- **Problema original:** Generators secuenciales con clocks variables y mensajes, sin assertions integradas.
- **Remediación:** Anchor controlable único, mutex de fixtures, llegada DB después del lock, batches completos, mensajes de llegada reales; runner automatiza nueve generadores y casos adicionales preservando RAW.
- **Archivos cambiados o inspeccionados:** data_generator/*.py; agridax/fixtures.py; agridax/acceptance_fixtures.py; agridax/acceptance.py; docs/fixtures.md.
- **Comandos/tests/evidencia:** repository_correction_then_old_retry; repository_late_arrival; repository_invalid_observable; repository_fixture_reruns_no_duplicate_batches; todos los checks posteriores. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** Fixtures no son ingestion productiva. Un anchor histórico falla freshness honestamente; arrivals/UUIDs operativos no son idénticos entre runs. Concurrencia nativa queda en B01.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

### F24 — Cierre de packaging

- **Severidad original / estado:** P3 / **CLOSED**.
- **Problema original:** Starter README/placeholders y versiones/update/lock sin cerrar.
- **Remediación:** README dbt específico; .gitkeep sólo scaffold vacío; Python 3.12/direct pins/backend pin/constraints Linux: 61; Docker 16.15-bookworm y policy de actualización. Sin LICENSE inventada.
- **Archivos cambiados o inspeccionados:** dbt/agridax/README.md; requirements.txt; requirements-py312.lock.txt; pyproject.toml; docker-compose.yml; docs/runtime_and_dependencies.md; .gitattributes.
- **Comandos/tests/evidencia:** pip install literal y fresh-copy -c lock; pip check; unit/preflight; ZIP allowlisted; .user.yml/.gitkeep redundantes removidos. Ejecución: `python -m agridax.acceptance --existing-disposable --allow-reset --embedded-diagnostic`, builds coordinados, y validaciones de `VALIDATION_EVIDENCE.md`.
- **Resultado:** Comportamiento funcional/contrato indicado aprobado dentro del alcance de evidencia declarado.
- **Limitación restante:** No digest/pull de imagen ni resolución/wheels Windows verificados. Licencia es decisión del propietario; no bloquea un commit técnico ni debe inventarse.
- **Primer commit / GitHub:** No como hallazgo residual del componente; B01 sigue bloqueando aceptación global.

## Defectos adicionales y revisión adversarial de las correcciones

| ID | Severidad | Evidencia | Corrección / estado |
|---|---|---|---|
| N01 | P1 | Input sin cambios: cantidad NaN y weather NaN entraron a facts con 174 tests verdes | Rechazo finite compartido, generic finite y fixtures integradas: CLOSED funcional |
| N02 | P1 | Input sin cambios: OPS_1002 corregido a 3000 volvió a 3200 por retry sin source_updated_at | Dated-first/NULLS LAST en ambos streams; all-undated limit explícito: CLOSED funcional |
| N03 | P2 | Revisión del runner aceptaba cualquier RuntimeError como prueba de fallo previsto | Tipo/mensaje/SQLSTATE y unique_id del test fallido obligatorios; errores de bootstrap/config no se toman como rollback simulado: CLOSED |
| N04 | P2 | Los comandos de inspección directos de una revisión intermedia no cargaban .env | Wrapper inspect_dbt; entorno de configuración limpiado + cwd externo: CLOSED |
| N05 | P2 | En revisión, fingerprint fuera de TX no fijaba snapshot entre comprobación/copia; un trigger podía modificar copia | REPEATABLE READ desde validación y checksum del contenido publicado dentro de TX; trigger adverso rechazado y rollback: CLOSED funcional; concurrencia nativa pendiente B01 |
| N07 | P1 | Test literal: 5 casos de keys sólo tabs/newlines fallaron antes de corregir; TRIM sólo quitaba espacios | Macro business_text_is_blank compartida y fixtures RAW/quarantine/facts: CLOSED funcional, 121 assertions PASS |
| N06 | P2 | Inspección final manifest/catálogo: el hook evaluado en parse resolvía source a target y registraba27 winners en vez de36 deliveries RAW; lower siempre NULL | Hooks diferidos, lower congelado en pre-hook antes de DML y RAW en post-hook. Assertions independientes de physical counts, normal/backfill/empty bounds: CLOSED funcional, verificadas en la ejecución final |

La hipótesis de que un área histórica cero/NaN escaparía por validar sólo current fue **refutada**: `test_field_history_positive_intervals` ya controla área/finite en toda la historia. Se agregaron assertions integradas para ambas variantes y conservación de release. No se contabiliza como defecto confirmado ni se declara evidencia falsa de corrupción.

No se bajó severity para esconder fallos, no se eliminó RAW adverso, no se actualizaron timestamps para freshness y no se promocionó tras un test fallido. Las reparaciones de fixtures fueron nuevas revisiones del mismo estado/evento. DROP SCHEMA/CASCADE y TRUNCATE sólo se usan en la base de aceptación explícitamente aislada, nunca para publicación ni bootstrap normal.

## Trabajo terminado y aceptación pendiente

Correcciones fuente, contratos, automatización, fixtures, higiene y paquete están entregados. Quedan `F11`, `F14`, `F16`, `F18` parcialmente cerrados por falta del entorno nativo. El comando de cierre está implementado: `python -m agridax.acceptance --docker`, con Docker Compose y PowerShell disponibles. Su ausencia produce NOT RUN/fallo de aceptación completa; no un falso PASS.

No se requiere implementar GCP para cerrar estos problemas locales. BigQuery y servicios asociados permanecen target; las cinco ADRs explican adaptación y límites sin despliegue inventado.

La evaluación diferida de hooks sigue el contrato de [dbt pre/post hooks](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook). Se verificaron los hooks ejecutados y las filas del ledger, además del build verde; la primera versión operativa con counts canónicos incorrectos no se usa como evidencia de cierre F10.

La última ejecución funcional del source corregido cerró 121 assertions PASS,2 NOT RUN nativos,0 FAIL y 258 data tests/283 recursos por build. Una copia/venv/storage SQL18 nuevos completó baseline/publicación/rerun/debug/parse/compile; datos iguales. No se contabiliza como Docker/PG 16.
