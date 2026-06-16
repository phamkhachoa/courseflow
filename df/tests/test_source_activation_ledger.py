from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

import yaml

from enterprise_df.source_activation_ledger import (
    build_source_activation_index,
    source_effective_status,
    validate_source_activation_registry,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "governance" / "source-activations.yaml"
BILLING_SOURCE_ID = "billing-platform-billing-transaction-settled-outbox"
AS_OF = "2026-06-16T12:00:00Z"


def test_source_activation_registry_is_valid_and_promotes_billing_for_local_and_staging() -> None:
    validation = validate_source_activation_registry(ROOT)

    assert validation.errors == []
    assert validation.checked_count >= 2

    local_index = build_source_activation_index(ROOT, environment="local", as_of=AS_OF, ledger_path=LEDGER)
    staging_index = build_source_activation_index(ROOT, environment="staging", as_of=AS_OF, ledger_path=LEDGER)
    source = billing_source(ROOT)

    assert local_index[BILLING_SOURCE_ID]["activation_id"] == "activate-billing-platform-source-staging-20260118"
    assert local_index[BILLING_SOURCE_ID]["effective_status"] == "production_ready"
    assert source_effective_status(source, local_index) == "production_ready"
    assert source_effective_status(source, staging_index) == "production_ready"


def test_staging_activation_does_not_promote_prod_portfolio() -> None:
    prod_index = build_source_activation_index(ROOT, environment="prod", as_of=AS_OF, ledger_path=LEDGER)

    assert BILLING_SOURCE_ID not in prod_index
    assert source_effective_status(billing_source(ROOT), prod_index) == "pilot"


def test_source_activation_registry_rejects_bad_hash(tmp_path: Path) -> None:
    root = copy_activation_root(tmp_path)
    ledger_path = root / "governance" / "source-activations.yaml"
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    registry["activations"][0]["readinessReportHash"] = "sha256:not-a-real-hash"
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    validation = validate_source_activation_registry(root)

    assert any("readinessReportHash must be sha256" in error for error in validation.errors)


def test_newer_revoked_activation_blocks_previous_active_overlay(tmp_path: Path) -> None:
    root = copy_activation_root(tmp_path)
    ledger_path = root / "governance" / "source-activations.yaml"
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    revoked = deepcopy(registry["activations"][0])
    revoked["activationId"] = "revoke-billing-platform-source-staging-20260617"
    revoked["activationState"] = "revoked"
    revoked["activatedAt"] = "2026-06-17T10:30:00Z"
    revoked["expiresAt"] = "2026-07-19T10:30:00Z"
    registry["activations"].append(revoked)
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    activation_index = build_source_activation_index(root, environment="local", as_of="2026-06-18T12:00:00Z", ledger_path=ledger_path)

    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "blocked"
    assert activation_index[BILLING_SOURCE_ID]["block_reason"] == "activation_not_active:revoked"
    assert source_effective_status(billing_source(root), activation_index) == "pilot"


def test_expired_activation_does_not_promote_source(tmp_path: Path) -> None:
    root = copy_activation_root(tmp_path)
    ledger_path = root / "governance" / "source-activations.yaml"
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    registry["activations"][0]["expiresAt"] = "2026-02-18T10:30:00Z"
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    activation_index = build_source_activation_index(root, environment="local", as_of=AS_OF, ledger_path=ledger_path)

    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "blocked"
    assert activation_index[BILLING_SOURCE_ID]["block_reason"] == "activation_expired"
    assert source_effective_status(billing_source(root), activation_index) == "pilot"


def test_source_registry_hash_mismatch_blocks_active_overlay(tmp_path: Path) -> None:
    root = copy_activation_root(tmp_path)
    ledger_path = root / "governance" / "source-activations.yaml"
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    registry["activations"][0]["sourceRegistryHash"] = "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    activation_index = build_source_activation_index(root, environment="local", as_of=AS_OF, ledger_path=ledger_path)

    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "blocked"
    assert activation_index[BILLING_SOURCE_ID]["block_reason"] == "source_registry_hash_mismatch"
    assert source_effective_status(billing_source(root), activation_index) == "pilot"


def test_failed_gate_badge_blocks_active_overlay(tmp_path: Path) -> None:
    root = copy_activation_root(tmp_path)
    ledger_path = root / "governance" / "source-activations.yaml"
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    registry["activations"][0]["gateBadges"]["offsetLedger"] = "failed"
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    activation_index = build_source_activation_index(root, environment="local", as_of=AS_OF, ledger_path=ledger_path)

    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "blocked"
    assert activation_index[BILLING_SOURCE_ID]["block_reason"] == "gate_badges_not_passing:offsetLedger"
    assert source_effective_status(billing_source(root), activation_index) == "pilot"


def copy_activation_root(tmp_path: Path) -> Path:
    root = tmp_path / "df"
    for directory in ("governance", "platform", "use-cases"):
        shutil.copytree(ROOT / directory, root / directory)
    return root


def billing_source(root: Path) -> dict[str, object]:
    registry = yaml.safe_load((root / "platform" / "ingestion" / "source-registry.yaml").read_text(encoding="utf-8"))
    return next(source for source in registry["sources"] if source["sourceId"] == BILLING_SOURCE_ID)
