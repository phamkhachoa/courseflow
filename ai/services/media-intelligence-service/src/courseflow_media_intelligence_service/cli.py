from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from courseflow_media_intelligence_service.service import (
    MediaIntelligenceService,
    MediaIntelligenceServiceConfig,
    build_service_manifest,
    default_ai_root,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CourseFlow AI Platform media intelligence service."
    )
    parser.add_argument("--ai-root", type=Path, default=default_ai_root())
    parser.add_argument("--principal-id")
    parser.add_argument("--scopes")
    parser.add_argument("--disable-auth", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest")
    subparsers.add_parser("health")
    subparsers.add_parser("metrics")

    document = subparsers.add_parser("analyze-document")
    document.add_argument("--body-json")
    document.add_argument("--body-file", type=Path)

    speech = subparsers.add_parser("assess-speech")
    speech.add_argument("--body-json")
    speech.add_argument("--body-file", type=Path)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8094)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "manifest":
        print_json(build_service_manifest())
        return 0

    service = MediaIntelligenceService(
        MediaIntelligenceServiceConfig.from_paths(
            ai_root=args.ai_root,
            auth_enabled=not args.disable_auth,
        )
    )
    requested_scopes = parse_scopes(args.scopes)

    if args.command == "serve":
        from courseflow_media_intelligence_service.http_server import serve_http

        serve_http(service, host=args.host, port=args.port)
        return 0
    if args.command == "analyze-document":
        return print_response(
            service.handle_request(
                "POST",
                "/v1/media-intelligence/document:analyze",
                load_body(args, "analyze-document"),
                principal_id=args.principal_id,
                requested_scopes=requested_scopes,
            )
        )
    if args.command == "assess-speech":
        return print_response(
            service.handle_request(
                "POST",
                "/v1/media-intelligence/speech:assess",
                load_body(args, "assess-speech"),
                principal_id=args.principal_id,
                requested_scopes=requested_scopes,
            )
        )
    if args.command == "health":
        return print_response(
            service.handle_request(
                "GET",
                "/v1/media-intelligence/health",
                principal_id=args.principal_id,
                requested_scopes=requested_scopes,
            )
        )
    if args.command == "metrics":
        return print_response(
            service.handle_request(
                "GET",
                "/v1/media-intelligence/metrics",
                principal_id=args.principal_id,
                requested_scopes=requested_scopes,
            )
        )

    raise AssertionError(f"unhandled command: {args.command}")


def load_body(args: argparse.Namespace, command_name: str) -> dict[str, Any]:
    if args.body_json and args.body_file:
        raise SystemExit("Use either --body-json or --body-file, not both.")
    if args.body_file:
        raw = args.body_file.read_text(encoding="utf-8")
    elif args.body_json:
        raw = args.body_json
    else:
        raise SystemExit(f"{command_name} requires --body-json or --body-file.")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit(f"{command_name} body must be a JSON object.")
    return payload


def parse_scopes(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    return tuple(scope.strip() for scope in raw.split(",") if scope.strip())


def print_response(response: Any) -> int:
    print_json(response.to_dict())
    return 0 if response.status_code < 500 else 1


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
