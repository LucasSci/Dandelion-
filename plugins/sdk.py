from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][\w.]+)?$")


@dataclass(frozen=True)
class ExtensionPoint:
    name: str
    description: str
    payload_schema: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class HookDefinition:
    name: str
    extension_point: str
    description: str
    input_schema: Optional[Mapping[str, Any]] = None
    output_schema: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class PluginPermission:
    filesystem_read: bool = True
    filesystem_write: bool = False
    network: bool = False
    subprocess: bool = False


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str
    entrypoint: str
    hooks: Tuple[HookDefinition, ...]
    permissions: PluginPermission


class ManifestValidationError(ValueError):
    pass


def _require(data: Mapping[str, Any], key: str, expected_type: type) -> Any:
    if key not in data:
        raise ManifestValidationError(f"Missing required field: {key}")
    value = data[key]
    if not isinstance(value, expected_type):
        raise ManifestValidationError(f"Field '{key}' must be {expected_type.__name__}")
    return value


def _optional(data: Mapping[str, Any], key: str, expected_type: type, default: Any) -> Any:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, expected_type):
        raise ManifestValidationError(f"Field '{key}' must be {expected_type.__name__}")
    return value


def validate_manifest(raw_manifest: Mapping[str, Any]) -> PluginManifest:
    plugin_id = _require(raw_manifest, "id", str)
    name = _require(raw_manifest, "name", str)
    version = _require(raw_manifest, "version", str)
    description = _require(raw_manifest, "description", str)
    entrypoint = _require(raw_manifest, "entrypoint", str)

    if not SEMVER_RE.match(version):
        raise ManifestValidationError("Version must follow semver (e.g. 1.2.3)")

    if ":" not in entrypoint:
        raise ManifestValidationError("Entrypoint must be in the form 'module:function'")

    permissions_raw = _optional(raw_manifest, "permissions", dict, {})
    permissions = PluginPermission(
        filesystem_read=bool(permissions_raw.get("filesystem_read", True)),
        filesystem_write=bool(permissions_raw.get("filesystem_write", False)),
        network=bool(permissions_raw.get("network", False)),
        subprocess=bool(permissions_raw.get("subprocess", False)),
    )

    hooks_raw = _optional(raw_manifest, "hooks", list, [])
    hooks: List[HookDefinition] = []
    for hook in hooks_raw:
        if not isinstance(hook, dict):
            raise ManifestValidationError("Each hook must be an object")
        hook_name = _require(hook, "name", str)
        extension_point = _require(hook, "extension_point", str)
        hook_description = _require(hook, "description", str)
        hooks.append(
            HookDefinition(
                name=hook_name,
                extension_point=extension_point,
                description=hook_description,
                input_schema=_optional(hook, "input_schema", dict, None),
                output_schema=_optional(hook, "output_schema", dict, None),
            )
        )

    return PluginManifest(
        plugin_id=plugin_id,
        name=name,
        version=version,
        description=description,
        entrypoint=entrypoint,
        hooks=tuple(hooks),
        permissions=permissions,
    )


def validate_payload(schema: Optional[Mapping[str, Any]], payload: Mapping[str, Any]) -> None:
    if not schema:
        return
    if not isinstance(payload, Mapping):
        raise ManifestValidationError("Payload must be a mapping")

    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for field in required:
        if field not in payload:
            raise ManifestValidationError(f"Payload missing required field: {field}")

    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    for field, field_type in properties.items():
        if field not in payload:
            continue
        expected = type_map.get(field_type)
        if expected is None:
            raise ManifestValidationError(f"Unsupported schema type: {field_type}")
        if not isinstance(payload[field], expected):
            raise ManifestValidationError(
                f"Payload field '{field}' must be {expected.__name__}"
            )


def load_manifest_from_path(path: str) -> PluginManifest:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return validate_manifest(raw)


DEFAULT_EXTENSION_POINTS: Tuple[ExtensionPoint, ...] = (
    ExtensionPoint(
        name="narration",
        description="Geração de narrativa e respostas contextuais.",
        payload_schema={"required": ["prompt"], "properties": {"prompt": "str"}},
    ),
    ExtensionPoint(
        name="combat_rules",
        description="Modificadores ou ganchos para cálculo de combate.",
        payload_schema={
            "required": ["attacker", "defender"],
            "properties": {"attacker": "dict", "defender": "dict"},
        },
    ),
    ExtensionPoint(
        name="inventory",
        description="Hooks para inventário e itens especiais.",
        payload_schema={"required": ["character_id"], "properties": {"character_id": "str"}},
    ),
)
