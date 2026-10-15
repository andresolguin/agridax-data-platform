# Repository fixture contract

The generators are transactional acceptance inputs, not production connectors. Install the editable package first and invoke them from the working-tree root with the same Python environment. Configuration comes from agridax.config; there is no external profile or CSV dependency.

`AGRIDAX_FIXTURE_ANCHOR` optionally fixes business timestamps (ISO-8601 with seconds and Z/offset). It must be at or after 2024-02-01 UTC and not in the database-clock future. The acceptance runner uses one UTC anchor for each isolated run, honoring this override; by default it chooses current UTC. A deliberately old anchor makes arrival freshness fail and is not a way to produce a fresh accepted release. Identifiers, quantities, offsets and expected relationships are fixed; wall-clock operational arrivals/run IDs are intentionally different between executions.

Baseline receipt timestamps are deliberately relative simulated metadata (2–30 minutes before the anchor). Load baseline before the first managed build. Loading historical fixtures into an existing checkpoint requires the documented recovery path; changing their RAW timestamps to pass freshness is unsupported. Subsequent scenario deliveries assign actual database arrival time after the shared ingestion lock. Source/business timestamps retain their fixture meaning. Console ingestion messages report the inserted arrival, not the business anchor.

| Script | Input/precondition | Expected property |
|---|---|---|
| seed_initial_data | Initialized RAW; empty baseline batch or complete prior baseline | 3 farms, 4 fields, 4 events, 4 weather, 4 practices; rerun does not rewrite |
| scenario_source_correction | Baseline OPS_1002 | One logical fertilizer event becomes 3000 kg |
| scenario_duplicate_delivery | Baseline OPS_1002; run after correction to challenge precedence | RAW gains one old delivery; logical count/value do not regress |
| scenario_late_arrival | Baseline field/master history | Old business date, new arrival; trusted event appears |
| scenario_invalid_record | Initialized RAW | Wrong irrigation unit stays RAW/physical quarantine, excluded trusted/facts |
| scenario_publication_candidate | Baseline field/master history | Pesticide 24 kg reaches candidate; accepted data waits for promotion |
| scenario_field_state_change | Baseline FIELD_AR_001_A | New effective state wheat → soy |
| scenario_post_change_event | Prior FIELD_STATE_CHANGE_01 | Event 15 minutes after its effective boundary gets soy before further corrections |
| scenario_harvest_event | Baseline OPS_1001 planting | First harvest 420000 kg, two hours after planting |

The runner executes baseline/rerun, correction → managed release → old delivery → release, late/invalid/candidate → validated skip-publication → release, and state change → post-change event/harvest → release. It then loads parameterized adversarial deliveries from agridax.acceptance_fixtures and checks every layer. Each named scenario is rerunnable by batch/logical existence, and fixtures take a transaction mutex. This is not evidence of native concurrent fixture execution in an environment where native sessions were unavailable.

Run `python -m agridax.acceptance --docker` for complete native acceptance. It creates a unique Compose project and private temporary configuration, tests PowerShell clean bootstrap and existing-volume rerun, resets only that isolated test database, and removes only that project's volume. Its intentional future-ingestion fixture is last and causes a checked failure, not an accepted release. A missing Docker/PowerShell runtime makes native acceptance incomplete. Embedded diagnostics report excluded authentication/concurrency checks explicitly; they do not validate the Docker path.
