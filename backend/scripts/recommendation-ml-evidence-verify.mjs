#!/usr/bin/env node

/**
 * Verifies Recommendation ML ops smoke evidence for release signoff.
 *
 * Usage:
 *   node scripts/recommendation-ml-evidence-verify.mjs <evidence-json> --mode=staging --expected-commit-sha=<sha>
 *   node scripts/recommendation-ml-evidence-verify.mjs <evidence-json> --mode=local
 */

import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const evidencePath = args.find((arg) => !arg.startsWith("--"));
const mode = optionValue("--mode") || "staging";
const maxAgeHours = nonNegativeNumberOption("--max-age-hours", mode === "staging" ? 24 : 0);
const maxFutureSkewMinutes = nonNegativeNumberOption(
  "--max-future-skew-minutes",
  mode === "staging" ? 10 : 0
);
const expectedProvenance = {
  repository: optionValue("--expected-repository"),
  commitSha: optionValue("--expected-commit-sha"),
  ref: optionValue("--expected-ref"),
  workflow: optionValue("--expected-workflow"),
  job: optionValue("--expected-job"),
  runId: optionValue("--expected-run-id"),
  runAttempt: optionValue("--expected-run-attempt"),
  actor: optionValue("--expected-actor"),
  runUrl: optionValue("--expected-run-url")
};
const expectedTarget = {
  environment: optionValue("--expected-environment"),
  recommendationMlUrl: optionValue("--expected-service-url"),
  analyticsUrl: optionValue("--expected-analytics-url"),
  prometheusUrl: optionValue("--expected-prometheus-url")
};
const expectedMonitoring = {
  targets: parseExpectedTargetsOption("--expected-prometheus-targets"),
  alerts: parseRequiredCsvOption("--expected-required-alerts")
};
const expectedThresholds = {
  maxQueuedAgeSeconds: optionalNonNegativeIntegerOption("--expected-max-queued-age-seconds"),
  maxRunningAgeSeconds: optionalNonNegativeIntegerOption("--expected-max-running-age-seconds"),
  maxPendingActivationApprovalAgeSeconds: optionalNonNegativeIntegerOption(
    "--expected-max-pending-activation-approval-age-seconds"
  ),
  maxTokenTtlSeconds: optionalPositiveIntegerOption("--expected-max-token-ttl-seconds"),
  analyticsMetricWindow: optionValue("--expected-analytics-metric-window")
};

if (!evidencePath) {
  usage("evidence-json path is required");
}
if (!["staging", "local"].includes(mode)) {
  usage("--mode must be staging or local");
}

const evidence = readEvidence(evidencePath);
const failures = [];

requireEqual("artifactType", evidence.artifactType, "recommendation_ml_ops_smoke_evidence");
requireEqual("artifactVersion", evidence.artifactVersion, 1);
requireEqual("status", evidence.status, "pass");
requireNonBlank("serviceUrl", evidence.serviceUrl);
requireTrue("requireActiveModel", evidence.requireActiveModel === true);
requireTrue("expectSyncTrainDisabled", evidence.expectSyncTrainDisabled === true);
requireEvidenceFreshness();
requireChecksPassed();
requireCheckNamed("recommendation ml synchronous training endpoint is disabled");
requireCheckNamed("recommendation ml active model endpoint returns trainingRunId");
requireCheckNamed("recommendation ml checker rejects smoke activation request");
requireActiveModelContract();
requireMutationEvidence();

if (mode === "staging") {
  requireSourceProvenance();
  requireSourceProvenanceBinding();
  requireUrlPolicy();
  requireTargetBinding();
  requireStagingTokenPolicy();
  requireThresholdPolicyBinding();
  requirePrometheusEvidence();
  requireMonitoringPolicyBinding();
  requireAnalyticsEvidence();
} else {
  requireTrue(
    "tokenPolicy.source",
    ["preminted", "local_hs256"].includes(evidence.tokenPolicy?.source)
  );
}

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(
  `Recommendation ML ${mode} evidence verified: `
    + `${path.basename(evidencePath)} checks=${evidence.checks.length}`
    + ` maxAgeHours=${maxAgeHours}`
    + ` commit=${String(evidence.sourceProvenance?.commitSha ?? "").slice(0, 12)}`
);

function readEvidence(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    throw new Error(`Unable to read evidence JSON ${filePath}: ${error.message}`);
  }
}

function requireChecksPassed() {
  if (!Array.isArray(evidence.checks) || evidence.checks.length === 0) {
    failures.push("checks must be a non-empty array");
    return;
  }
  const failed = evidence.checks.filter((check) => check?.pass !== true);
  if (failed.length > 0) {
    failures.push(`checks contain failures: ${failed.map((check) => check.name).join(",")}`);
  }
}

function requireEvidenceFreshness() {
  const checkedAt = parseCheckedAt();
  if (!checkedAt) {
    return;
  }

  const nowMs = Date.now();
  const checkedAtMs = checkedAt.getTime();
  const futureSkewMs = maxFutureSkewMinutes * 60 * 1000;
  if (checkedAtMs - nowMs > futureSkewMs) {
    failures.push(
      `checkedAt must not be more than ${maxFutureSkewMinutes} minute(s) in the future, `
        + `got ${evidence.checkedAt}`
    );
  }

  if (maxAgeHours > 0) {
    const ageHours = (nowMs - checkedAtMs) / (60 * 60 * 1000);
    if (ageHours > maxAgeHours) {
      failures.push(
        `checkedAt is too old for release signoff: `
          + `ageHours=${ageHours.toFixed(2)} maxAgeHours=${maxAgeHours}`
      );
    }
  }
}

function parseCheckedAt() {
  if (evidence.checkedAt === undefined || evidence.checkedAt === null) {
    failures.push("checkedAt must be present");
    return null;
  }

  const raw = String(evidence.checkedAt).trim();
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(raw)) {
    failures.push(`checkedAt must be an ISO-8601 UTC timestamp, got ${JSON.stringify(evidence.checkedAt)}`);
    return null;
  }

  const timestamp = Date.parse(raw);
  if (!Number.isFinite(timestamp)) {
    failures.push(`checkedAt must be parseable, got ${JSON.stringify(evidence.checkedAt)}`);
    return null;
  }
  return new Date(timestamp);
}

function requireCheckNamed(name) {
  if (!Array.isArray(evidence.checks)) {
    return;
  }
  if (!evidence.checks.some((check) => check?.name === name && check?.pass === true)) {
    failures.push(`missing passing check: ${name}`);
  }
}

function requireActiveModelContract() {
  requireEqual("activeModel.status", evidence.activeModel?.status, "found");
  requireNonBlank("activeModel.trainingRunId", evidence.activeModel?.trainingRunId);
  requireNonBlank("activeModel.modelVersion", evidence.activeModel?.modelVersion);
  requireNonBlank("activeModel.algorithm", evidence.activeModel?.algorithm);
}

function requireMutationEvidence() {
  requireTrue("mutationFlowEnabled", evidence.mutationFlowEnabled === true);
  requireEqual("mutationFlow.status", evidence.mutationFlow?.status, "rejected");
  requireEqual(
    "mutationFlow.trainingRunStatus",
    evidence.mutationFlow?.trainingRunStatus,
    "ACTIVATION_REJECTED"
  );
  requireEqual(
    "mutationFlow.activationRequestStatus",
    evidence.mutationFlow?.activationRequestStatus,
    "REJECTED"
  );
  requireNonBlank("mutationFlow.smokeRunId", evidence.mutationFlow?.smokeRunId);
  requireNonBlank("mutationFlow.trainingRunId", evidence.mutationFlow?.trainingRunId);
  requireNonBlank("mutationFlow.modelVersion", evidence.mutationFlow?.modelVersion);
  requireNonBlank("mutationFlow.approvalId", evidence.mutationFlow?.approvalId);
}

function requireSourceProvenance() {
  requireNonBlank("environment", evidence.environment);
  requireEqual("sourceProvenance.provider", evidence.sourceProvenance?.provider, "github_actions");
  requireNonBlank("sourceProvenance.repository", evidence.sourceProvenance?.repository);
  requirePattern(
    "sourceProvenance.commitSha",
    evidence.sourceProvenance?.commitSha,
    /^[0-9a-f]{40}$/i
  );
  requireNonBlank("sourceProvenance.ref", evidence.sourceProvenance?.ref);
  requireNonBlank("sourceProvenance.workflow", evidence.sourceProvenance?.workflow);
  requireNonBlank("sourceProvenance.job", evidence.sourceProvenance?.job);
  requirePattern("sourceProvenance.runId", evidence.sourceProvenance?.runId, /^[0-9]+$/);
  requirePattern("sourceProvenance.runAttempt", evidence.sourceProvenance?.runAttempt, /^[0-9]+$/);
  requireNonBlank("sourceProvenance.actor", evidence.sourceProvenance?.actor);
  requireNonBlank("sourceProvenance.runUrl", evidence.sourceProvenance?.runUrl);
  if (
    evidence.sourceProvenance?.runUrl
    && !String(evidence.sourceProvenance.runUrl).includes("/actions/runs/")
  ) {
    failures.push("sourceProvenance.runUrl must point to a CI workflow run");
  }
}

function requireSourceProvenanceBinding() {
  requireExpectedProvenance("repository", expectedProvenance.repository);
  requireExpectedProvenance("commitSha", expectedProvenance.commitSha, { pattern: /^[0-9a-f]{40}$/i });
  requireExpectedProvenance("ref", expectedProvenance.ref);
  requireExpectedProvenance("workflow", expectedProvenance.workflow);
  requireExpectedProvenance("job", expectedProvenance.job);
  requireExpectedProvenance("runId", expectedProvenance.runId, { pattern: /^[0-9]+$/ });
  requireExpectedProvenance("runAttempt", expectedProvenance.runAttempt, { pattern: /^[0-9]+$/ });
  requireExpectedProvenance("actor", expectedProvenance.actor);
  requireExpectedProvenance("runUrl", expectedProvenance.runUrl);
}

function requireExpectedProvenance(field, expected, options = {}) {
  const optionName = `--expected-${field.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`;
  if (expected === "") {
    failures.push(`${optionName} is required for staging evidence verification`);
    return;
  }
  if (options.pattern && !options.pattern.test(expected)) {
    failures.push(`${optionName} must match ${options.pattern}, got ${JSON.stringify(expected)}`);
    return;
  }
  const actual = evidence.sourceProvenance?.[field];
  if (actual !== expected) {
    failures.push(
      `sourceProvenance.${field} must match ${optionName}: `
        + `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`
    );
  }
}

function requireUrlPolicy() {
  requireTrue("urlPolicy.requireHttps", evidence.urlPolicy?.requireHttps === true);
  requireTrue("urlPolicy.rejectLocalUrls", evidence.urlPolicy?.rejectLocalUrls === true);
  requireEndpointUrl("recommendationMl", "serviceUrl");
  requireEndpointUrl("analytics", "analytics.serviceUrl");
  requireEndpointUrl("prometheus", "prometheusUrl");
}

function requireTargetBinding() {
  requireExpectedField(
    "--expected-environment",
    expectedTarget.environment,
    evidence.environment,
    "environment"
  );
  requireExpectedEndpoint(
    "recommendationMl",
    "--expected-service-url",
    expectedTarget.recommendationMlUrl
  );
  requireExpectedEndpoint("analytics", "--expected-analytics-url", expectedTarget.analyticsUrl);
  requireExpectedEndpoint("prometheus", "--expected-prometheus-url", expectedTarget.prometheusUrl);
}

function requireEndpointUrl(name, fallbackField) {
  const endpoint = evidence.urlPolicy?.endpoints?.[name];
  if (!endpoint) {
    failures.push(`urlPolicy.endpoints.${name} must be present`);
    return;
  }
  requireTrue(`urlPolicy.endpoints.${name}.configured`, endpoint.configured === true);
  requireTrue(`urlPolicy.endpoints.${name}.parseable`, endpoint.parseable === true);
  requireEqual(`urlPolicy.endpoints.${name}.scheme`, endpoint.scheme, "https");
  requireTrue(`urlPolicy.endpoints.${name}.https`, endpoint.https === true);
  requireTrue(`urlPolicy.endpoints.${name}.localhost`, endpoint.localhost === false);
  requireNonBlank(`urlPolicy.endpoints.${name}.host`, endpoint.host);
  requireNonBlank(`urlPolicy.endpoints.${name}.url`, endpoint.url);
  if (isLocalUrl(endpoint.url)) {
    failures.push(`urlPolicy.endpoints.${name}.url must not be local: ${endpoint.url}`);
  }
  if (fallbackField === "serviceUrl" && endpoint.url !== evidence.serviceUrl) {
    failures.push("urlPolicy.endpoints.recommendationMl.url must match serviceUrl");
  }
  if (fallbackField === "analytics.serviceUrl" && endpoint.url !== evidence.analytics?.serviceUrl) {
    failures.push("urlPolicy.endpoints.analytics.url must match analytics.serviceUrl");
  }
}

function requireExpectedEndpoint(endpointName, optionName, expectedUrl) {
  if (expectedUrl === "") {
    failures.push(`${optionName} is required for staging evidence verification`);
    return;
  }

  const expectedCanonical = canonicalEndpointUrl(expectedUrl);
  if (!expectedCanonical) {
    failures.push(`${optionName} must be a parseable URL, got ${JSON.stringify(expectedUrl)}`);
    return;
  }
  if (!expectedCanonical.startsWith("https://")) {
    failures.push(`${optionName} must be an HTTPS URL, got ${JSON.stringify(expectedUrl)}`);
  }
  if (isLocalUrl(expectedUrl)) {
    failures.push(`${optionName} must not point to a local host, got ${JSON.stringify(expectedUrl)}`);
  }
  if (/[?#]/.test(expectedUrl)) {
    failures.push(`${optionName} must not include query string or fragment, got ${JSON.stringify(expectedUrl)}`);
  }

  const actualUrl = evidence.urlPolicy?.endpoints?.[endpointName]?.url;
  const actualCanonical = canonicalEndpointUrl(actualUrl);
  if (actualCanonical !== expectedCanonical) {
    failures.push(
      `urlPolicy.endpoints.${endpointName}.url must match ${optionName}: `
        + `expected ${JSON.stringify(expectedCanonical)}, got ${JSON.stringify(actualCanonical)}`
    );
  }
}

function requireExpectedField(optionName, expected, actual, fieldName) {
  if (expected === "") {
    failures.push(`${optionName} is required for staging evidence verification`);
    return;
  }
  if (actual !== expected) {
    failures.push(
      `${fieldName} must match ${optionName}: `
        + `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`
    );
  }
}

function requireStagingTokenPolicy() {
  requireEqual("tokenPolicy.source", evidence.tokenPolicy?.source, "preminted");
  requireTrue("tokenPolicy.premintedRequired", evidence.tokenPolicy?.premintedRequired === true);
  requireTrue("tokenPolicy.trainConfigured", evidence.tokenPolicy?.trainConfigured === true);
  requireTrue("tokenPolicy.inferConfigured", evidence.tokenPolicy?.inferConfigured === true);
  requireTrue("tokenPolicy.opsConfigured", evidence.tokenPolicy?.opsConfigured === true);
  requireTrue("tokenPolicy.opsCheckerConfigured", evidence.tokenPolicy?.opsCheckerConfigured === true);
  requireTrue(
    "tokenPolicy.analyticsModelConfigured",
    evidence.tokenPolicy?.analyticsModelConfigured === true
  );
  requirePositiveNumber("tokenPolicy.maxTtlSeconds", evidence.tokenPolicy?.maxTtlSeconds);
  if (typeof evidence.tokenPolicy?.maxTtlSeconds === "number"
      && evidence.tokenPolicy.maxTtlSeconds > 900) {
    failures.push(
      `tokenPolicy.maxTtlSeconds must be <= 900, got ${evidence.tokenPolicy.maxTtlSeconds}`
    );
  }
  requireTokenClaim("train", "internal:recommendation-ml:train");
  requireTokenClaim("infer", "internal:recommendation-ml:infer");
  requireTokenClaim("ops", "internal:recommendation-ml:ops");
  requireTokenClaim("opsChecker", "internal:recommendation-ml:ops");
  requireTokenClaim("analyticsModel", "internal:analytics:model-write");
  requireTrue(
    "tokenPolicy.actorSeparation.required",
    evidence.tokenPolicy?.actorSeparation?.required === true
  );
  requireNonBlank(
    "tokenPolicy.actorSeparation.opsSubjectHash",
    evidence.tokenPolicy?.actorSeparation?.opsSubjectHash
  );
  requireNonBlank(
    "tokenPolicy.actorSeparation.opsCheckerSubjectHash",
    evidence.tokenPolicy?.actorSeparation?.opsCheckerSubjectHash
  );
  requireTrue(
    "tokenPolicy.actorSeparation.opsCheckerDifferent",
    evidence.tokenPolicy?.actorSeparation?.opsCheckerDifferent === true
  );
  if (
    evidence.tokenPolicy?.actorSeparation?.opsSubjectHash
    && evidence.tokenPolicy?.actorSeparation?.opsCheckerSubjectHash
    && evidence.tokenPolicy.actorSeparation.opsSubjectHash
      === evidence.tokenPolicy.actorSeparation.opsCheckerSubjectHash
  ) {
    failures.push("ops maker and ops checker token subject hashes must be different");
  }
}

function requireThresholdPolicyBinding() {
  requireExpectedNumber(
    "--expected-max-queued-age-seconds",
    expectedThresholds.maxQueuedAgeSeconds,
    evidence.thresholds?.maxQueuedAgeSeconds,
    "thresholds.maxQueuedAgeSeconds"
  );
  requireExpectedNumber(
    "--expected-max-running-age-seconds",
    expectedThresholds.maxRunningAgeSeconds,
    evidence.thresholds?.maxRunningAgeSeconds,
    "thresholds.maxRunningAgeSeconds"
  );
  requireExpectedNumber(
    "--expected-max-pending-activation-approval-age-seconds",
    expectedThresholds.maxPendingActivationApprovalAgeSeconds,
    evidence.thresholds?.maxPendingActivationApprovalAgeSeconds,
    "thresholds.maxPendingActivationApprovalAgeSeconds"
  );
  requireExpectedNumber(
    "--expected-max-token-ttl-seconds",
    expectedThresholds.maxTokenTtlSeconds,
    evidence.tokenPolicy?.maxTtlSeconds,
    "tokenPolicy.maxTtlSeconds"
  );
  requireExpectedMetricWindow();
}

function requireExpectedMetricWindow() {
  if (expectedThresholds.analyticsMetricWindow === "") {
    failures.push("--expected-analytics-metric-window is required for staging evidence verification");
    return;
  }
  if (!/^[1-9][0-9]*[smhd]$/.test(expectedThresholds.analyticsMetricWindow)) {
    failures.push(
      "--expected-analytics-metric-window must be a Prometheus range like 30m, "
        + `got ${JSON.stringify(expectedThresholds.analyticsMetricWindow)}`
    );
    return;
  }
  requireExpectedField(
    "--expected-analytics-metric-window",
    expectedThresholds.analyticsMetricWindow,
    evidence.analytics?.metricWindow,
    "analytics.metricWindow"
  );
}

function requireExpectedNumber(optionName, expected, actual, fieldName) {
  if (expected === null) {
    failures.push(`${optionName} is required for staging evidence verification`);
    return;
  }
  if (actual !== expected) {
    failures.push(
      `${fieldName} must match ${optionName}: `
        + `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`
    );
  }
}

function requireTokenClaim(name, requiredScope) {
  const token = evidence.tokenPolicy?.tokens?.[name];
  if (!token) {
    failures.push(`tokenPolicy.tokens.${name} must be present`);
    return;
  }
  requireTrue(`tokenPolicy.tokens.${name}.parseable`, token.parseable === true);
  requireNonBlank(`tokenPolicy.tokens.${name}.issuer`, token.issuer);
  if (!Array.isArray(token.audience) || token.audience.length === 0) {
    failures.push(`tokenPolicy.tokens.${name}.audience must contain at least one value`);
  }
  requireNonBlank(`tokenPolicy.tokens.${name}.subjectHash`, token.subjectHash);
  requireEqual(`tokenPolicy.tokens.${name}.actorType`, token.actorType, "service");
  requireEqual(`tokenPolicy.tokens.${name}.tokenUse`, token.tokenUse, "internal");
  requireTrue(
    `tokenPolicy.tokens.${name}.requiredScopesPresent`,
    token.requiredScopesPresent === true
  );
  if (!Array.isArray(token.scopes) || !token.scopes.includes(requiredScope)) {
    failures.push(`tokenPolicy.tokens.${name}.scopes must include ${requiredScope}`);
  }
  requireTrue(`tokenPolicy.tokens.${name}.notExpired`, token.notExpired === true);
  requireTrue(`tokenPolicy.tokens.${name}.ttlWithinLimit`, token.ttlWithinLimit === true);
  requirePositiveNumber(`tokenPolicy.tokens.${name}.ttlSeconds`, token.ttlSeconds);
  if (
    typeof token.ttlSeconds === "number"
    && typeof evidence.tokenPolicy?.maxTtlSeconds === "number"
    && token.ttlSeconds > evidence.tokenPolicy.maxTtlSeconds
  ) {
    failures.push(
      `tokenPolicy.tokens.${name}.ttlSeconds exceeds max: `
        + `${token.ttlSeconds} > ${evidence.tokenPolicy.maxTtlSeconds}`
    );
  }
}

function requirePrometheusEvidence() {
  requireCheckNamed("recommendation ml required Prometheus alert rules are loaded");
  requireTrue("prometheus.configured", evidence.prometheus?.configured === true);
  if (!Array.isArray(evidence.prometheus?.targetResults)
      || evidence.prometheus.targetResults.length === 0) {
    failures.push("prometheus.targetResults must contain at least one target");
  } else {
    const downTargets = evidence.prometheus.targetResults.filter((target) => target?.value !== 1);
    if (downTargets.length > 0) {
      failures.push(
        `prometheus targets not up: ${downTargets.map((target) => target.name).join(",")}`
      );
    }
  }
  if (
    Array.isArray(evidence.prometheus?.criticalAlertsFiring)
    && evidence.prometheus.criticalAlertsFiring.length > 0
  ) {
    failures.push(
      `critical alerts firing: ${evidence.prometheus.criticalAlertsFiring.join(",")}`
    );
  }
  if (!Array.isArray(evidence.requiredTargets) || evidence.requiredTargets.length === 0) {
    failures.push("requiredTargets must contain at least one target");
  }
  const requiredAlerts = Array.isArray(evidence.requiredAlerts)
    ? evidence.requiredAlerts
    : evidence.prometheus?.requiredAlerts;
  if (!Array.isArray(requiredAlerts) || requiredAlerts.length === 0) {
    failures.push("requiredAlerts must contain at least one alert rule");
  }
  if (!Array.isArray(evidence.prometheus?.alertRuleResults)
      || evidence.prometheus.alertRuleResults.length === 0) {
    failures.push("prometheus.alertRuleResults must contain required alert rules");
  } else {
    const missingRules = evidence.prometheus.alertRuleResults
      .filter((rule) => rule?.loaded !== true)
      .map((rule) => rule?.name ?? "<unknown>");
    if (missingRules.length > 0) {
      failures.push(`prometheus alert rules missing: ${missingRules.join(",")}`);
    }
    const unhealthyRules = evidence.prometheus.alertRuleResults
      .filter((rule) => rule?.loaded === true && rule?.health && rule.health !== "ok")
      .map((rule) => `${rule.name}:${rule.health}`);
    if (unhealthyRules.length > 0) {
      failures.push(`prometheus alert rules unhealthy: ${unhealthyRules.join(",")}`);
    }
    if (Array.isArray(requiredAlerts)) {
      const observed = new Set(evidence.prometheus.alertRuleResults.map((rule) => rule?.name));
      const unobserved = requiredAlerts.filter((name) => !observed.has(name));
      if (unobserved.length > 0) {
        failures.push(`required alert rules not checked: ${unobserved.join(",")}`);
      }
    }
  }
}

function requireMonitoringPolicyBinding() {
  requireExpectedTargetsBinding();
  requireExpectedAlertsBinding();
}

function requireExpectedTargetsBinding() {
  if (expectedMonitoring.targets.length === 0) {
    failures.push("--expected-prometheus-targets is required for staging evidence verification");
    return;
  }

  const expectedKeys = new Set(expectedMonitoring.targets.map(targetKey));
  const evidenceTargets = Array.isArray(evidence.requiredTargets) ? evidence.requiredTargets : [];
  const evidenceKeys = new Set(evidenceTargets.map(targetKey));
  const prometheusTargets = Array.isArray(evidence.prometheus?.requiredTargets)
    ? evidence.prometheus.requiredTargets
    : [];
  const prometheusKeys = new Set(prometheusTargets.map(targetKey));
  const targetResultKeys = new Set(
    (Array.isArray(evidence.prometheus?.targetResults) ? evidence.prometheus.targetResults : [])
      .map(targetKey)
  );

  requireExactSet(
    "requiredTargets",
    expectedKeys,
    evidenceKeys,
    "expected Prometheus target policy"
  );
  requireExactSet(
    "prometheus.requiredTargets",
    expectedKeys,
    prometheusKeys,
    "expected Prometheus target policy"
  );
  requireExactSet(
    "prometheus.targetResults",
    expectedKeys,
    targetResultKeys,
    "expected Prometheus target policy"
  );
}

function requireExpectedAlertsBinding() {
  if (expectedMonitoring.alerts.length === 0) {
    failures.push("--expected-required-alerts is required for staging evidence verification");
    return;
  }

  const expected = new Set(expectedMonitoring.alerts);
  const evidenceAlerts = new Set(Array.isArray(evidence.requiredAlerts) ? evidence.requiredAlerts : []);
  const prometheusAlerts = new Set(
    Array.isArray(evidence.prometheus?.requiredAlerts) ? evidence.prometheus.requiredAlerts : []
  );
  const alertRuleResults = new Set(
    (Array.isArray(evidence.prometheus?.alertRuleResults) ? evidence.prometheus.alertRuleResults : [])
      .map((rule) => rule?.name)
      .filter(Boolean)
  );

  requireExactSet("requiredAlerts", expected, evidenceAlerts, "expected alert rule policy");
  requireExactSet(
    "prometheus.requiredAlerts",
    expected,
    prometheusAlerts,
    "expected alert rule policy"
  );
  requireExactSet(
    "prometheus.alertRuleResults",
    expected,
    alertRuleResults,
    "expected alert rule policy"
  );
}

function requireExactSet(name, expected, actual, label) {
  const missing = [...expected].filter((value) => !actual.has(value)).sort();
  const unexpected = [...actual].filter((value) => !expected.has(value)).sort();
  if (missing.length > 0) {
    failures.push(`${name} missing ${label}: ${missing.join(",")}`);
  }
  if (unexpected.length > 0) {
    failures.push(`${name} has unexpected values outside ${label}: ${unexpected.join(",")}`);
  }
}

function requireAnalyticsEvidence() {
  requireCheckNamed("analytics active model sync endpoint materializes active ML model");
  requireCheckNamed("analytics recommendation ml active-model client metric observed");
  requireCheckNamed("analytics recommendation ml client fallback metric is zero");
  requireTrue("analytics.required", evidence.analytics?.required === true);
  requireTrue("analytics.configured", evidence.analytics?.configured === true);
  requireNonBlank("analytics.serviceUrl", evidence.analytics?.serviceUrl);
  requireEqual("analytics.materializeStatus", evidence.analytics?.materializeStatus, "available");
  requireEqual("analytics.materializeHttpStatus", evidence.analytics?.materializeHttpStatus, 200);
  requireEqual("analytics.responseStatus", evidence.analytics?.responseStatus, "ACTIVE");
  requireEqual("analytics.engine", evidence.analytics?.engine, "ML_ACTIVE_MODEL_SYNC");
  requireNonBlank("analytics.trainingRunId", evidence.analytics?.trainingRunId);
  requireNonBlank("analytics.modelVersion", evidence.analytics?.modelVersion);
  if (
    evidence.analytics?.fallbackReason !== undefined
    && evidence.analytics?.fallbackReason !== null
    && String(evidence.analytics.fallbackReason).trim() !== ""
  ) {
    failures.push(`analytics.fallbackReason must be empty, got ${
      JSON.stringify(evidence.analytics.fallbackReason)
    }`);
  }
  requirePositiveNumber(
    "analytics.availableMetricValue",
    evidence.analytics?.availableMetricValue
  );
  requireEqual("analytics.fallbackMetricValue", evidence.analytics?.fallbackMetricValue, 0);
}

function requireEqual(name, actual, expected) {
  if (actual !== expected) {
    failures.push(`${name} expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function requireTrue(name, pass) {
  if (!pass) {
    failures.push(`${name} is required`);
  }
}

function requireNonBlank(name, value) {
  if (value === undefined || value === null || String(value).trim() === "") {
    failures.push(`${name} must be present`);
  }
}

function requirePattern(name, value, pattern) {
  if (value === undefined || value === null || !pattern.test(String(value))) {
    failures.push(`${name} must match ${pattern}, got ${JSON.stringify(value)}`);
  }
}

function requirePositiveNumber(name, value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    failures.push(`${name} must be a positive number, got ${JSON.stringify(value)}`);
  }
}

function parseExpectedTargetsOption(optionName) {
  const raw = optionValue(optionName);
  if (raw === "") {
    return [];
  }
  return csvList(raw).map((entry) => {
    const parts = entry.split("|").map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) {
      usage(`${optionName} entries must be name|job|instance`);
    }
    return { name: parts[0], job: parts[1], instance: parts[2] };
  });
}

function parseRequiredCsvOption(optionName) {
  const raw = optionValue(optionName);
  if (raw === "") {
    return [];
  }
  return csvList(raw);
}

function optionalNonNegativeIntegerOption(optionName) {
  const raw = optionValue(optionName);
  if (raw === "") {
    return null;
  }
  if (!/^[0-9]+$/.test(raw)) {
    usage(`${optionName} must be a non-negative integer`);
  }
  return Number(raw);
}

function optionalPositiveIntegerOption(optionName) {
  const value = optionalNonNegativeIntegerOption(optionName);
  if (value !== null && value <= 0) {
    usage(`${optionName} must be a positive integer`);
  }
  return value;
}

function csvList(value) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function targetKey(target) {
  return `${target?.name ?? ""}|${target?.job ?? ""}|${target?.instance ?? ""}`;
}

function isLocalUrl(rawUrl) {
  try {
    const host = new URL(String(rawUrl)).hostname.toLowerCase();
    return host === "localhost"
      || host === "127.0.0.1"
      || host.startsWith("127.")
      || host === "::1"
      || host === "0.0.0.0"
      || host === "host.docker.internal";
  } catch (_error) {
    return true;
  }
}

function canonicalEndpointUrl(rawUrl) {
  try {
    const parsed = new URL(String(rawUrl));
    const pathname = parsed.pathname.replace(/\/+$/, "") || "/";
    return `${parsed.protocol}//${parsed.host}${pathname === "/" ? "" : pathname}`;
  } catch (_error) {
    return null;
  }
}

function optionValue(name) {
  const exact = args.indexOf(name);
  if (exact >= 0) {
    return args[exact + 1] ?? "";
  }
  const prefix = `${name}=`;
  const arg = args.find((value) => value.startsWith(prefix));
  return arg ? arg.slice(prefix.length) : "";
}

function nonNegativeNumberOption(name, fallback) {
  const raw = optionValue(name);
  if (raw === "") {
    return fallback;
  }
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) {
    usage(`${name} must be a non-negative number`);
  }
  return value;
}

function usage(message) {
  console.error(message);
  console.error(
    "Usage: node scripts/recommendation-ml-evidence-verify.mjs <evidence-json> "
      + "--mode=staging|local [--max-age-hours=24] [--max-future-skew-minutes=10] "
      + "[--expected-repository=<repo>] [--expected-commit-sha=<sha>] "
      + "[--expected-ref=<ref>] [--expected-workflow=<name>] [--expected-job=<job>] "
      + "[--expected-run-id=<id>] [--expected-run-attempt=<n>] "
      + "[--expected-actor=<actor>] [--expected-run-url=<url>] "
      + "[--expected-environment=<env>] [--expected-service-url=<url>] "
      + "[--expected-analytics-url=<url>] [--expected-prometheus-url=<url>] "
      + "[--expected-prometheus-targets=<name|job|instance,...>] "
      + "[--expected-required-alerts=<alert-name,...>] "
      + "[--expected-max-queued-age-seconds=<n>] [--expected-max-running-age-seconds=<n>] "
      + "[--expected-max-pending-activation-approval-age-seconds=<n>] "
      + "[--expected-max-token-ttl-seconds=<n>] [--expected-analytics-metric-window=<range>]"
  );
  process.exit(2);
}
