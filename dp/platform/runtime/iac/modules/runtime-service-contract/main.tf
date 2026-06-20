variable "runtime" {
  type        = any
  description = "Runtime service deployment contract emitted by a staging/prod root module."

  validation {
    condition     = can(var.runtime.service_id) && length(trimspace(tostring(var.runtime.service_id))) > 0
    error_message = "runtime.service_id is required."
  }

  validation {
    condition     = can(var.runtime.environment) && contains(["staging", "prod"], tostring(var.runtime.environment))
    error_message = "runtime.environment must be staging or prod."
  }

  validation {
    condition = (
      try(var.runtime.private_network, false) == true &&
      try(var.runtime.workload_identity, false) == true &&
      try(var.runtime.external_secrets, false) == true &&
      try(var.runtime.encryption_at_rest, false) == true
    )
    error_message = "production-like runtime contracts require private network, workload identity, external secrets and encryption at rest."
  }
}

locals {
  service_id        = tostring(var.runtime.service_id)
  evidence_required = try(tolist(var.runtime.evidence_required), [])
}

output "service_evidence" {
  description = "Machine-readable service contract used by runtime readiness and IaC evidence normalization."
  value = {
    service_id           = local.service_id
    environment          = tostring(var.runtime.environment)
    region               = try(tostring(var.runtime.region), null)
    secondary_region     = try(tostring(var.runtime.secondary_region), null)
    platform_name        = try(tostring(var.runtime.platform_name), null)
    private_network      = try(var.runtime.private_network, false)
    workload_identity    = try(var.runtime.workload_identity, false)
    external_secrets     = try(var.runtime.external_secrets, false)
    encryption_at_rest   = try(var.runtime.encryption_at_rest, false)
    deletion_protection  = try(var.runtime.deletion_protection, false)
    multi_az             = try(var.runtime.multi_az, false)
    backup_restore_drill = try(var.runtime.backup_restore_drill, false)
    metrics_enabled      = try(var.runtime.metrics_enabled, false)
    audit_siem_export    = try(var.runtime.audit_siem_export, false)
    backup_required      = try(var.runtime.backup_required, false)
    evidence_required    = local.evidence_required
    tags                 = try(var.runtime.tags, {})
  }
}
