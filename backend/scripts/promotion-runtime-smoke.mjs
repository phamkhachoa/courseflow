#!/usr/bin/env node

/**
 * Promotion runtime smoke gate.
 *
 * Local mode proves the service-only incentive runtime path against the Docker cluster:
 *   checkout-service STS token -> promotion-service evaluate -> reserve -> commit -> outbox relay.
 *
 * Staging mode uses pre-provisioned fixture data and reachable URLs. It never seeds data unless an
 * operator explicitly runs local mode against a disposable cluster.
 */

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";

const MODE = (process.env.PROMOTION_SMOKE_MODE ?? "local").trim().toLowerCase();
const LOCAL = MODE === "local";
const STAGING = MODE === "staging";
if (!LOCAL && !STAGING) {
  throw new Error("PROMOTION_SMOKE_MODE must be local or staging");
}

const RUN_ID = sanitizeRunId(process.env.PROMOTION_SMOKE_RUN_ID ?? `rt-${Date.now()}-${crypto.randomBytes(3).toString("hex")}`);
const TENANT_ID = process.env.PROMOTION_SMOKE_TENANT_ID ?? "courseflow";
const APPLICATION_ID = process.env.PROMOTION_SMOKE_APPLICATION_ID ?? "lms";
const NEGATIVE_APPLICATION_IDS = {
  unbound: negativeApplicationEnv("PROMOTION_SMOKE_UNBOUND_APPLICATION_ID", "unbound"),
  suspendedApplication: negativeApplicationEnv("PROMOTION_SMOKE_SUSPENDED_APPLICATION_ID", "suspended-app"),
  suspendedBinding: negativeApplicationEnv("PROMOTION_SMOKE_SUSPENDED_BINDING_APPLICATION_ID", "suspended-binding"),
  emptyBinding: negativeApplicationEnv("PROMOTION_SMOKE_EMPTY_BINDING_APPLICATION_ID", "empty-binding"),
  evaluateOnlyBinding: negativeApplicationEnv("PROMOTION_SMOKE_EVALUATE_ONLY_APPLICATION_ID", "evaluate-only")
};
const COUPON_APPLICATION_ID = couponApplicationEnv("PROMOTION_SMOKE_COUPON_APPLICATION_ID");
const COUPON_CAMPAIGN_CODE = process.env.PROMOTION_SMOKE_COUPON_CAMPAIGN_CODE
  ?? (LOCAL ? `CP-${RUN_ID}`.slice(0, 120) : "");
const QUOTA_APPLICATION_ID = quotaApplicationEnv("PROMOTION_SMOKE_QUOTA_APPLICATION_ID");
const QUOTA_CAMPAIGN_CODE = process.env.PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE
  ?? (LOCAL ? `HQ-${RUN_ID}`.slice(0, 120) : "");
const COUPON_CODES = {
  valid: couponCodeEnv("PROMOTION_SMOKE_COUPON_VALID_CODE", "VALID"),
  inactive: couponCodeEnv("PROMOTION_SMOKE_COUPON_INACTIVE_CODE", "PAUSED"),
  notStarted: couponCodeEnv("PROMOTION_SMOKE_COUPON_NOT_STARTED_CODE", "FUTURE"),
  expired: couponCodeEnv("PROMOTION_SMOKE_COUPON_EXPIRED_CODE", "EXPIRED"),
  holderMismatch: couponCodeEnv("PROMOTION_SMOKE_COUPON_HOLDER_MISMATCH_CODE", "HOLDER"),
  exhausted: couponCodeEnv("PROMOTION_SMOKE_COUPON_EXHAUSTED_CODE", "EXHAUST"),
  invalid: couponCodeEnv("PROMOTION_SMOKE_COUPON_INVALID_CODE", "INVALID")
};
const COUPON_FINGERPRINT_KEY_ID = firstNonBlank(
  process.env.PROMOTION_SMOKE_COUPON_FINGERPRINT_KEY_ID,
  process.env.PROMOTION_COUPON_FINGERPRINT_KEY_ID,
  "local"
);
const COUPON_FINGERPRINT_PEPPER = firstNonBlank(
  process.env.PROMOTION_SMOKE_COUPON_FINGERPRINT_PEPPER,
  process.env.PROMOTION_COUPON_FINGERPRINT_PEPPER,
  "courseflow-local-coupon-fingerprint-pepper-change-me"
);
const CHECKOUT_CLIENT_ID = process.env.PROMOTION_SMOKE_CHECKOUT_CLIENT_ID ?? "checkout-service";
const PROMOTION_CLIENT_ID = process.env.PROMOTION_SMOKE_PROMOTION_CLIENT_ID ?? "promotion-service";
const CHECKOUT_CLIENT_SECRET = firstNonBlank(
  process.env.PROMOTION_SMOKE_CHECKOUT_CLIENT_SECRET,
  process.env.COURSEFLOW_STS_CHECKOUT_SERVICE_SECRET,
  process.env.COURSEFLOW_STS_CLIENT_SECRET,
  LOCAL ? "local-courseflow-sts-client-secret-change-me-32" : ""
);
const PROMOTION_CLIENT_SECRET = firstNonBlank(
  process.env.PROMOTION_SMOKE_PROMOTION_CLIENT_SECRET,
  process.env.COURSEFLOW_STS_PROMOTION_SERVICE_SECRET,
  process.env.COURSEFLOW_STS_CLIENT_SECRET,
  LOCAL ? "local-courseflow-sts-client-secret-change-me-32" : ""
);
const INTERNAL_AUDIENCE = process.env.COURSEFLOW_INTERNAL_JWT_AUDIENCE ?? "courseflow-services";
const INTERNAL_JWT_ISSUER = process.env.COURSEFLOW_INTERNAL_JWT_ISSUER ?? "courseflow-token-converter";
const INTERNAL_JWT_SECRET = firstNonBlank(
  process.env.PROMOTION_SMOKE_INTERNAL_JWT_SECRET,
  process.env.COURSEFLOW_INTERNAL_JWT_SECRET,
  LOCAL ? "courseflow-local-internal-jwt-secret-change-me-32" : ""
);
const REQUIRED_SCOPES = [
  "internal:promotion:evaluate",
  "internal:promotion:reserve",
  "internal:promotion:commit",
  "internal:promotion:cancel",
  "internal:promotion:reverse"
];

const DOCKER_NETWORK = process.env.PROMOTION_SMOKE_DOCKER_NETWORK ?? "courseflow-v2-backend_default";
const POSTGRES_CONTAINER = process.env.PROMOTION_SMOKE_POSTGRES_CONTAINER ?? "courseflow-postgres";
const PSQL_USER = process.env.PROMOTION_SMOKE_PSQL_USER ?? "courseflow";
const PROMOTION_DB = process.env.PROMOTION_SMOKE_PROMOTION_DB ?? "cf_promotion";
const OUTBOX_DB = process.env.PROMOTION_SMOKE_OUTBOX_DB ?? "cf_outbox";
const OUTBOX_SERVICE_NAME = process.env.PROMOTION_SMOKE_OUTBOX_SERVICE_NAME ?? "promotion";
const CURL_IMAGE = process.env.PROMOTION_SMOKE_CURL_IMAGE ?? "curlimages/curl:8.10.1";
const TOKEN_CONVERTER_URL = stripTrailingSlash(
  process.env.PROMOTION_SMOKE_TOKEN_CONVERTER_URL
    ?? process.env.COURSEFLOW_TOKEN_CONVERTER_URL
    ?? (LOCAL ? "http://identity-token-converter-service:8080" : "")
);
const PROMOTION_URL = stripTrailingSlash(
  process.env.PROMOTION_SMOKE_PROMOTION_URL
    ?? (LOCAL ? "http://promotion-service:8080" : "")
);
const GATEWAY_URL = stripTrailingSlash(
  process.env.PROMOTION_SMOKE_GATEWAY_URL
    ?? process.env.COURSEFLOW_API_URL
    ?? "http://localhost:28080/api"
);
const COUPON_IMPORT_GATEWAY_ENABLED =
  (process.env.PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED ?? "false").toLowerCase() === "true";
const LOCAL_INTERNAL_ADMIN_INVENTORY_ENABLED =
  (process.env.PROMOTION_SMOKE_LOCAL_INTERNAL_ADMIN_INVENTORY_ENABLED ?? "true").toLowerCase() !== "false";
const ADMIN_ACCESS_TOKEN = firstNonBlank(process.env.PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN);
const COUPON_IMPORT_GATEWAY_CAMPAIGN_ID = firstNonBlank(
  process.env.PROMOTION_SMOKE_COUPON_CAMPAIGN_ID,
  LOCAL ? uuidFromText(`coupon-campaign:${TENANT_ID}:${COUPON_APPLICATION_ID}:${RUN_ID}`) : ""
);
const POLL_TIMEOUT_MS = positiveInt(process.env.PROMOTION_SMOKE_POLL_TIMEOUT_MS, 60_000);
const POLL_INTERVAL_MS = positiveInt(process.env.PROMOTION_SMOKE_POLL_INTERVAL_MS, 2_000);
const ALLOW_SKIP_DB_CHECKS = (process.env.PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS ?? "false").toLowerCase() === "true";
const COUPON_ABUSE_GUARD_BURST_ATTEMPTS = positiveInt(
  process.env.PROMOTION_SMOKE_COUPON_ABUSE_GUARD_BURST_ATTEMPTS,
  6
);
const HOT_QUOTA_PARALLEL_ATTEMPTS = positiveInt(
  process.env.PROMOTION_SMOKE_HOT_QUOTA_PARALLEL_ATTEMPTS,
  12
);
const HOT_QUOTA_SOAK_WAVES = positiveInt(
  process.env.PROMOTION_SMOKE_HOT_QUOTA_SOAK_WAVES
    ?? process.env.PROMOTION_SMOKE_HOT_QUOTA_WAVES
    ?? process.env.PROMOTION_SMOKE_HOT_QUOTA_SOAK_ROUNDS,
  1
);
const HOT_QUOTA_SOAK_ARTIFACT_FILE = firstNonBlank(
  process.env.PROMOTION_SMOKE_HOT_QUOTA_SOAK_ARTIFACT_FILE,
  process.env.PROMOTION_SMOKE_HOT_QUOTA_ARTIFACT,
  HOT_QUOTA_SOAK_WAVES > 1 ? "promotion-runtime-smoke-artifacts/promotion-hot-quota-soak.json" : ""
);
const REQUIRE_COUPON_INVENTORY_READY =
  (process.env.PROMOTION_SMOKE_REQUIRE_COUPON_INVENTORY_READY ?? "true").toLowerCase() !== "false";
const CAMPAIGN_PRIORITY = positiveInt(
  process.env.PROMOTION_SMOKE_CAMPAIGN_PRIORITY,
  Math.min(2_100_000_000, Math.floor(Date.now() / 1000))
);

const checks = [];
const couponInventoryReadyChecks = [];
let expectedCampaignCode = process.env.PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE ?? "";

async function main() {
  requireValue("PROMOTION_SMOKE_TOKEN_CONVERTER_URL", TOKEN_CONVERTER_URL);
  requireValue("PROMOTION_SMOKE_PROMOTION_URL", PROMOTION_URL);
  requireValue("PROMOTION_SMOKE_CHECKOUT_CLIENT_SECRET", CHECKOUT_CLIENT_SECRET);
  requireValue("PROMOTION_SMOKE_PROMOTION_CLIENT_SECRET", PROMOTION_CLIENT_SECRET);
  if (COUPON_IMPORT_GATEWAY_ENABLED) {
    requireValue("PROMOTION_SMOKE_GATEWAY_URL", GATEWAY_URL);
    requireValue("PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN", ADMIN_ACCESS_TOKEN);
    requireValue("PROMOTION_SMOKE_COUPON_CAMPAIGN_ID", COUPON_IMPORT_GATEWAY_CAMPAIGN_ID);
  }
  if (STAGING && !dbChecksAvailable() && !ALLOW_SKIP_DB_CHECKS) {
    throw new Error(
      "staging mode requires PROMOTION_SMOKE_PROMOTION_DATABASE_URL and PROMOTION_SMOKE_OUTBOX_DATABASE_URL "
        + "for outbox/DLQ verification, or PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true for an explicit partial smoke"
    );
  }
  if (STAGING && !expectedCampaignCode) {
    throw new Error(
      "staging mode requires PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE so the smoke cannot mutate an arbitrary campaign"
    );
  }
  if (STAGING) {
    requireValue("PROMOTION_SMOKE_UNBOUND_APPLICATION_ID", NEGATIVE_APPLICATION_IDS.unbound);
    requireValue("PROMOTION_SMOKE_SUSPENDED_APPLICATION_ID", NEGATIVE_APPLICATION_IDS.suspendedApplication);
    requireValue("PROMOTION_SMOKE_SUSPENDED_BINDING_APPLICATION_ID", NEGATIVE_APPLICATION_IDS.suspendedBinding);
    requireValue("PROMOTION_SMOKE_EMPTY_BINDING_APPLICATION_ID", NEGATIVE_APPLICATION_IDS.emptyBinding);
    requireValue("PROMOTION_SMOKE_EVALUATE_ONLY_APPLICATION_ID", NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding);
    requireValue("PROMOTION_SMOKE_COUPON_APPLICATION_ID", COUPON_APPLICATION_ID);
    requireValue("PROMOTION_SMOKE_COUPON_CAMPAIGN_CODE", COUPON_CAMPAIGN_CODE);
    requireValue("PROMOTION_SMOKE_QUOTA_APPLICATION_ID", QUOTA_APPLICATION_ID);
    requireValue("PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE", QUOTA_CAMPAIGN_CODE);
    requireValue("PROMOTION_SMOKE_COUPON_VALID_CODE", COUPON_CODES.valid);
    requireValue("PROMOTION_SMOKE_COUPON_INACTIVE_CODE", COUPON_CODES.inactive);
    requireValue("PROMOTION_SMOKE_COUPON_NOT_STARTED_CODE", COUPON_CODES.notStarted);
    requireValue("PROMOTION_SMOKE_COUPON_EXPIRED_CODE", COUPON_CODES.expired);
    requireValue("PROMOTION_SMOKE_COUPON_HOLDER_MISMATCH_CODE", COUPON_CODES.holderMismatch);
    requireValue("PROMOTION_SMOKE_COUPON_EXHAUSTED_CODE", COUPON_CODES.exhausted);
    requireValue("PROMOTION_SMOKE_COUPON_INVALID_CODE", COUPON_CODES.invalid);
    requireValue("PROMOTION_SMOKE_COUPON_FINGERPRINT_KEY_ID", COUPON_FINGERPRINT_KEY_ID);
    requireValue("PROMOTION_SMOKE_COUPON_FINGERPRINT_PEPPER", COUPON_FINGERPRINT_PEPPER);
  }

  console.log("CourseFlow Promotion Runtime smoke");
  console.log(`mode=${MODE}`);
  console.log(`runId=${RUN_ID}`);
  console.log(`tenant=${TENANT_ID} application=${APPLICATION_ID}`);
  console.log(`checkoutClient=${CHECKOUT_CLIENT_ID}`);
  console.log(`negativeApplications=${Object.values(NEGATIVE_APPLICATION_IDS).join(",")}`);
  console.log(`couponApplication=${COUPON_APPLICATION_ID} couponCampaign=${COUPON_CAMPAIGN_CODE}`);
  console.log(`quotaApplication=${QUOTA_APPLICATION_ID} quotaCampaign=${QUOTA_CAMPAIGN_CODE}`);

  if (LOCAL) {
    ensureLocalTooling();
    expectedCampaignCode = seedLocalFixture();
  }
  assertApplicationFixturePreflight();

  await assertGatewayRuntimeRouteClosed("/v1/incentives/evaluate");
  await assertGatewayRuntimeRouteClosed("/v1/incentives/reservations");
  await assertGatewayRuntimeRouteClosed("/v1/incentives/reservations/00000000-0000-0000-0000-000000000000/commit");
  await assertGatewayRuntimeRouteClosed("/v1/incentives/reservations/00000000-0000-0000-0000-000000000000/cancel");
  await assertGatewayRuntimeRouteClosed("/v1/incentives/redemptions/00000000-0000-0000-0000-000000000000/reverse");
  await assertCouponImportGatewaySmoke();
  await assertLocalInternalAdminCouponInventory();

  await assertWrongSecretRejected();
  await assertPromotionServiceCannotMintRuntimeScope();
  await assertRuntimeAuthRequired();

  const token = await mintCheckoutToken();
  await assertRuntimeOperationScopesRequired();
  await assertUnknownApplicationRejected(token);
  await assertClientBindingNegativeFixtures(token);
  await assertHotQuotaConcurrencyFixture(token);
  await assertCouponAbuseFixtures(token);
  await assertCouponAbuseGuardFixtures(token);
  await assertReserveIdempotencyKeyRequired(token);

  const cancelContext = runtimeContext("cancel");
  const reservationToCancel = await reserve(token, cancelContext, "cancel");
  await assertCommitIdempotencyKeyRequired(token, reservationToCancel.reservationId);
  await assertCancelIdempotencyKeyRequired(token, reservationToCancel.reservationId);
  const cancelled = await cancel(token, reservationToCancel.reservationId);
  const replayedCancel = await cancel(token, reservationToCancel.reservationId);
  assertEqual(replayedCancel.reservationId, cancelled.reservationId, "cancel idempotency replay reservationId");
  record("cancel idempotency replay returns same reservation", true, cancelled.reservationId);
  await assertCancelIdempotencyPayloadConflict(token, reservationToCancel.reservationId);
  await assertCommitCancelledReservationReturnsNotCommitted(token, reservationToCancel.reservationId);
  assertCancellationReconciliationEvidence(reservationToCancel.reservationId);

  const context = runtimeContext("commit");
  const evaluation = await evaluate(token, context);
  const reservation = await reserve(token, context, "commit");
  const replayedReservation = await reserve(token, context, "commit");
  assertEqual(replayedReservation.reservationId, reservation.reservationId, "reservation idempotency replay reservationId");
  record("reserve idempotency replay returns same reservation", true, reservation.reservationId);
  await assertReserveIdempotencyPayloadConflict(token, context, "commit");

  const committed = await commit(token, reservation.reservationId, "commit");
  const replayedCommit = await commit(token, reservation.reservationId, "commit");
  assertEqual(replayedCommit.redemptionId, committed.redemptionId, "commit idempotency replay redemptionId");
  record("commit idempotency replay returns same redemption", true, committed.redemptionId);
  await assertCommitIdempotencyPayloadConflict(token, reservation.reservationId, "commit");
  await assertReverseIdempotencyKeyRequired(token, committed.redemptionId);

  const reversed = await reverse(token, committed.redemptionId);
  const replayedReverse = await reverse(token, committed.redemptionId);
  assertEqual(replayedReverse.redemptionId, reversed.redemptionId, "reverse idempotency replay redemptionId");
  record("reverse idempotency replay returns same redemption", true, reversed.redemptionId);
  await assertReverseIdempotencyPayloadConflict(token, committed.redemptionId);

  await assertOutboxPublished(committed.redemptionId, "incentive.redemption.committed");
  await assertOutboxPublished(committed.redemptionId, "incentive.redemption.reversed");
  await assertReversalKeepsQuota(committed.redemptionId);
  assertRedemptionReconciliationEvidence(reservation.reservationId, committed.redemptionId);
  await assertNoOpenDeadLetters();

  printSummary({
    campaign: evaluation.campaignCode,
    cancelledReservationId: cancelled.reservationId,
    reservationId: reservation.reservationId,
    redemptionId: committed.redemptionId,
    reversedRedemptionId: reversed.redemptionId
  });
}

function seedLocalFixture() {
  const campaignUuid = uuidFromText(`campaign:${TENANT_ID}:${APPLICATION_ID}:${RUN_ID}`);
  const versionUuid = uuidFromText(`campaign-version:${TENANT_ID}:${APPLICATION_ID}:${RUN_ID}`);
  const couponCampaignUuid = uuidFromText(`coupon-campaign:${TENANT_ID}:${COUPON_APPLICATION_ID}:${RUN_ID}`);
  const couponVersionUuid = uuidFromText(`coupon-campaign-version:${TENANT_ID}:${COUPON_APPLICATION_ID}:${RUN_ID}`);
  const quotaCampaignUuid = uuidFromText(`quota-campaign:${TENANT_ID}:${QUOTA_APPLICATION_ID}:${RUN_ID}`);
  const quotaVersionUuid = uuidFromText(`quota-campaign-version:${TENANT_ID}:${QUOTA_APPLICATION_ID}:${RUN_ID}`);
  const campaignCode = `CX-${RUN_ID}`.slice(0, 120);
  const campaignName = `Codex runtime smoke ${RUN_ID}`.slice(0, 255);
  const couponCampaignName = `Codex coupon abuse smoke ${RUN_ID}`.slice(0, 255);
  const quotaCampaignName = `Codex hot quota smoke ${RUN_ID}`.slice(0, 255);
  const rules = JSON.stringify([
    {
      type: "MIN_ORDER_AMOUNT",
      schemaVersion: 1,
      parameters: { amount: 100, currency: "USD" }
    }
  ]);
  const actions = JSON.stringify([
    {
      type: "ORDER_FIXED_OFF",
      schemaVersion: 1,
      parameters: { amount: 5 }
    }
  ]);
  const operations = JSON.stringify(["evaluate", "reserve", "commit", "cancel", "reverse"]);
  const sql = `
    ${applicationUpsertSql(APPLICATION_ID, "ACTIVE", "Promotion smoke fixture")}
    ${bindingUpsertSql(APPLICATION_ID, CHECKOUT_CLIENT_ID, "ACTIVE", operations)}
    ${applicationUpsertSql(COUPON_APPLICATION_ID, "ACTIVE", "Promotion smoke coupon abuse fixture")}
    ${bindingUpsertSql(COUPON_APPLICATION_ID, CHECKOUT_CLIENT_ID, "ACTIVE", operations)}
    ${applicationUpsertSql(QUOTA_APPLICATION_ID, "ACTIVE", "Promotion smoke hot quota fixture")}
    ${bindingUpsertSql(QUOTA_APPLICATION_ID, CHECKOUT_CLIENT_ID, "ACTIVE", operations)}

    UPDATE incentive_campaign_versions v
    SET active_snapshot = FALSE,
        version_status = CASE WHEN v.version_status = 'PUBLISHED' THEN 'SUPERSEDED' ELSE v.version_status END,
        version = v.version + 1
    FROM incentive_campaigns c
    WHERE v.campaign_id = c.id
      AND v.tenant_id = ${sqlString(TENANT_ID)}
      AND v.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
      AND v.active_snapshot = TRUE
      AND c.code <> ${sqlString(QUOTA_CAMPAIGN_CODE)};

    ${applicationUpsertSql(NEGATIVE_APPLICATION_IDS.unbound, "ACTIVE", "Promotion smoke unbound fixture")}
    DELETE FROM incentive_application_client_bindings
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(NEGATIVE_APPLICATION_IDS.unbound)}
      AND client_id = ${sqlString(CHECKOUT_CLIENT_ID)};

    ${applicationUpsertSql(NEGATIVE_APPLICATION_IDS.suspendedApplication, "SUSPENDED", "Promotion smoke suspended application fixture")}
    ${bindingUpsertSql(NEGATIVE_APPLICATION_IDS.suspendedApplication, CHECKOUT_CLIENT_ID, "ACTIVE", operations)}

    ${applicationUpsertSql(NEGATIVE_APPLICATION_IDS.suspendedBinding, "ACTIVE", "Promotion smoke suspended binding fixture")}
    ${bindingUpsertSql(NEGATIVE_APPLICATION_IDS.suspendedBinding, CHECKOUT_CLIENT_ID, "SUSPENDED", operations)}

    ${applicationUpsertSql(NEGATIVE_APPLICATION_IDS.emptyBinding, "ACTIVE", "Promotion smoke empty binding fixture")}
    ${bindingUpsertSql(NEGATIVE_APPLICATION_IDS.emptyBinding, CHECKOUT_CLIENT_ID, "ACTIVE", JSON.stringify([]))}

    ${applicationUpsertSql(NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding, "ACTIVE", "Promotion smoke evaluate-only binding fixture")}
    ${bindingUpsertSql(NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding, CHECKOUT_CLIENT_ID, "ACTIVE", JSON.stringify(["evaluate"]))}

    INSERT INTO incentive_campaigns
      (id, tenant_id, application_id, code, name, status, priority, coupon_required, match_policy, currency,
       rules_json, actions_json, max_redemptions, max_redemptions_per_profile, created_by, published_at)
    VALUES (${sqlString(campaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(APPLICATION_ID)},
            ${sqlString(campaignCode)}, ${sqlString(campaignName)}, 'PUBLISHED', ${CAMPAIGN_PRIORITY}, FALSE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1000, NULL, 'promotion-runtime-smoke', NOW())
    ON CONFLICT (tenant_id, application_id, code) DO NOTHING;

    INSERT INTO incentive_campaign_versions
      (id, campaign_id, tenant_id, application_id, code, name, version_number, version_status, active_snapshot,
       priority, coupon_required, match_policy, currency, rules_json, actions_json, max_redemptions,
       max_redemptions_per_profile, created_by, published_by, published_at)
    VALUES (${sqlString(versionUuid)}, ${sqlString(campaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(APPLICATION_ID)},
            ${sqlString(campaignCode)}, ${sqlString(campaignName)}, 1, 'PUBLISHED', TRUE, ${CAMPAIGN_PRIORITY}, FALSE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1000, 1,
            'promotion-runtime-smoke', 'promotion-runtime-smoke', NOW())
    ON CONFLICT (campaign_id, version_number) DO NOTHING;

    INSERT INTO incentive_campaigns
      (id, tenant_id, application_id, code, name, status, priority, coupon_required, match_policy, currency,
       rules_json, actions_json, max_redemptions, max_redemptions_per_profile, created_by, published_at)
    VALUES (${sqlString(couponCampaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(COUPON_APPLICATION_ID)},
            ${sqlString(COUPON_CAMPAIGN_CODE)}, ${sqlString(couponCampaignName)}, 'PUBLISHED', ${CAMPAIGN_PRIORITY}, TRUE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1000, NULL, 'promotion-runtime-smoke', NOW())
    ON CONFLICT (tenant_id, application_id, code)
    DO UPDATE SET status = 'PUBLISHED',
                  coupon_required = TRUE,
                  rules_json = EXCLUDED.rules_json,
                  actions_json = EXCLUDED.actions_json,
                  priority = EXCLUDED.priority,
                  updated_at = NOW(),
                  published_at = NOW();

    INSERT INTO incentive_campaign_versions
      (id, campaign_id, tenant_id, application_id, code, name, version_number, version_status, active_snapshot,
       priority, coupon_required, match_policy, currency, rules_json, actions_json, max_redemptions,
       max_redemptions_per_profile, created_by, published_by, published_at)
    VALUES (${sqlString(couponVersionUuid)}, ${sqlString(couponCampaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(COUPON_APPLICATION_ID)},
            ${sqlString(COUPON_CAMPAIGN_CODE)}, ${sqlString(couponCampaignName)}, 1, 'PUBLISHED', TRUE, ${CAMPAIGN_PRIORITY}, TRUE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1000, NULL,
            'promotion-runtime-smoke', 'promotion-runtime-smoke', NOW())
    ON CONFLICT (campaign_id, version_number) DO NOTHING;

    ${couponUpsertSql(couponCampaignUuid, "valid", COUPON_CODES.valid, "ACTIVE", "NULL", "NULL", "NULL", "NULL")}
    ${couponUpsertSql(couponCampaignUuid, "inactive", COUPON_CODES.inactive, "PAUSED", "NULL", "NULL", "NULL", "NULL")}
    ${couponUpsertSql(couponCampaignUuid, "not-started", COUPON_CODES.notStarted, "ACTIVE", "NULL", "NOW() + INTERVAL '1 day'", "NOW() + INTERVAL '30 days'", "NULL")}
    ${couponUpsertSql(couponCampaignUuid, "expired", COUPON_CODES.expired, "ACTIVE", "NULL", "NOW() - INTERVAL '30 days'", "NOW() - INTERVAL '1 day'", "NULL")}
    ${couponUpsertSql(couponCampaignUuid, "holder-mismatch", COUPON_CODES.holderMismatch, "ACTIVE", sqlString(couponHolderProfileId()), "NULL", "NULL", "NULL")}
    ${couponUpsertSql(couponCampaignUuid, "exhausted", COUPON_CODES.exhausted, "ACTIVE", "NULL", "NULL", "NULL", "0")}

    INSERT INTO incentive_campaigns
      (id, tenant_id, application_id, code, name, status, priority, coupon_required, match_policy, currency,
       rules_json, actions_json, max_redemptions, max_redemptions_per_profile, created_by, published_at)
    VALUES (${sqlString(quotaCampaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(QUOTA_APPLICATION_ID)},
            ${sqlString(QUOTA_CAMPAIGN_CODE)}, ${sqlString(quotaCampaignName)}, 'PUBLISHED', ${CAMPAIGN_PRIORITY}, FALSE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1, NULL, 'promotion-runtime-smoke', NOW())
    ON CONFLICT (tenant_id, application_id, code)
    DO UPDATE SET status = 'PUBLISHED',
                  coupon_required = FALSE,
                  rules_json = EXCLUDED.rules_json,
                  actions_json = EXCLUDED.actions_json,
                  max_redemptions = 1,
                  max_redemptions_per_profile = NULL,
                  priority = EXCLUDED.priority,
                  updated_at = NOW(),
                  published_at = NOW();

    INSERT INTO incentive_campaign_versions
      (id, campaign_id, tenant_id, application_id, code, name, version_number, version_status, active_snapshot,
       priority, coupon_required, match_policy, currency, rules_json, actions_json, max_redemptions,
       max_redemptions_per_profile, created_by, published_by, published_at)
    VALUES (${sqlString(quotaVersionUuid)}, ${sqlString(quotaCampaignUuid)}, ${sqlString(TENANT_ID)}, ${sqlString(QUOTA_APPLICATION_ID)},
            ${sqlString(QUOTA_CAMPAIGN_CODE)}, ${sqlString(quotaCampaignName)}, 1, 'PUBLISHED', TRUE, ${CAMPAIGN_PRIORITY}, FALSE, 'ALL', 'USD',
            ${sqlString(rules)}::jsonb, ${sqlString(actions)}::jsonb, 1, NULL,
            'promotion-runtime-smoke', 'promotion-runtime-smoke', NOW())
    ON CONFLICT (campaign_id, version_number) DO NOTHING;
  `;
  queryPromotion(sql);
  record("local promotion fixture seeded", true, `${campaignCode} priority=${CAMPAIGN_PRIORITY}`);
  record("local negative application fixtures seeded", true,
    Object.values(NEGATIVE_APPLICATION_IDS).join(","));
  record("local coupon abuse fixtures seeded", true, `${COUPON_APPLICATION_ID}/${COUPON_CAMPAIGN_CODE}`);
  record("local hot quota fixture seeded", true, `${QUOTA_APPLICATION_ID}/${QUOTA_CAMPAIGN_CODE}`);
  return campaignCode;
}

function applicationUpsertSql(applicationId, status, name) {
  return `
    INSERT INTO incentive_applications (id, tenant_id, application_id, name, status, created_by, updated_at)
    VALUES (${sqlString(uuidFromText(`application:${TENANT_ID}:${applicationId}`))},
            ${sqlString(TENANT_ID)}, ${sqlString(applicationId)}, ${sqlString(name)},
            ${sqlString(status)}, 'promotion-runtime-smoke', NOW())
    ON CONFLICT (tenant_id, application_id)
    DO UPDATE SET name = EXCLUDED.name,
                  status = EXCLUDED.status,
                  updated_at = NOW();
  `;
}

function bindingUpsertSql(applicationId, clientId, status, operationsJson) {
  return `
    INSERT INTO incentive_application_client_bindings
      (id, tenant_id, application_id, client_id, status, allowed_operations, created_by, updated_at)
    VALUES (${sqlString(uuidFromText(`binding:${TENANT_ID}:${applicationId}:${clientId}`))},
            ${sqlString(TENANT_ID)}, ${sqlString(applicationId)}, ${sqlString(clientId)},
            ${sqlString(status)}, ${sqlString(operationsJson)}::jsonb,
            'promotion-runtime-smoke', NOW())
    ON CONFLICT (tenant_id, application_id, client_id)
    DO UPDATE SET status = EXCLUDED.status,
                  allowed_operations = EXCLUDED.allowed_operations,
                  updated_at = NOW();
  `;
}

function couponUpsertSql(campaignId, kind, rawCode, status, holderSql, startsAtSql, expiresAtSql, maxRedemptionsSql) {
  const normalized = normalizeCouponCode(rawCode);
  const mask = couponMask(normalized);
  const fingerprint = couponFingerprint(normalized);
  return `
    INSERT INTO incentive_coupons
      (id, campaign_id, code, normalized_code, code_mask, status, holder_profile_id,
       starts_at, expires_at, max_redemptions, max_redemptions_per_profile, metadata_json, updated_at)
    VALUES (${sqlString(uuidFromText(`coupon:${TENANT_ID}:${COUPON_APPLICATION_ID}:${kind}:${RUN_ID}`))},
            ${sqlString(campaignId)}, ${sqlString(mask)}, ${sqlString(fingerprint)}, ${sqlString(mask)},
            ${sqlString(status)}, ${holderSql}, ${startsAtSql}, ${expiresAtSql}, ${maxRedemptionsSql}, NULL,
            ${sqlString(JSON.stringify({ smoke: true, kind }))}::jsonb, NOW())
    ON CONFLICT (campaign_id, normalized_code)
    DO UPDATE SET code = EXCLUDED.code,
                  code_mask = EXCLUDED.code_mask,
                  status = EXCLUDED.status,
                  holder_profile_id = EXCLUDED.holder_profile_id,
                  starts_at = EXCLUDED.starts_at,
                  expires_at = EXCLUDED.expires_at,
                  max_redemptions = EXCLUDED.max_redemptions,
                  max_redemptions_per_profile = EXCLUDED.max_redemptions_per_profile,
                  metadata_json = EXCLUDED.metadata_json,
                  updated_at = NOW();
  `;
}

function assertApplicationFixturePreflight() {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record("application fixture preflight skipped", true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }

  const negativeIds = Object.values(NEGATIVE_APPLICATION_IDS);
  requirePreflight(
    "negative application fixture ids configured",
    negativeIds.every((value) => value && value.trim()),
    negativeIds.join(",")
  );
  requirePreflight(
    "negative application fixture ids are distinct",
    new Set(negativeIds).size === negativeIds.length,
    negativeIds.join(",")
  );
  requirePreflight(
    "negative application fixture ids do not reuse positive application",
    !negativeIds.includes(APPLICATION_ID),
    `positive=${APPLICATION_ID} negative=${negativeIds.join(",")}`
  );
  requirePreflight(
    "coupon abuse application fixture id is distinct",
    COUPON_APPLICATION_ID
      && COUPON_APPLICATION_ID !== APPLICATION_ID
      && !negativeIds.includes(COUPON_APPLICATION_ID),
    `couponApplication=${COUPON_APPLICATION_ID} positive=${APPLICATION_ID}`
  );
  requirePreflight(
    "hot quota application fixture id is distinct",
    QUOTA_APPLICATION_ID
      && QUOTA_APPLICATION_ID !== APPLICATION_ID
      && QUOTA_APPLICATION_ID !== COUPON_APPLICATION_ID
      && !negativeIds.includes(QUOTA_APPLICATION_ID),
    `quotaApplication=${QUOTA_APPLICATION_ID} positive=${APPLICATION_ID}`
  );

  requireApplicationStatus(APPLICATION_ID, "ACTIVE", "positive promotion smoke application");
  requireBindingIncludes(
    APPLICATION_ID,
    "ACTIVE",
    ["evaluate", "reserve", "commit", "cancel", "reverse"],
    "positive checkout binding includes all runtime operations"
  );
  requireExpectedCampaignFixture();

  requireApplicationStatus(
    NEGATIVE_APPLICATION_IDS.unbound,
    "ACTIVE",
    "negative unbound application fixture"
  );
  requireNoBinding(
    NEGATIVE_APPLICATION_IDS.unbound,
    "negative unbound fixture has no checkout binding"
  );

  requireApplicationStatus(
    NEGATIVE_APPLICATION_IDS.suspendedApplication,
    "SUSPENDED",
    "negative suspended application fixture"
  );
  requireBindingIncludes(
    NEGATIVE_APPLICATION_IDS.suspendedApplication,
    "ACTIVE",
    ["evaluate", "reserve", "commit", "cancel", "reverse"],
    "negative suspended application fixture checkout binding remains active"
  );

  requireApplicationStatus(
    NEGATIVE_APPLICATION_IDS.suspendedBinding,
    "ACTIVE",
    "negative suspended binding application fixture"
  );
  requireBindingIncludes(
    NEGATIVE_APPLICATION_IDS.suspendedBinding,
    "SUSPENDED",
    ["evaluate", "reserve", "commit", "cancel", "reverse"],
    "negative suspended binding fixture has suspended checkout binding"
  );

  requireApplicationStatus(
    NEGATIVE_APPLICATION_IDS.emptyBinding,
    "ACTIVE",
    "negative empty binding application fixture"
  );
  requireBindingExactly(
    NEGATIVE_APPLICATION_IDS.emptyBinding,
    "ACTIVE",
    [],
    "negative empty binding fixture has deny-all operations"
  );

  requireApplicationStatus(
    NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding,
    "ACTIVE",
    "negative evaluate-only binding application fixture"
  );
  requireBindingExactly(
    NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding,
    "ACTIVE",
    ["evaluate"],
    "negative evaluate-only binding fixture has evaluate-only operations"
  );

  requireNoPublishedCampaignsForNegativeApplications(negativeIds);

  requireApplicationStatus(COUPON_APPLICATION_ID, "ACTIVE", "coupon abuse application fixture");
  requireBindingIncludes(
    COUPON_APPLICATION_ID,
    "ACTIVE",
    ["evaluate", "reserve", "commit", "cancel", "reverse"],
    "coupon abuse checkout binding includes all runtime operations"
  );
  requireCouponCampaignFixture();
  requireApplicationStatus(QUOTA_APPLICATION_ID, "ACTIVE", "hot quota application fixture");
  requireBindingIncludes(
    QUOTA_APPLICATION_ID,
    "ACTIVE",
    ["evaluate", "reserve", "commit", "cancel", "reverse"],
    "hot quota checkout binding includes all runtime operations"
  );
  requireHotQuotaCampaignFixture();
  requireCouponFixture("valid coupon fixture", COUPON_CODES.valid, {
    status: "ACTIVE",
    starts: "not_future",
    expires: "not_past",
    holder: null,
    maxRedemptions: null
  });
  requireCouponFixture("inactive coupon fixture", COUPON_CODES.inactive, {
    status: "PAUSED"
  });
  requireCouponFixture("not-started coupon fixture", COUPON_CODES.notStarted, {
    status: "ACTIVE",
    starts: "future"
  });
  requireCouponFixture("expired coupon fixture", COUPON_CODES.expired, {
    status: "ACTIVE",
    expires: "past"
  });
  requireCouponFixture("holder-mismatch coupon fixture", COUPON_CODES.holderMismatch, {
    status: "ACTIVE",
    holder: couponHolderProfileId()
  });
  requireCouponFixture("exhausted coupon fixture", COUPON_CODES.exhausted, {
    status: "ACTIVE",
    maxRedemptions: 0
  });
  requireCouponMissing("invalid coupon fixture is not stored", COUPON_CODES.invalid);
  requireCouponStorageInventoryReady("coupon fixture campaign storage inventory cutover-ready",
    COUPON_APPLICATION_ID, COUPON_CAMPAIGN_CODE);
  requireCouponStorageInventoryReady("coupon fixture application storage inventory cutover-ready",
    COUPON_APPLICATION_ID, null);
}

function requireApplicationStatus(applicationId, expectedStatus, name) {
  const status = queryPromotion(`
    SELECT COALESCE(MAX(status), '')
    FROM incentive_applications
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(applicationId)};
  `).trim();
  requirePreflight(name, status === expectedStatus, `application=${applicationId} status=${status || "<missing>"}`);
}

function requireNoBinding(applicationId, name) {
  const count = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_application_client_bindings
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(applicationId)}
      AND client_id = ${sqlString(CHECKOUT_CLIENT_ID)};
  `).trim() || 0);
  requirePreflight(name, count === 0, `application=${applicationId} bindings=${count}`);
}

function requireBindingIncludes(applicationId, expectedStatus, requiredOperations, name) {
  const binding = readCheckoutBinding(applicationId);
  const pass = binding?.status === expectedStatus
    && requiredOperations.every((operation) => binding.operations.includes(operation));
  requirePreflight(
    name,
    pass,
    `application=${applicationId} status=${binding?.status ?? "<missing>"} operations=${binding?.operations.join(",") ?? "<missing>"}`
  );
}

function requireBindingExactly(applicationId, expectedStatus, expectedOperations, name) {
  const binding = readCheckoutBinding(applicationId);
  const pass = binding?.status === expectedStatus && sameStringSet(binding.operations, expectedOperations);
  requirePreflight(
    name,
    pass,
    `application=${applicationId} status=${binding?.status ?? "<missing>"} operations=${binding?.operations.join(",") ?? "<missing>"}`
  );
}

function requireExpectedCampaignFixture() {
  if (!expectedCampaignCode) {
    return;
  }
  const campaignCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaigns
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(APPLICATION_ID)}
      AND code = ${sqlString(expectedCampaignCode)}
      AND status = 'PUBLISHED';
  `).trim() || 0);
  const versionCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaign_versions
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(APPLICATION_ID)}
      AND code = ${sqlString(expectedCampaignCode)}
      AND version_status = 'PUBLISHED'
      AND active_snapshot = TRUE;
  `).trim() || 0);
  requirePreflight(
    "positive expected campaign fixture is published with active snapshot",
    campaignCount === 1 && versionCount >= 1,
    `campaign=${expectedCampaignCode} campaigns=${campaignCount} activeSnapshots=${versionCount}`
  );
}

function requireCouponCampaignFixture() {
  const campaignCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaigns
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(COUPON_APPLICATION_ID)}
      AND code = ${sqlString(COUPON_CAMPAIGN_CODE)}
      AND status = 'PUBLISHED'
      AND coupon_required = TRUE;
  `).trim() || 0);
  const versionCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaign_versions
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(COUPON_APPLICATION_ID)}
      AND code = ${sqlString(COUPON_CAMPAIGN_CODE)}
      AND version_status = 'PUBLISHED'
      AND active_snapshot = TRUE
      AND coupon_required = TRUE;
  `).trim() || 0);
  const fallbackCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaign_versions
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(COUPON_APPLICATION_ID)}
      AND version_status = 'PUBLISHED'
      AND active_snapshot = TRUE
      AND coupon_required = FALSE;
  `).trim() || 0);
  requirePreflight(
    "coupon abuse campaign fixture is published and coupon-required",
    campaignCount === 1 && versionCount === 1 && fallbackCount === 0,
    `campaign=${COUPON_CAMPAIGN_CODE} campaigns=${campaignCount} activeSnapshots=${versionCount} nonCouponSnapshots=${fallbackCount}`
  );
}

function requireHotQuotaCampaignFixture() {
  const output = queryPromotion(`
    SELECT
      COUNT(*) FILTER (
        WHERE source = 'campaign'
          AND status = 'PUBLISHED'
          AND coupon_required = FALSE
          AND max_redemptions = 1
      ) AS campaign_count,
      COUNT(*) FILTER (
        WHERE source = 'version'
          AND status = 'PUBLISHED'
          AND active_snapshot = TRUE
          AND coupon_required = FALSE
          AND max_redemptions = 1
      ) AS version_count,
      COUNT(*) FILTER (
        WHERE source = 'version'
          AND status = 'PUBLISHED'
          AND active_snapshot = TRUE
          AND code <> ${sqlString(QUOTA_CAMPAIGN_CODE)}
      ) AS other_active_versions
    FROM (
      SELECT 'campaign' AS source, code, status, FALSE AS active_snapshot, coupon_required, max_redemptions
      FROM incentive_campaigns
      WHERE tenant_id = ${sqlString(TENANT_ID)}
        AND application_id = ${sqlString(QUOTA_APPLICATION_ID)}
        AND code = ${sqlString(QUOTA_CAMPAIGN_CODE)}
      UNION ALL
      SELECT 'version' AS source, code, version_status AS status, active_snapshot, coupon_required, max_redemptions
      FROM incentive_campaign_versions
      WHERE tenant_id = ${sqlString(TENANT_ID)}
        AND application_id = ${sqlString(QUOTA_APPLICATION_ID)}
    ) fixture;
  `).trim();
  const row = pipeRow(output, 3);
  const pass = row
    && numberValue(row[0]) === 1
    && numberValue(row[1]) === 1
    && numberValue(row[2]) === 0;
  requirePreflight(
    "hot quota campaign fixture is published with max quota one",
    pass,
    row
      ? `campaign=${QUOTA_CAMPAIGN_CODE} campaigns=${row[0]} activeSnapshots=${row[1]} otherActiveSnapshots=${row[2]}`
      : "campaign=<missing>"
  );
}

function requireCouponFixture(name, rawCode, expected) {
  const row = readCouponByCode(rawCode);
  if (!row) {
    requirePreflight(name, false, "coupon=<missing>");
    return;
  }
  const checks = [
    row.status === expected.status,
    row.storageFormat === "current_hmac",
    row.codeEqualsMask,
    !row.normalizedEqualsCode,
    expected.holder === undefined || row.holder === expected.holder,
    expected.maxRedemptions === undefined || row.maxRedemptions === expected.maxRedemptions
  ];
  if (expected.starts === "future") {
    checks.push(row.startsState === "future");
  } else if (expected.starts === "not_future") {
    checks.push(row.startsState !== "future");
  }
  if (expected.expires === "past") {
    checks.push(row.expiresState === "past");
  } else if (expected.expires === "not_past") {
    checks.push(row.expiresState !== "past");
  }
  requirePreflight(
    name,
    checks.every(Boolean),
    `status=${row.status} storage=${row.storageFormat} holder=${row.holder ?? "<none>"} starts=${row.startsState} expires=${row.expiresState} max=${row.maxRedemptions ?? "<none>"}`
  );
}

function requireCouponMissing(name, rawCode) {
  const row = readCouponByCode(rawCode);
  requirePreflight(name, row == null, row ? "coupon=<unexpected>" : "coupon=<missing-as-expected>");
}

function requireCouponStorageInventoryReady(name, applicationId, campaignCode) {
  if (!REQUIRE_COUPON_INVENTORY_READY) {
    record(name, true, "PROMOTION_SMOKE_REQUIRE_COUPON_INVENTORY_READY=false");
    return;
  }
  const campaignFilter = campaignCode
    ? `AND campaign.code = ${sqlString(campaignCode)}`
    : "";
  const output = queryPromotion(`
    WITH classified AS (
      SELECT CASE
          WHEN c.normalized_code IS NULL OR btrim(c.normalized_code) = '' THEN 'malformed'
          WHEN c.normalized_code LIKE ${sqlString(currentCouponStoragePrefix() + "%")}
           AND substring(c.normalized_code from ${currentCouponStoragePrefix().length + 1}) ~ '^[0-9a-f]{64}$'
            THEN 'current_hmac'
          WHEN c.normalized_code ~ '^hmac-sha256:[A-Za-z0-9._-]+:[0-9a-f]{64}$' THEN 'previous_hmac'
          WHEN c.normalized_code LIKE 'hmac-sha256:%' THEN 'malformed'
          WHEN c.normalized_code ~ '^[0-9a-f]{64}$' THEN 'legacy_sha'
          ELSE 'legacy_raw'
        END AS storage_format,
        (c.code = c.code_mask) AS code_equals_mask,
        (c.normalized_code = c.code) AS normalized_equals_code
      FROM incentive_coupons c
      JOIN incentive_campaigns campaign ON campaign.id = c.campaign_id
      WHERE campaign.tenant_id = ${sqlString(TENANT_ID)}
        AND campaign.application_id = ${sqlString(applicationId)}
        ${campaignFilter}
        AND c.status = 'ACTIVE'
    )
    SELECT
      COUNT(*) AS total_coupons,
      COUNT(*) FILTER (WHERE storage_format = 'current_hmac') AS current_hmac,
      COUNT(*) FILTER (WHERE storage_format = 'previous_hmac') AS previous_hmac,
      COUNT(*) FILTER (WHERE storage_format = 'legacy_sha') AS legacy_sha,
      COUNT(*) FILTER (WHERE storage_format = 'legacy_raw') AS legacy_raw,
      COUNT(*) FILTER (WHERE storage_format = 'malformed') AS malformed,
      COUNT(*) FILTER (WHERE code_equals_mask IS DISTINCT FROM TRUE) AS mask_violations,
      COUNT(*) FILTER (WHERE normalized_equals_code IS TRUE) AS normalized_code_leaks
    FROM classified;
  `).trim();
  const row = pipeRow(output, 8);
  const total = row ? numberValue(row[0]) : 0;
  const current = row ? numberValue(row[1]) : 0;
  const previous = row ? numberValue(row[2]) : 0;
  const legacySha = row ? numberValue(row[3]) : 0;
  const legacyRaw = row ? numberValue(row[4]) : 0;
  const malformed = row ? numberValue(row[5]) : 0;
  const maskViolations = row ? numberValue(row[6]) : 0;
  const normalizedCodeLeaks = row ? numberValue(row[7]) : 0;
  const pass = total > 0
    && current > 0
    && legacySha === 0
    && legacyRaw === 0
    && malformed === 0
    && maskViolations === 0
    && normalizedCodeLeaks === 0;
  record(
    name,
    pass,
    `application=${applicationId} campaign=${campaignCode ?? "<all>"} total=${total} current_hmac=${current} previous_hmac=${previous} legacy_sha=${legacySha} legacy_raw=${legacyRaw} malformed=${malformed} maskViolations=${maskViolations} normalizedCodeLeaks=${normalizedCodeLeaks}`
  );
  if (!pass) {
    throw new Error(`coupon storage inventory cutover readiness failed: ${name}`);
  }
  couponInventoryReadyChecks.push(campaignCode ? "campaign" : "application");
}

function readCouponByCode(rawCode) {
  const fingerprint = couponFingerprint(normalizeCouponCode(rawCode));
  const output = queryPromotion(`
    SELECT c.id::text
           || '|' || c.status
           || '|' || COALESCE(c.holder_profile_id, '')
           || '|' || CASE
                WHEN c.starts_at IS NULL THEN 'none'
                WHEN c.starts_at > NOW() THEN 'future'
                ELSE 'active'
              END
           || '|' || CASE
                WHEN c.expires_at IS NULL THEN 'none'
                WHEN c.expires_at < NOW() THEN 'past'
                ELSE 'active'
              END
           || '|' || COALESCE(c.max_redemptions::text, '')
           || '|' || CASE
                WHEN c.normalized_code LIKE ${sqlString(currentCouponStoragePrefix() + "%")}
                 AND substring(c.normalized_code from ${currentCouponStoragePrefix().length + 1}) ~ '^[0-9a-f]{64}$'
                  THEN 'current_hmac'
                WHEN c.normalized_code ~ '^hmac-sha256:[A-Za-z0-9._-]+:[0-9a-f]{64}$' THEN 'previous_hmac'
                WHEN c.normalized_code ~ '^[0-9a-f]{64}$' THEN 'legacy_sha'
                WHEN c.normalized_code LIKE 'hmac-sha256:%' THEN 'malformed'
                ELSE 'legacy_raw'
              END
           || '|' || (c.code = c.code_mask)::text
           || '|' || (c.normalized_code = c.code)::text
    FROM incentive_coupons c
    JOIN incentive_campaigns campaign ON campaign.id = c.campaign_id
    WHERE campaign.tenant_id = ${sqlString(TENANT_ID)}
      AND campaign.application_id = ${sqlString(COUPON_APPLICATION_ID)}
      AND campaign.code = ${sqlString(COUPON_CAMPAIGN_CODE)}
      AND c.normalized_code = ${sqlString(fingerprint)}
    LIMIT 1;
  `).trim();
  if (!output) {
    return null;
  }
  const [id, status, holder, startsState, expiresState, maxRedemptions, storageFormat,
    codeEqualsMask, normalizedEqualsCode] = output.split("|");
  return {
    id,
    status,
    holder: holder || null,
    startsState,
    expiresState,
    maxRedemptions: maxRedemptions === "" ? null : Number(maxRedemptions),
    storageFormat,
    codeEqualsMask: codeEqualsMask === "true",
    normalizedEqualsCode: normalizedEqualsCode === "true"
  };
}

function requireNoPublishedCampaignsForNegativeApplications(applicationIds) {
  const list = applicationIds.map(sqlString).join(",");
  const campaignCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaigns
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id IN (${list})
      AND status = 'PUBLISHED';
  `).trim() || 0);
  const versionCount = Number(queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_campaign_versions
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id IN (${list})
      AND version_status = 'PUBLISHED'
      AND active_snapshot = TRUE;
  `).trim() || 0);
  requirePreflight(
    "negative application fixtures have no published campaign snapshots",
    campaignCount === 0 && versionCount === 0,
    `campaigns=${campaignCount} activeSnapshots=${versionCount}`
  );
}

function readCheckoutBinding(applicationId) {
  const output = queryPromotion(`
    SELECT status || '|' || allowed_operations::text
    FROM incentive_application_client_bindings
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(applicationId)}
      AND client_id = ${sqlString(CHECKOUT_CLIENT_ID)}
    LIMIT 1;
  `).trim();
  if (!output) {
    return null;
  }
  const [status, operationsJson = "[]"] = output.split("|");
  return {
    status,
    operations: JSON.parse(operationsJson).map((operation) => String(operation).toLowerCase())
  };
}

function requirePreflight(name, pass, detail = "") {
  record(name, pass, detail);
  if (!pass) {
    throw new Error(`application fixture preflight failed: ${name} (${detail})`);
  }
}

async function assertGatewayRuntimeRouteClosed(path) {
  const response = await directHttp("POST", `${GATEWAY_URL}${path}`, {
    headers: { "content-type": "application/json" },
    body: "{}"
  });
  const allowed = parseStatuses(process.env.PROMOTION_SMOKE_GATEWAY_RUNTIME_BLOCKED_STATUSES ?? "404");
  const pass = allowed.has(response.status);
  record(`gateway runtime route closed ${path}`, pass, `status=${response.status}`);
}

async function assertCouponImportGatewaySmoke() {
  if (!COUPON_IMPORT_GATEWAY_ENABLED) {
    record("gateway admin coupon import smoke skipped", true,
      "PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED=false");
    return;
  }

  const unauth = await directHttp(
    "GET",
    `${GATEWAY_URL}/admin/v1/incentives/coupons/storage-inventory?tenantId=${encodeURIComponent(TENANT_ID)}`
      + `&applicationId=${encodeURIComponent(COUPON_APPLICATION_ID)}`
      + `&campaignId=${encodeURIComponent(COUPON_IMPORT_GATEWAY_CAMPAIGN_ID)}`);
  recordStatusIn("gateway admin coupon inventory requires bearer", unauth, [401, 403]);

  const inventory = await gatewayAdminJson(
    "GET",
    `/admin/v1/incentives/coupons/storage-inventory?tenantId=${encodeURIComponent(TENANT_ID)}`
      + `&applicationId=${encodeURIComponent(COUPON_APPLICATION_ID)}`
      + `&campaignId=${encodeURIComponent(COUPON_IMPORT_GATEWAY_CAMPAIGN_ID)}`
      + "&activeOnly=true",
    undefined,
    `${RUN_ID}-coupon-import-inventory`);
  record(
    "gateway admin coupon inventory cutover-ready",
    inventory.legacyCoupons === 0
      && inventory.malformedCoupons === 0
      && inventory.fallbackDisableReady === true
      && Number(inventory.totalCoupons ?? 0) > 0,
    `legacy=${inventory.legacyCoupons} malformed=${inventory.malformedCoupons} total=${inventory.totalCoupons}`
  );

  const fixture = couponImportGatewayFixture();
  const idempotencyKey = `coupon-import-gateway-${RUN_ID}`;
  const correlationId = `${RUN_ID}-coupon-import-gateway`;
  const dryRun = await gatewayAdminMultipart(
    "POST",
    "/admin/v1/incentives/coupons:import-dry-run",
    couponImportGatewayForm(fixture.csv, idempotencyKey),
    correlationId,
    { "Idempotency-Key": idempotencyKey });
  const dryRunBody = requireJson(dryRun, "gateway admin coupon import dry-run");
  record(
    "gateway admin coupon import dry-run returns invalid evidence",
    dryRunBody.dryRun === true
      && dryRunBody.campaignId === COUPON_IMPORT_GATEWAY_CAMPAIGN_ID
      && Number(dryRunBody.requestedRows) >= 5
      && Number(dryRunBody.invalidRows) >= 3
      && Number(dryRunBody.duplicateInFileRows) >= 1
      && Number(dryRunBody.duplicateExistingRows) >= 1
      && dryRunBody.commitReady === false,
    `dryRunId=${dryRunBody.dryRunId ?? "missing"} invalid=${dryRunBody.invalidRows ?? "missing"}`
  );
  assertNoCouponImportGatewayLeak("gateway dry-run response redacts import secrets",
    JSON.stringify(dryRunBody), fixture.secrets, ["normalizedCode", "fingerprint", idempotencyKey]);

  const replay = await gatewayAdminMultipart(
    "POST",
    "/admin/v1/incentives/coupons:import-dry-run",
    couponImportGatewayForm(fixture.csv, idempotencyKey),
    `${correlationId}-replay`,
    { "Idempotency-Key": idempotencyKey });
  const replayBody = requireJson(replay, "gateway admin coupon import idempotency replay");
  record(
    "gateway admin coupon import dry-run idempotency replay",
    replayBody.dryRunId === dryRunBody.dryRunId,
    `dryRunId=${replayBody.dryRunId ?? "missing"}`
  );

  const history = await gatewayAdminJson(
    "GET",
    `/admin/v1/incentives/coupons/import-dry-runs?tenantId=${encodeURIComponent(TENANT_ID)}`
      + `&applicationId=${encodeURIComponent(COUPON_APPLICATION_ID)}`
      + `&campaignId=${encodeURIComponent(COUPON_IMPORT_GATEWAY_CAMPAIGN_ID)}`
      + "&status=COMPLETED&limit=5",
    undefined,
    `${RUN_ID}-coupon-import-history`);
  record(
    "gateway admin coupon import history includes dry-run",
    Array.isArray(history.items) && history.items.some((item) => item.dryRunId === dryRunBody.dryRunId),
    `items=${Array.isArray(history.items) ? history.items.length : "missing"}`
  );

  const detail = await gatewayAdminJson(
    "GET",
    `/admin/v1/incentives/coupons/import-dry-runs/${encodeURIComponent(dryRunBody.dryRunId)}`,
    undefined,
    `${RUN_ID}-coupon-import-detail`);
  record(
    "gateway admin coupon import detail returns same result",
    detail.dryRunId === dryRunBody.dryRunId && detail.resultHash === dryRunBody.resultHash,
    `dryRunId=${detail.dryRunId ?? "missing"}`
  );

  const issueExport = await gatewayAdminJson(
    "GET",
    `/admin/v1/incentives/coupons/import-dry-runs/${encodeURIComponent(dryRunBody.dryRunId)}`
      + "/issue-export?rowStatus=INVALID",
    undefined,
    `${RUN_ID}-coupon-import-issue-export`);
  const content = String(issueExport.content ?? "");
  record(
    "gateway admin coupon issue export returns masked CSV",
    issueExport.rowStatus === "INVALID"
      && issueExport.contentType === "text/csv"
      && Number(issueExport.rowCount) === Number(dryRunBody.invalidRows)
      && content.includes("rowNumber,codeMask,rowStatus,issueCodes")
      && content.includes("DUPLICATE_IN_FILE")
      && content.includes("DUPLICATE_EXISTING"),
    `rowCount=${issueExport.rowCount ?? "missing"}`
  );
  assertNoCouponImportGatewayLeak("gateway issue export redacts import secrets",
    content, fixture.secrets, ["normalizedCode", "hmac-sha256", "fingerprint", idempotencyKey]);
  assertGatewayIssueExportAudit(
    dryRunBody.dryRunId,
    issueExport,
    `${RUN_ID}-coupon-import-issue-export`,
    fixture.secrets,
    idempotencyKey);
}

function assertGatewayIssueExportAudit(dryRunId, issueExport, correlationId, secrets, idempotencyKey) {
  if (!dbChecksAvailable()) {
    record("gateway issue export audit DB evidence skipped", false, "database checks are not configured");
    return;
  }
  const output = queryPromotion(`
    SELECT jsonb_build_object(
      'action', action,
      'aggregateType', aggregate_type,
      'aggregateId', aggregate_id,
      'tenantId', tenant_id,
      'applicationId', application_id,
      'actorId', actor_id,
      'correlationId', correlation_id,
      'sourceClientId', source_client_id,
      'payload', payload_json,
      'payloadText', payload_json::text
    )::text
    FROM incentive_audit_events
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(COUPON_APPLICATION_ID)}
      AND aggregate_id = ${sqlString(dryRunId)}
      AND aggregate_type = 'coupon-import-dry-run'
      AND action = 'coupon.import_issue_export_downloaded'
      AND correlation_id = ${sqlString(correlationId)}
    ORDER BY created_at DESC
    LIMIT 1;
  `).trim();
  const audit = parseJson(output);
  const payload = audit?.payload ?? {};
  const pass = audit?.action === "coupon.import_issue_export_downloaded"
    && audit.aggregateType === "coupon-import-dry-run"
    && audit.aggregateId === dryRunId
    && audit.tenantId === TENANT_ID
    && audit.applicationId === COUPON_APPLICATION_ID
    && Boolean(String(audit.actorId ?? "").trim())
    && audit.correlationId === correlationId
    && Boolean(String(audit.sourceClientId ?? "").trim())
    && payload.dryRunId === dryRunId
    && payload.campaignId === COUPON_IMPORT_GATEWAY_CAMPAIGN_ID
    && payload.rowStatus === "INVALID"
    && Number(payload.rowCount) === Number(issueExport.rowCount)
    && payload.filename === issueExport.filename;
  record(
    "gateway issue export audit DB evidence persisted",
    pass,
    audit
      ? `dryRunId=${audit.aggregateId} rowStatus=${payload.rowStatus ?? "<missing>"} rowCount=${payload.rowCount ?? "<missing>"} sourceClient=${audit.sourceClientId ?? "<missing>"}`
      : "audit=<missing>"
  );
  assertNoCouponImportGatewayLeak(
    "gateway issue export audit payload redacts import secrets",
    String(audit?.payloadText ?? ""),
    secrets,
    ["normalizedCode", "hmac-sha256", "fingerprint", idempotencyKey, "csvContent", "contentHash"]
  );
}

async function assertLocalInternalAdminCouponInventory() {
  if (!LOCAL) {
    record("local internal admin coupon inventory smoke skipped", true, "PROMOTION_SMOKE_MODE=staging");
    return;
  }
  if (!LOCAL_INTERNAL_ADMIN_INVENTORY_ENABLED) {
    record("local internal admin coupon inventory smoke skipped", true,
      "PROMOTION_SMOKE_LOCAL_INTERNAL_ADMIN_INVENTORY_ENABLED=false");
    return;
  }
  requireValue("PROMOTION_SMOKE_INTERNAL_JWT_SECRET", INTERNAL_JWT_SECRET);

  const path = "/internal/incentives/coupons/storage-inventory"
    + `?tenantId=${encodeURIComponent(TENANT_ID)}`
    + `&applicationId=${encodeURIComponent(COUPON_APPLICATION_ID)}`
    + `&campaignId=${encodeURIComponent(COUPON_IMPORT_GATEWAY_CAMPAIGN_ID)}`
    + "&activeOnly=true";
  const unauth = await requestInternal("GET", `${PROMOTION_URL}${path}`);
  recordStatusIn("local internal admin coupon inventory requires internal JWT", unauth, [401, 403]);

  const response = await requestInternal("GET", `${PROMOTION_URL}${path}`, {
    headers: localInternalAdminHeaders(`${RUN_ID}-local-internal-admin-inventory`)
  });
  assertStatus(response, 200, "local internal admin coupon storage inventory");
  const inventory = requireJson(response, "local internal admin coupon storage inventory");
  const total = Number(inventory.totalCoupons ?? 0);
  const legacy = Number(inventory.legacyCoupons ?? -1);
  const malformed = Number(inventory.malformedCoupons ?? -1);
  const current = storageFormatCount(inventory, "current_hmac");
  const pass = inventory.tenantId === TENANT_ID
    && inventory.applicationId === COUPON_APPLICATION_ID
    && inventory.campaignId === COUPON_IMPORT_GATEWAY_CAMPAIGN_ID
    && inventory.activeOnly === true
    && typeof inventory.legacyFallbackEnabled === "boolean"
    && inventory.fallbackDisableReady === true
    && total > 0
    && current > 0
    && legacy === 0
    && malformed === 0;
  record(
    "local internal admin coupon inventory cutover-ready",
    pass,
    `legacyFallback=${inventory.legacyFallbackEnabled} total=${total} current_hmac=${current} legacy=${legacy} malformed=${malformed}`
  );
  assertNoCouponImportGatewayLeak(
    "local internal admin coupon inventory redacts coupon secrets",
    JSON.stringify(inventory),
    couponSecretNeedles(),
    ["normalizedCode", "fingerprint", "hmac-sha256"]
  );
}

function localInternalAdminHeaders(correlationId) {
  const userId = "1";
  const email = "promotion-smoke-admin@example.com";
  const roles = ["ADMIN"];
  const token = signLocalInternalUserJwt({
    userId,
    email,
    roles,
    azp: "promotion-runtime-smoke"
  });
  return {
    accept: "application/json",
    authorization: `Bearer ${token}`,
    "x-internal-authorization": `Bearer ${token}`,
    "x-user-id": userId,
    "x-user-email": email,
    "x-user-role": "ADMIN",
    "x-user-roles": roles.join(","),
    "x-correlation-id": correlationId
  };
}

function signLocalInternalUserJwt({ userId, email, roles, azp }) {
  const now = Math.floor(Date.now() / 1000);
  const header = {
    alg: "HS256",
    typ: "JWT"
  };
  const payload = {
    jti: crypto.randomUUID(),
    iss: INTERNAL_JWT_ISSUER,
    sub: userId,
    aud: [INTERNAL_AUDIENCE],
    token_use: "internal",
    actor_type: "user",
    azp,
    uid: userId,
    email,
    roles,
    scope: "internal:user",
    scp: ["internal:user"],
    iat: now,
    nbf: now - 1,
    exp: now + 180
  };
  const encoded = `${base64UrlJson(header)}.${base64UrlJson(payload)}`;
  const signature = crypto
    .createHmac("sha256", INTERNAL_JWT_SECRET)
    .update(encoded)
    .digest("base64url");
  return `${encoded}.${signature}`;
}

function base64UrlJson(value) {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function storageFormatCount(inventory, storageFormat) {
  const item = Array.isArray(inventory.items)
    ? inventory.items.find((entry) => entry.storageFormat === storageFormat)
    : null;
  return Number(item?.count ?? 0);
}

async function gatewayAdminJson(method, path, body, correlationId) {
  const headers = {
    accept: "application/json",
    authorization: `Bearer ${ADMIN_ACCESS_TOKEN}`,
    "x-correlation-id": correlationId
  };
  if (body !== undefined) {
    headers["content-type"] = "application/json";
  }
  const response = await directHttp(method, `${GATEWAY_URL}${path}`, {
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  assertStatus(response, 200, `${method} ${path}`);
  return requireJson(response, `${method} ${path}`);
}

async function gatewayAdminMultipart(method, path, form, correlationId, extraHeaders = {}) {
  const response = await directHttp(method, `${GATEWAY_URL}${path}`, {
    headers: {
      accept: "application/json",
      authorization: `Bearer ${ADMIN_ACCESS_TOKEN}`,
      "x-correlation-id": correlationId,
      ...extraHeaders
    },
    body: form
  });
  assertStatus(response, 200, `${method} ${path}`);
  return response;
}

function couponImportGatewayForm(csv, idempotencyKey) {
  const form = new FormData();
  form.set("campaignId", COUPON_IMPORT_GATEWAY_CAMPAIGN_ID);
  form.set("maxRows", "20");
  form.set("idempotencyKey", idempotencyKey);
  form.set("file", new Blob([csv], { type: "text/csv" }), `coupon-import-${RUN_ID}.csv`);
  return form;
}

function couponImportGatewayFixture() {
  const duplicate = `GW-DUP-${RUN_ID}`.replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 80);
  const tooLong = `GW-${"X".repeat(130)}`;
  const csv = [
    "code,startsAt,expiresAt,maxRedemptions",
    `${duplicate},,,`,
    `${duplicate},,,`,
    `${COUPON_CODES.valid},,,`,
    ",,,",
    `${tooLong},,,`
  ].join("\n");
  return {
    csv,
    secrets: [duplicate, normalizeCouponCode(duplicate), COUPON_CODES.valid,
      normalizeCouponCode(COUPON_CODES.valid), tooLong, normalizeCouponCode(tooLong)]
  };
}

function requireJson(response, name) {
  if (!response.json) {
    throw new Error(`${name} did not return JSON: ${redact(response.text).slice(0, 500)}`);
  }
  return response.json;
}

function assertNoCouponImportGatewayLeak(name, text, secrets, forbiddenTerms = []) {
  const value = String(text ?? "");
  let secretHits = 0;
  for (const secret of secrets) {
    if (secret && secret.length >= 4 && value.includes(secret)) {
      secretHits += 1;
    }
  }
  const termHits = forbiddenTerms.filter((term) => term && value.includes(term));
  record(name, secretHits === 0 && termHits.length === 0,
    secretHits || termHits.length ? `secretHits=${secretHits} termHits=${termHits.join(",")}` : "redacted");
}

async function assertWrongSecretRejected() {
  const response = await requestInternal("POST", `${TOKEN_CONVERTER_URL}/oauth/token`, {
    headers: { "content-type": "application/x-www-form-urlencoded" },
    form: {
      grant_type: "client_credentials",
      client_id: CHECKOUT_CLIENT_ID,
      client_secret: `${CHECKOUT_CLIENT_SECRET}-wrong`,
      audience: INTERNAL_AUDIENCE,
      scope: "internal:promotion:evaluate"
    }
  });
  record("STS rejects wrong checkout client secret", response.status >= 400, `status=${response.status}`);
}

async function assertPromotionServiceCannotMintRuntimeScope() {
  const response = await requestInternal("POST", `${TOKEN_CONVERTER_URL}/oauth/token`, {
    headers: { "content-type": "application/x-www-form-urlencoded" },
    form: {
      grant_type: "client_credentials",
      client_id: PROMOTION_CLIENT_ID,
      client_secret: PROMOTION_CLIENT_SECRET,
      audience: INTERNAL_AUDIENCE,
      scope: "internal:promotion:evaluate"
    }
  });
  record("STS rejects promotion-service runtime operation scope", response.status >= 400, `status=${response.status}`);
}

async function mintCheckoutToken() {
  const token = await mintCheckoutTokenWithScopes(REQUIRED_SCOPES, "checkout-service STS runtime token minted");
  const claims = decodeJwtPayload(token);
  assertEqual(claims.azp, CHECKOUT_CLIENT_ID, "checkout STS token azp");
  for (const scope of REQUIRED_SCOPES) {
    if (!scopeSet(claims).has(scope)) {
      throw new Error(`checkout STS token missing ${scope}`);
    }
  }
  return token;
}

async function mintCheckoutTokenWithScopes(scopes, checkName) {
  const response = await requestInternal("POST", `${TOKEN_CONVERTER_URL}/oauth/token`, {
    headers: { "content-type": "application/x-www-form-urlencoded" },
    form: {
      grant_type: "client_credentials",
      client_id: CHECKOUT_CLIENT_ID,
      client_secret: CHECKOUT_CLIENT_SECRET,
      audience: INTERNAL_AUDIENCE,
      scope: scopes.join(" ")
    }
  });
  assertStatus(response, 200, "checkout-service STS client_credentials");
  const token = response.json?.access_token;
  if (!token) {
    throw new Error("checkout-service STS response did not include access_token");
  }
  record(checkName, true, `scopes=${scopes.length}`);
  return token;
}

async function assertRuntimeAuthRequired() {
  const missing = await requestInternal("POST", `${PROMOTION_URL}/internal/incentives/evaluate`, {
    headers: {
      "content-type": "application/json",
      "x-correlation-id": `${RUN_ID}-missing-runtime-token`
    },
    body: JSON.stringify(runtimeContext("missing-runtime-token"))
  });
  recordStatusIn(
    "promotion runtime rejects missing internal token",
    missing,
    [401, 403]
  );

  const malformed = await requestInternal("POST", `${PROMOTION_URL}/internal/incentives/evaluate`, {
    headers: {
      authorization: "Bearer not-a-jwt",
      "x-internal-authorization": "Bearer not-a-jwt",
      "content-type": "application/json",
      "x-correlation-id": `${RUN_ID}-malformed-runtime-token`
    },
    body: JSON.stringify(runtimeContext("malformed-runtime-token"))
  });
  recordStatusIn(
    "promotion runtime rejects malformed internal token",
    malformed,
    [401, 403]
  );
}

async function assertRuntimeOperationScopesRequired() {
  const zeroUuid = "00000000-0000-0000-0000-000000000000";
  const cases = [
    {
      name: "evaluate rejects token without evaluate scope",
      scopes: ["internal:promotion:reserve"],
      method: "POST",
      path: "/internal/incentives/evaluate",
      correlationId: `${RUN_ID}-missing-evaluate-scope`,
      body: runtimeContext("missing-evaluate-scope")
    },
    {
      name: "reserve rejects token without reserve scope",
      scopes: ["internal:promotion:evaluate"],
      method: "POST",
      path: "/internal/incentives/reservations",
      correlationId: `${RUN_ID}-missing-reserve-scope`,
      idempotencyKey: `${RUN_ID}-missing-reserve-scope`,
      body: { context: runtimeContext("missing-reserve-scope") }
    },
    {
      name: "commit rejects token without commit scope",
      scopes: ["internal:promotion:reserve"],
      method: "POST",
      path: `/internal/incentives/reservations/${zeroUuid}/commit`,
      correlationId: `${RUN_ID}-missing-commit-scope`,
      idempotencyKey: `${RUN_ID}-missing-commit-scope`,
      body: { externalReference: `order-${RUN_ID}-missing-commit-scope` }
    },
    {
      name: "cancel rejects token without cancel scope",
      scopes: ["internal:promotion:commit"],
      method: "POST",
      path: `/internal/incentives/reservations/${zeroUuid}/cancel`,
      correlationId: `${RUN_ID}-missing-cancel-scope`,
      idempotencyKey: `${RUN_ID}-missing-cancel-scope`,
      body: { reason: `smoke missing cancel scope ${RUN_ID}` }
    },
    {
      name: "reverse rejects token without reverse scope",
      scopes: ["internal:promotion:commit"],
      method: "POST",
      path: `/internal/incentives/redemptions/${zeroUuid}/reverse`,
      correlationId: `${RUN_ID}-missing-reverse-scope`,
      idempotencyKey: `${RUN_ID}-missing-reverse-scope`,
      body: { reason: `smoke missing reverse scope ${RUN_ID}` }
    }
  ];

  for (const testCase of cases) {
    const limitedToken = await mintCheckoutTokenWithScopes(
      testCase.scopes,
      `checkout-service limited STS token minted for ${testCase.name}`
    );
    const response = await promotionRequest(limitedToken, testCase.method, testCase.path, {
      correlationId: testCase.correlationId,
      idempotencyKey: testCase.idempotencyKey,
      body: testCase.body
    });
    recordStatusIn(`promotion ${testCase.name}`, response, [401, 403]);
  }
}

async function assertUnknownApplicationRejected(token) {
  const context = {
    ...runtimeContext("unknown-application"),
    tenantId: `${TENANT_ID}-missing`,
    applicationId: `${APPLICATION_ID}-missing`
  };
  const response = await promotionRequest(token, "POST", "/internal/incentives/evaluate", {
    correlationId: `${RUN_ID}-unknown-application`,
    body: context
  });
  recordStatusIn("promotion evaluate rejects unknown incentive application", response, [403, 404]);
}

async function assertClientBindingNegativeFixtures(token) {
  const cases = [
    {
      name: "unbound application rejects checkout client",
      method: "POST",
      path: "/internal/incentives/evaluate",
      appId: NEGATIVE_APPLICATION_IDS.unbound,
      correlationId: `${RUN_ID}-unbound-application`,
      body: runtimeContextForApplication("unbound-application", NEGATIVE_APPLICATION_IDS.unbound),
      expectedDetail: "Incentive caller is not bound to application"
    },
    {
      name: "suspended application rejects checkout client",
      method: "POST",
      path: "/internal/incentives/evaluate",
      appId: NEGATIVE_APPLICATION_IDS.suspendedApplication,
      correlationId: `${RUN_ID}-suspended-application`,
      body: runtimeContextForApplication("suspended-application", NEGATIVE_APPLICATION_IDS.suspendedApplication),
      expectedDetail: "Incentive application is not active"
    },
    {
      name: "suspended binding rejects checkout client",
      method: "POST",
      path: "/internal/incentives/evaluate",
      appId: NEGATIVE_APPLICATION_IDS.suspendedBinding,
      correlationId: `${RUN_ID}-suspended-binding`,
      body: runtimeContextForApplication("suspended-binding", NEGATIVE_APPLICATION_IDS.suspendedBinding),
      expectedDetail: "Incentive caller binding is suspended"
    },
    {
      name: "empty operation binding rejects checkout client",
      method: "POST",
      path: "/internal/incentives/evaluate",
      appId: NEGATIVE_APPLICATION_IDS.emptyBinding,
      correlationId: `${RUN_ID}-empty-binding`,
      body: runtimeContextForApplication("empty-binding", NEGATIVE_APPLICATION_IDS.emptyBinding),
      expectedDetail: "Incentive caller binding has no allowed operations"
    },
    {
      name: "evaluate-only binding rejects reserve operation",
      method: "POST",
      path: "/internal/incentives/reservations",
      appId: NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding,
      correlationId: `${RUN_ID}-evaluate-only-binding`,
      idempotencyKey: `${RUN_ID}-evaluate-only-binding-reserve`,
      body: {
        context: runtimeContextForApplication(
          "evaluate-only-binding",
          NEGATIVE_APPLICATION_IDS.evaluateOnlyBinding
        )
      },
      expectedDetail: "Incentive caller is not allowed to run operation: reserve"
    }
  ];

  for (const testCase of cases) {
    const response = await promotionRequest(token, testCase.method, testCase.path, {
      correlationId: testCase.correlationId,
      idempotencyKey: testCase.idempotencyKey,
      body: testCase.body
    });
    recordForbiddenDetail(`promotion ${testCase.name}`, response, testCase.expectedDetail);
    assertNoReservationForScenario(
      testCase.appId,
      scenarioFromCorrelation(testCase.correlationId),
      `promotion ${testCase.name} creates no reservation`
    );
  }
}

async function assertCouponAbuseFixtures(token) {
  const declineCases = [
    {
      name: "missing required coupon",
      scenario: "coupon-missing-required",
      couponCodes: [],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "invalid coupon code",
      scenario: "coupon-invalid",
      couponCodes: [COUPON_CODES.invalid],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "inactive coupon",
      scenario: "coupon-inactive",
      couponCodes: [COUPON_CODES.inactive],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "not-started coupon",
      scenario: "coupon-not-started",
      couponCodes: [COUPON_CODES.notStarted],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "expired coupon",
      scenario: "coupon-expired",
      couponCodes: [COUPON_CODES.expired],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "holder mismatch coupon",
      scenario: "coupon-holder-mismatch",
      couponCodes: [COUPON_CODES.holderMismatch],
      reason: "NO_ELIGIBLE_INCENTIVE",
      expectCampaign: false,
      expectCoupon: false
    },
    {
      name: "exhausted coupon",
      scenario: "coupon-exhausted",
      couponCodes: [COUPON_CODES.exhausted],
      reason: "QUOTA_EXHAUSTED",
      expectCampaign: true,
      expectCoupon: true
    }
  ];

  for (const testCase of declineCases) {
    const response = await couponEvaluate(token, testCase.scenario, testCase.couponCodes);
    assertCouponDeclineResponse(`promotion evaluate rejects ${testCase.name}`, response, testCase);
    assertNoCouponSecretsInResponse(`promotion evaluate ${testCase.name} response hides coupon secrets`, response);
    assertNoReservationForScenario(
      COUPON_APPLICATION_ID,
      testCase.scenario,
      `promotion evaluate ${testCase.name} creates no reservation`
    );
  }

  const valid = await couponEvaluate(token, "coupon-valid", [COUPON_CODES.valid]);
  assertCouponEligibleResponse("promotion evaluate accepts valid coupon fixture", valid);
  assertNoCouponSecretsInResponse("promotion evaluate valid coupon response hides coupon secrets", valid);
  assertNoReservationForScenario(
    COUPON_APPLICATION_ID,
    "coupon-valid",
    "promotion evaluate valid coupon remains read-only"
  );

  const reserveInvalid = await couponReserve(token, "coupon-invalid-reserve", [COUPON_CODES.invalid]);
  assertCouponReserveDeclineResponse("promotion reserve rejects invalid coupon without reservation", reserveInvalid);
  assertNoCouponSecretsInResponse("promotion reserve invalid coupon response hides coupon secrets", reserveInvalid);
  assertNoReservationForScenario(
    COUPON_APPLICATION_ID,
    "coupon-invalid-reserve",
    "promotion reserve invalid coupon creates no reservation"
  );
}

async function assertCouponAbuseGuardFixtures(token) {
  const evaluateScenario = "coupon-abuse-guard-evaluate";
  const limitedEvaluate = await burstUntilLimited(
    "promotion evaluate coupon abuse guard limits invalid burst",
    async () => couponEvaluate(token, evaluateScenario, [COUPON_CODES.invalid]),
    (response) => response.json?.eligible === false
      && Array.isArray(response.json?.reasonCodes)
      && response.json.reasonCodes.includes("RATE_LIMITED")
  );
  assertCouponEvaluateRateLimitedResponse(
    "promotion evaluate coupon abuse guard returns generic limited decline",
    limitedEvaluate
  );
  assertNoCouponSecretsInResponse(
    "promotion evaluate coupon abuse guard response hides coupon secrets",
    limitedEvaluate
  );
  assertNoReservationForScenario(
    COUPON_APPLICATION_ID,
    evaluateScenario,
    "promotion evaluate coupon abuse guard creates no reservation"
  );

  const reserveScenario = "coupon-abuse-guard-reserve";
  const limitedReserve = await burstUntilLimited(
    "promotion reserve coupon abuse guard limits invalid burst",
    async (attempt) => couponReserveAttempt(token, reserveScenario, attempt, [COUPON_CODES.invalid]),
    (response) => response.json?.reserved === false
      && Array.isArray(response.json?.reasonCodes)
      && response.json.reasonCodes.includes("RATE_LIMITED")
  );
  assertCouponReserveRateLimitedResponse(
    "promotion reserve coupon abuse guard returns generic limited decline",
    limitedReserve
  );
  assertNoCouponSecretsInResponse(
    "promotion reserve coupon abuse guard response hides coupon secrets",
    limitedReserve
  );
  assertNoReservationForScenario(
    COUPON_APPLICATION_ID,
    reserveScenario,
    "promotion reserve coupon abuse guard creates no reservation"
  );
}

async function assertHotQuotaConcurrencyFixture(token) {
  const waves = [];
  for (let wave = 1; wave <= HOT_QUOTA_SOAK_WAVES; wave += 1) {
    const scenario = wave === 1 ? "hot-quota-concurrency" : `hot-quota-soak-${wave}`;
    waves.push(await runHotQuotaConcurrencyWave(token, scenario, wave));
  }
  await writeHotQuotaSoakArtifactIfNeeded(waves);
}

async function runHotQuotaConcurrencyWave(token, scenario, wave) {
  const started = Date.now();
  const responses = await Promise.all(
    Array.from({ length: HOT_QUOTA_PARALLEL_ATTEMPTS }, (_, attempt) =>
      quotaReserveAttempt(token, scenario, attempt + 1))
  );
  const durationMs = Date.now() - started;
  responses.forEach((response, index) =>
    assertStatus(response, 200, hotQuotaCheckName(`promotion hot quota concurrent reserve attempt ${index + 1}`, wave)));

  const reserved = responses.filter((response) => response.json?.reserved === true);
  const exhausted = responses.filter((response) => response.json?.reserved === false
    && Array.isArray(response.json?.reasonCodes)
    && response.json.reasonCodes.includes("QUOTA_EXHAUSTED"));
  const http5xxCount = responses.filter((response) => response.status >= 500).length;
  const unexpectedDeclineCount = responses.filter((response) => response.json?.reserved === false
    && (!Array.isArray(response.json?.reasonCodes) || !response.json.reasonCodes.includes("QUOTA_EXHAUSTED"))).length;
  const apiPass = reserved.length === 1
    && exhausted.length === HOT_QUOTA_PARALLEL_ATTEMPTS - 1
    && http5xxCount === 0
    && unexpectedDeclineCount === 0;
  record(
    hotQuotaCheckName("promotion hot quota concurrent reserve allows exactly one winner", wave),
    apiPass,
    `attempts=${HOT_QUOTA_PARALLEL_ATTEMPTS} reserved=${reserved.length} exhausted=${exhausted.length} durationMs=${durationMs}`
  );
  let winningReservationId = null;
  let dbEvidencePass = null;
  let releaseEvidencePass = null;
  if (reserved.length === 1) {
    winningReservationId = reserved[0].json.reservationId;
    dbEvidencePass = assertHotQuotaConcurrencyEvidence(scenario, winningReservationId, wave);
    await cancel(token, winningReservationId, `${scenario}-release`);
    releaseEvidencePass = assertHotQuotaReleaseEvidence(scenario, winningReservationId, wave);
  }
  return {
    wave,
    scenario,
    durationMs,
    attempts: HOT_QUOTA_PARALLEL_ATTEMPTS,
    reservedCount: reserved.length,
    quotaExhaustedCount: exhausted.length,
    http5xxCount,
    unexpectedDeclineCount,
    winnerReservationId: winningReservationId,
    dbEvidencePass,
    releaseEvidencePass,
    pass: apiPass && dbEvidencePass !== false && releaseEvidencePass !== false
  };
}

async function writeHotQuotaSoakArtifactIfNeeded(waves) {
  if (!HOT_QUOTA_SOAK_ARTIFACT_FILE) {
    return;
  }
  const totalAttempts = waves.reduce((sum, wave) => sum + wave.attempts, 0);
  const totalReserved = waves.reduce((sum, wave) => sum + wave.reservedCount, 0);
  const totalQuotaExhausted = waves.reduce((sum, wave) => sum + wave.quotaExhaustedCount, 0);
  const totalHttp5xx = waves.reduce((sum, wave) => sum + wave.http5xxCount, 0);
  const totalUnexpectedDeclines = waves.reduce((sum, wave) => sum + wave.unexpectedDeclineCount, 0);
  const durations = waves.map((wave) => wave.durationMs).sort((left, right) => left - right);
  const payload = {
    schemaVersion: 1,
    artifactType: "promotion_hot_quota_soak_evidence",
    generatedAt: new Date().toISOString(),
    runId: RUN_ID,
    tenantId: TENANT_ID,
    applicationId: QUOTA_APPLICATION_ID,
    campaignCode: QUOTA_CAMPAIGN_CODE,
    configuration: {
      waves: HOT_QUOTA_SOAK_WAVES,
      concurrency: HOT_QUOTA_PARALLEL_ATTEMPTS
    },
    summary: {
      passed: waves.every((wave) => wave.pass),
      passedWaves: waves.filter((wave) => wave.pass).length,
      totalWaves: waves.length,
      totalAttempts,
      totalReserved,
      totalQuotaExhausted,
      totalHttp5xx,
      totalUnexpectedDeclines,
      uniqueWinnerReservationIds: new Set(waves.map((wave) => wave.winnerReservationId).filter(Boolean)).size,
      latencyMs: {
        p50: percentile(durations, 0.5),
        p95: percentile(durations, 0.95),
        p99: percentile(durations, 0.99),
        max: durations.at(-1) ?? 0
      }
    },
    waves: waves.map((wave) => ({
      wave: wave.wave,
      scenario: wave.scenario,
      attempts: wave.attempts,
      reservedCount: wave.reservedCount,
      quotaExhaustedCount: wave.quotaExhaustedCount,
      http5xxCount: wave.http5xxCount,
      unexpectedDeclineCount: wave.unexpectedDeclineCount,
      winnerReservationId: wave.winnerReservationId,
      dbEvidencePass: wave.dbEvidencePass,
      releaseEvidencePass: wave.releaseEvidencePass,
      durationMs: wave.durationMs,
      pass: wave.pass
    }))
  };
  await writeJsonArtifact(HOT_QUOTA_SOAK_ARTIFACT_FILE, payload);
  record(
    "promotion hot quota soak artifact written",
    payload.summary.passed,
    `${HOT_QUOTA_SOAK_ARTIFACT_FILE} waves=${payload.summary.totalWaves} attempts=${payload.summary.totalAttempts}`
  );
}

function hotQuotaCheckName(name, wave) {
  return HOT_QUOTA_SOAK_WAVES > 1 ? `${name} wave ${wave}/${HOT_QUOTA_SOAK_WAVES}` : name;
}

async function burstUntilLimited(name, requestFactory, limitedPredicate) {
  let last = null;
  for (let attempt = 1; attempt <= COUPON_ABUSE_GUARD_BURST_ATTEMPTS; attempt += 1) {
    last = await requestFactory(attempt);
    assertStatus(last, 200, `${name} attempt ${attempt}`);
    if (limitedPredicate(last)) {
      record(name, true, `attempt=${attempt}`);
      return last;
    }
  }
  record(name, false, `attempts=${COUPON_ABUSE_GUARD_BURST_ATTEMPTS}`);
  return last;
}

async function assertReserveIdempotencyKeyRequired(token) {
  const response = await promotionRequest(token, "POST", "/internal/incentives/reservations", {
    correlationId: `${RUN_ID}-reserve-missing-idempotency`,
    body: { context: runtimeContext("reserve-missing-idempotency") }
  });
  recordStatus("promotion reserve requires idempotency key", response, 400);
}

async function assertCommitIdempotencyKeyRequired(token, reservationId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/commit`, {
    correlationId: `${RUN_ID}-commit-missing-idempotency`,
    body: { externalReference: `order-${RUN_ID}-commit-missing-idempotency` }
  });
  recordStatus("promotion commit requires idempotency key", response, 400);
}

async function assertCancelIdempotencyKeyRequired(token, reservationId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/cancel`, {
    correlationId: `${RUN_ID}-cancel-missing-idempotency`,
    body: { reason: `smoke cancel missing idempotency ${RUN_ID}` }
  });
  recordStatus("promotion cancel requires idempotency key", response, 400);
}

async function assertReverseIdempotencyKeyRequired(token, redemptionId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/redemptions/${redemptionId}/reverse`, {
    correlationId: `${RUN_ID}-reverse-missing-idempotency`,
    body: { reason: `smoke reverse missing idempotency ${RUN_ID}` }
  });
  recordStatus("promotion reverse requires idempotency key", response, 400);
}

async function assertReserveIdempotencyPayloadConflict(token, originalContext, scenario) {
  const response = await promotionRequest(token, "POST", "/internal/incentives/reservations", {
    correlationId: `${RUN_ID}-${scenario}-reserve-conflict`,
    idempotencyKey: `${RUN_ID}-${scenario}-reserve`,
    body: { context: conflictingContext(originalContext, `${scenario}-reserve-conflict`) }
  });
  recordStatus("promotion reserve rejects idempotency payload conflict", response, 409);
}

async function assertCommitIdempotencyPayloadConflict(token, reservationId, scenario) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/commit`, {
    correlationId: `${RUN_ID}-${scenario}-commit-conflict`,
    idempotencyKey: `${RUN_ID}-${scenario}-commit`,
    body: { externalReference: `order-${RUN_ID}-${scenario}-commit-conflict` }
  });
  recordStatus("promotion commit rejects idempotency payload conflict", response, 409);
}

async function assertCancelIdempotencyPayloadConflict(token, reservationId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/cancel`, {
    correlationId: `${RUN_ID}-cancel-conflict`,
    idempotencyKey: `${RUN_ID}-cancel`,
    body: { reason: `smoke cancel conflict ${RUN_ID}` }
  });
  recordStatus("promotion cancel rejects idempotency payload conflict", response, 409);
}

async function assertReverseIdempotencyPayloadConflict(token, redemptionId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/redemptions/${redemptionId}/reverse`, {
    correlationId: `${RUN_ID}-reverse-conflict`,
    idempotencyKey: `${RUN_ID}-reverse`,
    body: { reason: `smoke reverse conflict ${RUN_ID}` }
  });
  recordStatus("promotion reverse rejects idempotency payload conflict", response, 409);
}

async function assertCommitCancelledReservationReturnsNotCommitted(token, reservationId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/commit`, {
    correlationId: `${RUN_ID}-commit-cancelled`,
    idempotencyKey: `${RUN_ID}-commit-cancelled`,
    body: { externalReference: `order-${RUN_ID}-commit-cancelled` }
  });
  assertStatus(response, 200, "promotion commit cancelled reservation");
  const body = response.json;
  const pass = body?.committed === false
    && body?.status === "CANCELLED"
    && body?.redemptionId == null
    && Array.isArray(body?.reasonCodes)
    && body.reasonCodes.includes("RESERVATION_CANCELLED");
  record(
    "promotion commit cancelled reservation returns not committed",
    pass,
    `status=${body?.status ?? "<missing>"} reasons=${(body?.reasonCodes ?? []).join(",") || "<missing>"}`
  );
  assertNoRedemptionForReservation(reservationId, "promotion commit cancelled reservation creates no redemption");
}

function runtimeContext(scenario) {
  return {
    tenantId: TENANT_ID,
    applicationId: APPLICATION_ID,
    profileId: `profile-${RUN_ID}-${scenario}`,
    externalReference: `order-${RUN_ID}-${scenario}`,
    channel: "WEB",
    currency: "USD",
    transaction: {
      subtotal: 200,
      shippingAmount: 0
    },
    items: [
      {
        id: `course-${scenario}`,
        type: "COURSE",
        quantity: 1,
        unitPrice: 200
      }
    ],
    attributes: {
      smoke: true,
      runId: RUN_ID,
      scenario
    }
  };
}

function runtimeContextForApplication(scenario, applicationId) {
  return {
    ...runtimeContext(scenario),
    applicationId
  };
}

function couponRuntimeContext(scenario, couponCodes) {
  return {
    ...runtimeContextForApplication(scenario, COUPON_APPLICATION_ID),
    couponCodes
  };
}

function quotaRuntimeContext(scenario, attempt) {
  return {
    ...runtimeContextForApplication(`${scenario}-${attempt}`, QUOTA_APPLICATION_ID),
    profileId: `profile-${RUN_ID}-${scenario}-${attempt}`,
    externalReference: `order-${RUN_ID}-${scenario}-${attempt}`
  };
}

function conflictingContext(context, scenario) {
  return {
    ...context,
    profileId: `${context.profileId}-${scenario}`,
    externalReference: `${context.externalReference}-${scenario}`,
    transaction: {
      ...context.transaction,
      subtotal: Number(context.transaction?.subtotal ?? 0) + 1
    },
    attributes: {
      ...(context.attributes ?? {}),
      scenario
    }
  };
}

async function evaluate(token, context) {
  const response = await promotionRequest(token, "POST", "/internal/incentives/evaluate", {
    correlationId: `${RUN_ID}-evaluate`,
    body: context
  });
  assertStatus(response, 200, "promotion evaluate");
  const body = response.json;
  if (!body?.eligible || !body.campaignId || !Array.isArray(body.effects) || body.effects.length === 0) {
    throw new Error(`promotion evaluate did not return an eligible incentive: ${redact(JSON.stringify(body ?? {}))}`);
  }
  if (expectedCampaignCode && body.campaignCode !== expectedCampaignCode) {
    throw new Error(`promotion evaluate selected ${body.campaignCode}, expected ${expectedCampaignCode}`);
  }
  record("promotion evaluate eligible", true, `campaign=${body.campaignCode} effects=${body.effects.length}`);
  return body;
}

async function couponEvaluate(token, scenario, couponCodes) {
  return promotionRequest(token, "POST", "/internal/incentives/evaluate", {
    correlationId: `${RUN_ID}-${scenario}`,
    body: couponRuntimeContext(scenario, couponCodes)
  });
}

async function couponReserve(token, scenario, couponCodes) {
  return couponReserveAttempt(token, scenario, null, couponCodes);
}

async function couponReserveAttempt(token, scenario, attempt, couponCodes) {
  const suffix = attempt == null ? "" : `-${attempt}`;
  return promotionRequest(token, "POST", "/internal/incentives/reservations", {
    correlationId: `${RUN_ID}-${scenario}${suffix}`,
    idempotencyKey: `${RUN_ID}-${scenario}${suffix}`,
    body: { context: couponRuntimeContext(scenario, couponCodes) }
  });
}

async function quotaReserveAttempt(token, scenario, attempt) {
  return promotionRequest(token, "POST", "/internal/incentives/reservations", {
    correlationId: `${RUN_ID}-${scenario}-${attempt}`,
    idempotencyKey: `${RUN_ID}-${scenario}-${attempt}`,
    body: { context: quotaRuntimeContext(scenario, attempt) }
  });
}

function assertCouponDeclineResponse(name, response, expected) {
  assertStatus(response, 200, name);
  const body = response.json;
  const pass = body?.eligible === false
    && Array.isArray(body.effects)
    && body.effects.length === 0
    && Array.isArray(body.reasonCodes)
    && body.reasonCodes.includes(expected.reason)
    && (expected.expectCampaign ? Boolean(body.campaignId) : body.campaignId == null)
    && (expected.expectCampaign ? body.campaignCode === COUPON_CAMPAIGN_CODE : body.campaignCode == null)
    && (expected.expectCoupon ? Boolean(body.couponId) : body.couponId == null);
  record(
    name,
    pass,
    `reason=${(body?.reasonCodes ?? []).join(",") || "<missing>"} campaign=${body?.campaignCode ?? "<none>"} coupon=${body?.couponId ?? "<none>"}`
  );
}

function assertCouponEligibleResponse(name, response) {
  assertStatus(response, 200, name);
  const body = response.json;
  const pass = body?.eligible === true
    && body.campaignCode === COUPON_CAMPAIGN_CODE
    && Boolean(body.couponId)
    && Array.isArray(body.effects)
    && body.effects.length > 0;
  record(
    name,
    pass,
    `campaign=${body?.campaignCode ?? "<none>"} coupon=${body?.couponId ?? "<none>"} effects=${body?.effects?.length ?? 0}`
  );
}

function assertCouponReserveDeclineResponse(name, response) {
  assertStatus(response, 200, name);
  const body = response.json;
  const pass = body?.reserved === false
    && body.reservationId == null
    && Array.isArray(body.effects)
    && body.effects.length === 0
    && Array.isArray(body.reasonCodes)
    && body.reasonCodes.includes("NO_ELIGIBLE_INCENTIVE");
  record(
    name,
    pass,
    `reason=${(body?.reasonCodes ?? []).join(",") || "<missing>"} reservation=${body?.reservationId ?? "<none>"}`
  );
}

function assertCouponEvaluateRateLimitedResponse(name, response) {
  assertStatus(response, 200, name);
  const body = response.json;
  const pass = body?.eligible === false
    && body.campaignId == null
    && body.campaignCode == null
    && body.couponId == null
    && Array.isArray(body.effects)
    && body.effects.length === 0
    && Array.isArray(body.reasonCodes)
    && body.reasonCodes.includes("RATE_LIMITED");
  record(
    name,
    pass,
    `reason=${(body?.reasonCodes ?? []).join(",") || "<missing>"} campaign=${body?.campaignCode ?? "<none>"} coupon=${body?.couponId ?? "<none>"}`
  );
}

function assertCouponReserveRateLimitedResponse(name, response) {
  assertStatus(response, 200, name);
  const body = response.json;
  const pass = body?.reserved === false
    && body.reservationId == null
    && body.campaignId == null
    && body.couponId == null
    && Array.isArray(body.effects)
    && body.effects.length === 0
    && Array.isArray(body.reasonCodes)
    && body.reasonCodes.includes("RATE_LIMITED");
  record(
    name,
    pass,
    `reason=${(body?.reasonCodes ?? []).join(",") || "<missing>"} reservation=${body?.reservationId ?? "<none>"}`
  );
}

function assertNoCouponSecretsInResponse(name, response) {
  assertNoCouponSecretsInText(name, response.text ?? "");
}

function assertNoCouponSecretsInText(name, text) {
  const needles = couponSecretNeedles();
  const leaked = needles.some((needle) => needle && String(text).includes(needle));
  record(name, !leaked, leaked ? "coupon secret leaked" : "no raw coupon/fingerprint text");
}

async function reserve(token, context, scenario) {
  const response = await promotionRequest(token, "POST", "/internal/incentives/reservations", {
    correlationId: `${RUN_ID}-${scenario}-reserve`,
    idempotencyKey: `${RUN_ID}-${scenario}-reserve`,
    body: { context }
  });
  assertStatus(response, 200, "promotion reserve");
  const body = response.json;
  if (!body?.reserved || !body.reservationId || !Array.isArray(body.effects) || body.effects.length === 0) {
    throw new Error(`promotion reserve failed: ${redact(JSON.stringify(body ?? {}))}`);
  }
  record("promotion reserve", true, `reservation=${body.reservationId}`);
  return body;
}

async function cancel(token, reservationId, scenario = "cancel") {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/cancel`, {
    correlationId: `${RUN_ID}-${scenario}`,
    idempotencyKey: `${RUN_ID}-${scenario}`,
    body: { reason: `smoke ${scenario} ${RUN_ID}` }
  });
  assertStatus(response, 200, "promotion cancel");
  const body = response.json;
  if (!body?.cancelled || !body.reservationId || !Array.isArray(body.reasonCodes)) {
    throw new Error(`promotion cancel failed: ${redact(JSON.stringify(body ?? {}))}`);
  }
  record("promotion cancel", true, `reservation=${body.reservationId}`);
  return body;
}

async function commit(token, reservationId, scenario) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/reservations/${reservationId}/commit`, {
    correlationId: `${RUN_ID}-${scenario}-commit`,
    idempotencyKey: `${RUN_ID}-${scenario}-commit`,
    body: { externalReference: `order-${RUN_ID}-${scenario}` }
  });
  assertStatus(response, 200, "promotion commit");
  const body = response.json;
  if (!body?.committed || !body.redemptionId || !Array.isArray(body.effects) || body.effects.length === 0) {
    throw new Error(`promotion commit failed: ${redact(JSON.stringify(body ?? {}))}`);
  }
  record("promotion commit", true, `redemption=${body.redemptionId}`);
  return body;
}

async function reverse(token, redemptionId) {
  const response = await promotionRequest(token, "POST", `/internal/incentives/redemptions/${redemptionId}/reverse`, {
    correlationId: `${RUN_ID}-reverse`,
    idempotencyKey: `${RUN_ID}-reverse`,
    body: { reason: `smoke reverse ${RUN_ID}` }
  });
  assertStatus(response, 200, "promotion reverse");
  const body = response.json;
  if (!body?.reversed || !body.redemptionId || !Array.isArray(body.effects) || body.effects.length === 0) {
    throw new Error(`promotion reverse failed: ${redact(JSON.stringify(body ?? {}))}`);
  }
  record("promotion reverse", true, `redemption=${body.redemptionId}`);
  return body;
}

async function promotionRequest(token, method, path, options) {
  return requestInternal(method, `${PROMOTION_URL}${path}`, {
    headers: {
      authorization: `Bearer ${token}`,
      "x-internal-authorization": `Bearer ${token}`,
      "content-type": "application/json",
      "x-correlation-id": options.correlationId,
      ...(options.idempotencyKey ? { "idempotency-key": options.idempotencyKey } : {})
    },
    body: JSON.stringify(options.body ?? {})
  });
}

async function assertOutboxPublished(redemptionId, eventType) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record(`outbox ${eventType} check skipped`, true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const result = await pollUntil(`outbox ${eventType} event published`, () => {
    const output = queryPromotion(`
      SELECT COUNT(*) || '|' || COUNT(*) FILTER (WHERE published_at IS NOT NULL)
      FROM outbox_events
      WHERE aggregate_type = 'incentive-redemption'
        AND event_type = ${sqlString(eventType)}
        AND aggregate_id = ${sqlString(redemptionId)};
    `).trim();
    const [total, published] = output.split("|").map((value) => Number(value || 0));
    return {
      pass: total === 1 && published === 1,
      detail: `total=${total} published=${published}`
    };
  });
  record(`outbox ${eventType} event published`, true, result.detail);
}

async function assertNoOpenDeadLetters() {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record("relay DLQ check skipped", true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryOutbox(
    `SELECT COUNT(*) FROM relay_dead_letters WHERE status = 'OPEN' AND service_name = ${sqlString(OUTBOX_SERVICE_NAME)};`
  ).trim();
  const count = Number(output || 0);
  record("outbox relay DLQ has no open promotion rows", count === 0, `service=${OUTBOX_SERVICE_NAME} open=${count}`);
}

async function assertReversalKeepsQuota(redemptionId) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record("reversal quota policy check skipped", true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryPromotion(`
    SELECT COALESCE(payload ->> 'quotaReleased', '')
    FROM outbox_events
    WHERE aggregate_type = 'incentive-redemption'
      AND event_type = 'incentive.redemption.reversed'
      AND aggregate_id = ${sqlString(redemptionId)}
    ORDER BY created_at DESC
    LIMIT 1;
  `).trim();
  record("reversal keeps committed quota consumed", output === "false", `quotaReleased=${output || "<missing>"}`);
}

function assertCancellationReconciliationEvidence(reservationId) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record("cancel reconciliation evidence check skipped", true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryPromotion(`
    SELECT
      COALESCE(MAX(r.status), '') AS reservation_status,
      COUNT(*) FILTER (WHERE l.entry_type = 'RESERVE') AS reserve_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'CANCEL') AS cancel_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'COMMIT') AS commit_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'REVERSE') AS reverse_count,
      COUNT(DISTINCT red.id) AS redemption_count,
      COUNT(*) FILTER (
        WHERE l.id IS NOT NULL
          AND (l.effect_json IS NULL OR jsonb_typeof(l.effect_json) <> 'array' OR jsonb_array_length(l.effect_json) = 0)
      ) AS missing_effect_count,
      COALESCE(string_agg(l.effect_json::text, ' '), '') AS evidence_json
    FROM incentive_reservations r
    LEFT JOIN incentive_ledger_entries l
      ON l.reservation_id = r.id
    LEFT JOIN incentive_redemptions red
      ON red.reservation_id = r.id
    WHERE r.id = ${sqlString(reservationId)}
      AND r.tenant_id = ${sqlString(TENANT_ID)}
      AND r.application_id = ${sqlString(APPLICATION_ID)}
    GROUP BY r.id;
  `).trim();
  const row = pipeRow(output, 8);
  const pass = row
    && row[0] === "CANCELLED"
    && numberValue(row[1]) === 1
    && numberValue(row[2]) === 1
    && numberValue(row[3]) === 0
    && numberValue(row[4]) === 0
    && numberValue(row[5]) === 0
    && numberValue(row[6]) === 0;
  record(
    "cancel reconciliation evidence is balanced",
    pass,
    row
      ? `status=${row[0]} reserve=${row[1]} cancel=${row[2]} commit=${row[3]} reverse=${row[4]} redemptions=${row[5]}`
      : "reservation=<missing>"
  );
  if (row) {
    assertNoCouponSecretsInText("cancel reconciliation evidence hides coupon secrets", row[7]);
  }
  record("cancel reconciliation quota policy releases reserved hold", Boolean(row), "policy=RELEASE_RESERVED_QUOTA");
}

function assertRedemptionReconciliationEvidence(reservationId, redemptionId) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record("redemption reconciliation evidence check skipped", true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryPromotion(`
    SELECT
      COALESCE(MAX(red.status), '') AS redemption_status,
      COUNT(*) FILTER (WHERE l.entry_type = 'RESERVE') AS reserve_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'COMMIT') AS commit_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'REVERSE') AS reverse_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'CANCEL') AS cancel_count,
      COUNT(*) FILTER (
        WHERE l.id IS NOT NULL
          AND (l.effect_json IS NULL OR jsonb_typeof(l.effect_json) <> 'array' OR jsonb_array_length(l.effect_json) = 0)
      ) AS missing_effect_count,
      COUNT(*) FILTER (
        WHERE l.entry_type = 'COMMIT'
          AND o.event_type = 'incentive.redemption.committed'
          AND o.published_at IS NOT NULL
          AND o.payload ->> 'correlationId' = ${sqlString(`${RUN_ID}-commit-commit`)}
          AND o.payload ->> 'sourceClientId' = ${sqlString(CHECKOUT_CLIENT_ID)}
      ) AS committed_outbox_count,
      COUNT(*) FILTER (
        WHERE l.entry_type = 'REVERSE'
          AND o.event_type = 'incentive.redemption.reversed'
          AND o.published_at IS NOT NULL
          AND o.payload ->> 'correlationId' = ${sqlString(`${RUN_ID}-reverse`)}
          AND o.payload ->> 'sourceClientId' = ${sqlString(CHECKOUT_CLIENT_ID)}
          AND o.payload ->> 'quotaReleased' = 'false'
      ) AS reversed_outbox_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'COMMIT' AND red.redeemed_at IS NOT NULL) AS committed_redeemed_count,
      COUNT(*) FILTER (WHERE l.entry_type = 'REVERSE' AND red.reversed_at IS NOT NULL) AS reversed_at_count,
      COALESCE(string_agg(COALESCE(l.effect_json::text, '') || ' ' || COALESCE(o.payload::text, ''), ' '), '') AS evidence_json
    FROM incentive_redemptions red
    LEFT JOIN incentive_ledger_entries l
      ON l.reservation_id = red.reservation_id
    LEFT JOIN outbox_events o
      ON o.aggregate_type = 'incentive-redemption'
     AND o.aggregate_id = cast(red.id AS text)
     AND (
            (l.entry_type = 'COMMIT' AND o.event_type = 'incentive.redemption.committed')
         OR (l.entry_type = 'REVERSE' AND o.event_type = 'incentive.redemption.reversed')
     )
    WHERE red.id = ${sqlString(redemptionId)}
      AND red.reservation_id = ${sqlString(reservationId)}
      AND red.tenant_id = ${sqlString(TENANT_ID)}
      AND red.application_id = ${sqlString(APPLICATION_ID)}
    GROUP BY red.id;
  `).trim();
  const row = pipeRow(output, 11);
  const pass = row
    && row[0] === "REVERSED"
    && numberValue(row[1]) === 1
    && numberValue(row[2]) === 1
    && numberValue(row[3]) === 1
    && numberValue(row[4]) === 0
    && numberValue(row[5]) === 0
    && numberValue(row[6]) === 1
    && numberValue(row[7]) === 1
    && numberValue(row[8]) === 1
    && numberValue(row[9]) === 1;
  record(
    "redemption reconciliation evidence is balanced",
    pass,
    row
      ? `status=${row[0]} reserve=${row[1]} commit=${row[2]} reverse=${row[3]} commitOutbox=${row[6]} reverseOutbox=${row[7]}`
      : "redemption=<missing>"
  );
  if (row) {
    assertNoCouponSecretsInText("redemption reconciliation evidence hides coupon secrets", row[10]);
  }
  record(
    "redemption reconciliation quota policy keeps committed reversal consumed",
    Boolean(row) && numberValue(row[7]) === 1,
    "policy=NO_RELEASE_ON_COMMITTED_REVERSAL"
  );
}

function assertNoRedemptionForReservation(reservationId, name) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record(`${name} check skipped`, true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_redemptions
    WHERE reservation_id = ${sqlString(reservationId)};
  `).trim();
  const count = Number(output || 0);
  record(name, count === 0, `reservation=${reservationId} redemptions=${count}`);
}

function assertHotQuotaConcurrencyEvidence(scenario, winningReservationId, wave = 1) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record(
      hotQuotaCheckName("hot quota concurrency evidence check skipped", wave),
      true,
      "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true"
    );
    return true;
  }
  const output = queryPromotion(`
    WITH campaign AS (
      SELECT id
      FROM incentive_campaigns
      WHERE tenant_id = ${sqlString(TENANT_ID)}
        AND application_id = ${sqlString(QUOTA_APPLICATION_ID)}
        AND code = ${sqlString(QUOTA_CAMPAIGN_CODE)}
      LIMIT 1
    ),
    run_reservations AS (
      SELECT r.*
      FROM incentive_reservations r
      JOIN campaign c ON c.id = r.campaign_id
      WHERE r.tenant_id = ${sqlString(TENANT_ID)}
        AND r.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
        AND r.profile_id LIKE ${sqlString(`profile-${RUN_ID}-${scenario}-%`)}
        AND r.external_reference LIKE ${sqlString(`order-${RUN_ID}-${scenario}-%`)}
    )
    SELECT
      COUNT(*) AS reservation_count,
      COUNT(*) FILTER (WHERE id = ${sqlString(winningReservationId)}) AS winning_reservation_count,
      COUNT(*) FILTER (WHERE status = 'RESERVED') AS reserved_count,
      (
        SELECT COUNT(*)
        FROM incentive_ledger_entries l
        JOIN run_reservations r ON r.id = l.reservation_id
        WHERE l.entry_type = 'RESERVE'
      ) AS reserve_ledger_count,
      (
        SELECT COUNT(*)
        FROM incentive_quota_counters q
        JOIN campaign c ON c.id::text = q.scope_id
        WHERE q.tenant_id = ${sqlString(TENANT_ID)}
          AND q.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
          AND q.scope_type = 'CAMPAIGN'
          AND q.profile_id = '*'
          AND q.used_count = 1
          AND q.limit_count = 1
      ) AS counter_count,
      (
        SELECT COUNT(*)
        FROM incentive_quota_counters q
        WHERE q.tenant_id = ${sqlString(TENANT_ID)}
          AND q.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
          AND (q.used_count < 0 OR q.used_count > q.limit_count)
      ) AS invariant_violations
    FROM run_reservations;
  `).trim();
  const row = pipeRow(output, 6);
  const pass = row
    && numberValue(row[0]) === 1
    && numberValue(row[1]) === 1
    && numberValue(row[2]) === 1
    && numberValue(row[3]) === 1
    && numberValue(row[4]) === 1
    && numberValue(row[5]) === 0;
  record(
    hotQuotaCheckName("hot quota concurrency DB evidence is bounded", wave),
    pass,
    row
      ? `reservations=${row[0]} winner=${row[1]} reserved=${row[2]} reserveLedger=${row[3]} counter=${row[4]} violations=${row[5]}`
      : "evidence=<missing>"
  );
  return Boolean(pass);
}

function assertHotQuotaReleaseEvidence(scenario, winningReservationId, wave = 1) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record(
      hotQuotaCheckName("hot quota release evidence check skipped", wave),
      true,
      "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true"
    );
    return true;
  }
  const output = queryPromotion(`
    WITH campaign AS (
      SELECT id
      FROM incentive_campaigns
      WHERE tenant_id = ${sqlString(TENANT_ID)}
        AND application_id = ${sqlString(QUOTA_APPLICATION_ID)}
        AND code = ${sqlString(QUOTA_CAMPAIGN_CODE)}
      LIMIT 1
    ),
    run_reservations AS (
      SELECT r.*
      FROM incentive_reservations r
      JOIN campaign c ON c.id = r.campaign_id
      WHERE r.tenant_id = ${sqlString(TENANT_ID)}
        AND r.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
        AND r.profile_id LIKE ${sqlString(`profile-${RUN_ID}-${scenario}-%`)}
        AND r.external_reference LIKE ${sqlString(`order-${RUN_ID}-${scenario}-%`)}
    )
    SELECT
      COUNT(*) FILTER (WHERE id = ${sqlString(winningReservationId)} AND status = 'CANCELLED') AS cancelled_winner,
      (
        SELECT COUNT(*)
        FROM incentive_quota_counters q
        JOIN campaign c ON c.id::text = q.scope_id
        WHERE q.tenant_id = ${sqlString(TENANT_ID)}
          AND q.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
          AND q.scope_type = 'CAMPAIGN'
          AND q.profile_id = '*'
          AND q.used_count = 0
          AND q.limit_count = 1
      ) AS released_counter_count,
      (
        SELECT COUNT(*)
        FROM incentive_ledger_entries l
        JOIN run_reservations r ON r.id = l.reservation_id
        WHERE l.entry_type = 'CANCEL'
      ) AS cancel_ledger_count,
      (
        SELECT COUNT(*)
        FROM incentive_quota_counters q
        WHERE q.tenant_id = ${sqlString(TENANT_ID)}
          AND q.application_id = ${sqlString(QUOTA_APPLICATION_ID)}
          AND (q.used_count < 0 OR q.used_count > q.limit_count)
      ) AS invariant_violations
    FROM run_reservations;
  `).trim();
  const row = pipeRow(output, 4);
  const pass = row
    && numberValue(row[0]) === 1
    && numberValue(row[1]) === 1
    && numberValue(row[2]) === 1
    && numberValue(row[3]) === 0;
  record(
    hotQuotaCheckName("hot quota fixture cleanup releases winning reservation", wave),
    pass,
    row
      ? `cancelled=${row[0]} releasedCounter=${row[1]} cancelLedger=${row[2]} violations=${row[3]}`
      : "evidence=<missing>"
  );
  return Boolean(pass);
}

function assertNoReservationForScenario(applicationId, scenario, name) {
  if (!dbChecksAvailable() && ALLOW_SKIP_DB_CHECKS) {
    record(`${name} check skipped`, true, "PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true");
    return;
  }
  const output = queryPromotion(`
    SELECT COUNT(*)
    FROM incentive_reservations
    WHERE tenant_id = ${sqlString(TENANT_ID)}
      AND application_id = ${sqlString(applicationId)}
      AND profile_id = ${sqlString(`profile-${RUN_ID}-${scenario}`)}
      AND external_reference = ${sqlString(`order-${RUN_ID}-${scenario}`)};
  `).trim();
  const count = Number(output || 0);
  record(name, count === 0, `application=${applicationId} scenario=${scenario} reservations=${count}`);
}

async function requestInternal(method, url, options = {}) {
  if (LOCAL) {
    return dockerCurl(method, url, options);
  }
  return directHttp(method, url, options);
}

async function directHttp(method, url, options = {}) {
  const response = await fetch(url, {
    method,
    headers: options.headers ?? {},
    body: options.form ? new URLSearchParams(options.form) : options.body
  });
  const text = await response.text();
  return {
    status: response.status,
    text,
    json: parseJson(text)
  };
}

async function dockerCurl(method, url, options = {}) {
  const args = [
    "run",
    "--rm",
    "--network",
    DOCKER_NETWORK,
    CURL_IMAGE,
    "-sS",
    "-w",
    "\\n__HTTP_STATUS__:%{http_code}\\n",
    "-X",
    method
  ];
  for (const [key, value] of Object.entries(options.headers ?? {})) {
    if (value !== undefined && value !== null && String(value).trim()) {
      args.push("-H", `${key}: ${value}`);
    }
  }
  if (options.form) {
    for (const [key, value] of Object.entries(options.form)) {
      args.push("--data-urlencode", `${key}=${value ?? ""}`);
    }
  } else if (options.body !== undefined) {
    args.push("--data-binary", options.body);
  }
  args.push(url);
  const output = await runAsync("docker", args, { sensitive: true });
  const marker = "\n__HTTP_STATUS__:";
  const markerIndex = output.lastIndexOf(marker);
  if (markerIndex < 0) {
    throw new Error(`curl output did not include HTTP status for ${url}`);
  }
  const text = output.slice(0, markerIndex);
  const status = Number(output.slice(markerIndex + marker.length).trim());
  return {
    status,
    text,
    json: parseJson(text)
  };
}

function queryPromotion(sql) {
  return queryDb(PROMOTION_DB, process.env.PROMOTION_SMOKE_PROMOTION_DATABASE_URL, sql);
}

function queryOutbox(sql) {
  return queryDb(OUTBOX_DB, process.env.PROMOTION_SMOKE_OUTBOX_DATABASE_URL, sql);
}

function queryDb(databaseName, databaseUrl, sql) {
  if (LOCAL) {
    return run("docker", [
      "exec",
      POSTGRES_CONTAINER,
      "psql",
      "-U",
      PSQL_USER,
      "-d",
      databaseName,
      "-tA",
      "-v",
      "ON_ERROR_STOP=1",
      "-c",
      sql
    ]);
  }
  if (databaseUrl) {
    return run(process.env.PROMOTION_SMOKE_PSQL_BIN ?? "psql", [
      databaseUrl,
      "-tA",
      "-v",
      "ON_ERROR_STOP=1",
      "-c",
      sql
    ], { sensitive: true });
  }
  throw new Error("database checks are not configured");
}

function ensureLocalTooling() {
  run("docker", ["version", "--format", "{{.Server.Version}}"]);
  queryPromotion("SELECT 1;");
  queryOutbox("SELECT 1;");
}

function dbChecksAvailable() {
  return LOCAL
    || (Boolean(process.env.PROMOTION_SMOKE_PROMOTION_DATABASE_URL)
      && Boolean(process.env.PROMOTION_SMOKE_OUTBOX_DATABASE_URL));
}

async function pollUntil(name, probe) {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let last = { pass: false, detail: "not checked" };
  while (Date.now() <= deadline) {
    last = probe();
    if (last.pass) {
      return last;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(`${name} did not pass within ${POLL_TIMEOUT_MS}ms (${last.detail})`);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024
  });
  if (result.status !== 0) {
    const stderr = redact(result.stderr || "");
    const stdout = redact(result.stdout || "");
    const detail = options.sensitive
      ? `${command} failed with exit ${result.status}`
      : `${command} ${args.join(" ")} failed with exit ${result.status}`;
    throw new Error(`${detail}\n${stderr || stdout}`.trim());
  }
  return result.stdout;
}

function runAsync(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: ["ignore", "pipe", "pipe"]
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        const detail = options.sensitive
          ? `${command} failed with exit ${code}`
          : `${command} ${args.join(" ")} failed with exit ${code}`;
        reject(new Error(`${detail}\n${redact(stderr || stdout)}`.trim()));
        return;
      }
      resolve(stdout);
    });
  });
}

function assertStatus(response, expected, name) {
  if (response.status !== expected) {
    throw new Error(`${name} expected HTTP ${expected}, got ${response.status}: ${redact(response.text).slice(0, 500)}`);
  }
}

function assertEqual(actual, expected, name) {
  if (actual !== expected) {
    throw new Error(`${name} expected ${expected}, got ${actual}`);
  }
}

function record(name, pass, detail = "") {
  checks.push({ name, pass, detail });
  const status = pass ? "PASS" : "FAIL";
  console.log(`[${status}] ${name}${detail ? ` - ${detail}` : ""}`);
}

function recordStatus(name, response, expected) {
  record(name, response.status === expected, `status=${response.status}`);
}

function recordStatusIn(name, response, expectedStatuses) {
  record(name, expectedStatuses.includes(response.status), `status=${response.status}`);
}

function recordForbiddenDetail(name, response, expectedDetail) {
  const detail = String(response.json?.detail ?? response.text ?? "");
  record(
    name,
    response.status === 403 && detail.includes(expectedDetail),
    `status=${response.status}${detail ? ` detail=${redact(detail).slice(0, 180)}` : ""}`
  );
}

function pipeRow(output, expectedColumns) {
  if (!output || !output.trim()) {
    return null;
  }
  const row = output.split("\n")[0].split("|");
  if (row.length < expectedColumns) {
    throw new Error(`expected at least ${expectedColumns} psql columns, got ${row.length}: ${redact(output)}`);
  }
  return row;
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function percentile(values, percentileRank) {
  if (values.length === 0) {
    return 0;
  }
  const index = Math.min(
    values.length - 1,
    Math.max(0, Math.ceil(values.length * percentileRank) - 1)
  );
  return values[index];
}

async function writeJsonArtifact(file, payload) {
  const artifactPath = path.resolve(process.cwd(), file);
  await fs.mkdir(path.dirname(artifactPath), { recursive: true });
  await fs.writeFile(artifactPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function printSummary(facts) {
  const failed = checks.filter((check) => !check.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
  console.log(`campaign=${facts.campaign}`);
  console.log(`cancelledReservationId=${facts.cancelledReservationId}`);
  console.log(`reservationId=${facts.reservationId}`);
  console.log(`redemptionId=${facts.redemptionId}`);
  console.log(`reversedRedemptionId=${facts.reversedRedemptionId}`);
  console.log(`couponInventoryReady=${couponInventoryReadyChecks.join(",") || "not-checked"}`);
  if (failed.length > 0) {
    process.exitCode = 1;
    for (const check of failed) {
      console.error(`FAILED: ${check.name} ${check.detail}`);
    }
    return;
  }
  console.log("Promotion runtime smoke passed");
}

function parseJson(text) {
  if (!text || !text.trim()) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function decodeJwtPayload(jwt) {
  const [, payload] = String(jwt).split(".");
  if (!payload) {
    throw new Error("access_token is not a JWT");
  }
  return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
}

function scopeSet(claims) {
  const scopes = new Set();
  if (claims.scope) {
    for (const scope of String(claims.scope).split(/\s+/)) {
      if (scope) {
        scopes.add(scope);
      }
    }
  }
  if (Array.isArray(claims.scp)) {
    for (const scope of claims.scp) {
      scopes.add(String(scope));
    }
  }
  return scopes;
}

function uuidFromText(value) {
  const hex = crypto.createHash("sha256").update(value).digest("hex").slice(0, 32);
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function negativeApplicationId(suffix) {
  const suffixPart = `neg-${suffix}`;
  const normalized = String(APPLICATION_ID || "app").trim() || "app";
  const maxLength = 80;
  if (normalized.length + suffixPart.length + 1 <= maxLength) {
    return `${normalized}-${suffixPart}`;
  }
  return `${normalized.slice(0, maxLength - suffixPart.length - 1)}-${suffixPart}`;
}

function negativeApplicationEnv(name, suffix) {
  const value = process.env[name];
  if (value && String(value).trim()) {
    return String(value).trim();
  }
  return LOCAL ? negativeApplicationId(suffix) : "";
}

function couponApplicationEnv(name) {
  const value = process.env[name];
  if (value && String(value).trim()) {
    return String(value).trim();
  }
  return LOCAL ? negativeApplicationId("coupon-abuse") : "";
}

function quotaApplicationEnv(name) {
  const value = process.env[name];
  if (value && String(value).trim()) {
    return String(value).trim();
  }
  return LOCAL ? negativeApplicationId("hot-quota") : "";
}

function couponCodeEnv(name, prefix) {
  const value = process.env[name];
  if (value && String(value).trim()) {
    return String(value).trim();
  }
  return LOCAL ? couponCode(prefix) : "";
}

function couponCode(prefix) {
  return `${prefix}-${RUN_ID}`.replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 80);
}

function couponHolderProfileId() {
  return `profile-${RUN_ID}-coupon-owner`;
}

function normalizeCouponCode(code) {
  return String(code ?? "").trim().normalize("NFKC").toUpperCase();
}

function couponMask(normalizedCode) {
  if (!normalizedCode || !normalizedCode.trim()) {
    return "";
  }
  if (normalizedCode.length <= 4) {
    return "****";
  }
  const suffixStart = Math.max(2, normalizedCode.length - 2);
  return `${normalizedCode.slice(0, 2)}****${normalizedCode.slice(suffixStart)}`;
}

function currentCouponStoragePrefix() {
  return `hmac-sha256:${COUPON_FINGERPRINT_KEY_ID}:`;
}

function couponFingerprint(normalizedCode) {
  const digest = crypto
    .createHmac("sha256", COUPON_FINGERPRINT_PEPPER)
    .update(normalizedCode)
    .digest("hex");
  return `${currentCouponStoragePrefix()}${digest}`;
}

function couponSecretNeedles() {
  const values = new Set();
  for (const raw of Object.values(COUPON_CODES)) {
    if (!raw) {
      continue;
    }
    const normalized = normalizeCouponCode(raw);
    values.add(raw);
    values.add(normalized);
    values.add(couponFingerprint(normalized));
  }
  return [...values].filter((value) => value && value.length >= 4);
}

function sameStringSet(actual, expected) {
  const actualSet = new Set((actual ?? []).map((value) => String(value).toLowerCase()));
  const expectedSet = new Set((expected ?? []).map((value) => String(value).toLowerCase()));
  return actualSet.size === expectedSet.size
    && [...expectedSet].every((value) => actualSet.has(value));
}

function scenarioFromCorrelation(correlationId) {
  const prefix = `${RUN_ID}-`;
  return String(correlationId).startsWith(prefix)
    ? String(correlationId).slice(prefix.length)
    : String(correlationId);
}

function sqlString(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function firstNonBlank(...values) {
  for (const value of values) {
    if (value && String(value).trim()) {
      return String(value).trim();
    }
  }
  return "";
}

function sanitizeRunId(value) {
  return String(value)
    .trim()
    .replace(/[^A-Za-z0-9._-]/g, "-")
    .slice(0, 72);
}

function positiveInt(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback;
}

function parseStatuses(raw) {
  return new Set(String(raw)
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value)));
}

function requireValue(name, value) {
  if (!value || !String(value).trim()) {
    throw new Error(`${name} is required`);
  }
}

function redact(value) {
  let redacted = String(value);
  for (const needle of couponSecretNeedles()) {
    redacted = redacted.split(needle).join("<redacted-coupon>");
  }
  return redacted
    .replace(/Bearer\s+[A-Za-z0-9._-]+/gi, "Bearer <redacted>")
    .replace(/("access_token"\s*:\s*")[^"]+/gi, "$1<redacted>")
    .replace(/(client_secret=)[^&\s]+/gi, "$1<redacted>");
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((error) => {
  console.error(`Promotion runtime smoke failed: ${redact(error.message)}`);
  process.exit(1);
});
