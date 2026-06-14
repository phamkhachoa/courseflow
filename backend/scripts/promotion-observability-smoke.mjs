#!/usr/bin/env node

/**
 * Promotion observability smoke gate.
 *
 * Runs after promotion-runtime-smoke against a Prometheus that scrapes the deployed cluster.
 * It proves the core pilot targets are up, promotion runtime metrics appeared after the smoke,
 * and no critical promotion/outbox/token-converter alert is firing.
 */

import fs from "node:fs/promises";
import path from "node:path";

const PROMETHEUS_URL = stripTrailingSlash(
  process.env.PROMOTION_SMOKE_PROMETHEUS_URL
    ?? process.env.COURSEFLOW_PROMETHEUS_URL
    ?? "http://localhost:19090"
);
const GATEWAY_URL = stripTrailingSlash(
  process.env.PROMOTION_SMOKE_GATEWAY_URL
    ?? process.env.COURSEFLOW_API_URL
    ?? "http://localhost:28080/api"
);
const ADMIN_ACCESS_TOKEN = firstNonBlank(process.env.PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN);
const TIMEOUT_MS = positiveInt(process.env.PROMOTION_OBSERVABILITY_TIMEOUT_MS, 90_000);
const POLL_INTERVAL_MS = positiveInt(process.env.PROMOTION_OBSERVABILITY_POLL_INTERVAL_MS, 5_000);
const REQUIRED_TARGETS = parseTargets(process.env.PROMOTION_OBSERVABILITY_REQUIRED_TARGETS);
const RUNTIME_RECENT_WINDOW = process.env.PROMOTION_OBSERVABILITY_RUNTIME_RECENT_WINDOW ?? "15m";
const CUTOVER_WINDOW = process.env.PROMOTION_OBSERVABILITY_CUTOVER_WINDOW
  ?? process.env.PROMOTION_CUTOVER_EVIDENCE_WINDOW
  ?? "24h";
const CUTOVER_ENVIRONMENT = process.env.PROMOTION_CUTOVER_ENVIRONMENT
  ?? process.env.PROMOTION_SMOKE_MODE
  ?? "unknown";
const MIN_RECENT_RUNTIME_OPERATIONS = positiveInt(process.env.PROMOTION_OBSERVABILITY_MIN_RECENT_RUNTIME_OPERATIONS, 1);
const REQUIRED_COUPON_MATCH_RESULTS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_COUPON_MATCH_RESULTS,
  "not_supplied,not_found,inactive,not_started,expired,holder_mismatch,matched"
);
const REQUIRED_COUPON_ABUSE_GUARD_RESULTS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_COUPON_ABUSE_GUARD_RESULTS,
  "limited"
);
const ADMIN_OPERATION_RATE_GUARD_REQUIRED =
  (process.env.PROMOTION_OBSERVABILITY_ADMIN_OPERATION_RATE_GUARD_REQUIRED
    ?? process.env.PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED
    ?? "false").toLowerCase() === "true";
const REQUIRED_ADMIN_OPERATION_RATE_GUARD_RESULTS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_RESULTS,
  ADMIN_OPERATION_RATE_GUARD_REQUIRED ? "allowed" : ""
);
const REQUIRED_ADMIN_OPERATION_RATE_GUARD_OPERATIONS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_OPERATIONS,
  ADMIN_OPERATION_RATE_GUARD_REQUIRED ? "coupon_import_dry_run" : ""
);
const REQUIRED_COUPON_LOOKUP_STORAGE_PATHS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS,
  "current_hmac"
);
const FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS = csvList(
  process.env.PROMOTION_OBSERVABILITY_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS,
  "legacy_sha,legacy_raw"
);
const MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE = nonNegativeInt(
  process.env.PROMOTION_OBSERVABILITY_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE,
  0
);
const REQUIRED_QUOTA_METRICS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_QUOTA_METRICS,
  "consumed:campaign,exhausted:campaign,released:campaign"
).map(parseQuotaMetric);
const REQUIRED_QUOTA_FALLBACK_RESULTS = csvList(
  process.env.PROMOTION_OBSERVABILITY_REQUIRED_QUOTA_FALLBACK_RESULTS,
  "candidate_conflict,exhausted"
);
const MAX_OUTBOX_UNPUBLISHED = nonNegativeInt(process.env.PROMOTION_OBSERVABILITY_MAX_OUTBOX_UNPUBLISHED, 0);
const MAX_OUTBOX_OLDEST_AGE_SECONDS = nonNegativeInt(
  process.env.PROMOTION_OBSERVABILITY_MAX_OUTBOX_OLDEST_AGE_SECONDS,
  0
);
const CRITICAL_ALERTS = process.env.PROMOTION_OBSERVABILITY_CRITICAL_ALERTS
  ?? "PromotionOutboxLagHigh|PromotionOutboxBacklogHigh|OutboxRelayPromotionDeadLettersOpen|"
  + "OutboxRelayPublishFailuresHigh|PromotionMetricsRefreshFailing|TokenConverterFailuresDetected|"
  + "TokenConverterJwksFailuresDetected";
const CUTOVER_EVIDENCE_ENABLED =
  (process.env.PROMOTION_CUTOVER_EVIDENCE_ENABLED ?? "false").toLowerCase() === "true";
const CUTOVER_EVIDENCE_SCOPES = parseCutoverScopes(process.env.PROMOTION_CUTOVER_EVIDENCE_SCOPES ?? "");
const CUTOVER_EVIDENCE_FILE = process.env.PROMOTION_CUTOVER_EVIDENCE_FILE
  ?? process.env.PROMOTION_OBSERVABILITY_CUTOVER_EVIDENCE_FILE
  ?? "promotion-cutover-evidence.json";
const CUTOVER_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS = csvList(
  process.env.PROMOTION_CUTOVER_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS,
  REQUIRED_COUPON_LOOKUP_STORAGE_PATHS.join(",")
);
const CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS = csvList(
  process.env.PROMOTION_CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS,
  FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.join(",")
);
const CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE = nonNegativeNumber(
  process.env.PROMOTION_CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE,
  MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE
);

const checks = [];

async function main() {
  console.log("CourseFlow Promotion Observability smoke");
  console.log(`Prometheus: ${PROMETHEUS_URL}`);

  for (const target of REQUIRED_TARGETS) {
    await assertTargetUp(target);
  }
  await assertPromotionRuntimeMetricsPresent();
  await assertPromotionRuntimeMetricsRecentlyIncreased();
  await assertCouponMatchMetricsRecentlyIncreased();
  await assertCouponLookupMetricsRecentlyIncreased();
  await assertForbiddenCouponLookupMetricsNotIncreased();
  await assertCouponAbuseGuardMetricsRecentlyIncreased();
  await assertAdminOperationRateGuardMetricsRecentlyIncreased();
  await assertQuotaMetricsRecentlyIncreased();
  await assertQuotaFallbackMetricsRecentlyIncreased();
  await assertPromotionOutboxBacklogHealthy();
  await assertPromotionDeadLettersZero();
  await assertNoCriticalAlerts();
  await assertCouponCutoverEvidence();
  printSummary();
}

async function assertTargetUp(target) {
  const query = `up{job="${target.job}",instance="${target.instance}"}`;
  const result = await pollUntil(`target ${target.name} up`, async () => {
    const vector = await queryPrometheus(query);
    const value = vectorValue(vector);
    return {
      pass: value === 1,
      detail: `job=${target.job} instance=${target.instance} value=${value ?? "<missing>"}`
    };
  });
  record(`Prometheus target up ${target.name}`, true, result.detail);
}

async function assertPromotionRuntimeMetricsPresent() {
  const query = 'sum(promotion_runtime_operation_total{operation=~"reserve|commit|cancel|reverse"})';
  const result = await pollUntil("promotion runtime metric present", async () => {
    const vector = await queryPrometheus(query);
    const value = vectorValue(vector);
    return {
      pass: Number.isFinite(value) && value > 0,
      detail: `promotion_runtime_operation_total=${value ?? "<missing>"}`
    };
  });
  record("promotion runtime metrics present", true, result.detail);
}

async function assertPromotionRuntimeMetricsRecentlyIncreased() {
  const query = `sum(increase(promotion_runtime_operation_total{operation=~"reserve|commit|cancel|reverse"}[${RUNTIME_RECENT_WINDOW}]))`;
  const result = await pollUntil("promotion runtime metric recent increase", async () => {
    const vector = await queryPrometheus(query);
    const value = vectorValue(vector);
    return {
      pass: Number.isFinite(value) && value >= MIN_RECENT_RUNTIME_OPERATIONS,
      detail: `increase=${value ?? "<missing>"} window=${RUNTIME_RECENT_WINDOW}`
    };
  });
  record("promotion runtime metrics increased recently", true, result.detail);
}

async function assertCouponMatchMetricsRecentlyIncreased() {
  for (const resultName of REQUIRED_COUPON_MATCH_RESULTS) {
    const selector = `promotion_coupon_match_total{result="${resultName}",coupon_required="true"}`;
    const result = await pollUntil(`coupon match metric recent evidence ${resultName}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `result=${resultName} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion coupon match metric recent evidence ${resultName}`, true, result.detail);
  }
}

async function assertCouponLookupMetricsRecentlyIncreased() {
  for (const storagePath of REQUIRED_COUPON_LOOKUP_STORAGE_PATHS) {
    const selector = `promotion_coupon_lookup_total{storage_path="${storagePath}"}`;
    const result = await pollUntil(`coupon lookup metric recent evidence ${storagePath}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `storagePath=${storagePath} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion coupon lookup metric recent evidence ${storagePath}`, true, result.detail);
  }
}

async function assertForbiddenCouponLookupMetricsNotIncreased() {
  if (FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.length === 0) {
    return;
  }
  const pattern = FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.map(escapePromRegex).join("|");
  const query = `sum(increase(promotion_coupon_lookup_total{storage_path=~"${pattern}"}[${RUNTIME_RECENT_WINDOW}]))`;
  const vector = await queryPrometheus(query);
  const increase = vectorValueOrZero(vector);
  record(
    "promotion forbidden coupon lookup metrics did not increase",
    increase <= MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE,
    `storagePaths=${FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.join(",")} increase=${increase} max=${MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE} window=${RUNTIME_RECENT_WINDOW}`
  );
}

async function assertCouponAbuseGuardMetricsRecentlyIncreased() {
  for (const resultName of REQUIRED_COUPON_ABUSE_GUARD_RESULTS) {
    const selector = `promotion_coupon_abuse_guard_total{result="${resultName}"}`;
    const result = await pollUntil(`coupon abuse guard metric recent evidence ${resultName}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `result=${resultName} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion coupon abuse guard metric recent evidence ${resultName}`, true, result.detail);
  }
}

async function assertAdminOperationRateGuardMetricsRecentlyIncreased() {
  for (const resultName of REQUIRED_ADMIN_OPERATION_RATE_GUARD_RESULTS) {
    const selector = `promotion_admin_operation_rate_guard_total{result="${resultName}"}`;
    const result = await pollUntil(`admin operation rate guard metric recent evidence ${resultName}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `result=${resultName} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion admin operation rate guard metric recent evidence ${resultName}`, true, result.detail);
  }
  for (const operationName of REQUIRED_ADMIN_OPERATION_RATE_GUARD_OPERATIONS) {
    const selector = `promotion_admin_operation_rate_guard_total{operation="${operationName}"}`;
    const result = await pollUntil(`admin operation rate guard metric recent evidence ${operationName}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `operation=${operationName} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion admin operation rate guard metric recent evidence ${operationName}`, true, result.detail);
  }
}

async function assertQuotaMetricsRecentlyIncreased() {
  for (const metric of REQUIRED_QUOTA_METRICS) {
    const selector = `promotion_quota_total{result="${metric.result}",scope_type="${metric.scopeType}"}`;
    const result = await pollUntil(`quota metric recent evidence ${metric.result}:${metric.scopeType}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `result=${metric.result} scopeType=${metric.scopeType} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion quota metric recent evidence ${metric.result}:${metric.scopeType}`, true, result.detail);
  }
}

async function assertQuotaFallbackMetricsRecentlyIncreased() {
  for (const resultName of REQUIRED_QUOTA_FALLBACK_RESULTS) {
    const selector = `promotion_quota_reserve_fallback_total{result="${resultName}"}`;
    const result = await pollUntil(`quota reserve fallback metric recent evidence ${resultName}`, async () => {
      const evidence = await recentCounterEvidence(selector, RUNTIME_RECENT_WINDOW);
      return {
        pass: evidence.increase > 0 || evidence.recentMax > 0,
        detail: `result=${resultName} increase=${evidence.increase} recentMax=${evidence.recentMax} window=${RUNTIME_RECENT_WINDOW}`
      };
    });
    record(`promotion quota reserve fallback metric recent evidence ${resultName}`, true, result.detail);
  }
}

async function recentCounterEvidence(selector, window) {
  const increase = vectorValueOrZero(await queryPrometheus(`sum(increase(${selector}[${window}]))`));
  const recentMax = vectorValueOrZero(await queryPrometheus(`sum(max_over_time(${selector}[${window}]))`));
  return { increase, recentMax };
}

async function assertPromotionOutboxBacklogHealthy() {
  const unpublishedQuery = 'sum(promotion_outbox_unpublished{aggregate_type="incentive-redemption"})';
  const ageQuery = 'max(promotion_outbox_oldest_unpublished_age_seconds{aggregate_type="incentive-redemption"})';
  const result = await pollUntil("promotion outbox backlog healthy", async () => {
    const unpublished = vectorValueOrZero(await queryPrometheus(unpublishedQuery));
    const oldestAge = vectorValueOrZero(await queryPrometheus(ageQuery));
    return {
      pass: unpublished <= MAX_OUTBOX_UNPUBLISHED && oldestAge <= MAX_OUTBOX_OLDEST_AGE_SECONDS,
      detail: `unpublished=${unpublished} oldestAgeSeconds=${oldestAge}`
    };
  });
  record("promotion outbox backlog within smoke thresholds", true, result.detail);
}

async function assertPromotionDeadLettersZero() {
  const query = 'sum(outbox_relay_dead_letters_open{service="promotion"})';
  const result = await pollUntil("promotion relay DLQ zero", async () => {
    const open = vectorValueOrZero(await queryPrometheus(query));
    return {
      pass: open === 0,
      detail: `open=${open}`
    };
  });
  record("outbox relay has zero open promotion dead letters", true, result.detail);
}

async function assertNoCriticalAlerts() {
  const query = `ALERTS{alertstate="firing",alertname=~"${CRITICAL_ALERTS}"}`;
  const vector = await queryPrometheus(query);
  const firing = vector.map((sample) => sample.metric?.alertname ?? "unknown");
  record("no critical promotion observability alerts firing", firing.length === 0,
    firing.length === 0 ? "none" : firing.join(","));
}

async function assertCouponCutoverEvidence() {
  if (!CUTOVER_EVIDENCE_ENABLED) {
    record("promotion coupon cutover evidence artifact skipped", true,
      "PROMOTION_CUTOVER_EVIDENCE_ENABLED=false");
    return;
  }
  requireValue("PROMOTION_SMOKE_GATEWAY_URL", GATEWAY_URL);
  requireValue("PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN", ADMIN_ACCESS_TOKEN);
  if (CUTOVER_EVIDENCE_SCOPES.length === 0) {
    throw new Error("PROMOTION_CUTOVER_EVIDENCE_SCOPES must include at least one name|tenantId|applicationId scope");
  }

  const storageEvidence = await cutoverStorageEvidence();
  const scopeEvidence = [];
  for (const scope of CUTOVER_EVIDENCE_SCOPES) {
    scopeEvidence.push(await cutoverInventoryEvidence(scope));
  }

  const artifact = {
    schemaVersion: 1,
    artifactType: "promotion_coupon_hmac_cutover_evidence",
    environment: CUTOVER_ENVIRONMENT,
    runId: process.env.PROMOTION_SMOKE_RUN_ID ?? process.env.GITHUB_RUN_ID ?? null,
    generatedAt: new Date().toISOString(),
    git: {
      sha: process.env.GITHUB_SHA ?? null,
      ref: process.env.GITHUB_REF_NAME ?? process.env.GITHUB_REF ?? null,
      workflowRunId: process.env.GITHUB_RUN_ID ?? null
    },
    window: CUTOVER_WINDOW,
    gatewayUrl: GATEWAY_URL,
    prometheusUrl: PROMETHEUS_URL,
    requiredStoragePaths: CUTOVER_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS,
    forbiddenStoragePaths: CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS,
    maxForbiddenLookupIncrease: CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE,
    storageEvidence,
    scopes: scopeEvidence,
    redactionEvidence: redactionEvidence(scopeEvidence),
    observabilityChecks: {
      passed: checks.filter((check) => check.pass).length,
      failed: checks.filter((check) => !check.pass).length,
      failures: checks.filter((check) => !check.pass)
        .map((check) => ({ name: check.name, detail: check.detail }))
    },
    decision: cutoverDecision(storageEvidence, scopeEvidence)
  };
  await writeJsonArtifact(CUTOVER_EVIDENCE_FILE, artifact);
  record("promotion coupon cutover evidence artifact written", true, CUTOVER_EVIDENCE_FILE);
}

async function cutoverStorageEvidence() {
  const required = [];
  for (const storagePath of CUTOVER_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS) {
    const selector = `promotion_coupon_lookup_total{storage_path="${storagePath}"}`;
    const evidence = await recentCounterEvidence(selector, CUTOVER_WINDOW);
    const pass = evidence.increase > 0 || evidence.recentMax > 0;
    record(
      `promotion cutover lookup evidence ${storagePath}`,
      pass,
      `increase=${evidence.increase} recentMax=${evidence.recentMax} window=${CUTOVER_WINDOW}`
    );
    required.push({ storagePath, ...evidence, pass });
  }

  const forbiddenPattern = CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.map(escapePromRegex).join("|");
  const forbiddenIncrease = forbiddenPattern
    ? vectorValueOrZero(await queryPrometheus(
      `sum(increase(promotion_coupon_lookup_total{storage_path=~"${forbiddenPattern}"}[${CUTOVER_WINDOW}]))`))
    : 0;
  const forbiddenPass = forbiddenIncrease <= CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE;
  record(
    "promotion cutover forbidden legacy lookup window",
    forbiddenPass,
    `storagePaths=${CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS.join(",") || "<none>"} increase=${forbiddenIncrease} max=${CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE} window=${CUTOVER_WINDOW}`
  );
  return {
    required,
    forbidden: {
      storagePaths: CUTOVER_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS,
      increase: forbiddenIncrease,
      maxAllowedIncrease: CUTOVER_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE,
      pass: forbiddenPass
    }
  };
}

async function cutoverInventoryEvidence(scope) {
  const query = new URLSearchParams();
  query.set("tenantId", scope.tenantId);
  query.set("applicationId", scope.applicationId);
  query.set("activeOnly", String(scope.activeOnly));
  if (scope.campaignId) {
    query.set("campaignId", scope.campaignId);
  }
  const response = await gatewayAdminJson(
    "GET",
    `/admin/v1/incentives/coupons/storage-inventory?${query.toString()}`
  );
  const rawText = JSON.stringify(response);
  const counts = storageCounts(response.items);
  const total = Number(response.totalCoupons ?? 0);
  const legacy = Number(response.legacyCoupons ?? -1);
  const malformed = Number(response.malformedCoupons ?? -1);
  const readyPass = response.tenantId === scope.tenantId
    && response.applicationId === scope.applicationId
    && (scope.campaignId ? response.campaignId === scope.campaignId : response.campaignId == null)
    && response.activeOnly === scope.activeOnly
    && response.fallbackDisableReady === true
    && legacy === 0
    && malformed === 0
    && (!scope.requireNonEmpty || total > 0);
  record(
    `promotion cutover inventory ready ${scope.name}`,
    readyPass,
    `tenant=${scope.tenantId} application=${scope.applicationId} campaign=${scope.campaignId ?? "<all>"} total=${total} legacy=${legacy} malformed=${malformed}`
  );
  const leakHits = forbiddenInventoryTerms().filter((term) => rawText.includes(term));
  record(
    `promotion cutover inventory redacts internals ${scope.name}`,
    leakHits.length === 0,
    leakHits.length === 0 ? "redacted" : `terms=${leakHits.join(",")}`
  );
  return {
    name: scope.name,
    tenantId: response.tenantId,
    applicationId: response.applicationId,
    campaignId: response.campaignId ?? null,
    activeOnly: response.activeOnly,
    requireNonEmpty: scope.requireNonEmpty,
    legacyFallbackEnabled: response.legacyFallbackEnabled,
    fallbackDisableReady: response.fallbackDisableReady,
    totalCoupons: total,
    legacyCoupons: legacy,
    malformedCoupons: malformed,
    storageCounts: counts,
    generatedAt: response.generatedAt ?? null,
    redaction: {
      forbiddenTermsPresent: leakHits.length > 0,
      forbiddenTerms: leakHits
    },
    pass: readyPass && leakHits.length === 0
  };
}

function cutoverDecision(storageEvidence, scopeEvidence) {
  const failureReasons = [];
  for (const item of storageEvidence.required) {
    if (!item.pass) {
      failureReasons.push(`missing required lookup evidence for ${item.storagePath}`);
    }
  }
  if (!storageEvidence.forbidden.pass) {
    failureReasons.push("forbidden legacy coupon lookup increased in the cutover window");
  }
  for (const scope of scopeEvidence) {
    if (!scope.pass) {
      failureReasons.push(`inventory scope is not cutover-ready: ${scope.name}`);
    }
  }
  for (const check of checks.filter((item) => !item.pass)) {
    failureReasons.push(`observability check failed: ${check.name}`);
  }
  return {
    status: failureReasons.length === 0 ? "pass" : "fail",
    cutoverApproved: failureReasons.length === 0,
    failureReasons
  };
}

function redactionEvidence(scopeEvidence) {
  const forbiddenTerms = new Set();
  for (const scope of scopeEvidence) {
    for (const term of scope.redaction?.forbiddenTerms ?? []) {
      forbiddenTerms.add(term);
    }
  }
  return {
    rawCouponCodesPresent: false,
    normalizedCodesPresent: forbiddenTerms.has("normalizedCode"),
    fingerprintsPresent: forbiddenTerms.has("fingerprint") || forbiddenTerms.has("hmac-sha256"),
    holderProfileIdsPresent: forbiddenTerms.has("holderProfileId"),
    forbiddenInventoryTerms: [...forbiddenTerms]
  };
}

async function gatewayAdminJson(method, path) {
  const response = await fetch(`${GATEWAY_URL}${path}`, {
    method,
    headers: {
      accept: "application/json",
      authorization: `Bearer ${ADMIN_ACCESS_TOKEN}`
    }
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${method} ${path} failed HTTP ${response.status}: ${text.slice(0, 300)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${method} ${path} did not return JSON: ${text.slice(0, 300)}`);
  }
}

async function queryPrometheus(query) {
  const response = await fetch(`${PROMETHEUS_URL}/api/v1/query?query=${encodeURIComponent(query)}`);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Prometheus query failed HTTP ${response.status}: ${text.slice(0, 300)}`);
  }
  const body = JSON.parse(text);
  if (body.status !== "success") {
    throw new Error(`Prometheus query was not successful: ${text.slice(0, 300)}`);
  }
  return body.data?.result ?? [];
}

async function writeJsonArtifact(file, payload) {
  const directory = path.dirname(file);
  if (directory && directory !== ".") {
    await fs.mkdir(directory, { recursive: true });
  }
  await fs.writeFile(file, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function pollUntil(name, probe) {
  const deadline = Date.now() + TIMEOUT_MS;
  let last = { pass: false, detail: "not checked" };
  while (Date.now() <= deadline) {
    last = await probe();
    if (last.pass) {
      return last;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(`${name} did not pass within ${TIMEOUT_MS}ms (${last.detail})`);
}

function vectorValue(vector) {
  if (!Array.isArray(vector) || vector.length === 0 || !Array.isArray(vector[0].value)) {
    return null;
  }
  const value = Number(vector[0].value[1]);
  return Number.isFinite(value) ? value : null;
}

function vectorValueOrZero(vector) {
  const value = vectorValue(vector);
  return Number.isFinite(value) ? value : 0;
}

function parseTargets(raw) {
  const value = raw && raw.trim()
    ? raw
    : "api-gateway|courseflow-api-gateway|api-gateway:8080,"
      + "identity-token-converter-service|courseflow-services|identity-token-converter-service:8080,"
      + "promotion-service|courseflow-services|promotion-service:8080,"
      + "outbox-relay|courseflow-services|outbox-relay:8080";
  return value.split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const [name, job, instance] = entry.split("|").map((part) => part?.trim());
      if (!name || !job || !instance) {
        throw new Error("PROMOTION_OBSERVABILITY_REQUIRED_TARGETS entries must be name|job|instance");
      }
      return { name, job, instance };
    });
}

function parseQuotaMetric(entry) {
  const [result, scopeType] = entry.split(":").map((part) => part?.trim());
  if (!result || !scopeType) {
    throw new Error("PROMOTION_OBSERVABILITY_REQUIRED_QUOTA_METRICS entries must be result:scope_type");
  }
  return { result, scopeType };
}

function parseCutoverScopes(raw) {
  if (!raw || !raw.trim()) {
    return [];
  }
  return raw.split(";")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const [name, tenantId, applicationId, campaignId, activeOnly = "true", requireNonEmpty = "false"] =
        entry.split("|").map((part) => part?.trim() ?? "");
      if (!name || !tenantId || !applicationId) {
        throw new Error(
          "PROMOTION_CUTOVER_EVIDENCE_SCOPES entries must be name|tenantId|applicationId|campaignId?|activeOnly?|requireNonEmpty?"
        );
      }
      return {
        name,
        tenantId,
        applicationId,
        campaignId: campaignId || null,
        activeOnly: activeOnly.toLowerCase() !== "false",
        requireNonEmpty: requireNonEmpty.toLowerCase() === "true"
      };
    });
}

function storageCounts(items) {
  const counts = {};
  if (!Array.isArray(items)) {
    return counts;
  }
  for (const item of items) {
    if (item?.storageFormat) {
      counts[item.storageFormat] = Number(item.count ?? 0);
    }
  }
  return counts;
}

function forbiddenInventoryTerms() {
  return ["normalizedCode", "fingerprint", "couponId", "holderProfileId", "hmac-sha256"];
}

function csvList(raw, fallback) {
  const value = raw && raw.trim() ? raw : fallback;
  return value.split(",").map((entry) => entry.trim()).filter(Boolean);
}

function escapePromRegex(value) {
  return value.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&");
}

function record(name, pass, detail = "") {
  checks.push({ name, pass, detail });
  const status = pass ? "PASS" : "FAIL";
  console.log(`[${status}] ${name}${detail ? ` - ${detail}` : ""}`);
}

function printSummary() {
  const failed = checks.filter((check) => !check.pass);
  console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
  if (failed.length > 0) {
    process.exitCode = 1;
    for (const check of failed) {
      console.error(`FAILED: ${check.name} ${check.detail}`);
    }
    return;
  }
  console.log("Promotion observability smoke passed");
}

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function positiveInt(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback;
}

function nonNegativeInt(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? Math.floor(value) : fallback;
}

function nonNegativeNumber(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function firstNonBlank(...values) {
  for (const value of values) {
    if (value && String(value).trim()) {
      return String(value).trim();
    }
  }
  return "";
}

function requireValue(name, value) {
  if (!value || !String(value).trim()) {
    throw new Error(`${name} is required`);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((error) => {
  console.error(`Promotion observability smoke failed: ${error.message}`);
  process.exit(1);
});
