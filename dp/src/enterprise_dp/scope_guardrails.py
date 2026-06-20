from __future__ import annotations

import fnmatch
from pathlib import Path
import re
from typing import Any, Iterable

from enterprise_dp.contracts import ValidationResult, load_yaml


TEXT_EXTENSIONS = {".json", ".md", ".py", ".toml", ".yaml", ".yml"}


def validate_scope_guardrails(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "governance" / "scope-guardrails.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "governance/scope-guardrails.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    policy = registry.get("policy")
    if not isinstance(policy, dict):
        result.error(registry_path, "policy must be an object")
        return result

    protected_paths = require_string_list(registry_path, result, policy, "protected_paths")
    ignored_paths = set(require_string_list(registry_path, result, policy, "ignored_paths", required=False))
    guardrails = registry.get("guardrails")
    if not isinstance(guardrails, list) or not guardrails:
        result.error(registry_path, "guardrails must be a non-empty list")
        return result

    compiled = compile_guardrails(registry_path, guardrails, result)
    if result.errors:
        return result

    protected_files = list(iter_protected_files(root, protected_paths, ignored_paths))
    result.checked_count += len(protected_files)
    for path in protected_files:
        scan_file(root, path, compiled, result)
    return result


def compile_guardrails(
    registry_path: Path,
    guardrails: list[object],
    result: ValidationResult,
) -> list[dict[str, Any]]:
    compiled: list[dict[str, Any]] = []
    for index, guardrail in enumerate(guardrails):
        prefix = f"guardrails[{index}]"
        if not isinstance(guardrail, dict):
            result.error(registry_path, f"{prefix} must be an object")
            continue

        guardrail_id = require_string(registry_path, result, guardrail, "id", prefix)
        status = require_string(registry_path, result, guardrail, "status", prefix)
        owner = require_string(registry_path, result, guardrail, "owner", prefix)
        rationale = require_string(registry_path, result, guardrail, "rationale", prefix)
        patterns = require_string_list(registry_path, result, guardrail, "patterns")
        allowed_paths = require_string_list(registry_path, result, guardrail, "allowed_paths")
        if status and status not in {"active", "disabled"}:
            result.error(registry_path, f"{prefix}.status must be active or disabled")
        if status == "disabled":
            continue
        if not (guardrail_id and owner and rationale and patterns and allowed_paths):
            continue

        regexes: list[re.Pattern[str]] = []
        for pattern in patterns:
            try:
                regexes.append(re.compile(pattern))
            except re.error as exc:
                result.error(registry_path, f"{prefix}.patterns contains invalid regex {pattern!r}: {exc}")
        compiled.append(
            {
                "id": guardrail_id,
                "patterns": regexes,
                "allowed_paths": allowed_paths,
            }
        )
    return compiled


def iter_protected_files(root: Path, protected_paths: Iterable[str], ignored_paths: set[str]) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        if path_matches_any(relative, ignored_paths):
            continue
        if path_matches_any(relative, protected_paths):
            yield path


def scan_file(
    root: Path,
    path: Path,
    guardrails: list[dict[str, Any]],
    result: ValidationResult,
) -> None:
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    for guardrail in guardrails:
        if path_matches_any(relative, guardrail["allowed_paths"]):
            continue
        for regex in guardrail["patterns"]:
            match = regex.search(text)
            if match is None:
                continue
            line_number = text.count("\n", 0, match.start()) + 1
            result.error(
                path,
                (
                    f"scope guardrail {guardrail['id']} matched {regex.pattern!r} at line {line_number}; "
                    "move product-specific content under products/<product-code>/ or add an reviewed allowed path"
                ),
            )
            break


def path_matches_any(relative: str, patterns: Iterable[str]) -> bool:
    return any(path_matches(relative, pattern) for pattern in patterns)


def path_matches(relative: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return relative == prefix or relative.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(relative, pattern)


def require_string(path: Path, result: ValidationResult, mapping: dict[str, Any], key: str, prefix: str) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        result.error(path, f"{prefix}.{key} must be a non-empty string")
        return None
    return value


def require_string_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    *,
    required: bool = True,
) -> list[str]:
    value = mapping.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or not value:
        result.error(path, f"{key} must be a non-empty list")
        return []
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            result.error(path, f"{key}[{index}] must be a non-empty string")
            continue
        items.append(item)
    return items
