from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class PipelineSpec:
    runner_id: str
    name: str
    product: str
    domain: str
    use_cases: tuple[str, ...]
    input_kind: str
    output_data_products: tuple[str, ...]
    description: str
    input_topics: tuple[str, ...] = ()
    input_data_products: tuple[str, ...] = ()
    primary_output: str | None = None
    evidence_capabilities: tuple[str, ...] = ()
    required_options: tuple[str, ...] = ()
    optional_options: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "runner_id": self.runner_id,
            "name": self.name,
            "product": self.product,
            "domain": self.domain,
            "use_cases": list(self.use_cases),
            "input_kind": self.input_kind,
            "input_topics": list(self.input_topics),
            "input_data_products": list(self.input_data_products),
            "output_data_products": list(self.output_data_products),
            "primary_output": self.primary_output,
            "evidence_capabilities": list(self.evidence_capabilities),
            "description": self.description,
            "required_options": list(self.required_options),
            "optional_options": list(self.optional_options),
        }


@dataclass(frozen=True)
class PipelineRunRequest:
    input_path: Path
    output_dir: Path
    options: dict[str, Any] = field(default_factory=dict)


class PipelineRunner(Protocol):
    spec: PipelineSpec

    def run(self, request: PipelineRunRequest) -> Any:
        ...
