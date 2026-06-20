from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.broker_acl_smoke import write_broker_acl_smoke_report
from enterprise_dp.event_backbone_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]


def test_broker_acl_smoke_proves_allowed_and_denied_principals(tmp_path: Path) -> None:
    runner = BrokerAclFakeRunner(deny_user_blocked=True)

    result = write_broker_acl_smoke_report(
        ROOT,
        tmp_path / "broker-acl-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="broker-acl-test",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=runner,
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "broker_acl_smoke_report.v1"
    assert report["passed"] is True
    assert report["summary"]["broker_acl_enforced"] is True
    assert report["summary"]["allowed_user_can_produce"] is True
    assert report["summary"]["denied_user_blocked"] is True
    assert report["summary"]["authorization_denied_verified"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["redpanda"]["config"]["sasl_listener"] is True
    assert report["redpanda"]["mechanism"] == "SCRAM-SHA-256"
    assert "production_mtls_listener" in report["runtime_scope"]["not_covered"]
    assert any(command["step"] == "allowed_user_produce_probe" for command in report["commands"])
    assert any(command["step"] == "denied_user_produce_probe" for command in report["commands"])
    assert any(command["step"] == "cleanup_acl_container" for command in report["commands"])
    assert any("TOPIC_AUTHORIZATION_FAILED" in command["stderr_preview"] for command in report["commands"])
    serialized_commands = json.dumps(report["commands"], ensure_ascii=True, sort_keys=True)
    assert "admin-secret" not in serialized_commands
    assert "allowed-secret" not in serialized_commands
    assert "denied-secret" not in serialized_commands
    assert "<redacted>" in serialized_commands


def test_broker_acl_smoke_fails_when_denied_user_can_produce(tmp_path: Path) -> None:
    runner = BrokerAclFakeRunner(deny_user_blocked=False)

    result = write_broker_acl_smoke_report(
        ROOT,
        tmp_path / "broker-acl-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="broker-acl-test",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=runner,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["broker_acl_enforced"] is False
    assert result.report["summary"]["allowed_user_can_produce"] is True
    assert result.report["summary"]["denied_user_blocked"] is False
    assert result.report["summary"]["authorization_denied_verified"] is False
    assert result.report["summary"]["failed_check_count"] == 1
    assert result.report["summary"]["failed_checks"][0]["check"] == "broker_acl_denied_user_blocked"


class BrokerAclFakeRunner:
    def __init__(self, *, deny_user_blocked: bool) -> None:
        self.deny_user_blocked = deny_user_blocked

    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        command = " ".join(args)
        if args[:3] == ["docker", "rm", "-f"]:
            return CommandResult(tuple(args), 0, "removed", "")
        if args[:2] == ["docker", "run"]:
            return CommandResult(tuple(args), 0, "started", "")
        if "rpk cluster health" in command or args[-3:] == ["rpk", "cluster", "health"]:
            return CommandResult(tuple(args), 0, "Healthy: true\n", "")
        if "rpk security user create" in command:
            return CommandResult(tuple(args), 0, "Created user", "")
        if "rpk cluster config set kafka_enable_authorization true" in command:
            return CommandResult(tuple(args), 0, "Set cluster config", "")
        if "rpk topic create" in command:
            return CommandResult(tuple(args), 0, "Created topic", "")
        if "rpk security acl create" in command and "--topic" in command:
            return CommandResult(
                tuple(args),
                0,
                "ALLOW User:dp_allowed TOPIC dp.local.broker.acl.smoke READ WRITE DESCRIBE\n",
                "",
            )
        if "rpk security acl create" in command and "--group" in command:
            return CommandResult(
                tuple(args),
                0,
                "ALLOW User:dp_allowed GROUP dp.local.broker.acl.smoke.group READ DESCRIBE\n",
                "",
            )
        if "rpk security user list" in command:
            return CommandResult(tuple(args), 0, "admin\ndp_allowed\ndp_denied\n", "")
        if "rpk topic produce" in command and "user=dp_allowed" in command:
            assert input_text == '{"acl":"allowed"}\n'
            return CommandResult(tuple(args), 0, "Produced to partition 0 at offset 0\n", "")
        if "rpk topic produce" in command and "user=dp_denied" in command:
            assert input_text == '{"acl":"denied"}\n'
            if self.deny_user_blocked:
                return CommandResult(
                    tuple(args),
                    1,
                    "",
                    "TOPIC_AUTHORIZATION_FAILED: Not authorized to access topics\n",
                )
            return CommandResult(tuple(args), 0, "Produced to partition 0 at offset 1\n", "")
        raise AssertionError(f"unexpected command: {args}")
