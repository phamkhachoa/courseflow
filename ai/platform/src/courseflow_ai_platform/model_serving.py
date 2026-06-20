from __future__ import annotations

import importlib.util
import sys
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

if TYPE_CHECKING:
    from courseflow_ai_platform.model_audit import ModelAuditStore

CALL_METHODS = ("predict", "recommend", "assist")
AUDIT_FAILURE_MODES = ("fail_open", "fail_closed")


class ModelServingError(ValueError):
    """Raised when a model cannot be served through the platform facade."""


@dataclass(frozen=True, slots=True)
class ServedModel:
    model_id: str
    artifact_id: str
    artifact_manifest: str
    product: str
    use_case_id: str
    status: str
    entrypoint: str
    method: str
    human_in_the_loop_required: bool

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "artifactId": self.artifact_id,
            "artifactManifest": self.artifact_manifest,
            "entrypoint": self.entrypoint,
            "humanInTheLoopRequired": self.human_in_the_loop_required,
            "method": self.method,
            "modelId": self.model_id,
            "product": self.product,
            "status": self.status,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class ModelServingResult:
    model_id: str
    artifact_id: str
    artifact_manifest: str
    method: str
    latency_ms: float
    output: dict[str, Any]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactId": self.artifact_id,
            "artifactManifest": self.artifact_manifest,
            "latencyMs": self.latency_ms,
            "method": self.method,
            "modelId": self.model_id,
            "output": self.output,
            "requiresHumanReview": self.requires_human_review,
        }


@dataclass(frozen=True, slots=True)
class ModelServingRequest:
    request_id: str
    tenant_id: str
    model_id: str
    payload: dict[str, Any]
    fallback_output: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ModelServingRequest:
        request_id = require_non_empty_str(row, "request_id", "model serving request")
        tenant_id = require_non_empty_str(row, "tenant_id", "model serving request")
        model_id = require_non_empty_str(row, "model_id", "model serving request")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            raise ModelServingError("model serving request payload must be a mapping")
        fallback_output = row.get("fallback_output")
        if fallback_output is not None and not isinstance(fallback_output, dict):
            raise ModelServingError("model serving request fallback_output must be a mapping")
        return cls(
            request_id=request_id,
            tenant_id=tenant_id,
            model_id=model_id,
            payload=payload,
            fallback_output=fallback_output,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fallbackOutput": self.fallback_output,
            "modelId": self.model_id,
            "payload": self.payload,
            "requestId": self.request_id,
            "tenantId": self.tenant_id,
        }


@dataclass(frozen=True, slots=True)
class ModelServingGatewayResponse:
    request_id: str
    tenant_id: str
    model_id: str
    status: str
    output: dict[str, Any]
    latency_ms: float
    model_latency_ms: float
    requires_human_review: bool
    fallback_used: bool
    error_code: str = ""
    error_message: str = ""
    artifact_id: str = ""
    artifact_manifest: str = ""
    method: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactId": self.artifact_id,
            "artifactManifest": self.artifact_manifest,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "fallbackUsed": self.fallback_used,
            "latencyMs": self.latency_ms,
            "method": self.method,
            "modelId": self.model_id,
            "modelLatencyMs": self.model_latency_ms,
            "output": self.output,
            "requestId": self.request_id,
            "requiresHumanReview": self.requires_human_review,
            "status": self.status,
            "tenantId": self.tenant_id,
        }


@dataclass(frozen=True, slots=True)
class ModelServingMetricsSnapshot:
    request_count: int
    success_count: int
    fallback_count: int
    error_count: int
    human_review_count: int
    audit_record_count: int
    audit_failure_count: int
    by_model: dict[str, dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditFailureCount": self.audit_failure_count,
            "auditRecordCount": self.audit_record_count,
            "byModel": self.by_model,
            "errorCount": self.error_count,
            "fallbackCount": self.fallback_count,
            "humanReviewCount": self.human_review_count,
            "requestCount": self.request_count,
            "successCount": self.success_count,
        }


class ModelServingMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.success_count = 0
        self.fallback_count = 0
        self.error_count = 0
        self.human_review_count = 0
        self.audit_record_count = 0
        self.audit_failure_count = 0
        self._by_model: dict[str, dict[str, int]] = {}

    def record(self, response: ModelServingGatewayResponse) -> None:
        self.request_count += 1
        if response.status == "ok":
            self.success_count += 1
        elif response.status == "fallback":
            self.fallback_count += 1
            self.error_count += 1
        else:
            self.error_count += 1
        if response.requires_human_review:
            self.human_review_count += 1

        row = self._model_row(response.model_id)
        row["request"] += 1
        if response.status == "ok":
            row["ok"] += 1
        elif response.status == "fallback":
            row["fallback"] += 1
            row["error"] += 1
        else:
            row["error"] += 1
        if response.requires_human_review:
            row["humanReview"] += 1

    def record_audit_success(self, model_id: str) -> None:
        self.audit_record_count += 1
        self._model_row(model_id)["auditRecord"] += 1

    def record_audit_failure(self, model_id: str) -> None:
        self.audit_failure_count += 1
        self._model_row(model_id)["auditFailure"] += 1

    def snapshot(self) -> ModelServingMetricsSnapshot:
        return ModelServingMetricsSnapshot(
            request_count=self.request_count,
            success_count=self.success_count,
            fallback_count=self.fallback_count,
            error_count=self.error_count,
            human_review_count=self.human_review_count,
            audit_record_count=self.audit_record_count,
            audit_failure_count=self.audit_failure_count,
            by_model={
                model_id: dict(values)
                for model_id, values in sorted(self._by_model.items())
            },
        )

    def _model_row(self, model_id: str) -> dict[str, int]:
        return self._by_model.setdefault(
            model_id,
            {
                "auditFailure": 0,
                "auditRecord": 0,
                "error": 0,
                "fallback": 0,
                "humanReview": 0,
                "ok": 0,
                "request": 0,
            },
        )


class ModelServingGateway:
    """API-boundary envelope around the model serving facade."""

    def __init__(
        self,
        ai_root: Path | str,
        *,
        fallback_outputs: Mapping[str, dict[str, Any]] | None = None,
        audit_store: ModelAuditStore | None = None,
        audit_retention_days: int = 30,
        audit_failure_mode: str = "fail_open",
    ) -> None:
        if audit_failure_mode not in AUDIT_FAILURE_MODES:
            allowed = ", ".join(AUDIT_FAILURE_MODES)
            raise ModelServingError(f"audit_failure_mode must be one of: {allowed}")
        self.facade = ModelServingFacade(ai_root)
        self.fallback_outputs = dict(fallback_outputs or {})
        self.audit_store = audit_store
        self.audit_retention_days = audit_retention_days
        self.audit_failure_mode = audit_failure_mode
        self.metrics = ModelServingMetrics()

    def invoke(
        self,
        request: ModelServingRequest | dict[str, Any],
    ) -> ModelServingGatewayResponse:
        serving_request = (
            request
            if isinstance(request, ModelServingRequest)
            else ModelServingRequest.from_dict(request)
        )
        started = time.perf_counter()
        try:
            result = self.facade.serve(serving_request.model_id, serving_request.payload)
            response = ModelServingGatewayResponse(
                request_id=serving_request.request_id,
                tenant_id=serving_request.tenant_id,
                model_id=serving_request.model_id,
                status="ok",
                output=result.output,
                latency_ms=round((time.perf_counter() - started) * 1000, 6),
                model_latency_ms=result.latency_ms,
                requires_human_review=result.requires_human_review,
                fallback_used=False,
                artifact_id=result.artifact_id,
                artifact_manifest=result.artifact_manifest,
                method=result.method,
            )
        except Exception as exc:
            response = self._error_response(serving_request, started, exc)
        final_response = self._record_audit(serving_request, response)
        self.metrics.record(final_response)
        return final_response

    def snapshot_metrics(self) -> ModelServingMetricsSnapshot:
        return self.metrics.snapshot()

    def _record_audit(
        self,
        request: ModelServingRequest,
        response: ModelServingGatewayResponse,
    ) -> ModelServingGatewayResponse:
        if self.audit_store is None:
            return response
        try:
            from courseflow_ai_platform.model_audit import build_model_audit_record

            self.audit_store.append(
                build_model_audit_record(
                    request,
                    response,
                    retention_days=self.audit_retention_days,
                )
            )
        except Exception as exc:
            self.metrics.record_audit_failure(response.model_id)
            if self.audit_failure_mode == "fail_closed":
                return ModelServingGatewayResponse(
                    request_id=response.request_id,
                    tenant_id=response.tenant_id,
                    model_id=response.model_id,
                    status="error",
                    output={},
                    latency_ms=response.latency_ms,
                    model_latency_ms=response.model_latency_ms,
                    requires_human_review=True,
                    fallback_used=False,
                    error_code="model_audit_failed",
                    error_message=safe_error_message(exc),
                    artifact_id=response.artifact_id,
                    artifact_manifest=response.artifact_manifest,
                    method=response.method,
                )
            return response

        self.metrics.record_audit_success(response.model_id)
        return response

    def _error_response(
        self,
        request: ModelServingRequest,
        started: float,
        exc: Exception,
    ) -> ModelServingGatewayResponse:
        fallback_output = request.fallback_output or self.fallback_outputs.get(request.model_id)
        if fallback_output is not None:
            return ModelServingGatewayResponse(
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                model_id=request.model_id,
                status="fallback",
                output=dict(fallback_output),
                latency_ms=round((time.perf_counter() - started) * 1000, 6),
                model_latency_ms=0.0,
                requires_human_review=True,
                fallback_used=True,
                error_code="model_invocation_failed",
                error_message=safe_error_message(exc),
            )
        return ModelServingGatewayResponse(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            model_id=request.model_id,
            status="error",
            output={},
            latency_ms=round((time.perf_counter() - started) * 1000, 6),
            model_latency_ms=0.0,
            requires_human_review=True,
            fallback_used=False,
            error_code="model_invocation_failed",
            error_message=safe_error_message(exc),
        )


class ModelServingFacade:
    """Manifest-backed runtime facade for deterministic model baselines."""

    def __init__(self, ai_root: Path | str) -> None:
        self.root = Path(ai_root)
        self._model_index = build_manifest_index(self.root)

    def catalog(self) -> tuple[ServedModel, ...]:
        models: list[ServedModel] = []
        for manifest_path, manifest in sorted(
            self._model_index.values(),
            key=lambda item: require_str(item[1], "model_id", str(item[0])),
        ):
            try:
                model = self._build_served_model(manifest_path, manifest)
            except ModelServingError:
                continue
            models.append(model)
        return tuple(models)

    def serve(self, model_id: str, payload: dict[str, Any]) -> ModelServingResult:
        manifest_record = self._model_index.get(model_id)
        if manifest_record is None:
            raise ModelServingError(f"unknown model_id: {model_id}")
        manifest_path, manifest = manifest_record
        served_model = self._build_served_model(manifest_path, manifest)
        model_instance, module = instantiate_model(self.root, manifest)
        method = getattr(model_instance, served_model.method)
        request_payload = coerce_payload(module, model_instance, served_model.method, payload)

        started = time.perf_counter()
        raw_output = method(request_payload)
        latency_ms = round((time.perf_counter() - started) * 1000, 6)
        output = output_to_dict(raw_output)
        output_model_id = output.get("modelId") or output.get("model_id")
        if output_model_id is not None and output_model_id != model_id:
            raise ModelServingError(
                f"model output id {output_model_id!r} does not match request {model_id!r}"
            )

        return ModelServingResult(
            model_id=model_id,
            artifact_id=served_model.artifact_id,
            artifact_manifest=served_model.artifact_manifest,
            method=served_model.method,
            latency_ms=latency_ms,
            output=output,
            requires_human_review=bool(
                output.get("requiresHumanReview", output.get("requires_human_review", False))
            ),
        )

    def _build_served_model(
        self,
        manifest_path: Path,
        manifest: dict[str, Any],
    ) -> ServedModel:
        if require_str(manifest, "artifact_type", str(manifest_path)) != "source_algorithm":
            raise ModelServingError("only source_algorithm manifests are directly serveable")

        model_instance, _ = instantiate_model(self.root, manifest)
        method = first_supported_method(model_instance)
        model_id = require_str(manifest, "model_id", str(manifest_path))
        runtime = require_mapping(manifest, "runtime", f"manifest {model_id}")
        governance = require_mapping(manifest, "governance", f"manifest {model_id}")
        return ServedModel(
            model_id=model_id,
            artifact_id=require_str(manifest, "artifact_id", f"manifest {model_id}"),
            artifact_manifest=str(manifest_path.relative_to(self.root)),
            product=require_str(manifest, "product", f"manifest {model_id}"),
            use_case_id=require_str(manifest, "use_case_id", f"manifest {model_id}"),
            status=require_str(manifest, "status", f"manifest {model_id}"),
            entrypoint=require_str(runtime, "entrypoint", f"manifest {model_id} runtime"),
            method=method,
            human_in_the_loop_required=bool(
                governance.get("human_in_the_loop_required", False)
            ),
        )


def build_model_serving_catalog(ai_root: Path | str) -> tuple[ServedModel, ...]:
    return ModelServingFacade(ai_root).catalog()


def serve_model(
    ai_root: Path | str,
    model_id: str,
    payload: dict[str, Any],
) -> ModelServingResult:
    return ModelServingFacade(ai_root).serve(model_id, payload)


def invoke_model_serving_gateway(
    ai_root: Path | str,
    request: ModelServingRequest | dict[str, Any],
    *,
    fallback_outputs: Mapping[str, dict[str, Any]] | None = None,
    audit_store: ModelAuditStore | None = None,
    audit_retention_days: int = 30,
    audit_failure_mode: str = "fail_open",
) -> ModelServingGatewayResponse:
    return ModelServingGateway(
        ai_root,
        fallback_outputs=fallback_outputs,
        audit_store=audit_store,
        audit_retention_days=audit_retention_days,
        audit_failure_mode=audit_failure_mode,
    ).invoke(request)


def build_manifest_index(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    if not manifest_dir.exists():
        raise RegistryValidationError(f"artifact manifest directory does not exist: {manifest_dir}")
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for manifest_path in sorted(manifest_dir.glob("*.yaml")):
        manifest = load_yaml(manifest_path)
        model_id = require_str(manifest, "model_id", str(manifest_path))
        if model_id in result:
            raise RegistryValidationError(f"duplicate model manifest for model_id: {model_id}")
        result[model_id] = (manifest_path, manifest)
    return result


def instantiate_model(root: Path, manifest: dict[str, Any]) -> tuple[Any, ModuleType]:
    model_id = require_str(manifest, "model_id", "model manifest")
    artifact_uri = require_str(manifest, "artifact_uri", f"manifest {model_id}")
    runtime = require_mapping(manifest, "runtime", f"manifest {model_id}")
    entrypoint = require_str(runtime, "entrypoint", f"manifest {model_id} runtime")
    _, _, class_name = entrypoint.partition(":")
    if not class_name:
        raise ModelServingError(f"manifest {model_id} runtime entrypoint must include class")

    module = load_module(root / artifact_uri, f"model_serving_{sanitize_module_name(model_id)}")
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise ModelServingError(f"manifest {model_id} class not found: {class_name}")
    try:
        return model_class(), module
    except TypeError as exc:
        raise ModelServingError(f"manifest {model_id} class cannot be instantiated") from exc


def first_supported_method(model_instance: Any) -> str:
    for method_name in CALL_METHODS:
        if callable(getattr(model_instance, method_name, None)):
            return method_name
    raise ModelServingError("model does not expose predict, recommend or assist")


def coerce_payload(
    module: ModuleType,
    model_instance: Any,
    method: str,
    payload: dict[str, Any],
) -> Any:
    if method != "assist":
        return payload
    input_class_name = model_instance.__class__.__name__.removesuffix("Baseline") + "Input"
    input_class = getattr(module, input_class_name, None)
    if input_class is None:
        return payload
    return input_class(**payload)


def output_to_dict(raw_output: Any) -> dict[str, Any]:
    if hasattr(raw_output, "to_dict") and callable(raw_output.to_dict):
        output = raw_output.to_dict()
    elif is_dataclass(raw_output):
        output = asdict(raw_output)
    elif isinstance(raw_output, dict):
        output = raw_output
    else:
        raise ModelServingError(
            f"model output must be a dict, dataclass or expose to_dict: {type(raw_output)}"
        )
    if not isinstance(output, dict):
        raise ModelServingError("model output conversion did not produce a mapping")
    return output


def load_module(path: Path, module_name: str) -> ModuleType:
    if not path.exists():
        raise ModelServingError(f"model source does not exist: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ModelServingError(f"cannot load model source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ModelServingError(f"cannot execute model source: {path}") from exc
    return module


def sanitize_module_name(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)


def require_mapping(row: dict[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


def require_non_empty_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ModelServingError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message if message else exc.__class__.__name__
