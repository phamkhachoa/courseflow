terraform {
  required_version = ">= 1.7.0"
}

variable "region" {
  type        = string
  description = "Cloud region for the managed staging data-platform runtime."
}

variable "environment" {
  type        = string
  description = "Runtime environment bound to this root module."
  default     = "staging"

  validation {
    condition     = var.environment == "staging"
    error_message = "This root module is bound to the staging runtime profile."
  }
}

variable "platform_name" {
  type        = string
  description = "Stable name used for tags, network names and service identities."
  default     = "enterprise-dp"
}

variable "cost_center" {
  type        = string
  description = "FinOps cost allocation tag for staging runtime resources."
}

variable "owner" {
  type        = string
  description = "Owning team for all managed runtime resources."
  default     = "data-platform-team"
}

locals {
  common_tags = {
    Environment = var.environment
    Platform    = var.platform_name
    Owner       = var.owner
    CostCenter  = var.cost_center
    ManagedBy   = "opentofu"
  }

  runtime_defaults = {
    environment        = var.environment
    region             = var.region
    platform_name      = var.platform_name
    private_network    = true
    workload_identity  = true
    external_secrets   = true
    encryption_at_rest = true
    metrics_enabled    = true
    tags               = local.common_tags
  }
}

module "event_backbone" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "event_backbone"
    ha_mode           = "multi_az"
    acl_enforced      = true
    consumer_lag_slo  = true
    backup_required   = true
    evidence_required = ["broker_health", "topic_acl", "consumer_lag"]
  })
}

module "outbox_relay" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "outbox_relay"
    ha_mode           = "active_active"
    idempotency       = true
    dead_letter_queue = true
    evidence_required = ["relay_deployment", "replay_proof", "idempotency_report"]
  })
}

module "cdc_connect" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "cdc"
    ha_mode           = "restartable_workers"
    offset_storage    = true
    schema_history    = true
    evidence_required = ["connector_status", "source_offset", "schema_history"]
  })
}

module "schema_registry" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id              = "schema_registry"
    ha_mode                 = "multi_az"
    compatibility_policy    = "backward_transitive"
    backup_required         = true
    producer_id_enforcement = true
    evidence_required       = ["subject_export", "compatibility_report", "registry_backup"]
  })
}

module "object_storage" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "object_storage"
    ha_mode           = "managed_regional"
    versioning        = true
    lifecycle_policy  = true
    private_endpoint  = true
    backup_required   = true
    evidence_required = ["bucket_policy", "lifecycle_policy", "encryption_report"]
  })
}

module "lakehouse_catalog" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id         = "table_format"
    table_format       = "apache_iceberg"
    ha_mode            = "catalog_ha"
    optimistic_locking = true
    snapshot_retention = true
    backup_required    = true
    evidence_required  = ["catalog_snapshot", "table_property_export", "snapshot_manifest"]
  })
}

module "batch_processing" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "batch_processing"
    engine            = "spark"
    retry_policy      = true
    artifact_version  = true
    event_log         = true
    evidence_required = ["job_run_log", "event_log", "pipeline_manifest"]
  })
}

module "sql_transform" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "sql_transform"
    engine            = "dbt_core"
    manifest_artifact = true
    rollback_enabled  = true
    evidence_required = ["dbt_run_results", "manifest", "test_artifact"]
  })
}

module "orchestration" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id            = "orchestration"
    engine                = "dagster"
    scheduler_ha          = true
    run_history_backup    = true
    distributed_launcher  = true
    service_identity_oidc = true
    alert_rules           = true
    evidence_required     = ["asset_materialization", "retry_history", "run_storage_backup"]
  })
}

module "data_quality" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "data_quality"
    blocking_gate     = true
    quarantine_output = true
    audit_required    = true
    evidence_required = ["blocking_quality_report", "quarantine_manifest", "evidence_export"]
  })
}

module "lakehouse_sql" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id         = "lakehouse_sql"
    engine             = "trino"
    row_level_security = true
    workload_metrics   = true
    private_endpoint   = true
    evidence_required  = ["governed_query_probe", "access_audit", "latency_slo"]
  })
}

module "observability" {
  source = "../modules/runtime-service-contract"

  runtime = merge(local.runtime_defaults, {
    service_id        = "observability"
    slo_dashboard     = true
    alert_rules       = true
    oncall_route      = true
    metrics_retention = true
    evidence_required = ["slo_dashboard", "alert_rules", "oncall_route", "metrics_retention"]
  })
}

output "runtime_service_matrix" {
  description = "P0 runtime services declared by the staging managed runtime root module."
  value = {
    event_backbone   = module.event_backbone.service_evidence
    outbox_relay     = module.outbox_relay.service_evidence
    cdc              = module.cdc_connect.service_evidence
    schema_registry  = module.schema_registry.service_evidence
    object_storage   = module.object_storage.service_evidence
    table_format     = module.lakehouse_catalog.service_evidence
    batch_processing = module.batch_processing.service_evidence
    sql_transform    = module.sql_transform.service_evidence
    orchestration    = module.orchestration.service_evidence
    data_quality     = module.data_quality.service_evidence
    lakehouse_sql    = module.lakehouse_sql.service_evidence
    observability    = module.observability.service_evidence
  }
}
