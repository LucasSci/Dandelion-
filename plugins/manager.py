from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from plugins.catalog import CatalogEntry, load_catalog
from plugins.sdk import PluginManifest, load_manifest_from_path


@dataclass(frozen=True)
class InstalledPlugin:
    manifest: PluginManifest
    path: str


class PluginManagerError(RuntimeError):
    pass


def _sha256_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_installed_manifest(path: str) -> Optional[PluginManifest]:
    manifest_path = os.path.join(path, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    return load_manifest_from_path(manifest_path)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _compare_versions(version_a: str, version_b: str) -> int:
    parts_a = [int(part) for part in version_a.split(".")[:3]]
    parts_b = [int(part) for part in version_b.split(".")[:3]]
    return (parts_a > parts_b) - (parts_a < parts_b)


class PluginManager:
    def __init__(self, catalog_path: str, install_dir: str) -> None:
        self.catalog_path = catalog_path
        self.install_dir = install_dir
        _ensure_dir(self.install_dir)

    def catalog(self) -> Dict[str, CatalogEntry]:
        return load_catalog(self.catalog_path)

    def list_installed(self) -> Dict[str, InstalledPlugin]:
        installed: Dict[str, InstalledPlugin] = {}
        for name in os.listdir(self.install_dir):
            plugin_path = os.path.join(self.install_dir, name)
            if not os.path.isdir(plugin_path):
                continue
            manifest = _read_installed_manifest(plugin_path)
            if manifest:
                installed[manifest.plugin_id] = InstalledPlugin(manifest=manifest, path=plugin_path)
        return installed

    def install(self, plugin_id: str) -> InstalledPlugin:
        catalog = self.catalog()
        if plugin_id not in catalog:
            raise PluginManagerError(f"Plugin '{plugin_id}' not found in catalog")

        entry = catalog[plugin_id]
        if entry.checksum_sha256:
            actual_checksum = _sha256_file(entry.manifest_path)
            if actual_checksum != entry.checksum_sha256:
                raise PluginManagerError(
                    f"Catalog checksum mismatch for '{plugin_id}' (expected {entry.checksum_sha256})"
                )

        target_path = os.path.join(self.install_dir, plugin_id)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        shutil.copytree(entry.source_path, target_path)
        manifest = _read_installed_manifest(target_path)
        if not manifest:
            raise PluginManagerError("Installed plugin missing manifest")
        return InstalledPlugin(manifest=manifest, path=target_path)

    def update(self, plugin_id: str) -> InstalledPlugin:
        catalog = self.catalog()
        if plugin_id not in catalog:
            raise PluginManagerError(f"Plugin '{plugin_id}' not found in catalog")

        entry = catalog[plugin_id]
        installed = self.list_installed().get(plugin_id)
        if installed and _compare_versions(entry.version, installed.manifest.version) <= 0:
            return installed
        return self.install(plugin_id)
