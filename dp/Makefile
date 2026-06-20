.PHONY: validate test runtime-iac-contract-check schema-registry-runtime-smoke schema-registry-attestation schema-registry-auth-smoke schema-registry-storage-smoke data-plane-smoke live-lakehouse-smoke iceberg-catalog-smoke iceberg-catalog-smoke-from-live object-store-smoke object-store-smoke-from-live trino-sql-smoke trino-sql-smoke-from-live trino-iceberg-minio-smoke trino-iceberg-minio-smoke-from-live catalog-cross-engine-smoke catalog-cross-engine-smoke-from-live trino-runtime-security-smoke trino-runtime-security-smoke-from-live policy-decision-smoke oidc-auth-smoke secret-rotation-smoke catalog-runtime-ops-report orchestration-runtime-ops-report secret-rotation-ops-report managed-runtime-ops-reports production-ops-readiness-pack dagster-orchestration-smoke dagster-orchestration-smoke-from-live dagster-day2-smoke event-backbone-smoke broker-acl-smoke transactional-outbox-smoke live-bronze-ingestion-smoke orchestrated-publication-smoke live-quality-slo-smoke portfolio-release-smoke production-review-pack source-onboarding-release-gate partner-review-gate code-control-plane-gate production-readiness-gate ci check

PYTHON ?= python3.11
TERRAFORM ?= terraform
RUNTIME_IAC_CONTRACT_DIR ?= build/runtime-iac-contract-check
SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR ?= build/schema-registry-runtime-smoke
SCHEMA_REGISTRY_ATTESTATION_DIR ?= build/schema-registry-attestation
SCHEMA_REGISTRY_AUTH_SMOKE_DIR ?= build/schema-registry-auth-smoke
SCHEMA_REGISTRY_STORAGE_SMOKE_DIR ?= build/schema-registry-storage-smoke
DATA_PLANE_SMOKE_DIR ?= build/data-plane-smoke
LIVE_LAKEHOUSE_SMOKE_DIR ?= build/live-lakehouse-smoke
ICEBERG_CATALOG_SMOKE_DIR ?= build/iceberg-catalog-smoke
OBJECT_STORE_SMOKE_DIR ?= build/object-store-smoke
TRINO_SQL_SMOKE_DIR ?= build/trino-sql-smoke
TRINO_ICEBERG_MINIO_SMOKE_DIR ?= build/trino-iceberg-minio-smoke
CATALOG_CROSS_ENGINE_SMOKE_DIR ?= build/catalog-cross-engine-smoke
TRINO_RUNTIME_SECURITY_SMOKE_DIR ?= build/trino-runtime-security-smoke
POLICY_DECISION_SMOKE_DIR ?= build/policy-decision-smoke
OIDC_AUTH_SMOKE_DIR ?= build/oidc-auth-smoke
SECRET_ROTATION_SMOKE_DIR ?= build/secret-rotation-smoke
CATALOG_RUNTIME_OPS_DIR ?= build/catalog-runtime-ops
ORCHESTRATION_RUNTIME_OPS_DIR ?= build/orchestration-runtime-ops
SECRET_ROTATION_OPS_DIR ?= build/secret-rotation-ops
MANAGED_RUNTIME_OPS_REVIEW_DIR ?= build/managed-runtime-ops-review
DAGSTER_ORCHESTRATION_SMOKE_DIR ?= build/dagster-orchestration-smoke
DAGSTER_DAY2_SMOKE_DIR ?= build/dagster-day2-smoke
EVENT_BACKBONE_SMOKE_DIR ?= build/event-backbone-smoke
BROKER_ACL_SMOKE_DIR ?= build/broker-acl-smoke
TRANSACTIONAL_OUTBOX_SMOKE_DIR ?= build/transactional-outbox-smoke
LIVE_BRONZE_INGESTION_SMOKE_DIR ?= build/live-bronze-ingestion-smoke
ORCHESTRATED_PUBLICATION_SMOKE_DIR ?= build/orchestrated-publication-smoke
LIVE_QUALITY_SLO_SMOKE_DIR ?= build/live-quality-slo-smoke
PORTFOLIO_RELEASE_SMOKE_DIR ?= build/portfolio-release-smoke
SCHEMA_REGISTRY_RUNTIME_SMOKE_RELEASE ?= local-schema-registry-runtime-smoke
SCHEMA_REGISTRY_ATTESTATION_ENVIRONMENT ?= staging
DATA_PLANE_SMOKE_RELEASE ?= local-data-plane-smoke
LIVE_LAKEHOUSE_SMOKE_RELEASE ?= local-live-lakehouse-smoke
ICEBERG_CATALOG_SMOKE_RELEASE ?= local-iceberg-catalog-smoke
OBJECT_STORE_SMOKE_RELEASE ?= local-object-store-commit-smoke
TRINO_SQL_SMOKE_RELEASE ?= local-trino-sql-runtime-smoke
TRINO_ICEBERG_MINIO_SMOKE_RELEASE ?= local-trino-iceberg-minio-smoke
CATALOG_CROSS_ENGINE_SMOKE_RELEASE ?= local-catalog-cross-engine-smoke
TRINO_RUNTIME_SECURITY_SMOKE_RELEASE ?= local-trino-runtime-security-smoke
POLICY_DECISION_SMOKE_RELEASE ?= local-policy-decision-smoke
OIDC_AUTH_SMOKE_RELEASE ?= local-oidc-auth-smoke
SECRET_ROTATION_SMOKE_RELEASE ?= local-secret-rotation-smoke
MANAGED_RUNTIME_OPS_ENVIRONMENT ?= staging
MANAGED_RUNTIME_OPS_GENERATED_AT ?= 2026-06-19T02:20:00Z
DAGSTER_ORCHESTRATION_SMOKE_RELEASE ?= local-dagster-orchestration-smoke
DAGSTER_DAY2_SMOKE_RELEASE ?= local-dagster-day2-smoke
BROKER_ACL_SMOKE_RELEASE ?= local-broker-acl-smoke
TRANSACTIONAL_OUTBOX_SMOKE_RELEASE ?= local-transactional-outbox-smoke
LIVE_BRONZE_INGESTION_SMOKE_RELEASE ?= local-live-bronze-ingestion-smoke
ORCHESTRATED_PUBLICATION_SMOKE_RELEASE ?= local-orchestrated-live-publication-smoke
LIVE_QUALITY_SLO_SMOKE_RELEASE ?= local-live-quality-slo-smoke
PRODUCTION_REVIEW_DIR ?= build/production-review-pack
PRODUCTION_REVIEW_ENVIRONMENT ?= local
PRODUCTION_REVIEW_MANIFEST ?= $(PRODUCTION_REVIEW_DIR)/production-review-pack.json
PRODUCTION_REVIEW_GATE_DIR ?= build/production-review-gates
SOURCE_ACTIVATION_OPS_DIR ?= build/source-activation-ops
SOURCE_ONBOARDING_ENVIRONMENT ?= staging
SOURCE_ONBOARDING_AS_OF ?= 2026-06-19T02:05:00Z
SOURCE_ONBOARDING_OPS_REPORT ?= $(SOURCE_ACTIVATION_OPS_DIR)/$(SOURCE_ONBOARDING_ENVIRONMENT).json
SOURCE_ONBOARDING_REVIEW_DIR ?= build/source-onboarding-review-pack
SOURCE_ONBOARDING_REVIEW_MANIFEST ?= $(SOURCE_ONBOARDING_REVIEW_DIR)/production-review-pack.json
EVENT_BACKBONE_SMOKE_REPORT ?=
INGESTION_RUNTIME_REPORT ?=
CATALOG_LINEAGE_OPS_REPORT ?=
SEMANTIC_METRIC_SERVING_OPS_REPORT ?=
SOURCE_ACTIVATION_OPS_REPORT ?=
BACKFILL_READINESS_REPORT ?=
RUNTIME_READINESS_REPORT ?=
RUNTIME_IAC_PLAN ?=
RUNTIME_IAC_APPLY ?=
RUNTIME_DRIFT_REPORT ?=
RUNTIME_BACKUP_REPORT ?=
RUNTIME_DR_REPORT ?=
RUNTIME_HEALTH_REPORT ?=
WORKLOAD_BENCHMARK_REPORT ?=
SCHEMA_REGISTRY_RUNTIME_SMOKE_REPORT ?=
SCHEMA_REGISTRY_ATTESTATION_REPORT ?=
SCHEMA_REGISTRY_OPS_REPORT ?=
SCHEMA_REGISTRY_AUTH_SMOKE_REPORT ?=
SCHEMA_REGISTRY_STORAGE_SMOKE_REPORT ?=
LIVE_LAKEHOUSE_SMOKE_REPORT ?=
ICEBERG_CATALOG_SMOKE_REPORT ?=
OBJECT_STORE_SMOKE_REPORT ?=
TRINO_SQL_SMOKE_REPORT ?=
TRINO_ICEBERG_MINIO_SMOKE_REPORT ?=
CATALOG_CROSS_ENGINE_SMOKE_REPORT ?=
CATALOG_RUNTIME_OPS_REPORT ?=
ORCHESTRATION_RUNTIME_OPS_REPORT ?=
TRINO_RUNTIME_SECURITY_SMOKE_REPORT ?=
POLICY_DECISION_SMOKE_REPORT ?=
OIDC_AUTH_SMOKE_REPORT ?=
SECRET_ROTATION_SMOKE_REPORT ?=
SECRET_ROTATION_OPS_REPORT ?=
CATALOG_RUNTIME_EVIDENCE ?=
ORCHESTRATION_RUNTIME_EVIDENCE ?=
SECRET_ROTATION_EVIDENCE ?=
DAGSTER_ORCHESTRATION_SMOKE_REPORT ?=
DAGSTER_DAY2_SMOKE_REPORT ?=
BROKER_ACL_SMOKE_REPORT ?=
TRANSACTIONAL_OUTBOX_SMOKE_REPORT ?=
LIVE_BRONZE_INGESTION_SMOKE_REPORT ?=
ORCHESTRATED_PUBLICATION_SMOKE_REPORT ?=
LIVE_QUALITY_SLO_SMOKE_REPORT ?=
PORTFOLIO_RELEASE_SMOKE_REPORT ?=
EVENT_BACKBONE_TIMEOUT_SECONDS ?= 180
BROKER_ACL_TIMEOUT_SECONDS ?= 180
TRINO_SQL_TIMEOUT_SECONDS ?= 180
OBJECT_STORE_BUCKET ?= enterprise-dp-local-lakehouse
OBJECT_STORE_ENDPOINT_URL ?= http://localhost:19000

PRODUCTION_REVIEW_EXTRA_ARGS :=
ifneq ($(strip $(EVENT_BACKBONE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --event-backbone-smoke-report $(EVENT_BACKBONE_SMOKE_REPORT)
endif
ifneq ($(strip $(INGESTION_RUNTIME_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --ingestion-runtime-report $(INGESTION_RUNTIME_REPORT)
endif
ifneq ($(strip $(CATALOG_LINEAGE_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --catalog-lineage-ops-report $(CATALOG_LINEAGE_OPS_REPORT)
endif
ifneq ($(strip $(SEMANTIC_METRIC_SERVING_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --semantic-metric-serving-ops-report $(SEMANTIC_METRIC_SERVING_OPS_REPORT)
endif
ifneq ($(strip $(SOURCE_ACTIVATION_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --source-activation-ops-report $(SOURCE_ACTIVATION_OPS_REPORT)
endif
ifneq ($(strip $(BACKFILL_READINESS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --backfill-readiness-report $(BACKFILL_READINESS_REPORT)
endif
ifneq ($(strip $(RUNTIME_READINESS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-readiness-report $(RUNTIME_READINESS_REPORT)
endif
ifneq ($(strip $(RUNTIME_IAC_PLAN)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-iac-plan $(RUNTIME_IAC_PLAN)
endif
ifneq ($(strip $(RUNTIME_IAC_APPLY)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-iac-apply $(RUNTIME_IAC_APPLY)
endif
ifneq ($(strip $(RUNTIME_DRIFT_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-drift-report $(RUNTIME_DRIFT_REPORT)
endif
ifneq ($(strip $(RUNTIME_BACKUP_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-backup-report $(RUNTIME_BACKUP_REPORT)
endif
ifneq ($(strip $(RUNTIME_DR_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-dr-report $(RUNTIME_DR_REPORT)
endif
ifneq ($(strip $(RUNTIME_HEALTH_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --runtime-health-report $(RUNTIME_HEALTH_REPORT)
endif
ifneq ($(strip $(WORKLOAD_BENCHMARK_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --workload-benchmark-report $(WORKLOAD_BENCHMARK_REPORT)
endif
ifneq ($(strip $(SCHEMA_REGISTRY_RUNTIME_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --schema-registry-runtime-smoke-report $(SCHEMA_REGISTRY_RUNTIME_SMOKE_REPORT)
endif
ifneq ($(strip $(SCHEMA_REGISTRY_ATTESTATION_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --schema-registry-attestation-report $(SCHEMA_REGISTRY_ATTESTATION_REPORT)
endif
ifneq ($(strip $(SCHEMA_REGISTRY_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --schema-registry-ops-report $(SCHEMA_REGISTRY_OPS_REPORT)
endif
ifneq ($(strip $(SCHEMA_REGISTRY_AUTH_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --schema-registry-auth-smoke-report $(SCHEMA_REGISTRY_AUTH_SMOKE_REPORT)
endif
ifneq ($(strip $(SCHEMA_REGISTRY_STORAGE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --schema-registry-storage-smoke-report $(SCHEMA_REGISTRY_STORAGE_SMOKE_REPORT)
endif
ifneq ($(strip $(LIVE_LAKEHOUSE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_REPORT)
endif
ifneq ($(strip $(ICEBERG_CATALOG_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --iceberg-catalog-smoke-report $(ICEBERG_CATALOG_SMOKE_REPORT)
endif
ifneq ($(strip $(OBJECT_STORE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --object-store-smoke-report $(OBJECT_STORE_SMOKE_REPORT)
endif
ifneq ($(strip $(TRINO_SQL_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --trino-sql-smoke-report $(TRINO_SQL_SMOKE_REPORT)
endif
ifneq ($(strip $(TRINO_ICEBERG_MINIO_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --trino-iceberg-minio-smoke-report $(TRINO_ICEBERG_MINIO_SMOKE_REPORT)
endif
ifneq ($(strip $(CATALOG_CROSS_ENGINE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --catalog-cross-engine-smoke-report $(CATALOG_CROSS_ENGINE_SMOKE_REPORT)
endif
ifneq ($(strip $(CATALOG_RUNTIME_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --catalog-runtime-ops-report $(CATALOG_RUNTIME_OPS_REPORT)
endif
ifneq ($(strip $(ORCHESTRATION_RUNTIME_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --orchestration-runtime-ops-report $(ORCHESTRATION_RUNTIME_OPS_REPORT)
endif
ifneq ($(strip $(TRINO_RUNTIME_SECURITY_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --trino-runtime-security-smoke-report $(TRINO_RUNTIME_SECURITY_SMOKE_REPORT)
endif
ifneq ($(strip $(POLICY_DECISION_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --policy-decision-smoke-report $(POLICY_DECISION_SMOKE_REPORT)
endif
ifneq ($(strip $(OIDC_AUTH_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --oidc-auth-smoke-report $(OIDC_AUTH_SMOKE_REPORT)
endif
ifneq ($(strip $(SECRET_ROTATION_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --secret-rotation-smoke-report $(SECRET_ROTATION_SMOKE_REPORT)
endif
ifneq ($(strip $(SECRET_ROTATION_OPS_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --secret-rotation-ops-report $(SECRET_ROTATION_OPS_REPORT)
endif
ifneq ($(strip $(DAGSTER_ORCHESTRATION_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --dagster-orchestration-smoke-report $(DAGSTER_ORCHESTRATION_SMOKE_REPORT)
endif
ifneq ($(strip $(DAGSTER_DAY2_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --dagster-day2-smoke-report $(DAGSTER_DAY2_SMOKE_REPORT)
endif
ifneq ($(strip $(BROKER_ACL_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --broker-acl-smoke-report $(BROKER_ACL_SMOKE_REPORT)
endif
ifneq ($(strip $(TRANSACTIONAL_OUTBOX_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --transactional-outbox-smoke-report $(TRANSACTIONAL_OUTBOX_SMOKE_REPORT)
endif
ifneq ($(strip $(LIVE_BRONZE_INGESTION_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --live-bronze-ingestion-smoke-report $(LIVE_BRONZE_INGESTION_SMOKE_REPORT)
endif
ifneq ($(strip $(ORCHESTRATED_PUBLICATION_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --orchestrated-publication-smoke-report $(ORCHESTRATED_PUBLICATION_SMOKE_REPORT)
endif
ifneq ($(strip $(LIVE_QUALITY_SLO_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --live-quality-slo-smoke-report $(LIVE_QUALITY_SLO_SMOKE_REPORT)
endif
ifneq ($(strip $(PORTFOLIO_RELEASE_SMOKE_REPORT)),)
PRODUCTION_REVIEW_EXTRA_ARGS += --portfolio-release-smoke-report $(PORTFOLIO_RELEASE_SMOKE_REPORT)
endif

CATALOG_RUNTIME_OPS_EXTRA_ARGS :=
ifneq ($(strip $(CATALOG_RUNTIME_EVIDENCE)),)
CATALOG_RUNTIME_OPS_EXTRA_ARGS += --evidence $(CATALOG_RUNTIME_EVIDENCE)
endif

ORCHESTRATION_RUNTIME_OPS_EXTRA_ARGS :=
ifneq ($(strip $(ORCHESTRATION_RUNTIME_EVIDENCE)),)
ORCHESTRATION_RUNTIME_OPS_EXTRA_ARGS += --evidence $(ORCHESTRATION_RUNTIME_EVIDENCE)
endif

SECRET_ROTATION_OPS_EXTRA_ARGS :=
ifneq ($(strip $(SECRET_ROTATION_EVIDENCE)),)
SECRET_ROTATION_OPS_EXTRA_ARGS += --evidence $(SECRET_ROTATION_EVIDENCE)
endif

validate:
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli validate --root .

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests

runtime-iac-contract-check:
	rm -rf $(RUNTIME_IAC_CONTRACT_DIR)
	mkdir -p $(RUNTIME_IAC_CONTRACT_DIR)
	$(TERRAFORM) fmt -check -recursive platform/runtime/iac
	cp -R platform/runtime/iac/. $(RUNTIME_IAC_CONTRACT_DIR)/
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/staging init -backend=false -input=false -no-color
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/staging validate -no-color
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/staging validate -json > $(RUNTIME_IAC_CONTRACT_DIR)/staging-validate.json
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/prod init -backend=false -input=false -no-color
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/prod validate -no-color
	$(TERRAFORM) -chdir=$(RUNTIME_IAC_CONTRACT_DIR)/prod validate -json > $(RUNTIME_IAC_CONTRACT_DIR)/prod-validate.json

schema-registry-runtime-smoke:
	rm -rf $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli schema-registry-runtime-smoke \
		--root . \
		--output-dir $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/run \
		--output $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/schema-registry-runtime-smoke-report.json \
		--release-id $(SCHEMA_REGISTRY_RUNTIME_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

schema-registry-attestation:
	rm -rf $(SCHEMA_REGISTRY_ATTESTATION_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli schema-registry-attestation \
		--root . \
		--publication-manifest $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/run/schema-registry-publication-manifest.json \
		--schema-registry-runtime-smoke-report $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/schema-registry-runtime-smoke-report.json \
		--output $(SCHEMA_REGISTRY_ATTESTATION_DIR)/schema-registry-publication-attestation.json \
		--environment $(SCHEMA_REGISTRY_ATTESTATION_ENVIRONMENT) \
		--generated-at 2026-01-15T09:15:20Z

schema-registry-auth-smoke:
	rm -rf $(SCHEMA_REGISTRY_AUTH_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli schema-registry-auth-smoke \
		--root . \
		--output-dir $(SCHEMA_REGISTRY_AUTH_SMOKE_DIR)/run \
		--output $(SCHEMA_REGISTRY_AUTH_SMOKE_DIR)/schema-registry-auth-smoke-report.json \
		--release-id local-schema-registry-auth-smoke \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

schema-registry-storage-smoke:
	rm -rf $(SCHEMA_REGISTRY_STORAGE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli schema-registry-storage-smoke \
		--root . \
		--output-dir $(SCHEMA_REGISTRY_STORAGE_SMOKE_DIR)/run \
		--output $(SCHEMA_REGISTRY_STORAGE_SMOKE_DIR)/schema-registry-storage-smoke-report.json \
		--release-id local-schema-registry-storage-smoke \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

data-plane-smoke:
	rm -rf $(DATA_PLANE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli data-plane-smoke \
		--root . \
		--use-case-id finance-benefit-reconciliation \
		--output-dir $(DATA_PLANE_SMOKE_DIR)/run \
		--output $(DATA_PLANE_SMOKE_DIR)/data-plane-smoke-report.json \
		--release-id $(DATA_PLANE_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--built-at 2026-01-15T09:15:10Z \
		--evaluation-time 2026-01-15T09:15:15Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--snapshot-id finance-benefit-local-data-plane-smoke

live-lakehouse-smoke:
	rm -rf $(LIVE_LAKEHOUSE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli live-lakehouse-smoke \
		--root . \
		--output-dir $(LIVE_LAKEHOUSE_SMOKE_DIR)/run \
		--output $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--release-id $(LIVE_LAKEHOUSE_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--built-at 2026-01-15T09:15:10Z \
		--evaluation-time 2026-01-15T09:15:15Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--snapshot-id finance-benefit-local-live-lakehouse-smoke

iceberg-catalog-smoke: live-lakehouse-smoke iceberg-catalog-smoke-from-live

iceberg-catalog-smoke-from-live:
	rm -rf $(ICEBERG_CATALOG_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli iceberg-catalog-smoke \
		--root . \
		--output-dir $(ICEBERG_CATALOG_SMOKE_DIR)/run \
		--output $(ICEBERG_CATALOG_SMOKE_DIR)/iceberg-catalog-smoke-report.json \
		--live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--release-id $(ICEBERG_CATALOG_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

object-store-smoke: live-lakehouse-smoke object-store-smoke-from-live

object-store-smoke-from-live:
	rm -rf $(OBJECT_STORE_SMOKE_DIR)
	docker compose -f platform/runtime/local/docker-compose.yaml up -d minio
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli object-store-commit-smoke \
		--root . \
		--output-dir $(OBJECT_STORE_SMOKE_DIR)/run \
		--output $(OBJECT_STORE_SMOKE_DIR)/object-store-commit-smoke-report.json \
		--live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--bucket $(OBJECT_STORE_BUCKET) \
		--endpoint-url $(OBJECT_STORE_ENDPOINT_URL) \
		--release-id $(OBJECT_STORE_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

trino-sql-smoke: live-lakehouse-smoke trino-sql-smoke-from-live

trino-sql-smoke-from-live:
	rm -rf $(TRINO_SQL_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli trino-sql-runtime-smoke \
		--root . \
		--output-dir $(TRINO_SQL_SMOKE_DIR)/run \
		--output $(TRINO_SQL_SMOKE_DIR)/trino-sql-runtime-smoke-report.json \
		--live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--release-id $(TRINO_SQL_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(TRINO_SQL_TIMEOUT_SECONDS)

trino-iceberg-minio-smoke: live-lakehouse-smoke trino-iceberg-minio-smoke-from-live

trino-iceberg-minio-smoke-from-live:
	rm -rf $(TRINO_ICEBERG_MINIO_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli trino-iceberg-minio-smoke \
		--root . \
		--output-dir $(TRINO_ICEBERG_MINIO_SMOKE_DIR)/run \
		--output $(TRINO_ICEBERG_MINIO_SMOKE_DIR)/trino-iceberg-minio-smoke-report.json \
		--live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--release-id $(TRINO_ICEBERG_MINIO_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(TRINO_SQL_TIMEOUT_SECONDS)

catalog-cross-engine-smoke: trino-iceberg-minio-smoke catalog-cross-engine-smoke-from-live

catalog-cross-engine-smoke-from-live:
	rm -rf $(CATALOG_CROSS_ENGINE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli catalog-cross-engine-smoke \
		--root . \
		--output-dir $(CATALOG_CROSS_ENGINE_SMOKE_DIR)/run \
		--output $(CATALOG_CROSS_ENGINE_SMOKE_DIR)/catalog-cross-engine-smoke-report.json \
		--trino-iceberg-minio-smoke-report $(TRINO_ICEBERG_MINIO_SMOKE_DIR)/trino-iceberg-minio-smoke-report.json \
		--release-id $(CATALOG_CROSS_ENGINE_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(TRINO_SQL_TIMEOUT_SECONDS)

trino-runtime-security-smoke: live-lakehouse-smoke trino-iceberg-minio-smoke-from-live trino-runtime-security-smoke-from-live

trino-runtime-security-smoke-from-live:
	rm -rf $(TRINO_RUNTIME_SECURITY_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli trino-runtime-security-smoke \
		--root . \
		--output-dir $(TRINO_RUNTIME_SECURITY_SMOKE_DIR)/run \
		--output $(TRINO_RUNTIME_SECURITY_SMOKE_DIR)/trino-runtime-security-smoke-report.json \
		--trino-iceberg-minio-smoke-report $(TRINO_ICEBERG_MINIO_SMOKE_DIR)/trino-iceberg-minio-smoke-report.json \
		--release-id $(TRINO_RUNTIME_SECURITY_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(TRINO_SQL_TIMEOUT_SECONDS)

policy-decision-smoke:
	rm -rf $(POLICY_DECISION_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli policy-decision-smoke \
		--root . \
		--output-dir $(POLICY_DECISION_SMOKE_DIR)/run \
		--output $(POLICY_DECISION_SMOKE_DIR)/policy-decision-smoke-report.json \
		--release-id $(POLICY_DECISION_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

oidc-auth-smoke:
	rm -rf $(OIDC_AUTH_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli oidc-auth-smoke \
		--root . \
		--output-dir $(OIDC_AUTH_SMOKE_DIR)/run \
		--output $(OIDC_AUTH_SMOKE_DIR)/oidc-auth-smoke-report.json \
		--release-id $(OIDC_AUTH_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

secret-rotation-smoke:
	rm -rf $(SECRET_ROTATION_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli secret-rotation-smoke \
		--root . \
		--output-dir $(SECRET_ROTATION_SMOKE_DIR)/run \
		--output $(SECRET_ROTATION_SMOKE_DIR)/secret-rotation-smoke-report.json \
		--release-id $(SECRET_ROTATION_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

catalog-runtime-ops-report:
	rm -rf $(CATALOG_RUNTIME_OPS_DIR)
	- PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli catalog-runtime-ops-report \
		--root . \
		--output $(CATALOG_RUNTIME_OPS_DIR)/catalog-runtime-ops-report.json \
		--environment $(MANAGED_RUNTIME_OPS_ENVIRONMENT) \
		--generated-at $(MANAGED_RUNTIME_OPS_GENERATED_AT) $(CATALOG_RUNTIME_OPS_EXTRA_ARGS)
	test -f $(CATALOG_RUNTIME_OPS_DIR)/catalog-runtime-ops-report.json

orchestration-runtime-ops-report:
	rm -rf $(ORCHESTRATION_RUNTIME_OPS_DIR)
	- PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli orchestration-runtime-ops-report \
		--root . \
		--output $(ORCHESTRATION_RUNTIME_OPS_DIR)/orchestration-runtime-ops-report.json \
		--environment $(MANAGED_RUNTIME_OPS_ENVIRONMENT) \
		--generated-at $(MANAGED_RUNTIME_OPS_GENERATED_AT) $(ORCHESTRATION_RUNTIME_OPS_EXTRA_ARGS)
	test -f $(ORCHESTRATION_RUNTIME_OPS_DIR)/orchestration-runtime-ops-report.json

secret-rotation-ops-report:
	rm -rf $(SECRET_ROTATION_OPS_DIR)
	- PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli secret-rotation-ops-report \
		--root . \
		--output $(SECRET_ROTATION_OPS_DIR)/secret-rotation-ops-report.json \
		--environment $(MANAGED_RUNTIME_OPS_ENVIRONMENT) \
		--generated-at $(MANAGED_RUNTIME_OPS_GENERATED_AT) $(SECRET_ROTATION_OPS_EXTRA_ARGS)
	test -f $(SECRET_ROTATION_OPS_DIR)/secret-rotation-ops-report.json

managed-runtime-ops-reports: catalog-runtime-ops-report orchestration-runtime-ops-report secret-rotation-ops-report

production-ops-readiness-pack: managed-runtime-ops-reports
	rm -rf $(MANAGED_RUNTIME_OPS_REVIEW_DIR)
	$(MAKE) production-review-pack \
		PRODUCTION_REVIEW_DIR=$(MANAGED_RUNTIME_OPS_REVIEW_DIR) \
		PRODUCTION_REVIEW_ENVIRONMENT=$(MANAGED_RUNTIME_OPS_ENVIRONMENT) \
		CATALOG_RUNTIME_OPS_REPORT=$(CATALOG_RUNTIME_OPS_DIR)/catalog-runtime-ops-report.json \
		ORCHESTRATION_RUNTIME_OPS_REPORT=$(ORCHESTRATION_RUNTIME_OPS_DIR)/orchestration-runtime-ops-report.json \
		SECRET_ROTATION_OPS_REPORT=$(SECRET_ROTATION_OPS_DIR)/secret-rotation-ops-report.json

dagster-orchestration-smoke: live-lakehouse-smoke object-store-smoke-from-live trino-sql-smoke-from-live dagster-orchestration-smoke-from-live

dagster-orchestration-smoke-from-live:
	rm -rf $(DAGSTER_ORCHESTRATION_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli dagster-orchestration-smoke \
		--root . \
		--output-dir $(DAGSTER_ORCHESTRATION_SMOKE_DIR)/run \
		--output $(DAGSTER_ORCHESTRATION_SMOKE_DIR)/dagster-orchestration-smoke-report.json \
		--live-lakehouse-smoke-report $(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		--object-store-smoke-report $(OBJECT_STORE_SMOKE_DIR)/object-store-commit-smoke-report.json \
		--trino-sql-smoke-report $(TRINO_SQL_SMOKE_DIR)/trino-sql-runtime-smoke-report.json \
		--release-id $(DAGSTER_ORCHESTRATION_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

dagster-day2-smoke:
	rm -rf $(DAGSTER_DAY2_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli dagster-day2-smoke \
		--root . \
		--output-dir $(DAGSTER_DAY2_SMOKE_DIR)/run \
		--output $(DAGSTER_DAY2_SMOKE_DIR)/dagster-day2-smoke-report.json \
		--release-id $(DAGSTER_DAY2_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z

event-backbone-smoke:
	rm -rf $(EVENT_BACKBONE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli event-backbone-smoke \
		--root . \
		--output-dir $(EVENT_BACKBONE_SMOKE_DIR) \
		--output $(EVENT_BACKBONE_SMOKE_DIR)/event-backbone-smoke-report.json \
		--release-id $(DATA_PLANE_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--built-at 2026-01-15T09:15:10Z \
		--evaluation-time 2026-01-15T09:15:15Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--snapshot-id finance-benefit-local-event-backbone-smoke \
		--schema-registry-runtime-smoke-report $(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/schema-registry-runtime-smoke-report.json \
		--command-timeout-seconds $(EVENT_BACKBONE_TIMEOUT_SECONDS)

broker-acl-smoke:
	rm -rf $(BROKER_ACL_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli broker-acl-smoke \
		--root . \
		--output-dir $(BROKER_ACL_SMOKE_DIR)/run \
		--output $(BROKER_ACL_SMOKE_DIR)/broker-acl-smoke-report.json \
		--release-id $(BROKER_ACL_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(BROKER_ACL_TIMEOUT_SECONDS)

transactional-outbox-smoke:
	rm -rf $(TRANSACTIONAL_OUTBOX_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli transactional-outbox-smoke \
		--root . \
		--output-dir $(TRANSACTIONAL_OUTBOX_SMOKE_DIR)/run \
		--output $(TRANSACTIONAL_OUTBOX_SMOKE_DIR)/transactional-outbox-smoke-report.json \
		--release-id $(TRANSACTIONAL_OUTBOX_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--command-timeout-seconds $(EVENT_BACKBONE_TIMEOUT_SECONDS)

live-bronze-ingestion-smoke:
	rm -rf $(LIVE_BRONZE_INGESTION_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli live-bronze-ingestion-smoke \
		--root . \
		--output-dir $(LIVE_BRONZE_INGESTION_SMOKE_DIR)/run \
		--output $(LIVE_BRONZE_INGESTION_SMOKE_DIR)/live-bronze-ingestion-smoke-report.json \
		--release-id $(LIVE_BRONZE_INGESTION_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--command-timeout-seconds $(EVENT_BACKBONE_TIMEOUT_SECONDS)

orchestrated-publication-smoke:
	rm -rf $(ORCHESTRATED_PUBLICATION_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli orchestrated-publication-smoke \
		--root . \
		--output-dir $(ORCHESTRATED_PUBLICATION_SMOKE_DIR)/run \
		--output $(ORCHESTRATED_PUBLICATION_SMOKE_DIR)/orchestrated-publication-smoke-report.json \
		--live-bronze-ingestion-smoke-report $(LIVE_BRONZE_INGESTION_SMOKE_DIR)/live-bronze-ingestion-smoke-report.json \
		--release-id $(ORCHESTRATED_PUBLICATION_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--command-timeout-seconds $(EVENT_BACKBONE_TIMEOUT_SECONDS)

live-quality-slo-smoke:
	rm -rf $(LIVE_QUALITY_SLO_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli live-quality-slo-smoke \
		--root . \
		--output-dir $(LIVE_QUALITY_SLO_SMOKE_DIR)/run \
		--output $(LIVE_QUALITY_SLO_SMOKE_DIR)/live-quality-slo-smoke-report.json \
		--orchestrated-publication-smoke-report $(ORCHESTRATED_PUBLICATION_SMOKE_DIR)/orchestrated-publication-smoke-report.json \
		--release-id $(LIVE_QUALITY_SLO_SMOKE_RELEASE) \
		--environment local \
		--generated-at 2026-01-15T09:15:20Z \
		--freshness-slo-seconds 900 \
		--command-timeout-seconds $(EVENT_BACKBONE_TIMEOUT_SECONDS)

portfolio-release-smoke:
	rm -rf $(PORTFOLIO_RELEASE_SMOKE_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli portfolio-release-smoke \
		--root . \
		--output-dir $(PORTFOLIO_RELEASE_SMOKE_DIR)/run \
		--output $(PORTFOLIO_RELEASE_SMOKE_DIR)/portfolio-release-smoke-report.json \
		--environment local \
		--generated-at 2026-06-16T12:10:00Z

ci:
	$(MAKE) validate
	$(MAKE) runtime-iac-contract-check
	$(MAKE) test
	$(MAKE) schema-registry-runtime-smoke
	$(MAKE) schema-registry-attestation
	$(MAKE) schema-registry-auth-smoke
	$(MAKE) schema-registry-storage-smoke
	$(MAKE) event-backbone-smoke
	$(MAKE) broker-acl-smoke
	$(MAKE) transactional-outbox-smoke
	$(MAKE) live-bronze-ingestion-smoke
	$(MAKE) orchestrated-publication-smoke
	$(MAKE) live-quality-slo-smoke
	$(MAKE) data-plane-smoke
	$(MAKE) live-lakehouse-smoke
	$(MAKE) iceberg-catalog-smoke-from-live
	$(MAKE) object-store-smoke-from-live
	$(MAKE) trino-sql-smoke-from-live
	$(MAKE) trino-iceberg-minio-smoke-from-live
	$(MAKE) catalog-cross-engine-smoke-from-live
	$(MAKE) trino-runtime-security-smoke-from-live
	$(MAKE) policy-decision-smoke
	$(MAKE) oidc-auth-smoke
	$(MAKE) secret-rotation-smoke
	$(MAKE) dagster-orchestration-smoke-from-live
	$(MAKE) dagster-day2-smoke
	$(MAKE) portfolio-release-smoke
	$(MAKE) production-review-pack \
		EVENT_BACKBONE_SMOKE_REPORT=$(EVENT_BACKBONE_SMOKE_DIR)/event-backbone-smoke-report.json \
		INGESTION_RUNTIME_REPORT=$(EVENT_BACKBONE_SMOKE_DIR)/ingestion-runtime/event-cdc-ingestion-runtime-report.json \
		CATALOG_LINEAGE_OPS_REPORT=$(CATALOG_LINEAGE_OPS_REPORT) \
		SEMANTIC_METRIC_SERVING_OPS_REPORT=$(SEMANTIC_METRIC_SERVING_OPS_REPORT) \
		SOURCE_ACTIVATION_OPS_REPORT=$(SOURCE_ACTIVATION_OPS_REPORT) \
		BACKFILL_READINESS_REPORT=$(BACKFILL_READINESS_REPORT) \
		RUNTIME_READINESS_REPORT=$(RUNTIME_READINESS_REPORT) \
		RUNTIME_IAC_PLAN=$(RUNTIME_IAC_PLAN) \
		RUNTIME_IAC_APPLY=$(RUNTIME_IAC_APPLY) \
		RUNTIME_DRIFT_REPORT=$(RUNTIME_DRIFT_REPORT) \
		RUNTIME_BACKUP_REPORT=$(RUNTIME_BACKUP_REPORT) \
		RUNTIME_DR_REPORT=$(RUNTIME_DR_REPORT) \
		RUNTIME_HEALTH_REPORT=$(RUNTIME_HEALTH_REPORT) \
		WORKLOAD_BENCHMARK_REPORT=$(WORKLOAD_BENCHMARK_REPORT) \
		SCHEMA_REGISTRY_RUNTIME_SMOKE_REPORT=$(SCHEMA_REGISTRY_RUNTIME_SMOKE_DIR)/schema-registry-runtime-smoke-report.json \
		SCHEMA_REGISTRY_ATTESTATION_REPORT=$(SCHEMA_REGISTRY_ATTESTATION_DIR)/schema-registry-publication-attestation.json \
		SCHEMA_REGISTRY_OPS_REPORT=$(SCHEMA_REGISTRY_OPS_REPORT) \
		SCHEMA_REGISTRY_AUTH_SMOKE_REPORT=$(SCHEMA_REGISTRY_AUTH_SMOKE_DIR)/schema-registry-auth-smoke-report.json \
		SCHEMA_REGISTRY_STORAGE_SMOKE_REPORT=$(SCHEMA_REGISTRY_STORAGE_SMOKE_DIR)/schema-registry-storage-smoke-report.json \
		LIVE_LAKEHOUSE_SMOKE_REPORT=$(LIVE_LAKEHOUSE_SMOKE_DIR)/live-lakehouse-smoke-report.json \
		ICEBERG_CATALOG_SMOKE_REPORT=$(ICEBERG_CATALOG_SMOKE_DIR)/iceberg-catalog-smoke-report.json \
		OBJECT_STORE_SMOKE_REPORT=$(OBJECT_STORE_SMOKE_DIR)/object-store-commit-smoke-report.json \
		TRINO_SQL_SMOKE_REPORT=$(TRINO_SQL_SMOKE_DIR)/trino-sql-runtime-smoke-report.json \
		TRINO_ICEBERG_MINIO_SMOKE_REPORT=$(TRINO_ICEBERG_MINIO_SMOKE_DIR)/trino-iceberg-minio-smoke-report.json \
		CATALOG_CROSS_ENGINE_SMOKE_REPORT=$(CATALOG_CROSS_ENGINE_SMOKE_DIR)/catalog-cross-engine-smoke-report.json \
		CATALOG_RUNTIME_OPS_REPORT=$(CATALOG_RUNTIME_OPS_REPORT) \
		ORCHESTRATION_RUNTIME_OPS_REPORT=$(ORCHESTRATION_RUNTIME_OPS_REPORT) \
		TRINO_RUNTIME_SECURITY_SMOKE_REPORT=$(TRINO_RUNTIME_SECURITY_SMOKE_DIR)/trino-runtime-security-smoke-report.json \
		POLICY_DECISION_SMOKE_REPORT=$(POLICY_DECISION_SMOKE_DIR)/policy-decision-smoke-report.json \
		OIDC_AUTH_SMOKE_REPORT=$(OIDC_AUTH_SMOKE_DIR)/oidc-auth-smoke-report.json \
		SECRET_ROTATION_SMOKE_REPORT=$(SECRET_ROTATION_SMOKE_DIR)/secret-rotation-smoke-report.json \
		SECRET_ROTATION_OPS_REPORT=$(SECRET_ROTATION_OPS_REPORT) \
		DAGSTER_ORCHESTRATION_SMOKE_REPORT=$(DAGSTER_ORCHESTRATION_SMOKE_DIR)/dagster-orchestration-smoke-report.json \
		DAGSTER_DAY2_SMOKE_REPORT=$(DAGSTER_DAY2_SMOKE_DIR)/dagster-day2-smoke-report.json \
		BROKER_ACL_SMOKE_REPORT=$(BROKER_ACL_SMOKE_DIR)/broker-acl-smoke-report.json \
		TRANSACTIONAL_OUTBOX_SMOKE_REPORT=$(TRANSACTIONAL_OUTBOX_SMOKE_DIR)/transactional-outbox-smoke-report.json \
		LIVE_BRONZE_INGESTION_SMOKE_REPORT=$(LIVE_BRONZE_INGESTION_SMOKE_DIR)/live-bronze-ingestion-smoke-report.json \
		ORCHESTRATED_PUBLICATION_SMOKE_REPORT=$(ORCHESTRATED_PUBLICATION_SMOKE_DIR)/orchestrated-publication-smoke-report.json \
		LIVE_QUALITY_SLO_SMOKE_REPORT=$(LIVE_QUALITY_SLO_SMOKE_DIR)/live-quality-slo-smoke-report.json \
		PORTFOLIO_RELEASE_SMOKE_REPORT=$(PORTFOLIO_RELEASE_SMOKE_DIR)/portfolio-release-smoke-report.json
	$(MAKE) code-control-plane-gate

production-review-pack:
	rm -rf $(PRODUCTION_REVIEW_DIR)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli production-review-pack \
		--root . \
		--output-dir $(PRODUCTION_REVIEW_DIR) \
		--environment $(PRODUCTION_REVIEW_ENVIRONMENT) \
		--generated-at 2026-06-16T12:05:00Z \
		--release-id $(DATA_PLANE_SMOKE_RELEASE) \
		--smoke-generated-at 2026-01-15T09:15:20Z \
		--ingested-at 2026-01-15T09:15:05Z \
		--built-at 2026-01-15T09:15:10Z \
		--evaluation-time 2026-01-15T09:15:15Z \
		--schema-id registry:finance.benefit_settled.v1:1 \
		--snapshot-id finance-benefit-local-data-plane-smoke $(PRODUCTION_REVIEW_EXTRA_ARGS)

source-onboarding-release-gate:
	rm -rf $(SOURCE_ACTIVATION_OPS_DIR) $(SOURCE_ONBOARDING_REVIEW_DIR)
	- PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli source-activation-ops-report \
		--root . \
		--output $(SOURCE_ONBOARDING_OPS_REPORT) \
		--environment $(SOURCE_ONBOARDING_ENVIRONMENT) \
		--as-of $(SOURCE_ONBOARDING_AS_OF)
	test -f $(SOURCE_ONBOARDING_OPS_REPORT)
	$(MAKE) production-review-pack \
		PRODUCTION_REVIEW_DIR=$(SOURCE_ONBOARDING_REVIEW_DIR) \
		PRODUCTION_REVIEW_ENVIRONMENT=$(SOURCE_ONBOARDING_ENVIRONMENT) \
		SOURCE_ACTIVATION_OPS_REPORT=$(SOURCE_ONBOARDING_OPS_REPORT)
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli production-review-gate \
		--manifest $(SOURCE_ONBOARDING_REVIEW_MANIFEST) \
		--profile source-onboarding \
		--environment $(SOURCE_ONBOARDING_ENVIRONMENT) \
		--output $(PRODUCTION_REVIEW_GATE_DIR)/source-onboarding-release-gate.json

partner-review-gate:
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli production-review-gate \
		--manifest $(PRODUCTION_REVIEW_MANIFEST) \
		--profile partner-review \
		--environment $(PRODUCTION_REVIEW_ENVIRONMENT) \
		--output $(PRODUCTION_REVIEW_GATE_DIR)/partner-review-gate.json

code-control-plane-gate:
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli production-review-gate \
		--manifest $(PRODUCTION_REVIEW_MANIFEST) \
		--profile code-control-plane \
		--environment $(PRODUCTION_REVIEW_ENVIRONMENT) \
		--output $(PRODUCTION_REVIEW_GATE_DIR)/code-control-plane-gate.json

production-readiness-gate:
	PYTHONPATH=src $(PYTHON) -m enterprise_dp.cli production-review-gate \
		--manifest $(PRODUCTION_REVIEW_MANIFEST) \
		--profile production-ready \
		--environment $(PRODUCTION_REVIEW_ENVIRONMENT) \
		--output $(PRODUCTION_REVIEW_GATE_DIR)/production-readiness-gate.json

check: validate test
