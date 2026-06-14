const restoreDrillArtifactType = "postgres_restore_drill_evidence";
const restoreDrillDatabase = "cf_promotion";
const sha256ArtifactPattern = /^sha256:[a-f0-9]{64}$/i;

type EvidenceRecord = Record<string, unknown>;

export type RestoreDrillEvidence = {
  restoreDrillRef: string;
  databaseName: string;
  backupPath: string;
  artifactHash: string;
  status: "PASSED";
  checkedAt: string;
  expiresAt?: string;
  note?: string;
};

export function parseRestoreDrillEvidenceJson(rawJson: string): RestoreDrillEvidence {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch {
    throw new Error("Restore drill evidence JSON không hợp lệ");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Restore drill evidence phải là JSON object");
  }
  const record = parsed as EvidenceRecord;
  if (stringValue(record.artifactType) !== restoreDrillArtifactType) {
    throw new Error("Artifact type không phải postgres_restore_drill_evidence");
  }

  const restoreDrillRef = requiredString(record.restoreDrillRef, "restoreDrillRef");
  const databaseName = requiredString(record.databaseName, "databaseName");
  const backupPath = requiredString(record.backupPath, "backupPath");
  const artifactHash = requiredString(record.artifactHash, "artifactHash").toLowerCase();
  const status = requiredString(record.status, "status").toUpperCase();
  const checkedAt = requiredString(record.checkedAt, "checkedAt");
  const expiresAt = optionalString(record.expiresAt);

  if (databaseName !== restoreDrillDatabase) {
    throw new Error(`Restore drill evidence phải thuộc ${restoreDrillDatabase}`);
  }
  if (status !== "PASSED") {
    throw new Error("Restore drill evidence phải có status PASSED");
  }
  if (!sha256ArtifactPattern.test(artifactHash)) {
    throw new Error("Artifact hash phải đúng format sha256:<64-hex>");
  }
  if (!isValidDate(checkedAt)) {
    throw new Error("checkedAt không hợp lệ");
  }
  if (expiresAt && !isValidDate(expiresAt)) {
    throw new Error("expiresAt không hợp lệ");
  }

  const temporaryDatabase = optionalString(record.temporaryDatabase);
  const note = temporaryDatabase ? `restore-check ${temporaryDatabase}` : optionalString(record.generatedAt);
  return {
    restoreDrillRef,
    databaseName,
    backupPath,
    artifactHash,
    status: "PASSED",
    checkedAt,
    expiresAt,
    note
  };
}

function requiredString(value: unknown, field: string) {
  const text = stringValue(value);
  if (!text) {
    throw new Error(`${field} là bắt buộc trong restore drill evidence`);
  }
  return text;
}

function optionalString(value: unknown) {
  return stringValue(value) || undefined;
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function isValidDate(value: string) {
  return !Number.isNaN(Date.parse(value));
}
