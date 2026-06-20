from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from courseflow_rag_answer_service.service import RagAnswerService

PRINCIPAL_HEADER = "X-CourseFlow-Principal-Id"
SCOPES_HEADER = "X-CourseFlow-Scopes"


def serve_http(
    service: RagAnswerService,
    *,
    host: str = "127.0.0.1",
    port: int = 8101,
) -> None:
    server = ThreadingHTTPServer((host, port), handler_for(service))
    server.serve_forever()


def handler_for(service: RagAnswerService) -> type[BaseHTTPRequestHandler]:
    class RagAnswerRequestHandler(BaseHTTPRequestHandler):
        server_version = "CourseFlowRagAnswer/0.1"

        def do_GET(self) -> None:
            self.dispatch(None)

        def do_POST(self) -> None:
            self.dispatch(self.read_json_body())

        def dispatch(self, body: dict[str, Any] | None) -> None:
            response = service.handle_request(
                self.command,
                self.path,
                body,
                principal_id=self.headers.get(PRINCIPAL_HEADER),
                requested_scopes=parse_scopes(self.headers.get(SCOPES_HEADER)),
            )
            encoded = json.dumps(response.body, sort_keys=True).encode("utf-8")
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                return {}
            return payload

        def log_message(self, format: str, *args: object) -> None:
            return None

    return RagAnswerRequestHandler


def parse_scopes(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    return tuple(scope.strip() for scope in raw.split(",") if scope.strip())
