from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from courseflow_model_serving_service.service import (
    ModelServingService,
    ModelServingServiceConfig,
    build_service_manifest,
    default_ai_root,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CourseFlow AI Platform model-serving service.")
    parser.add_argument("--ai-root", type=Path, default=default_ai_root())
    parser.add_argument("--audit-log-path", type=Path)
    parser.add_argument("--principal-id")
    parser.add_argument(
        "--scopes",
        help="Comma-separated scopes requested for the resolved service principal.",
    )
    parser.add_argument("--disable-auth", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest")
    subparsers.add_parser("catalog")
    subparsers.add_parser("metrics")
    subparsers.add_parser("health")
    subparsers.add_parser("cockpit")
    subparsers.add_parser("product-readiness")

    invoke = subparsers.add_parser("invoke")
    invoke.add_argument("--body-json")
    invoke.add_argument("--body-file", type=Path)

    export = subparsers.add_parser("export-metrics")
    export.add_argument("--output-path", type=Path)
    export.add_argument("--generated-at")

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8091)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "manifest":
        print_json(build_service_manifest())
        return 0

    service = ModelServingService(
        ModelServingServiceConfig.from_paths(
            ai_root=args.ai_root,
            audit_log_path=args.audit_log_path,
            auth_enabled=not args.disable_auth,
        )
    )
    requested_scopes = parse_scopes(args.scopes)

    if args.command == "serve":
        from courseflow_model_serving_service.http_server import serve_http

        serve_http(service, host=args.host, port=args.port)
        return 0

    if args.command == "catalog":
        response = service.handle_request(
            "GET",
            "/v1/models",
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "invoke":
        response = service.handle_request(
            "POST",
            "/v1/model-invocations",
            load_body(args),
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "metrics":
        response = service.handle_request(
            "GET",
            "/v1/model-serving/metrics",
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "health":
        response = service.handle_request(
            "GET",
            "/v1/model-serving/health",
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "cockpit":
        response = service.handle_request(
            "GET",
            "/v1/model-serving/cockpit",
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "product-readiness":
        response = service.handle_request(
            "GET",
            "/v1/model-serving/product-readiness",
            principal_id=args.principal_id,
            requested_scopes=requested_scopes,
        )
        return print_adapter_response(response)
    if args.command == "export-metrics":
        path = service.export_metrics(args.output_path, generated_at=args.generated_at)
        print_json({"path": str(path)})
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


def load_body(args: argparse.Namespace) -> dict[str, Any]:
    if args.body_json and args.body_file:
        raise SystemExit("Use either --body-json or --body-file, not both.")
    if args.body_file:
        raw = args.body_file.read_text(encoding="utf-8")
    elif args.body_json:
        raw = args.body_json
    else:
        raise SystemExit("invoke requires --body-json or --body-file.")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("invoke body must be a JSON object.")
    return payload


def parse_scopes(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    return tuple(scope.strip() for scope in raw.split(",") if scope.strip())


def print_adapter_response(response: Any) -> int:
    print_json(response.to_dict())
    return 0 if response.status_code < 500 else 1


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
