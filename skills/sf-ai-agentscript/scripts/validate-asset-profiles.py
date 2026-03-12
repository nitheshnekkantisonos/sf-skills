#!/usr/bin/env python3
"""Validate Agent Script asset examples using profile-aware expectations.

Why this exists:
- Some files under assets/ are complete standalone templates.
- Some are reusable partial snippets that intentionally omit top-level blocks.
- Some are structurally valid but depend on org-specific resources.

This harness runs the main Agent Script validator against every asset file, then
interprets results according to `assets/validation-profiles.json`.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "hooks/scripts/agentscript-syntax-validator.py"
PROFILES_PATH = ROOT / "assets/validation-profiles.json"


def load_validator():
    spec = spec_from_file_location("agentscript_validator", VALIDATOR_PATH)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.AgentScriptValidator


def extract_rule_id(message: str) -> str | None:
    if message.startswith("[") and "]" in message:
        return message[1 : message.index("]")]
    return None


def load_profiles() -> Dict:
    with PROFILES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_file_map(profiles_payload: Dict) -> Dict[str, Dict]:
    file_map: Dict[str, Dict] = {}
    for profile in profiles_payload.get("profiles", []):
        for file_path in profile.get("files", []):
            resolved = str(Path(file_path).resolve())
            if resolved in file_map:
                raise SystemExit(f"Duplicate profile assignment for {file_path}")
            file_map[resolved] = profile
    return file_map


def main() -> int:
    AgentScriptValidator = load_validator()
    profiles_payload = load_profiles()
    file_map = build_file_map(profiles_payload)

    asset_files = sorted((ROOT / "assets").rglob("*.agent"))
    unprofiled = [str(path.resolve()) for path in asset_files if str(path.resolve()) not in file_map]
    if unprofiled:
        print("❌ Unprofiled asset files detected:")
        for path in unprofiled:
            print(f"  - {path}")
        return 1

    profile_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "blocking": 0, "warnings": 0})
    unexpected_failures: List[Tuple[str, str]] = []

    for path in asset_files:
        profile = file_map[str(path.resolve())]
        allowed_blocking_ids = set(profile.get("allowBlockingIds", []))

        validator = AgentScriptValidator(path.read_text(encoding="utf-8"), str(path))
        result = validator.validate()

        profile_name = profile["name"]
        profile_stats[profile_name]["files"] += 1
        profile_stats[profile_name]["blocking"] += len(result["errors"])
        profile_stats[profile_name]["warnings"] += len(result["warnings"])

        unexpected = []
        for _, _, message in result["errors"]:
            rule_id = extract_rule_id(message)
            if rule_id not in allowed_blocking_ids:
                unexpected.append(message)

        if unexpected:
            unexpected_failures.append((str(path), unexpected[0]))

    print("Asset validation profile summary")
    print("-------------------------------")
    for profile in profiles_payload.get("profiles", []):
        stats = profile_stats[profile["name"]]
        print(
            f"- {profile['name']}: {stats['files']} files, "
            f"{stats['blocking']} raw blocking findings, {stats['warnings']} warnings"
        )

    if unexpected_failures:
        print("\n❌ Unexpected blocking findings:")
        for path, message in unexpected_failures:
            print(f"- {path}\n    {message}")
        return 1

    print("\n✅ All asset files matched their configured validation profile expectations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
