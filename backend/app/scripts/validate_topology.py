#!/usr/bin/env python3
"""
Validation script for Kernel/Channel/Pipeline topology JSON files.

Checks:
- pipelines.json references existing kernels and channels
- channels.json pre/post stage dependency references are internal and valid
- channels.json wiring.maps values reference existing pre_stages keys
- kernels.json stage dependency references are internal and valid
- formatting hints: dependencies array types

Exit code 0 if all checks pass; non-zero and prints errors otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # app dir
APP_DIR = ROOT

PIPELINES_PATH = APP_DIR / "pipelines.json"
KERNELS_PATH = APP_DIR / "kernels.json"
CHANNELS_PATH = APP_DIR / "channels.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"Missing file: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {path}: {e}")


messages: list[str] = []


def fail(msg: str) -> None:
    messages.append(f"ERROR: {msg}")


def warn(msg: str) -> None:
    messages.append(f"WARN: {msg}")


def ok(msg: str) -> None:
    messages.append(f"OK: {msg}")


def validate_kernels(kernels: dict[str, Any]) -> None:
    if not isinstance(kernels, dict) or not kernels:
        fail("kernels.json must be a non-empty object")
        return
    for kname, kdef in kernels.items():
        stages = (kdef or {}).get("stages") or {}
        if not stages:
            fail(f"kernel '{kname}' has no stages")
            continue
        stage_names = set(stages.keys())
        # basic shape checks
        for sname, sdef in stages.items():
            if "class" not in sdef:
                fail(f"kernel '{kname}' stage '{sname}' missing 'class'")
            deps = sdef.get("dependencies", [])
            if deps and not isinstance(deps, list):
                fail(f"kernel '{kname}' stage '{sname}' dependencies must be a list")
            # internal dependency references should exist
            for d in deps:
                if d not in stage_names:
                    fail(f"kernel '{kname}' stage '{sname}' depends on unknown stage '{d}'")
        # outputs inputs arrays types
        for key in ("inputs", "outputs"):
            arr = kdef.get(key, [])
            if arr and not isinstance(arr, list):
                fail(f"kernel '{kname}' '{key}' must be a list if present")
        ok(f"kernel '{kname}' validated")


def validate_channels(channels: dict[str, Any]) -> None:
    if not isinstance(channels, dict) or not channels:
        fail("channels.json must be a non-empty object")
        return
    for cname, cdef in channels.items():
        pre = (cdef or {}).get("pre_stages") or {}
        post = (cdef or {}).get("post_stages") or {}
        wiring = (cdef or {}).get("wiring") or {}
        pre_names = set(pre.keys())
        if not pre:
            warn(f"channel '{cname}' has no pre_stages")
        if not post:
            warn(f"channel '{cname}' has no post_stages")
        # validate pre/post stage entries
        def _validate_stage_block(
            block: dict[str, Any], block_name: str, *, _cname: str = cname, _pre_names: set[str] = pre_names
        ) -> None:
            for sname, sdef in block.items():
                if "class" not in sdef:
                    fail(f"channel '{_cname}' {block_name} stage '{sname}' missing 'class'")
                deps = sdef.get("dependencies", [])
                if deps and not isinstance(deps, list):
                    fail(f"channel '{_cname}' {block_name} stage '{sname}' dependencies must be a list")
                for d in deps:
                    if d not in _pre_names:
                        fail(f"channel '{_cname}' {block_name} stage '{sname}' depends on unknown pre stage '{d}'")
        _validate_stage_block(pre, "pre_stages")
        _validate_stage_block(post, "post_stages")
        # validate wiring maps
        maps = wiring.get("maps") or {}
        if maps and not isinstance(maps, dict):
            fail(f"channel '{cname}' wiring.maps must be an object if present")
        for kstage, pre_ref in maps.items():
            if pre_ref not in pre_names:
                fail(f"channel '{cname}' wiring.maps '{kstage}' -> '{pre_ref}' references unknown pre stage")
        cout = wiring.get("channel_output_connects_to") or []
        if cout and not isinstance(cout, list):
            fail(f"channel '{cname}' wiring.channel_output_connects_to must be a list if present")
        ok(f"channel '{cname}' validated")


def validate_pipelines(pipes: dict[str, Any], kernels: dict[str, Any], channels: dict[str, Any]) -> None:
    if not isinstance(pipes, dict) or not pipes:
        fail("pipelines.json must be a non-empty object")
        return
    for pname, pdef in pipes.items():
        k = pdef.get("kernel")
        c = pdef.get("channel")
        if not k or k not in kernels:
            fail(f"pipeline '{pname}' references missing kernel '{k}'")
        if not c or c not in channels:
            fail(f"pipeline '{pname}' references missing channel '{c}'")
        # optional dependencies override shape
        deps = pdef.get("dependencies")
        if deps is not None and not isinstance(deps, dict):
            fail(f"pipeline '{pname}' dependencies must be an object if present")
        ok(f"pipeline '{pname}' validated")


def main() -> int:
    kernels = _load_json(KERNELS_PATH)
    channels = _load_json(CHANNELS_PATH)
    pipelines = _load_json(PIPELINES_PATH)

    validate_kernels(kernels)
    validate_channels(channels)
    validate_pipelines(pipelines, kernels, channels)

    has_error = any(m.startswith("ERROR:") for m in messages)
    for m in messages:
        print(m)
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
