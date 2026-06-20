# P0 Data Platform Gate Breach Runbook

Use this runbook when an enterprise data platform P0 release gate is red in production or during
production signoff. The current P0 asset set is the CourseFlow LMS pilot slice. The gates are defined in
`dp/platform/observability/production-slo-release-gates.md`.

## Scope

Covered P0 gates:

- `P0-INGESTION-LAG`
- `P0-FRESHNESS`
- `P0-QUALITY`
- `P0-CONTRACT-COMPATIBILITY`
- `P0-SCHEMA-REGISTRY-COMPATIBILITY`
- `P0-ACCESS-POLICY`
- `P0-PRODUCTION-EVIDENCE`
- `P0-GOLD-EVIDENCE`

Covered assets:

- `recommendation.tracking.v1`
- `bronze.events_recommendation_tracking`
- `silver.learner_activity`
- `gold.recsys_interactions`

## Immediate Response

1. Acknowledge the alert or failed signoff check.
2. Freeze impacted Gold publishes and downstream activation for the affected data product.
3. Open or attach the production incident/change record.
4. Capture the current gate state: metric query, dashboard timestamp, failed check output and
   pipeline run id.
5. Identify the highest upstream failing gate. Start with ingestion, then freshness, then quality,
   then contract compatibility, then schema registry compatibility, then access policy, then
   production evidence, then Gold evidence.

Do not disable checks, reduce severity or mark evidence complete manually to pass a release gate.

## P0-INGESTION-LAG

Symptoms:

- `enterprise_dp_ingestion_lag_seconds` exceeds the 15 minute SLO.
- `enterprise_dp_partition_stalled` is `1`.
- Backlog grows for `recommendation.tracking.v1`.

Triage:

1. Check whether all source services are publishing events: `analytics-service` and
   `web-next-learning`.
2. Check consumer health, sink task errors and retry queues for the Bronze writer.
3. Identify the stalled topic partition and the last committed offset.
4. Confirm object storage writes are succeeding and table commits are not blocked.
5. Compare source event `published_at` with Bronze `ingested_at` for a sample of late records.

Recovery:

1. Restore the source publisher, broker, consumer or Bronze sink.
2. Replay from the last committed safe offset when records were missed.
3. Verify lag is back inside SLO for two consecutive evaluations.
4. Attach offset ranges and replay evidence to the incident or release record.

## P0-FRESHNESS

Symptoms:

- Bronze freshness is over 15 minutes.
- Silver freshness is over 60 minutes.
- Gold freshness is over 240 minutes.

Triage:

1. Find the first stale layer in the dependency chain.
2. Check the orchestrator run status, retries and skipped materializations.
3. Check upstream freshness and source partition availability.
4. Validate that the latest complete event-time partition exists and is readable.
5. Confirm no quality gate is blocking publication under a freshness symptom.

Recovery:

1. Restart or re-run the failed materialization for the affected partition or snapshot.
2. Backfill only the missing event-time range unless a full rebuild is required.
3. Recompute dependent layers in order: Bronze, Silver, then Gold.
4. Verify all freshness SLOs are green before unfreezing downstream publish.

## P0-QUALITY

Symptoms:

- A blocking quality check reports fail.
- Privacy, tenant isolation or `no_sensitive_payload` fails.
- Gold candidate includes quarantined rows.

Triage:

1. Record the failed check name, affected data product and pipeline run id.
2. Inspect failed row samples through approved secure access only.
3. Classify the cause as source data regression, transformation regression, contract drift or check
   implementation defect.
4. Confirm quarantined rows are excluded from Gold candidates.
5. Notify the data product owner and business owner when serving data is affected.

Recovery:

1. Fix the source, transformation or quality check implementation.
2. Re-run the quality suite for the exact candidate window or snapshot.
3. Rebuild downstream layers from the last trusted input if any bad rows were published.
4. Keep the release blocked until all required checks pass and the quality report is attached.

## P0-CONTRACT-COMPATIBILITY

Symptoms:

- `cd dp && make check` fails.
- Schema registry compatibility is not `BACKWARD_TRANSITIVE`.
- A proposed data product change removes or narrows existing required fields, PII tags or access
  policy.

Triage:

1. Identify the contract, schema and commit that introduced the incompatibility.
2. Determine whether existing producers or consumers would break.
3. Check whether the change needs a new major version or a parallel data product.
4. Confirm the compatibility report is attached to the release record.

Recovery:

1. Reject the incompatible release from production promotion.
2. Publish a compatible change, or create a versioned replacement and migration plan.
3. Re-run local validation and external registry compatibility.
4. Attach the passing reports before restarting production signoff.

## P0-SCHEMA-REGISTRY-COMPATIBILITY

Symptoms:

- Schema registry compatibility report is missing.
- Local or external report has `compatibility_passed=false`.
- Report hash does not match the release evidence.

Triage:

1. Identify the topic subject and candidate schema hash.
2. Compare the topic contract, envelope schema and payload schema hashes in the report with the
   release commit.
3. Review incompatibilities against prior subject versions.
4. Confirm the registry compatibility mode is `BACKWARD_TRANSITIVE`.

Recovery:

1. Restore backward compatibility or create a new major topic and migration plan.
2. Re-run `enterprise-dp schema-registry-check` locally and the external registry workflow in CI.
3. Attach the new report URI and hash to the release evidence.

## P0-ACCESS-POLICY

Symptoms:

- Access-policy report is missing.
- Report has `passed=false`.
- Report hash does not match release evidence.

Triage:

1. Identify the data product and dataset snapshot.
2. Confirm `accessPolicy`, `accessPersonas`, `consumerContract`, PII classification and tenant
   isolation in the data product contract.
3. Check row-level org isolation has an `org_id` column when required.
4. Review failures for direct identifiers, unknown personas or missing audit metadata.

Recovery:

1. Fix the data product contract or serving policy metadata.
2. Re-run `enterprise-dp access-policy-check` or the production policy workflow.
3. Attach the new report URI and hash to the release evidence.

## P0-PRODUCTION-EVIDENCE

Symptoms:

- Production-like release evidence is missing commit SHA, schema registry report URI/hash,
  validator output, access-policy check id, access-policy report URI/hash or approver.
- Local placeholder evidence is attached to a staging/prod signoff.

Triage:

1. Confirm the target environment and release id.
2. Locate the CI run that produced the contract validator output and schema registry report.
3. Locate the access-policy evaluation for row-level isolation and PII controls.
4. Confirm the approver is allowed to approve the data product and is not the release creator when
   maker-checker applies.

Recovery:

1. Attach the missing durable evidence to the release record.
2. Re-run release gates after all evidence references are present.
3. Reject the release if evidence cannot be reproduced from the source commit and pipeline run.

## P0-GOLD-EVIDENCE

Symptoms:

- `enterprise_dp_gold_publish_evidence_status` is `0`.
- A `gold.recsys_interactions` snapshot is active without a complete evidence pack.
- Snapshot id, table version, offset range, quality report or lineage link is missing.

Triage:

1. Identify the active `gold_dataset_snapshot_id`.
2. Locate the orchestrator run that created the snapshot.
3. Verify source offset ranges, Bronze and Silver table versions, quality report and lineage record.
4. Check whether any consumer has already read the unevidenced snapshot.

Recovery:

1. Complete and attach the evidence pack if the snapshot is valid and all gates passed.
2. Withdraw the snapshot if evidence cannot prove source lineage, quality or access policy.
3. Rebuild and republish a new snapshot when the original cannot be audited.
4. Notify ML, BI and ReverseETL consumers when a published snapshot is withdrawn or replaced.

## Closeout

A gate breach can be closed only after:

- The failed gate is green for two consecutive evaluations.
- Impacted Gold publishes are either reactivated with evidence or explicitly withdrawn.
- Any replay, backfill or rebuild has an evidence pack.
- The incident/change record links the metrics, quality report, compatibility report and snapshot id.
- Follow-up actions are assigned to owners with due dates.
