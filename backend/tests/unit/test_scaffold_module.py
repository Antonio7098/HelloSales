from __future__ import annotations

from pathlib import Path

from hello_sales_backend.cli import scaffold_module as scaffold_module_cli

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_scaffold_module_writes_expected_files(tmp_path):
    template_root = BACKEND_ROOT / "templates" / "module"
    destination_root = tmp_path / "modules"

    written = scaffold_module_cli.scaffold_module(
        template_root=template_root,
        destination_root=destination_root,
        module_name="deals",
        package_name="hello_sales_backend",
    )

    assert destination_root.joinpath("deals", "bootstrap.py").exists()
    assert destination_root.joinpath("deals", "use_cases", "deals_service.py").exists()
    assert destination_root.joinpath("deals", "infra", "persistence.py").exists()
    assert any(path.name == "bootstrap.py" for path in written)
