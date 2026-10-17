"""YAML settings and editable metadata, with migration from the legacy JSON file."""
from __future__ import annotations

import json
import os
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError


def yaml_parser() -> YAML:
    parser = YAML()
    parser.preserve_quotes = True
    parser.indent(mapping=2, sequence=4, offset=2)
    return parser


def read_yaml(path: Path) -> CommentedMap:
    if not path.exists():
        return CommentedMap()
    try:
        data = yaml_parser().load(path.read_text())
    except YAMLError as exc:
        raise RuntimeError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return CommentedMap()
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a YAML mapping.")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Preserve comments and replace complete files; skip unchanged content."""
    buffer = StringIO()
    yaml_parser().dump(data, buffer)
    content = buffer.getvalue()
    if path.exists() and path.read_text() == content:
        return
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            if path.exists():
                temporary.chmod(path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def read_legacy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as stream:
        return json.load(stream)


def load_program_config(path: Path, legacy_path: Path) -> dict[str, Any]:
    data = read_yaml(path)
    if not path.exists():
        data["editor"] = read_legacy(legacy_path).get("editor", "codium")
        data.yaml_set_start_comment("Program settings. Editor commands may include arguments.")
    data.setdefault("editor", "codium")
    if not isinstance(data["editor"], str) or not data["editor"].strip():
        raise RuntimeError(f"{path}: editor must be a non-empty command string.")
    write_yaml(path, data)
    return data


def require_names(value: Any, context: str) -> None:
    if not isinstance(value, list) or any(
        not isinstance(name, str) or not name.strip() for name in value
    ):
        raise RuntimeError(f"{context} must be a list of non-empty names.")


def load_metadata(
    path: Path,
    legacy_path: Path,
    templates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Discover names without replacing manual provider groups or access lists."""
    data = read_yaml(path)
    if not path.exists():
        legacy = read_legacy(legacy_path)
        data.yaml_set_start_comment(
            "Editable metadata. New models go under 'default provider'.\n"
            "Existing harness model lists are manual; new harnesses are seeded from snippets.\n"
            "Templates and ui_state are maintained by the picker."
        )
        data["providers"] = CommentedMap()
        data["harnesses"] = CommentedMap()
        data["templates"] = legacy.get("templates", {})
        data["ui_state"] = legacy.get("ui_state", {"expanded_paths": []})
    for key in ("providers", "harnesses", "templates", "ui_state"):
        data.setdefault(key, CommentedMap())
        if not isinstance(data[key], dict):
            raise RuntimeError(f"{path}: {key} must be a mapping.")
    providers = data["providers"]
    harnesses = data["harnesses"]
    for provider, models in providers.items():
        require_names(models, f"{path}: providers.{provider}")
    for harness, settings in harnesses.items():
        if not isinstance(settings, dict) or "models" not in settings:
            raise RuntimeError(f"{path}: harnesses.{harness} must have a models list.")
        require_names(settings["models"], f"{path}: harnesses.{harness}.models")
    data["ui_state"].setdefault("expanded_paths", [])
    require_names(data["ui_state"]["expanded_paths"], f"{path}: ui_state.expanded_paths")
    if any(not isinstance(value, bool) for value in data["templates"].values()):
        raise RuntimeError(f"{path}: templates selections must be true or false.")

    discovered: dict[str, set[str]] = {}
    models = {model for settings in harnesses.values() for model in settings["models"]}
    for info in templates.values():
        meta = info["meta"]
        models.update(meta["llm"])
        for harness in meta["harness"] or ["general"]:
            discovered.setdefault(harness, set()).update(meta["llm"])
    known_models = {model for names in providers.values() for model in names}
    unknown_models = sorted(models - known_models)
    if unknown_models:
        providers.setdefault("default provider", []).extend(unknown_models)
    for harness, names in sorted(discovered.items()):
        if harness not in harnesses:
            harnesses[harness] = {"models": sorted(names)}
    for name in templates:
        data["templates"].setdefault(name, False)
    write_yaml(path, data)
    return data


def save_ui_state(
    path: Path,
    legacy_path: Path,
    templates: dict[str, dict[str, Any]],
    selected: dict[str, bool],
    expanded_paths: list[str],
) -> dict[str, Any]:
    # Re-read first so picker actions never overwrite manual metadata edits.
    data = load_metadata(path, legacy_path, templates)
    data["templates"].update(selected)
    data["ui_state"]["expanded_paths"] = expanded_paths
    write_yaml(path, data)
    return data
