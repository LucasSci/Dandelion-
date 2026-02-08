from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional


@dataclass(frozen=True)
class CatalogEntry:
    plugin_id: str
    name: str
    version: str
    description: str
    source_path: str
    manifest_path: str
    checksum_sha256: Optional[str] = None


class CatalogValidationError(ValueError):
    pass


def _require(data: Mapping[str, object], key: str, expected_type: type) -> object:
    if key not in data:
        raise CatalogValidationError(f"Missing required catalog field: {key}")
    value = data[key]
    if not isinstance(value, expected_type):
        raise CatalogValidationError(f"Catalog field '{key}' must be {expected_type.__name__}")
    return value


def load_catalog(path: str) -> Dict[str, CatalogEntry]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    entries = raw.get("plugins", [])
    if not isinstance(entries, list):
        raise CatalogValidationError("Catalog 'plugins' must be a list")

    catalog: Dict[str, CatalogEntry] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise CatalogValidationError("Catalog entry must be an object")
        plugin_id = _require(entry, "id", str)
        catalog[plugin_id] = CatalogEntry(
            plugin_id=plugin_id,
            name=_require(entry, "name", str),
            version=_require(entry, "version", str),
            description=_require(entry, "description", str),
            source_path=_require(entry, "source_path", str),
            manifest_path=_require(entry, "manifest_path", str),
            checksum_sha256=entry.get("checksum_sha256"),
        )
    return catalog
