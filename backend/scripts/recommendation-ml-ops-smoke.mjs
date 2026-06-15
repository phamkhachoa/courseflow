#!/usr/bin/env node

/**
 * Recommendation ML ops smoke gate.
 *
 * Proves the production-facing Recommendation ML operational surface:
 * health/readiness, disabled docs/OpenAPI, Prometheus metrics, internal JWT
 * rejection, core ops reads, active-model readiness, analytics read-model sync,
 * disabled sync training, queued worker training, and the maker-checker guards
 * for model activation.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const SERVICE_URL = stripTrailingSlash(
  process.env.RECOMMENDATION_ML_SMOKE_URL
    ?? process.env.RECOMMENDATION_ML_SERVICE_URL
    ?? "http://localhost:8080"
);
const PROMETHEUS_URL = stripTrailingSlash(
  process.env.RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL
    ?? process.env.COURSEFLOW_PROMETHEUS_URL
    ?? ""
);
const ANALYTICS_URL = stripTrailingSlash(
  process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_URL
    ?? process.env.ANALYTICS_SERVICE_URL
    ?? ""
);
const SMOKE_ENVIRONMENT = firstNonBlank(
  process.env.RECOMMENDATION_ML_SMOKE_ENVIRONMENT,
  process.env.COURSEFLOW_ENVIRONMENT,
  process.env.ENVIRONMENT_NAME
);
const REQUIRE_HTTPS_URLS = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_REQUIRE_HTTPS_URLS,
  false
);
const REJECT_LOCAL_URLS = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_REJECT_LOCAL_URLS,
  false
);
const TIMEOUT_MS = positiveInt(process.env.RECOMMENDATION_ML_SMOKE_TIMEOUT_MS, 60_000);
const POLL_INTERVAL_MS = positiveInt(
  process.env.RECOMMENDATION_ML_SMOKE_POLL_INTERVAL_MS,
  5_000
);
const REQUIRE_ACTIVE_MODEL = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_REQUIRE_ACTIVE_MODEL,
  true
);
const MUTATION_FLOW_ENABLED = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED,
  false
);
const EXPECT_SYNC_TRAIN_DISABLED = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED,
  false
);
const REQUIRE_PREMINTED_TOKENS = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS,
  false
);
const ANALYTICS_CLIENT_METRIC_REQUIRED = boolEnv(
  process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED,
  false
);
const ANALYTICS_CLIENT_METRIC_WINDOW = prometheusRangeWindow(
  firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW, "30m"),
  "RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW"
);
const MAX_QUEUED_AGE_SECONDS = nonNegativeNumber(
  process.env.RECOMMENDATION_ML_SMOKE_MAX_QUEUED_AGE_SECONDS,
  900
);
const MAX_RUNNING_AGE_SECONDS = nonNegativeNumber(
  process.env.RECOMMENDATION_ML_SMOKE_MAX_RUNNING_AGE_SECONDS,
  3600
);
const MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS = nonNegativeNumber(
  process.env.RECOMMENDATION_ML_SMOKE_MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS,
  86400
);
const MAX_TOKEN_TTL_SECONDS = positiveInt(
  process.env.RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS,
  900
);
const REQUIRED_TARGETS = parseTargets(process.env.RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS);
const CRITICAL_ALERTS = process.env.RECOMMENDATION_ML_SMOKE_CRITICAL_ALERTS
  ?? "RecommendationMlNoActiveModel|RecommendationMlTrainingJobsStuck|"
  + "RecommendationMlMigrationNotReady|RecommendationMlMetricsRefreshFailing|"
  + "RecommendationMlConsumerFallbackElevated";
const REQUIRED_ALERTS = csvList(
  process.env.RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS
    ?? "RecommendationMlNoActiveModel,RecommendationMlTrainingJobsStuck,"
      + "RecommendationMlMigrationNotReady,RecommendationMlMetricsRefreshFailing,"
      + "RecommendationMlConsumerFallbackElevated"
);
const EVIDENCE_FILE = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_EVIDENCE_FILE);
const sourceProvenance = buildSourceProvenance();
const urlPolicyEvidence = {
  requireHttps: REQUIRE_HTTPS_URLS,
  rejectLocalUrls: REJECT_LOCAL_URLS,
  endpoints: {
    recommendationMl: urlPolicyEndpointEvidence(SERVICE_URL),
    analytics: urlPolicyEndpointEvidence(ANALYTICS_URL),
    prometheus: urlPolicyEndpointEvidence(PROMETHEUS_URL),
  },
};

const TRAIN_TOKEN = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN)
  || mintLocalInternalToken("recommendation-ml-smoke-train", [
    "internal:recommendation-ml:train",
  ]);
const INFER_TOKEN = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_INFER_TOKEN)
  || mintLocalInternalToken("recommendation-ml-smoke-infer", [
    "internal:recommendation-ml:infer",
  ]);
const OPS_TOKEN = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_TOKEN)
  || mintLocalInternalToken("recommendation-ml-smoke-ops", [
    "internal:recommendation-ml:ops",
  ]);
const OPS_CHECKER_TOKEN = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN)
  || mintLocalInternalToken("recommendation-ml-smoke-ops-checker", [
    "internal:recommendation-ml:ops",
  ]);
const ANALYTICS_MODEL_TOKEN = firstNonBlank(
  process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN
) || mintLocalInternalToken("recommendation-ml-smoke-analytics-model", [
  "internal:analytics:model-write",
]);
const WILDCARD_SCOPE_TOKEN = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_WILDCARD_TOKEN)
  || (allPremintedTokensConfigured()
    ? ""
    : mintLocalInternalToken("recommendation-ml-smoke-wildcard", ["*"]));
const tokenEvidence = {
  source: allPremintedTokensConfigured() ? "preminted" : "local_hs256",
  premintedRequired: REQUIRE_PREMINTED_TOKENS,
  trainConfigured: Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN)),
  inferConfigured: Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_INFER_TOKEN)),
  opsConfigured: Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_TOKEN)),
  opsCheckerConfigured: Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN)),
  analyticsModelRequired: ANALYTICS_CLIENT_METRIC_REQUIRED,
  analyticsModelConfigured: Boolean(
    firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN)
  ),
  maxTtlSeconds: MAX_TOKEN_TTL_SECONDS,
  tokens: {
    train: jwtClaimEvidence(TRAIN_TOKEN, ["internal:recommendation-ml:train"]),
    infer: jwtClaimEvidence(INFER_TOKEN, ["internal:recommendation-ml:infer"]),
    ops: jwtClaimEvidence(OPS_TOKEN, ["internal:recommendation-ml:ops"]),
    opsChecker: jwtClaimEvidence(OPS_CHECKER_TOKEN, ["internal:recommendation-ml:ops"]),
    analyticsModel: jwtClaimEvidence(ANALYTICS_MODEL_TOKEN, ["internal:analytics:model-write"]),
  },
};
tokenEvidence.actorSeparation = actorSeparationEvidence(
  tokenEvidence.tokens.ops,
  tokenEvidence.tokens.opsChecker
);

const checks = [];
const activeModelEvidence = {
  required: REQUIRE_ACTIVE_MODEL,
  status: "not_checked",
  trainingRunId: null,
  modelVersion: null,
  algorithm: null,
  activatedAt: null,
};
const prometheusEvidence = {
  configured: Boolean(PROMETHEUS_URL),
  requiredTargets: REQUIRED_TARGETS,
  requiredAlerts: REQUIRED_ALERTS,
  targetResults: [],
  alertRuleResults: [],
  criticalAlertsQuery: CRITICAL_ALERTS,
  criticalAlertsFiring: [],
};
const analyticsEvidence = {
  configured: Boolean(ANALYTICS_URL),
  required: ANALYTICS_CLIENT_METRIC_REQUIRED,
  serviceUrl: ANALYTICS_URL || null,
  materializeStatus: ANALYTICS_URL ? "not_checked" : "not_configured",
  materializeHttpStatus: null,
  trainingRunId: null,
  modelVersion: null,
  responseStatus: null,
  engine: null,
  pairCount: null,
  generatedRelatedRows: null,
  fallbackReason: null,
  metricWindow: ANALYTICS_CLIENT_METRIC_WINDOW,
  availableMetricValue: null,
  fallbackMetricValue: null,
};
const mutationEvidence = {
  enabled: MUTATION_FLOW_ENABLED,
  status: MUTATION_FLOW_ENABLED ? "not_started" : "disabled",
  smokeRunId: null,
  trainingRunId: null,
  modelVersion: null,
  approvalId: null,
  trainingRunStatus: null,
  activationRequestStatus: null,
  cleanupAttempted: false,
  cleanupStatus: null,
};

async function main() {
  console.log("CourseFlow Recommendation ML ops smoke");
  console.log(`service=${SERVICE_URL}`);
  if (PROMETHEUS_URL) {
    console.log(`prometheus=${PROMETHEUS_URL}`);
  }
  if (ANALYTICS_URL) {
    console.log(`analytics=${ANALYTICS_URL}`);
  }
  if (SMOKE_ENVIRONMENT) {
    console.log(`environment=${SMOKE_ENVIRONMENT}`);
  }
  assertUrlPolicy();
  requireValue("RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN or COURSEFLOW_INTERNAL_JWT_SECRET", TRAIN_TOKEN);
  requireValue("RECOMMENDATION_ML_SMOKE_INFER_TOKEN or COURSEFLOW_INTERNAL_JWT_SECRET", INFER_TOKEN);
  requireValue("RECOMMENDATION_ML_SMOKE_OPS_TOKEN or COURSEFLOW_INTERNAL_JWT_SECRET", OPS_TOKEN);
  if (REQUIRE_PREMINTED_TOKENS) {
    record(
      "recommendation ml smoke uses pre-minted internal tokens",
      allPremintedTokensConfigured(),
      `source=${tokenEvidence.source}`
    );
  }
  if (ANALYTICS_CLIENT_METRIC_REQUIRED) {
    record(
      "recommendation ml analytics service URL is configured",
      Boolean(ANALYTICS_URL),
      `analyticsUrl=${ANALYTICS_URL || "<missing>"}`
    );
    record(
      "recommendation ml analytics model token is configured",
      Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN)),
      `configured=${tokenEvidence.analyticsModelConfigured}`
    );
  }
  assertInternalTokenClaims();
  if (MUTATION_FLOW_ENABLED) {
    requireValue(
      "RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN or COURSEFLOW_INTERNAL_JWT_SECRET",
      OPS_CHECKER_TOKEN
    );
  }

  await assertServiceHealth();
  await assertDocumentationSurfaceDisabled();
  await assertReadiness();
  await assertMetrics();
  await assertInvalidInternalJwtRejected();
  await assertScopeSeparation();
  await assertWildcardScopeRejected();
  await assertSyncTrainingDisabled();
  await assertTrainingInputValidation();
  await assertOpsReadSurface();
  await assertActiveModelSurface();
  await assertAnalyticsActiveModelSync();
  await assertMakerCheckerMutationFlow();
  await assertPrometheusSurface();
  printSummary();
}

async function assertServiceHealth() {
  const response = await httpJson("/health", { expectedStatuses: [200] });
  record(
    "recommendation ml health is UP",
    response.body?.status === "UP",
    `status=${response.body?.status ?? "<missing>"}`
  );
}

async function assertDocumentationSurfaceDisabled() {
  const docs = await httpText("/internal/recommendation-ml/docs", {
    expectedStatuses: [404],
  });
  record(
    "recommendation ml FastAPI docs are disabled",
    docs.status === 404,
    `status=${docs.status}`
  );
  const openapi = await httpText("/internal/recommendation-ml/openapi.json", {
    expectedStatuses: [404],
  });
  record(
    "recommendation ml OpenAPI schema is disabled",
    openapi.status === 404,
    `status=${openapi.status}`
  );
  const redoc = await httpText("/redoc", { expectedStatuses: [404] });
  record(
    "recommendation ml redoc is disabled",
    redoc.status === 404,
    `status=${redoc.status}`
  );
}

async function assertReadiness() {
  const response = await httpJson("/actuator/health", { expectedStatuses: [200] });
  const components = response.body?.components ?? {};
  record(
    "recommendation ml readiness is UP",
    response.body?.status === "UP",
    `status=${response.body?.status ?? "<missing>"}`
  );
  record(
    "recommendation ml migration readiness is UP",
    components.migration?.status === "UP",
    `migration=${components.migration?.status ?? "<missing>"}`
  );
  if (REQUIRE_ACTIVE_MODEL) {
    record(
      "recommendation ml active model readiness is UP",
      components.activeModel?.status === "UP",
      `activeModel=${components.activeModel?.status ?? "<missing>"}`
    );
  }
  if (MUTATION_FLOW_ENABLED) {
    record(
      "recommendation ml activation governance requires approval before mutation smoke",
      components.activationGovernance?.status === "UP"
        && components.activationGovernance?.requiresApprovalForTrainedModels === true,
      `activationGovernance=${components.activationGovernance?.status ?? "<missing>"} `
        + `requiresApproval=${
          components.activationGovernance?.requiresApprovalForTrainedModels ?? "<missing>"
        }`
    );
  }
}

async function assertMetrics() {
  const response = await httpText("/actuator/prometheus", { expectedStatuses: [200] });
  const metrics = response.body;
  const migrationReady = metricValue(metrics, "courseflow_recommendation_ml_migration_ready");
  const refreshSuccess = metricValue(
    metrics,
    "courseflow_recommendation_ml_metrics_refresh_total",
    { result: "success" }
  );
  const refreshErrors = metricValue(
    metrics,
    "courseflow_recommendation_ml_metrics_refresh_total",
    { result: "error" }
  ) ?? 0;
  const staleRunning = metricValue(
    metrics,
    "courseflow_recommendation_ml_training_stale_running_runs"
  );
  const oldestQueuedAge = metricValue(
    metrics,
    "courseflow_recommendation_ml_training_oldest_queued_age_seconds"
  ) ?? 0;
  const oldestRunningAge = metricValue(
    metrics,
    "courseflow_recommendation_ml_training_oldest_running_age_seconds"
  ) ?? 0;
  const pendingActivationApprovals = metricValue(
    metrics,
    "courseflow_recommendation_ml_pending_activation_approvals"
  );
  const oldestPendingActivationApprovalAge = metricValue(
    metrics,
    "courseflow_recommendation_ml_oldest_pending_activation_approval_age_seconds"
  ) ?? 0;

  record("recommendation ml metrics refresh succeeded", refreshSuccess > 0,
    `success=${refreshSuccess ?? "<missing>"}`);
  record("recommendation ml metrics refresh has no scrape-time errors", refreshErrors === 0,
    `errors=${refreshErrors}`);
  record("recommendation ml migration metric is ready", migrationReady === 1,
    `migration_ready=${migrationReady ?? "<missing>"}`);
  record("recommendation ml stale running jobs are zero", staleRunning === 0,
    `stale_running=${staleRunning ?? "<missing>"}`);
  record(
    "recommendation ml queued age within threshold",
    oldestQueuedAge <= MAX_QUEUED_AGE_SECONDS,
    `oldestQueuedAge=${oldestQueuedAge} max=${MAX_QUEUED_AGE_SECONDS}`
  );
  record(
    "recommendation ml running age within threshold",
    oldestRunningAge <= MAX_RUNNING_AGE_SECONDS,
    `oldestRunningAge=${oldestRunningAge} max=${MAX_RUNNING_AGE_SECONDS}`
  );
  record(
    "recommendation ml pending activation approval metric is present",
    pendingActivationApprovals !== undefined,
    `pendingActivationApprovals=${pendingActivationApprovals ?? "<missing>"}`
  );
  record(
    "recommendation ml pending activation approval age within threshold",
    oldestPendingActivationApprovalAge <= MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS,
    `oldestPendingActivationApprovalAge=${oldestPendingActivationApprovalAge} `
      + `max=${MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS}`
  );

  if (REQUIRE_ACTIVE_MODEL) {
    const activePresent = metricValue(
      metrics,
      "courseflow_recommendation_ml_active_model_present"
    );
    const activeStale = metricValue(metrics, "courseflow_recommendation_ml_active_model_stale");
    record("recommendation ml active model metric is present", activePresent === 1,
      `active_model_present=${activePresent ?? "<missing>"}`);
    record("recommendation ml active model is not stale", activeStale === 0,
      `active_model_stale=${activeStale ?? "<missing>"}`);
  }
}

async function assertSyncTrainingDisabled() {
  if (!EXPECT_SYNC_TRAIN_DISABLED) {
    record(
      "recommendation ml sync training disabled smoke skipped",
      true,
      "RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED is false"
    );
    return;
  }
  const trainingRunId = crypto.randomUUID();
  const response = await httpJson("/internal/recommendation-ml/related-courses:train", {
    method: "POST",
    headers: { ...authHeaders(TRAIN_TOKEN), "Content-Type": "application/json" },
    expectedStatuses: [403],
    body: JSON.stringify({
      trainingRunId,
      requestedModelVersion: `sync-disabled-smoke-${Date.now().toString(36)}`,
      minSupport: 1,
      maxRelatedPerCourse: 4,
      interactions: [],
    }),
  });
  record(
    "recommendation ml synchronous training endpoint is disabled",
    response.status === 403,
    `status=${response.status}`
  );
}

async function assertTrainingInputValidation() {
  const trainingRunId = crypto.randomUUID();
  const response = await httpJson("/internal/recommendation-ml/related-courses:enqueue", {
    method: "POST",
    headers: { ...authHeaders(TRAIN_TOKEN), "Content-Type": "application/json" },
    expectedStatuses: [400],
    body: JSON.stringify({
      trainingRunId,
      requestedModelVersion: `invalid-event-smoke-${Date.now().toString(36)}`,
      minSupport: 1,
      maxRelatedPerCourse: 4,
      interactions: [
        {
          principalId: "smoke-invalid-event-learner",
          courseId: "30000000-0000-0000-0000-000000000001",
          eventType: "PURCHASE",
        },
      ],
    }),
  });
  record(
    "recommendation ml training input rejects unsupported event type",
    response.status === 400,
    `status=${response.status}`
  );
}

async function assertInvalidInternalJwtRejected() {
  const response = await httpJson("/internal/recommendation-ml/models", {
    expectedStatuses: [403],
    headers: { Authorization: "Bearer invalid.internal.jwt" },
  });
  record(
    "recommendation ml rejects invalid internal JWT",
    response.status === 403,
    `status=${response.status}`
  );
  const metrics = await httpText("/actuator/prometheus", { expectedStatuses: [200] });
  const invalidJwtRejections = metricValue(
    metrics.body,
    "courseflow_recommendation_ml_internal_auth_rejections_total",
    { reason: "invalid_jwt" }
  );
  record(
    "recommendation ml invalid internal JWT rejection metric increments",
    invalidJwtRejections !== undefined && invalidJwtRejections > 0,
    `invalidJwtRejections=${invalidJwtRejections ?? "<missing>"}`
  );
}

async function assertScopeSeparation() {
  const missingTrainingRunId = "40000000-0000-0000-0000-000000000099";
  const inferOnlyOpsAttempt = await httpJson("/internal/recommendation-ml/models", {
    headers: authHeaders(INFER_TOKEN),
    expectedStatuses: [403],
  });
  record(
    "recommendation ml ops surface rejects infer-only token",
    inferOnlyOpsAttempt.status === 403,
    `status=${inferOnlyOpsAttempt.status}`
  );

  const trainOnlyActiveModelAttempt = await httpJson(
    "/internal/recommendation-ml/models/active",
    {
      headers: authHeaders(TRAIN_TOKEN),
      expectedStatuses: [403],
    }
  );
  record(
    "recommendation ml inference surface rejects train-only token",
    trainOnlyActiveModelAttempt.status === 403,
    `status=${trainOnlyActiveModelAttempt.status}`
  );

  const opsOnlyActiveModelAttempt = await httpJson(
    "/internal/recommendation-ml/models/active",
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [403],
    }
  );
  record(
    "recommendation ml inference surface rejects ops-only token",
    opsOnlyActiveModelAttempt.status === 403,
    `status=${opsOnlyActiveModelAttempt.status}`
  );

  const opsOnlyTrainStatusAttempt = await httpJson(
    `/internal/recommendation-ml/training-runs/${missingTrainingRunId}`,
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [403],
    }
  );
  record(
    "recommendation ml training status rejects ops-only token",
    opsOnlyTrainStatusAttempt.status === 403,
    `status=${opsOnlyTrainStatusAttempt.status}`
  );

  const inferOnlyTrainStatusAttempt = await httpJson(
    `/internal/recommendation-ml/training-runs/${missingTrainingRunId}`,
    {
      headers: authHeaders(INFER_TOKEN),
      expectedStatuses: [403],
    }
  );
  record(
    "recommendation ml training status rejects infer-only token",
    inferOnlyTrainStatusAttempt.status === 403,
    `status=${inferOnlyTrainStatusAttempt.status}`
  );
}

async function assertWildcardScopeRejected() {
  if (!WILDCARD_SCOPE_TOKEN) {
    record(
      "recommendation ml ops surface rejects wildcard service scope",
      true,
      "RECOMMENDATION_ML_SMOKE_WILDCARD_TOKEN not configured; prod STS policy forbids wildcard scopes"
    );
    return;
  }
  const response = await httpJson("/internal/recommendation-ml/models", {
    headers: authHeaders(WILDCARD_SCOPE_TOKEN),
    expectedStatuses: [403],
  });
  record(
    "recommendation ml ops surface rejects wildcard service scope",
    response.status === 403,
    `status=${response.status}`
  );
}

async function assertOpsReadSurface() {
  const trainOnlyOpsAttempt = await httpJson("/internal/recommendation-ml/models", {
    headers: authHeaders(TRAIN_TOKEN),
    expectedStatuses: [403],
  });
  record(
    "recommendation ml ops surface rejects train-only token",
    trainOnlyOpsAttempt.status === 403,
    `status=${trainOnlyOpsAttempt.status}`
  );

  const common = { headers: authHeaders(OPS_TOKEN), expectedStatuses: [200] };
  const runs = await httpJson("/internal/recommendation-ml/training-runs", common);
  record("recommendation ml training-runs ops list works", Array.isArray(runs.body),
    `items=${Array.isArray(runs.body) ? runs.body.length : "<not-list>"}`);

  const models = await httpJson("/internal/recommendation-ml/models", common);
  record("recommendation ml model versions ops list works", Array.isArray(models.body),
    `items=${Array.isArray(models.body) ? models.body.length : "<not-list>"}`);

  const approvals = await httpJson(
    "/internal/recommendation-ml/models/activation-requests",
    common
  );
  record("recommendation ml activation requests ops list works", Array.isArray(approvals.body),
    `items=${Array.isArray(approvals.body) ? approvals.body.length : "<not-list>"}`);

  const audits = await httpJson("/internal/recommendation-ml/models/audit", common);
  record("recommendation ml model audit ops list works", Array.isArray(audits.body),
    `items=${Array.isArray(audits.body) ? audits.body.length : "<not-list>"}`);

  const typoTrainingStatus = await httpJson(
    "/internal/recommendation-ml/training-runs?status=activ",
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [400],
    }
  );
  record(
    "recommendation ml training-runs status filter rejects typos",
    typoTrainingStatus.status === 400,
    `status=${typoTrainingStatus.status}`
  );

  const typoModelStatus = await httpJson(
    "/internal/recommendation-ml/models?status=activ",
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [400],
    }
  );
  record(
    "recommendation ml model status filter rejects typos",
    typoModelStatus.status === 400,
    `status=${typoModelStatus.status}`
  );

  const typoApprovalStatus = await httpJson(
    "/internal/recommendation-ml/models/activation-requests?status=pendng",
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [400],
    }
  );
  record(
    "recommendation ml activation request status filter rejects typos",
    typoApprovalStatus.status === 400,
    `status=${typoApprovalStatus.status}`
  );
}

async function assertActiveModelSurface() {
  const active = await httpJson("/internal/recommendation-ml/models/active", {
    headers: authHeaders(INFER_TOKEN),
    expectedStatuses: REQUIRE_ACTIVE_MODEL ? [200] : [200, 404],
  });
  if (active.status === 404) {
    activeModelEvidence.status = "not_found";
    record("recommendation ml active model optional", true, "active model is not required");
    return;
  }
  const modelVersion = active.body?.modelVersion;
  const trainingRunId = active.body?.trainingRunId;
  Object.assign(activeModelEvidence, {
    status: "found",
    trainingRunId: trainingRunId ?? null,
    modelVersion: modelVersion ?? null,
    algorithm: active.body?.algorithm ?? null,
    activatedAt: active.body?.activatedAt ?? null,
  });
  record("recommendation ml active model endpoint returns a model version",
    Boolean(modelVersion), `modelVersion=${modelVersion ?? "<missing>"}`);
  record("recommendation ml active model endpoint returns trainingRunId",
    Boolean(trainingRunId), `trainingRunId=${trainingRunId ?? "<missing>"}`);

  const directActivate = await httpJson(
    `/internal/recommendation-ml/models/${encodeURIComponent(modelVersion)}:activate`,
    {
      method: "POST",
      headers: { ...authHeaders(OPS_TOKEN), "Content-Type": "application/json" },
      expectedStatuses: [409],
      body: JSON.stringify({
        reason: "Smoke validates maker-checker direct activation guard",
        evidence: { smoke: true },
      }),
    }
  );
  record(
    "recommendation ml direct model activation is disabled",
    directActivate.status === 409,
    `status=${directActivate.status}`
  );
}

async function assertMakerCheckerMutationFlow() {
  if (!MUTATION_FLOW_ENABLED) {
    record(
      "recommendation ml maker-checker mutation smoke skipped",
      true,
      "RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED is false"
    );
    return;
  }

  const trainingRunId = crypto.randomUUID();
  const smokeRunId = `recommendation-ml-ops-smoke-${crypto.randomUUID()}`;
  const modelVersion = `smoke-${Date.now().toString(36)}-${crypto
    .randomUUID()
    .replaceAll("-", "")
    .slice(0, 12)}`;
  const smokeEvidence = { smoke: true, smokeRunId, trainingRunId, modelVersion };
  Object.assign(mutationEvidence, {
    status: "started",
    smokeRunId,
    trainingRunId,
    modelVersion,
  });
  let activationTerminal = false;
  let approvalId = null;
  let candidateCreated = false;

  try {
    const enqueueResponse = await httpJson("/internal/recommendation-ml/related-courses:enqueue", {
      method: "POST",
      headers: { ...authHeaders(TRAIN_TOKEN), "Content-Type": "application/json" },
      expectedStatuses: [202],
      body: JSON.stringify({
        trainingRunId,
        requestedModelVersion: modelVersion,
        minSupport: 1,
        maxRelatedPerCourse: 4,
        interactions: smokeTrainingInteractions(),
      }),
    });
    record(
      "recommendation ml smoke training job is queued",
      enqueueResponse.body?.status === "QUEUED",
      `status=${enqueueResponse.body?.status ?? "<missing>"} modelVersion=${modelVersion}`
    );

    const candidateResult = await pollUntil(
      "recommendation ml smoke queued training reaches pending activation",
      async () => {
        const trainingRun = await httpJson(
          `/internal/recommendation-ml/training-runs/${trainingRunId}`,
          {
            headers: authHeaders(TRAIN_TOKEN),
            expectedStatuses: [200],
          }
        );
        const runStatus = trainingRun.body?.status ?? "<missing>";
        mutationEvidence.trainingRunStatus = runStatus;
        return {
          pass: runStatus === "PENDING_ACTIVATION",
          detail: `status=${runStatus} modelVersion=${trainingRun.body?.modelVersion ?? "<missing>"}`,
          body: trainingRun.body,
        };
      }
    );
    candidateCreated = candidateResult.body?.status === "PENDING_ACTIVATION";
    record(
      "recommendation ml worker creates pending activation candidate",
      candidateCreated,
      `status=${candidateResult.body?.status ?? "<missing>"} modelVersion=${modelVersion}`
    );

    const sensitiveEvidenceRequest = await httpJson(
      `/internal/recommendation-ml/models/${encodeURIComponent(modelVersion)}:request-activation`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [400],
        body: JSON.stringify({
          reason: "Smoke validates audit evidence rejects sensitive fields",
          evidence: { ...smokeEvidence, accessToken: "Bearer should-never-be-audited" },
        }),
      }
    );
    record(
      "recommendation ml activation audit evidence rejects sensitive fields",
      sensitiveEvidenceRequest.status === 400,
      `status=${sensitiveEvidenceRequest.status}`
    );

    const activationRequest = await httpJson(
      `/internal/recommendation-ml/models/${encodeURIComponent(modelVersion)}:request-activation`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [202],
        body: JSON.stringify({
          reason: "Smoke requests activation for maker-checker rejection validation",
          evidence: smokeEvidence,
        }),
      }
    );
    approvalId = activationRequest.body?.id ?? null;
    Object.assign(mutationEvidence, {
      approvalId,
      activationRequestStatus: activationRequest.body?.status ?? null,
    });
    record(
      "recommendation ml smoke activation request is pending",
      activationRequest.body?.status === "PENDING" && Boolean(approvalId),
      `status=${activationRequest.body?.status ?? "<missing>"} approvalId=${approvalId ?? "<missing>"}`
    );

    const pendingApprovals = await httpJson(
      "/internal/recommendation-ml/models/activation-requests?status=PENDING&limit=100",
      {
        headers: authHeaders(OPS_TOKEN),
        expectedStatuses: [200],
      }
    );
    record(
      "recommendation ml smoke activation request is visible in pending ops list",
      Array.isArray(pendingApprovals.body)
        && pendingApprovals.body.some((row) => row.id === approvalId),
      `approvalId=${approvalId ?? "<missing>"}`
    );

    await assertPendingActivationMetricsDuringMutation();

    const duplicateRequest = await httpJson(
      `/internal/recommendation-ml/models/${encodeURIComponent(modelVersion)}:request-activation`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_CHECKER_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [409],
        body: JSON.stringify({
          reason: "Smoke validates duplicate pending activation guard",
          evidence: { ...smokeEvidence, duplicate: true },
        }),
      }
    );
    record(
      "recommendation ml duplicate pending activation request is rejected",
      duplicateRequest.status === 409,
      `status=${duplicateRequest.status}`
    );

    const makerSelfReject = await httpJson(
      `/internal/recommendation-ml/models/activation-requests/${approvalId}:reject`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [409],
        body: JSON.stringify({
          reason: "Smoke validates maker cannot reject own activation request",
          evidence: { ...smokeEvidence, makerSelfReview: true },
        }),
      }
    );
    record(
      "recommendation ml maker cannot reject own activation request",
      makerSelfReject.status === 409,
      `status=${makerSelfReject.status}`
    );

    const checkerReject = await httpJson(
      `/internal/recommendation-ml/models/activation-requests/${approvalId}:reject`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_CHECKER_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [200],
        body: JSON.stringify({
          reason: "Smoke rejects candidate to prove maker-checker rejection lifecycle",
          evidence: { ...smokeEvidence, checker: true },
        }),
      }
    );
    activationTerminal = checkerReject.body?.status === "REJECTED";
    mutationEvidence.activationRequestStatus = checkerReject.body?.status ?? null;
    record(
      "recommendation ml checker rejects smoke activation request",
      activationTerminal,
      `status=${checkerReject.body?.status ?? "<missing>"}`
    );

    const trainingRun = await httpJson(`/internal/recommendation-ml/training-runs/${trainingRunId}`, {
      headers: authHeaders(TRAIN_TOKEN),
      expectedStatuses: [200],
    });
    mutationEvidence.trainingRunStatus = trainingRun.body?.status ?? null;
    record(
      "recommendation ml rejected smoke candidate closes training run",
      trainingRun.body?.status === "ACTIVATION_REJECTED",
      `status=${trainingRun.body?.status ?? "<missing>"}`
    );

    const rejectedModels = await httpJson(
      "/internal/recommendation-ml/models?status=REJECTED&limit=100",
      {
        headers: authHeaders(OPS_TOKEN),
        expectedStatuses: [200],
      }
    );
    record(
      "recommendation ml rejected smoke candidate is queryable",
      Array.isArray(rejectedModels.body)
        && rejectedModels.body.some((row) => row.modelVersion === modelVersion),
      `modelVersion=${modelVersion}`
    );

    const audits = await httpJson("/internal/recommendation-ml/models/audit?limit=100", {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [200],
    });
    record(
      "recommendation ml smoke rejection writes model audit",
      Array.isArray(audits.body)
        && audits.body.some((row) => (
          row.modelVersion === modelVersion
          && row.action === "MODEL_ACTIVATION_REJECTED"
        )),
      `modelVersion=${modelVersion}`
    );
    mutationEvidence.status = "rejected";
  } finally {
    if (!activationTerminal && (approvalId || candidateCreated)) {
      await cleanupSmokeActivationRequest({ approvalId, modelVersion, smokeEvidence });
    }
  }
}

async function assertAnalyticsActiveModelSync() {
  if (!ANALYTICS_URL) {
    record(
      "recommendation ml analytics active model sync smoke skipped",
      !ANALYTICS_CLIENT_METRIC_REQUIRED,
      "RECOMMENDATION_ML_SMOKE_ANALYTICS_URL not set"
    );
    return;
  }
  requireValue(
    "RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN or COURSEFLOW_INTERNAL_JWT_SECRET",
    ANALYTICS_MODEL_TOKEN
  );

  const response = await httpJson(
    `${ANALYTICS_URL}/internal/analytics/recommendations/batch/related-course-pairs/active-model/materialize`,
    {
      method: "POST",
      headers: authHeaders(ANALYTICS_MODEL_TOKEN),
      expectedStatuses: [200],
    }
  );
  Object.assign(analyticsEvidence, {
    materializeHttpStatus: response.status,
    trainingRunId: response.body?.trainingRunId ?? null,
    modelVersion: response.body?.modelVersion ?? null,
    responseStatus: response.body?.status ?? null,
    engine: response.body?.engine ?? null,
    pairCount: response.body?.pairCount ?? null,
    generatedRelatedRows: response.body?.generatedRelatedRows ?? null,
    fallbackReason: response.body?.fallbackReason ?? null,
  });
  const available = response.body?.status === "ACTIVE"
    && response.body?.engine === "ML_ACTIVE_MODEL_SYNC"
    && Boolean(response.body?.trainingRunId)
    && Boolean(response.body?.modelVersion)
    && !response.body?.fallbackReason;
  analyticsEvidence.materializeStatus = available ? "available" : "fallback";
  record(
    "analytics active model sync endpoint materializes active ML model",
    available,
    `status=${response.body?.status ?? "<missing>"} `
      + `engine=${response.body?.engine ?? "<missing>"} `
      + `trainingRunId=${response.body?.trainingRunId ?? "<missing>"} `
      + `modelVersion=${response.body?.modelVersion ?? "<missing>"} `
      + `fallbackReason=${response.body?.fallbackReason ?? "none"}`
  );

  if (!PROMETHEUS_URL) {
    record(
      "analytics recommendation ml client Prometheus evidence skipped",
      !ANALYTICS_CLIENT_METRIC_REQUIRED,
      "RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL not set"
    );
    return;
  }

  const observed = await pollUntil(
    "analytics recommendation ml active-model client metric observed",
    async () => {
      const query = "sum("
        + "courseflow_analytics_recommendation_ml_client_requests_total"
        + '{operation="active_model",result="available"})';
      const vector = await queryPrometheus(query);
      const value = vectorValue(vector);
      analyticsEvidence.availableMetricValue = value ?? null;
      return {
        pass: value !== undefined && value > 0,
        detail: `value=${value ?? "<missing>"}`,
      };
    }
  );
  record(
    "analytics recommendation ml active-model client metric observed",
    true,
    observed.detail
  );

  const fallbackQuery = "(sum(increase("
    + "courseflow_analytics_recommendation_ml_client_requests_total"
    + `{result="fallback"}[${ANALYTICS_CLIENT_METRIC_WINDOW}])) or vector(0))`;
  const fallbackVector = await queryPrometheus(fallbackQuery);
  const fallbackValue = vectorValue(fallbackVector);
  analyticsEvidence.fallbackMetricValue = fallbackValue ?? null;
  record(
    "analytics recommendation ml client fallback metric is zero",
    fallbackValue === 0,
    `fallbackIncrease=${fallbackValue ?? "<missing>"} window=${ANALYTICS_CLIENT_METRIC_WINDOW}`
  );
}

async function cleanupSmokeActivationRequest({ approvalId, modelVersion, smokeEvidence }) {
  mutationEvidence.cleanupAttempted = true;
  mutationEvidence.status = "cleanup_started";
  try {
    let cleanupApprovalId = approvalId ?? await pendingActivationApprovalId(modelVersion);
    if (!cleanupApprovalId) {
      const created = await httpJson(
        `/internal/recommendation-ml/models/${encodeURIComponent(modelVersion)}:request-activation`,
        {
          method: "POST",
          headers: { ...authHeaders(OPS_TOKEN), "Content-Type": "application/json" },
          expectedStatuses: [202, 404, 409],
          body: JSON.stringify({
            reason: "Smoke cleanup requests activation so synthetic candidate can be rejected",
            evidence: { ...smokeEvidence, cleanup: true, cleanupRequest: true },
          }),
        }
      );
      cleanupApprovalId = created.body?.id ?? await pendingActivationApprovalId(modelVersion);
      mutationEvidence.approvalId = cleanupApprovalId ?? mutationEvidence.approvalId;
    }
    if (!cleanupApprovalId) {
      mutationEvidence.cleanupStatus = "pending_approval_not_found";
      mutationEvidence.status = "cleanup_skipped";
      console.warn(
        "[WARN] recommendation ml smoke cleanup skipped: "
        + `modelVersion=${modelVersion} pending approval id not found`
      );
      return;
    }
    const cleanup = await httpJson(
      `/internal/recommendation-ml/models/activation-requests/${cleanupApprovalId}:reject`,
      {
        method: "POST",
        headers: { ...authHeaders(OPS_CHECKER_TOKEN), "Content-Type": "application/json" },
        expectedStatuses: [200, 404, 409],
        body: JSON.stringify({
          reason: "Smoke cleanup rejects synthetic activation request after failed validation",
          evidence: { ...smokeEvidence, cleanup: true },
        }),
      }
    );
    mutationEvidence.cleanupStatus = `${cleanup.status}:${cleanup.body?.status ?? "none"}`;
    mutationEvidence.status = (
      cleanup.status === 200 && cleanup.body?.status === "REJECTED"
    ) ? "cleanup_rejected" : "cleanup_attempted";
    console.warn(
      "[WARN] recommendation ml smoke cleanup attempted: "
      + `approvalId=${cleanupApprovalId} status=${cleanup.status} `
      + `bodyStatus=${cleanup.body?.status ?? "<none>"}`
    );
  } catch (error) {
    mutationEvidence.cleanupStatus = `failed:${error.message}`;
    mutationEvidence.status = "cleanup_failed";
    console.warn(
      "[WARN] recommendation ml smoke cleanup failed: "
      + `modelVersion=${modelVersion} approvalId=${approvalId ?? "<unknown>"} `
      + `error=${error.message}`
    );
  }
}

async function pendingActivationApprovalId(modelVersion) {
  const pending = await httpJson(
    "/internal/recommendation-ml/models/activation-requests?status=PENDING&limit=100",
    {
      headers: authHeaders(OPS_TOKEN),
      expectedStatuses: [200],
    }
  );
  if (!Array.isArray(pending.body)) {
    return null;
  }
  return pending.body.find((row) => row.modelVersion === modelVersion)?.id ?? null;
}

async function assertPendingActivationMetricsDuringMutation() {
  const response = await httpText("/actuator/prometheus", { expectedStatuses: [200] });
  const pendingActivationApprovals = metricValue(
    response.body,
    "courseflow_recommendation_ml_pending_activation_approvals"
  );
  const oldestPendingActivationApprovalAge = metricValue(
    response.body,
    "courseflow_recommendation_ml_oldest_pending_activation_approval_age_seconds"
  );
  record(
    "recommendation ml pending activation approval metric observes mutation request",
    pendingActivationApprovals !== undefined && pendingActivationApprovals >= 1,
    `pendingActivationApprovals=${pendingActivationApprovals ?? "<missing>"}`
  );
  record(
    "recommendation ml pending activation approval age metric observes mutation request",
    oldestPendingActivationApprovalAge !== undefined
      && oldestPendingActivationApprovalAge >= 0,
    `oldestPendingActivationApprovalAge=${oldestPendingActivationApprovalAge ?? "<missing>"}`
  );
}

function smokeTrainingInteractions() {
  const courseA = "30000000-0000-0000-0000-0000000a0001";
  const courseB = "30000000-0000-0000-0000-0000000a0002";
  const interactions = [];
  for (let index = 1; index <= 6; index += 1) {
    interactions.push({
      principalId: `smoke-learner-${index}`,
      courseId: courseA,
      eventType: "ENROLLMENT",
    });
    interactions.push({
      principalId: `smoke-learner-${index}`,
      courseId: courseB,
      eventType: "ENROLLMENT",
    });
  }
  return interactions;
}

async function assertPrometheusSurface() {
  if (!PROMETHEUS_URL) {
    record("recommendation ml prometheus smoke skipped", true,
      "RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL not set");
    return;
  }
  for (const target of REQUIRED_TARGETS) {
    await assertTargetUp(target);
  }
  await assertRequiredAlertRulesLoaded();
  await assertNoCriticalAlerts();
}

async function assertTargetUp(target) {
  const query = `up{job="${target.job}",instance="${target.instance}"}`;
  const result = await pollUntil(`target ${target.name} up`, async () => {
    const vector = await queryPrometheus(query);
    const value = vectorValue(vector);
    return {
      pass: value === 1,
      detail: `job=${target.job} instance=${target.instance} value=${value ?? "<missing>"}`,
    };
  });
  prometheusEvidence.targetResults.push({
    name: target.name,
    job: target.job,
    instance: target.instance,
    value: 1,
  });
  record(`Prometheus target up ${target.name}`, true, result.detail);
}

async function assertRequiredAlertRulesLoaded() {
  if (REQUIRED_ALERTS.length === 0) {
    record(
      "recommendation ml required alert rule smoke skipped",
      true,
      "RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS not set"
    );
    return;
  }
  const url = `${PROMETHEUS_URL}/api/v1/rules?type=alert`;
  const response = await httpJson(url, { expectedStatuses: [200] });
  if (response.body?.status !== "success") {
    throw new Error("Prometheus alert rules query failed");
  }
  const rules = new Map();
  for (const group of response.body.data?.groups ?? []) {
    for (const rule of group.rules ?? []) {
      const ruleName = rule.name ?? rule.alert;
      if (ruleName) {
        rules.set(ruleName, rule);
      }
    }
  }
  prometheusEvidence.alertRuleResults = REQUIRED_ALERTS.map((name) => ({
    name,
    loaded: rules.has(name),
    health: rules.get(name)?.health ?? null,
  }));
  const missing = prometheusEvidence.alertRuleResults
    .filter((rule) => !rule.loaded)
    .map((rule) => rule.name);
  const unhealthy = prometheusEvidence.alertRuleResults
    .filter((rule) => rule.loaded && rule.health && rule.health !== "ok")
    .map((rule) => `${rule.name}:${rule.health}`);
  record(
    "recommendation ml required Prometheus alert rules are loaded",
    missing.length === 0 && unhealthy.length === 0,
    `missing=${missing.join(",") || "none"} unhealthy=${unhealthy.join(",") || "none"}`
  );
}

async function assertNoCriticalAlerts() {
  const query = `ALERTS{alertname=~"${CRITICAL_ALERTS}",alertstate="firing"}`;
  const vector = await queryPrometheus(query);
  prometheusEvidence.criticalAlertsFiring = vector
    .map((row) => row.metric?.alertname)
    .filter(Boolean);
  record(
    "recommendation ml critical alerts are not firing",
    vector.length === 0,
    `firing=${vector.map((row) => row.metric?.alertname).filter(Boolean).join(",") || "none"}`
  );
}

async function httpJson(path, options = {}) {
  const response = await http(path, options);
  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch (error) {
      throw new Error(`Expected JSON from ${path}: ${error.message}; body=${text.slice(0, 200)}`);
    }
  }
  return { status: response.status, body };
}

async function httpText(path, options = {}) {
  const response = await http(path, options);
  return { status: response.status, body: await response.text() };
}

async function http(path, options = {}) {
  const url = path.startsWith("http") ? path : `${SERVICE_URL}${path}`;
  const expectedStatuses = options.expectedStatuses ?? [200];
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: options.method ?? "GET",
      headers: options.headers,
      body: options.body,
      signal: controller.signal,
    });
    if (!expectedStatuses.includes(response.status)) {
      const body = await response.text();
      throw new Error(
        `${url} returned ${response.status}, expected ${expectedStatuses.join(",")}; `
        + `body=${body.slice(0, 300)}`
      );
    }
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function queryPrometheus(query) {
  const url = `${PROMETHEUS_URL}/api/v1/query?query=${encodeURIComponent(query)}`;
  const response = await httpJson(url, { expectedStatuses: [200] });
  if (response.body?.status !== "success") {
    throw new Error(`Prometheus query failed: ${query}`);
  }
  return response.body.data?.result ?? [];
}

async function pollUntil(name, fn) {
  const started = Date.now();
  let last = null;
  while (Date.now() - started <= TIMEOUT_MS) {
    last = await fn();
    if (last.pass) {
      return last;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(`${name} did not pass before timeout: ${last?.detail ?? "no detail"}`);
}

function metricValue(text, metricName, labels = {}) {
  for (const line of text.split("\n")) {
    if (!line || line.startsWith("#") || !line.startsWith(metricName)) {
      continue;
    }
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+([-+0-9.eE]+)$/);
    if (!match || match[1] !== metricName) {
      continue;
    }
    const parsedLabels = parseMetricLabels(match[2] ?? "");
    if (Object.entries(labels).every(([key, value]) => parsedLabels[key] === value)) {
      return Number(match[3]);
    }
  }
  return undefined;
}

function parseMetricLabels(raw) {
  const labels = {};
  const regex = /([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\.|[^"])*)"/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    labels[match[1]] = match[2].replace(/\\"/g, '"').replace(/\\\\/g, "\\");
  }
  return labels;
}

function vectorValue(vector) {
  if (!Array.isArray(vector) || vector.length === 0) {
    return undefined;
  }
  return Number(vector[0].value?.[1]);
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

function assertUrlPolicy() {
  const endpoints = [
    ["service", urlPolicyEvidence.endpoints.recommendationMl],
  ];
  if (ANALYTICS_CLIENT_METRIC_REQUIRED || ANALYTICS_URL) {
    endpoints.push(["analytics", urlPolicyEvidence.endpoints.analytics]);
  }
  if (PROMETHEUS_URL || ANALYTICS_CLIENT_METRIC_REQUIRED || REQUIRED_TARGETS.length > 0) {
    endpoints.push(["prometheus", urlPolicyEvidence.endpoints.prometheus]);
  }
  for (const [name, endpoint] of endpoints) {
    record(
      `recommendation ml ${name} smoke URL is configured and parseable`,
      endpoint.configured === true && endpoint.parseable === true,
      endpoint.parseError
        ? `url=${endpoint.url || "<missing>"} error=${endpoint.parseError}`
        : `scheme=${endpoint.scheme ?? "<missing>"} host=${endpoint.host ?? "<missing>"}`
    );
    if (REQUIRE_HTTPS_URLS) {
      record(
        `recommendation ml ${name} smoke URL uses HTTPS`,
        endpoint.https === true,
        `url=${endpoint.url || "<missing>"} scheme=${endpoint.scheme ?? "<missing>"}`
      );
    }
    if (REJECT_LOCAL_URLS) {
      record(
        `recommendation ml ${name} smoke URL is not local`,
        endpoint.localhost === false,
        `host=${endpoint.host ?? "<missing>"}`
      );
    }
  }
}

function urlPolicyEndpointEvidence(rawUrl) {
  const url = firstNonBlank(rawUrl);
  if (!url) {
    return {
      configured: false,
      parseable: false,
      parseError: "missing_url",
      url: null,
      scheme: null,
      host: null,
      https: false,
      localhost: false,
    };
  }
  try {
    const parsed = new URL(url);
    const host = parsed.hostname;
    return {
      configured: true,
      parseable: true,
      parseError: null,
      url,
      scheme: parsed.protocol.replace(/:$/, ""),
      host,
      https: parsed.protocol === "https:",
      localhost: isLocalHost(host),
    };
  } catch (error) {
    return {
      configured: true,
      parseable: false,
      parseError: error.message,
      url,
      scheme: null,
      host: null,
      https: false,
      localhost: false,
    };
  }
}

function isLocalHost(host) {
  const normalized = String(host ?? "").trim().toLowerCase();
  return normalized === "localhost"
    || normalized === "127.0.0.1"
    || normalized.startsWith("127.")
    || normalized === "::1"
    || normalized === "[::1]"
    || normalized === "0.0.0.0"
    || normalized === "host.docker.internal";
}

function assertInternalTokenClaims() {
  const requiredTokens = [
    ["train", tokenEvidence.tokens.train],
    ["infer", tokenEvidence.tokens.infer],
    ["ops", tokenEvidence.tokens.ops],
    ["ops checker", tokenEvidence.tokens.opsChecker],
  ];
  if (ANALYTICS_CLIENT_METRIC_REQUIRED) {
    requiredTokens.push(["analytics model", tokenEvidence.tokens.analyticsModel]);
  }
  for (const [name, token] of requiredTokens) {
    record(
      `recommendation ml ${name} token JWT claims are parseable`,
      token.parseable === true,
      token.parseError ? `error=${token.parseError}` : `issuer=${token.issuer ?? "<missing>"}`
    );
    record(
      `recommendation ml ${name} token is an internal service token`,
      token.tokenUse === "internal" && token.actorType === "service",
      `tokenUse=${token.tokenUse ?? "<missing>"} actorType=${token.actorType ?? "<missing>"}`
    );
    record(
      `recommendation ml ${name} token has required scope`,
      token.requiredScopesPresent === true,
      `required=${token.requiredScopes.join(",")} scopes=${token.scopes.join(",") || "<missing>"}`
    );
    record(
      `recommendation ml ${name} token is not expired`,
      token.notExpired === true,
      `expiresAt=${token.expiresAt ?? "<missing>"} expiresInSeconds=${
        token.expiresInSeconds ?? "<missing>"
      }`
    );
    record(
      `recommendation ml ${name} token TTL is within threshold`,
      token.ttlWithinLimit === true,
      `ttlSeconds=${token.ttlSeconds ?? "<missing>"} max=${MAX_TOKEN_TTL_SECONDS}`
    );
  }
  record(
    "recommendation ml ops maker and checker tokens use different service subjects",
    tokenEvidence.actorSeparation.opsCheckerDifferent === true,
    `opsSubjectHash=${tokenEvidence.actorSeparation.opsSubjectHash ?? "<missing>"} `
      + `checkerSubjectHash=${tokenEvidence.actorSeparation.opsCheckerSubjectHash ?? "<missing>"}`
  );
}

function actorSeparationEvidence(opsToken, opsCheckerToken) {
  const opsSubjectHash = opsToken?.subjectHash ?? null;
  const opsCheckerSubjectHash = opsCheckerToken?.subjectHash ?? null;
  return {
    required: true,
    opsSubjectHash,
    opsCheckerSubjectHash,
    opsCheckerDifferent: Boolean(
      opsSubjectHash
        && opsCheckerSubjectHash
        && opsSubjectHash !== opsCheckerSubjectHash
    ),
  };
}

function jwtClaimEvidence(token, requiredScopes) {
  const parsed = decodeJwtPayload(token);
  if (!parsed.ok) {
    return {
      parseable: false,
      parseError: parsed.error,
      requiredScopes,
      scopes: [],
      requiredScopesPresent: false,
      notExpired: false,
      ttlWithinLimit: false,
    };
  }
  const payload = parsed.payload;
  const issuedAtEpoch = numericDate(payload.iat);
  const expiresAtEpoch = numericDate(payload.exp);
  const now = Math.floor(Date.now() / 1000);
  const scopes = tokenScopes(payload);
  const ttlSeconds = issuedAtEpoch !== null && expiresAtEpoch !== null
    ? expiresAtEpoch - issuedAtEpoch
    : null;
  const expiresInSeconds = expiresAtEpoch === null ? null : expiresAtEpoch - now;
  return {
    parseable: true,
    issuer: stringClaim(payload.iss),
    audience: audienceClaim(payload.aud),
    subjectHash: payload.sub ? `sha256:${sha256Hex(String(payload.sub)).slice(0, 24)}` : null,
    actorType: stringClaim(payload.actor_type),
    tokenUse: stringClaim(payload.token_use),
    scopes,
    requiredScopes,
    requiredScopesPresent: requiredScopes.every((scope) => scopes.includes(scope)),
    issuedAt: issuedAtEpoch === null ? null : new Date(issuedAtEpoch * 1000).toISOString(),
    expiresAt: expiresAtEpoch === null ? null : new Date(expiresAtEpoch * 1000).toISOString(),
    ttlSeconds,
    expiresInSeconds,
    notExpired: expiresInSeconds !== null && expiresInSeconds > 0,
    ttlWithinLimit: ttlSeconds !== null && ttlSeconds > 0 && ttlSeconds <= MAX_TOKEN_TTL_SECONDS,
  };
}

function decodeJwtPayload(token) {
  const parts = String(token ?? "").split(".");
  if (parts.length < 2 || !parts[1]) {
    return { ok: false, error: "not_jwt" };
  }
  try {
    return {
      ok: true,
      payload: JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8")),
    };
  } catch (error) {
    return { ok: false, error: `payload_decode_failed:${error.message}` };
  }
}

function tokenScopes(payload) {
  const scopes = new Set();
  if (typeof payload.scope === "string") {
    payload.scope.split(/\s+/).filter(Boolean).forEach((scope) => scopes.add(scope));
  }
  if (typeof payload.scp === "string") {
    payload.scp.split(/\s+/).filter(Boolean).forEach((scope) => scopes.add(scope));
  }
  if (Array.isArray(payload.scp)) {
    payload.scp.map(String).filter(Boolean).forEach((scope) => scopes.add(scope));
  }
  return [...scopes].sort();
}

function audienceClaim(value) {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }
  if (value === undefined || value === null || String(value).trim() === "") {
    return [];
  }
  return [String(value)];
}

function stringClaim(value) {
  return value === undefined || value === null || String(value).trim() === ""
    ? null
    : String(value);
}

function numericDate(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.floor(parsed) : null;
}

function mintLocalInternalToken(subject, scopes) {
  const secret = firstNonBlank(
    process.env.RECOMMENDATION_ML_SMOKE_INTERNAL_JWT_SECRET,
    process.env.COURSEFLOW_INTERNAL_JWT_SECRET
  );
  if (!secret) {
    return "";
  }
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: process.env.COURSEFLOW_INTERNAL_JWT_ISSUER ?? "courseflow-token-converter",
    aud: process.env.COURSEFLOW_INTERNAL_JWT_AUDIENCE ?? "courseflow-services",
    sub: subject,
    iat: now,
    exp: now + 600,
    actor_type: "service",
    token_use: "internal",
    scope: scopes.join(" "),
  };
  return signHs256(payload, secret);
}

function signHs256(payload, secret) {
  const header = { alg: "HS256", typ: "JWT" };
  const encodedHeader = base64Url(JSON.stringify(header));
  const encodedPayload = base64Url(JSON.stringify(payload));
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const signature = crypto
    .createHmac("sha256", secret)
    .update(signingInput)
    .digest("base64url");
  return `${signingInput}.${signature}`;
}

function base64Url(value) {
  return Buffer.from(value).toString("base64url");
}

function sha256Hex(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function parseTargets(value) {
  return csvList(value).map((entry) => {
    const parts = entry.split("|").map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) {
      throw new Error("RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS entries must be name|job|instance");
    }
    return { name: parts[0], job: parts[1], instance: parts[2] };
  });
}

function prometheusRangeWindow(value, name) {
  if (!/^[1-9][0-9]*[smhd]$/.test(value)) {
    throw new Error(`${name} must be a Prometheus range like 30m`);
  }
  return value;
}

function csvList(value) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function record(name, pass, detail) {
  checks.push({ name, pass, detail });
  const marker = pass ? "PASS" : "FAIL";
  console.log(`[${marker}] ${name}: ${detail}`);
  if (!pass) {
    throw new Error(`${name}: ${detail}`);
  }
}

function printSummary() {
  writeEvidence("pass");
  console.log(`Recommendation ML ops smoke passed (${checks.length} checks)`);
}

function writeEvidence(status, errorMessage = null) {
  if (!EVIDENCE_FILE) {
    return;
  }
  const evidence = {
    artifactType: "recommendation_ml_ops_smoke_evidence",
    artifactVersion: 1,
    status,
    checkedAt: new Date().toISOString(),
    environment: SMOKE_ENVIRONMENT || null,
    sourceProvenance,
    urlPolicy: urlPolicyEvidence,
    serviceUrl: SERVICE_URL,
    prometheusConfigured: Boolean(PROMETHEUS_URL),
    requireActiveModel: REQUIRE_ACTIVE_MODEL,
    tokenPolicy: tokenEvidence,
    activeModel: activeModelEvidence,
    analytics: analyticsEvidence,
    thresholds: {
      maxQueuedAgeSeconds: MAX_QUEUED_AGE_SECONDS,
      maxRunningAgeSeconds: MAX_RUNNING_AGE_SECONDS,
      maxPendingActivationApprovalAgeSeconds: MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS,
    },
    mutationFlowEnabled: MUTATION_FLOW_ENABLED,
    expectSyncTrainDisabled: EXPECT_SYNC_TRAIN_DISABLED,
    mutationFlow: mutationEvidence,
    prometheus: prometheusEvidence,
    requiredTargets: REQUIRED_TARGETS,
    requiredAlerts: REQUIRED_ALERTS,
    criticalAlerts: CRITICAL_ALERTS,
    checks,
    errorMessage,
  };
  const payload = JSON.stringify(evidence, null, 2);
  fs.mkdirSync(path.dirname(EVIDENCE_FILE), { recursive: true });
  fs.writeFileSync(EVIDENCE_FILE, payload + "\n", "utf8");
  console.log(`Recommendation ML ops smoke evidence written to ${EVIDENCE_FILE}`);
}

function requireValue(name, value) {
  if (!value) {
    throw new Error(`${name} is required`);
  }
}

function allPremintedTokensConfigured() {
  const baseTokensConfigured = Boolean(
    firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN)
      && firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_INFER_TOKEN)
      && firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_TOKEN)
      && firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN)
  );
  if (!baseTokensConfigured) {
    return false;
  }
  if (!ANALYTICS_CLIENT_METRIC_REQUIRED) {
    return true;
  }
  return Boolean(firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN));
}

function buildSourceProvenance() {
  const serverUrl = firstNonBlank(
    process.env.RECOMMENDATION_ML_SMOKE_SERVER_URL,
    process.env.GITHUB_SERVER_URL
  );
  const repository = firstNonBlank(
    process.env.RECOMMENDATION_ML_SMOKE_REPOSITORY,
    process.env.GITHUB_REPOSITORY
  );
  const runId = firstNonBlank(
    process.env.RECOMMENDATION_ML_SMOKE_RUN_ID,
    process.env.GITHUB_RUN_ID
  );
  const explicitRunUrl = firstNonBlank(process.env.RECOMMENDATION_ML_SMOKE_RUN_URL);
  const runUrl = explicitRunUrl || (
    serverUrl && repository && runId ? `${serverUrl}/${repository}/actions/runs/${runId}` : ""
  );
  return {
    provider: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_CI_PROVIDER,
      process.env.GITHUB_ACTIONS === "true" ? "github_actions" : ""
    ) || null,
    repository: repository || null,
    commitSha: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_COMMIT_SHA,
      process.env.GITHUB_SHA
    ) || null,
    ref: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_REF,
      process.env.GITHUB_REF_NAME,
      process.env.GITHUB_REF
    ) || null,
    workflow: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_WORKFLOW,
      process.env.GITHUB_WORKFLOW
    ) || null,
    job: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_JOB,
      process.env.GITHUB_JOB
    ) || null,
    runId: runId || null,
    runAttempt: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_RUN_ATTEMPT,
      process.env.GITHUB_RUN_ATTEMPT
    ) || null,
    actor: firstNonBlank(
      process.env.RECOMMENDATION_ML_SMOKE_ACTOR,
      process.env.GITHUB_ACTOR
    ) || null,
    serverUrl: serverUrl || null,
    runUrl: runUrl || null,
  };
}

function firstNonBlank(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && String(value).trim()) {
      return String(value).trim();
    }
  }
  return "";
}

function stripTrailingSlash(value) {
  return String(value ?? "").replace(/\/+$/, "");
}

function boolEnv(value, defaultValue) {
  if (value === undefined || value === null || String(value).trim() === "") {
    return defaultValue;
  }
  return String(value).trim().toLowerCase() === "true";
}

function positiveInt(value, defaultValue) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : defaultValue;
}

function nonNegativeNumber(value, defaultValue) {
  if (value === undefined || value === null || String(value).trim() === "") {
    return defaultValue;
  }
  const parsed = Number(value ?? "");
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : defaultValue;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((error) => {
  try {
    writeEvidence("fail", error.message);
  } catch (evidenceError) {
    console.error(
      `Recommendation ML ops smoke evidence write failed: ${evidenceError.message}`
    );
  }
  console.error(`Recommendation ML ops smoke failed: ${error.message}`);
  process.exit(1);
});
