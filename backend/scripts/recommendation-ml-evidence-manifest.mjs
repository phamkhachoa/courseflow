#!/usr/bin/env node

/**
 * Creates or verifies an integrity manifest for Recommendation ML smoke release artifacts.
 *
 * Usage:
 *   node scripts/recommendation-ml-evidence-manifest.mjs \
 *     --output=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json \
 *     --checksum-output=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json.sha256 \
 *     recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-evidence.json \
 *     recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke.log
 *   node scripts/recommendation-ml-evidence-manifest.mjs \
 *     --verify=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json \
 *     --checksum=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json.sha256
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const verifyPath = optionValue("--verify");
const checksumPath = optionValue("--checksum");
const outputPath = optionValue("--output")
  || "recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json";
const checksumOutputPath = optionValue("--checksum-output");
const inputPaths = args.filter((arg) => !arg.startsWith("--"));

if (verifyPath) {
  verifyManifest(verifyPath, checksumPath);
  process.exit(0);
}

if (inputPaths.length === 0) {
  usage("at least one artifact file path is required");
}

const evidencePath = inputPaths[0];
const evidence = readEvidence(evidencePath);
const manifest = {
  artifactType: "recommendation_ml_ops_smoke_artifact_manifest",
  artifactVersion: 1,
  generatedAt: new Date().toISOString(),
  evidenceFile: normalizedPath(evidencePath),
  evidence: evidenceSummary(evidence),
  files: inputPaths.map(fileEntry),
};

const payload = `${JSON.stringify(manifest, null, 2)}\n`;
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, payload);

const manifestHash = `sha256:${sha256Hex(Buffer.from(payload))}`;
if (checksumOutputPath) {
  fs.mkdirSync(path.dirname(checksumOutputPath), { recursive: true });
  fs.writeFileSync(checksumOutputPath, `${manifestHash}  ${path.basename(outputPath)}\n`);
}

console.log(
  `Recommendation ML smoke artifact manifest written: `
    + `${outputPath} files=${manifest.files.length} manifestHash=${manifestHash}`
);

function verifyManifest(manifestPath, checksumFilePath) {
  const manifestBytes = fs.readFileSync(manifestPath);
  const manifestHash = `sha256:${sha256Hex(manifestBytes)}`;
  const manifestText = manifestBytes.toString("utf8");
  const manifest = JSON.parse(manifestText);
  const failures = [];

  if (manifest.artifactType !== "recommendation_ml_ops_smoke_artifact_manifest") {
    failures.push(`artifactType must be recommendation_ml_ops_smoke_artifact_manifest, got ${JSON.stringify(manifest.artifactType)}`);
  }
  if (manifest.artifactVersion !== 1) {
    failures.push(`artifactVersion must be 1, got ${JSON.stringify(manifest.artifactVersion)}`);
  }
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) {
    failures.push("files must contain at least one artifact");
  }
  if (manifest.evidence?.status !== "pass") {
    failures.push(`evidence.status must be pass, got ${JSON.stringify(manifest.evidence?.status)}`);
  }
  verifyEvidenceSummary(manifestPath, manifest, failures);
  if (looksLikeRawToken(manifestText)) {
    failures.push("manifest appears to contain raw token material");
  }

  if (checksumFilePath) {
    verifyChecksumSidecar(checksumFilePath, manifestPath, manifestHash, failures);
  }

  for (const entry of manifestFileEntries(manifest)) {
    verifyFileEntry(manifestPath, entry, failures);
  }

  if (failures.length > 0) {
    for (const failure of failures) {
      console.error(`- ${failure}`);
    }
    process.exit(1);
  }

  console.log(
    `Recommendation ML smoke artifact manifest verified: `
      + `${manifestPath} files=${manifest.files.length} manifestHash=${manifestHash}`
  );
}

function verifyChecksumSidecar(checksumFilePath, manifestPath, manifestHash, failures) {
  const checksumLine = fs.readFileSync(checksumFilePath, "utf8").trim();
  const match = checksumLine.match(/^(sha256:[0-9a-f]{64})\s+(.+)$/i);
  if (!match) {
    failures.push("checksum sidecar must contain 'sha256:<64-hex> <manifest-file>'");
    return;
  }
  const [, expectedHash, expectedFile] = match;
  if (expectedHash.toLowerCase() !== manifestHash.toLowerCase()) {
    failures.push(`manifest checksum mismatch: expected ${expectedHash}, got ${manifestHash}`);
  }
  if (path.basename(expectedFile.trim()) !== path.basename(manifestPath)) {
    failures.push(
      `checksum sidecar file name must match manifest: `
        + `${expectedFile.trim()} != ${path.basename(manifestPath)}`
    );
  }
}

function verifyFileEntry(manifestPath, entry, failures) {
  if (!entry || typeof entry !== "object") {
    failures.push("manifest file entry must be an object");
    return;
  }
  if (!entry.path) {
    failures.push("manifest file entry path must be present");
    return;
  }
  if (!/^sha256:[0-9a-f]{64}$/i.test(String(entry.sha256))) {
    failures.push(`manifest file entry ${entry.path} has invalid sha256 ${JSON.stringify(entry.sha256)}`);
    return;
  }
  if (typeof entry.bytes !== "number" || !Number.isInteger(entry.bytes) || entry.bytes < 0) {
    failures.push(`manifest file entry ${entry.path} has invalid byte size ${JSON.stringify(entry.bytes)}`);
    return;
  }

  const resolved = resolveManifestFile(manifestPath, entry.path);
  if (!resolved) {
    failures.push(`manifest file entry not found: ${entry.path}`);
    return;
  }
  const bytes = fs.readFileSync(resolved);
  const actualHash = `sha256:${sha256Hex(bytes)}`;
  if (actualHash.toLowerCase() !== String(entry.sha256).toLowerCase()) {
    failures.push(`manifest file entry ${entry.path} hash mismatch: expected ${entry.sha256}, got ${actualHash}`);
  }
  if (bytes.length !== entry.bytes) {
    failures.push(`manifest file entry ${entry.path} byte size mismatch: expected ${entry.bytes}, got ${bytes.length}`);
  }
}

function verifyEvidenceSummary(manifestPath, manifest, failures) {
  if (!manifest.evidenceFile) {
    failures.push("evidenceFile must be present");
    return;
  }
  const evidenceEntries = findManifestFileEntries(manifestPath, manifestFileEntries(manifest), manifest.evidenceFile);
  if (evidenceEntries.length === 0) {
    failures.push(`evidenceFile must match a hashed manifest file entry: ${manifest.evidenceFile}`);
    return;
  }
  if (evidenceEntries.length > 1) {
    failures.push(`evidenceFile must match exactly one manifest file entry: ${manifest.evidenceFile}`);
    return;
  }
  const evidencePath = resolveManifestFile(manifestPath, manifest.evidenceFile);
  if (!evidencePath) {
    failures.push(`evidenceFile not found: ${manifest.evidenceFile}`);
    return;
  }
  let evidence;
  try {
    evidence = readEvidence(evidencePath);
  } catch (error) {
    failures.push(error.message);
    return;
  }

  const expectedSummary = evidenceSummary(evidence);
  const actualSummaryJson = stableJson(manifest.evidence);
  const expectedSummaryJson = stableJson(expectedSummary);
  if (actualSummaryJson !== expectedSummaryJson) {
    failures.push("manifest evidence summary must match the referenced evidence JSON");
  }
}

function manifestFileEntries(manifest) {
  return Array.isArray(manifest.files) ? manifest.files : [];
}

function findManifestFileEntries(manifestPath, entries, targetPath) {
  const resolvedTarget = resolveManifestFile(manifestPath, targetPath);
  return entries.filter((entry) => {
    if (!entry || typeof entry !== "object" || !entry.path) {
      return false;
    }
    if (String(entry.path) === String(targetPath)) {
      return true;
    }
    if (!resolvedTarget) {
      return false;
    }
    const resolvedEntry = resolveManifestFile(manifestPath, entry.path);
    return resolvedEntry ? resolvedEntry === resolvedTarget : false;
  });
}

function resolveManifestFile(manifestPath, entryPath) {
  const candidates = [
    path.resolve(entryPath),
    path.resolve(path.dirname(manifestPath), entryPath),
    path.resolve(path.dirname(manifestPath), path.basename(entryPath)),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
}

function looksLikeRawToken(text) {
  return /Bearer\s+[A-Za-z0-9._-]+|[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|tokenValue|access_token|refresh_token/.test(text);
}

function stableJson(value) {
  return JSON.stringify(sortJson(value));
}

function sortJson(value) {
  if (Array.isArray(value)) {
    return value.map(sortJson);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, entry]) => [key, sortJson(entry)])
    );
  }
  return value;
}

function readEvidence(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    throw new Error(`Unable to read evidence JSON ${filePath}: ${error.message}`);
  }
}

function fileEntry(filePath) {
  const bytes = fs.readFileSync(filePath);
  const stats = fs.statSync(filePath);
  return {
    path: normalizedPath(filePath),
    bytes: bytes.length,
    sha256: `sha256:${sha256Hex(bytes)}`,
    modifiedAt: stats.mtime.toISOString(),
  };
}

function evidenceSummary(evidence) {
  return {
    artifactType: evidence.artifactType ?? null,
    artifactVersion: evidence.artifactVersion ?? null,
    status: evidence.status ?? null,
    checkedAt: evidence.checkedAt ?? null,
    environment: evidence.environment ?? null,
    serviceUrl: evidence.serviceUrl ?? null,
    sourceProvenance: evidence.sourceProvenance ?? null,
    activeModel: {
      trainingRunId: evidence.activeModel?.trainingRunId ?? null,
      modelVersion: evidence.activeModel?.modelVersion ?? null,
      algorithm: evidence.activeModel?.algorithm ?? null,
    },
    mutationFlow: {
      smokeRunId: evidence.mutationFlow?.smokeRunId ?? null,
      trainingRunId: evidence.mutationFlow?.trainingRunId ?? null,
      modelVersion: evidence.mutationFlow?.modelVersion ?? null,
      approvalId: evidence.mutationFlow?.approvalId ?? null,
      status: evidence.mutationFlow?.status ?? null,
      trainingRunStatus: evidence.mutationFlow?.trainingRunStatus ?? null,
      activationRequestStatus: evidence.mutationFlow?.activationRequestStatus ?? null,
      cleanupStatus: evidence.mutationFlow?.cleanupStatus ?? null,
    },
    tokenPolicy: {
      source: evidence.tokenPolicy?.source ?? null,
      premintedRequired: evidence.tokenPolicy?.premintedRequired ?? null,
      maxTtlSeconds: evidence.tokenPolicy?.maxTtlSeconds ?? null,
      actorSeparation: evidence.tokenPolicy?.actorSeparation ?? null,
    },
    thresholds: evidence.thresholds ?? null,
    analytics: {
      required: evidence.analytics?.required ?? null,
      serviceUrl: evidence.analytics?.serviceUrl ?? null,
      materializeStatus: evidence.analytics?.materializeStatus ?? null,
      trainingRunId: evidence.analytics?.trainingRunId ?? null,
      modelVersion: evidence.analytics?.modelVersion ?? null,
      metricWindow: evidence.analytics?.metricWindow ?? null,
      availableMetricValue: evidence.analytics?.availableMetricValue ?? null,
      fallbackMetricValue: evidence.analytics?.fallbackMetricValue ?? null,
    },
    prometheus: {
      requiredTargets: evidence.requiredTargets ?? evidence.prometheus?.requiredTargets ?? null,
      requiredAlerts: evidence.requiredAlerts ?? evidence.prometheus?.requiredAlerts ?? null,
      criticalAlertsFiring: evidence.prometheus?.criticalAlertsFiring ?? null,
    },
  };
}

function normalizedPath(filePath) {
  const absolute = path.resolve(filePath);
  return path.relative(process.cwd(), absolute).replaceAll(path.sep, "/");
}

function sha256Hex(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
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

function usage(message) {
  console.error(message);
  console.error(
    "Usage: node scripts/recommendation-ml-evidence-manifest.mjs "
      + "[--output=<manifest-json>] [--checksum-output=<sha256-file>] <artifact>... "
      + "or --verify=<manifest-json> [--checksum=<sha256-file>]"
  );
  process.exit(2);
}
