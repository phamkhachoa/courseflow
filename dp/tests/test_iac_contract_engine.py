from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_terraform_engine_validates_staging_and_prod_iac_contracts(tmp_path: Path) -> None:
    terraform = shutil.which("terraform")
    if terraform is None:
        pytest.skip("terraform is required for the IaC contract engine validation test")

    source = ROOT / "platform" / "runtime" / "iac"
    target = tmp_path / "iac"
    shutil.copytree(source, target)

    fmt = subprocess.run(
        [terraform, "fmt", "-check", "-recursive", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr

    for environment in ("staging", "prod"):
        root = target / environment
        init = subprocess.run(
            [terraform, f"-chdir={root}", "init", "-backend=false", "-input=false", "-no-color"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert init.returncode == 0, init.stdout + init.stderr

        validate = subprocess.run(
            [terraform, f"-chdir={root}", "validate", "-json"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert validate.returncode == 0, validate.stdout + validate.stderr
        payload = json.loads(validate.stdout)
        assert payload["valid"] is True
        assert payload["error_count"] == 0
