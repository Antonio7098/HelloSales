"""Scaffold a new backend module from the local template set."""

from __future__ import annotations

import argparse
from pathlib import Path

PLACEHOLDERS = {
    "__MODULE__": "module_name",
    "__CLASS__": "class_name",
    "__PACKAGE__": "package_name",
}


def to_class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def render_text(text: str, *, module_name: str, class_name: str, package_name: str) -> str:
    rendered = text
    replacements = {
        "module_name": module_name,
        "class_name": class_name,
        "package_name": package_name,
    }
    for placeholder, key in PLACEHOLDERS.items():
        rendered = rendered.replace(placeholder, replacements[key])
    return rendered


def render_path(path: Path, *, module_name: str, class_name: str, package_name: str) -> Path:
    rendered = str(path)
    rendered = render_text(rendered, module_name=module_name, class_name=class_name, package_name=package_name)
    if rendered.endswith(".tmpl"):
        rendered = rendered[:-5]
    return Path(rendered)


def scaffold_module(
    *,
    template_root: Path,
    destination_root: Path,
    module_name: str,
    package_name: str,
) -> list[Path]:
    class_name = to_class_name(module_name)
    written_paths: list[Path] = []
    for template_path in sorted(template_root.rglob("*")):
        relative = template_path.relative_to(template_root)
        rendered_relative = render_path(
            relative,
            module_name=module_name,
            class_name=class_name,
            package_name=package_name,
        )
        target_path = destination_root / module_name / rendered_relative
        if template_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        contents = template_path.read_text(encoding="utf-8")
        rendered = render_text(
            contents,
            module_name=module_name,
            class_name=class_name,
            package_name=package_name,
        )
        if target_path.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {target_path}")
        target_path.write_text(rendered, encoding="utf-8")
        written_paths.append(target_path)
    return written_paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a backend module.")
    parser.add_argument("module_name", help="Snake-case module name, e.g. practice_runs")
    parser.add_argument(
        "--package-name",
        default="hello_sales_backend",
        help="Python package name under backend/src",
    )
    parser.add_argument(
        "--template-root",
        default=str(Path(__file__).resolve().parents[3] / "templates" / "module"),
        help="Directory containing module templates",
    )
    parser.add_argument(
        "--destination-root",
        default=str(
            Path(__file__).resolve().parents[3] / "src" / "hello_sales_backend" / "modules"
        ),
        help="Directory where modules are created",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    written = scaffold_module(
        template_root=Path(args.template_root),
        destination_root=Path(args.destination_root),
        module_name=args.module_name,
        package_name=args.package_name,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
