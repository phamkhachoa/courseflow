#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const imageRef = process.argv[2] ?? process.env.RECOMMENDATION_ML_IMAGE_REF;
const evidenceFile = process.env.RECOMMENDATION_ML_IMAGE_CONTRACT_EVIDENCE_FILE;

if (!imageRef) {
  throw new Error("Usage: recommendation-ml-image-contract.mjs <image-ref>");
}

const image = inspectImage(imageRef);
const config = image.Config ?? {};
const checks = [];

record(
  "recommendation ml image runs as courseflow user",
  config.User === "courseflow",
  `user=${config.User ?? "<missing>"}`
);
record(
  "recommendation ml image exposes port 8080",
  Boolean(config.ExposedPorts?.["8080/tcp"]),
  `exposedPorts=${Object.keys(config.ExposedPorts ?? {}).join(",") || "<none>"}`
);

const env = new Set(config.Env ?? []);
record(
  "recommendation ml image disables startup migrations by default",
  env.has("RECOMMENDATION_ML_RUN_MIGRATIONS=false"),
  "RECOMMENDATION_ML_RUN_MIGRATIONS=false"
);
record(
  "recommendation ml image disables Python bytecode writes",
  env.has("PYTHONDONTWRITEBYTECODE=1"),
  "PYTHONDONTWRITEBYTECODE=1"
);

const healthcheck = config.Healthcheck?.Test ?? [];
const healthcheckText = healthcheck.join(" ");
record(
  "recommendation ml image healthcheck uses liveness endpoint",
  healthcheckText.includes("/health"),
  healthcheckText || "<missing>"
);
record(
  "recommendation ml image healthcheck does not use readiness endpoint",
  !healthcheckText.includes("/actuator/health"),
  healthcheckText || "<missing>"
);

const commandText = [
  ...(config.Entrypoint ?? []),
  ...(config.Cmd ?? []),
].join(" ");
record(
  "recommendation ml image starts uvicorn app",
  commandText.includes("uvicorn courseflow_ml.main:app"),
  commandText || "<missing>"
);
record(
  "recommendation ml image keeps migration execution explicitly gated",
  commandText.includes("RECOMMENDATION_ML_RUN_MIGRATIONS"),
  commandText || "<missing>"
);

writeEvidence();
console.log(`Recommendation ML image contract passed (${checks.length} checks)`);

function inspectImage(ref) {
  const raw = execFileSync("docker", ["image", "inspect", ref], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  const payload = JSON.parse(raw);
  if (!Array.isArray(payload) || payload.length !== 1) {
    throw new Error(`Expected one inspected image for ${ref}`);
  }
  return payload[0];
}

function record(name, pass, detail) {
  checks.push({ name, pass, detail });
  const marker = pass ? "PASS" : "FAIL";
  console.log(`[${marker}] ${name}: ${detail}`);
  if (!pass) {
    writeEvidence("fail", `${name}: ${detail}`);
    throw new Error(`${name}: ${detail}`);
  }
}

function writeEvidence(status = "pass", errorMessage = null) {
  if (!evidenceFile) {
    return;
  }
  const evidence = {
    artifactType: "recommendation_ml_image_contract_evidence",
    artifactVersion: 1,
    status,
    checkedAt: new Date().toISOString(),
    imageRef,
    checks,
    errorMessage,
  };
  fs.mkdirSync(path.dirname(evidenceFile), { recursive: true });
  fs.writeFileSync(evidenceFile, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  console.log(`Recommendation ML image contract evidence written to ${evidenceFile}`);
}
