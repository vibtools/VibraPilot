from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from vibrapilot.app_config import APP, SUPPORT

ROOT = Path(__file__).resolve().parents[1]


class AppMetadataConsistencyTest(unittest.TestCase):
    def test_static_package_metadata_matches_appconfig(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]
        self.assertEqual(project["name"], APP.app_id)
        self.assertEqual(project["version"], APP.version)
        self.assertEqual(project["description"], APP.description)
        self.assertEqual(project["license"]["text"], APP.license_identifier)
        self.assertEqual(project["authors"][0]["name"], APP.owner_name)
        self.assertEqual(project["urls"]["Homepage"], APP.homepage_url)
        self.assertEqual(project["urls"]["Repository"], APP.repository_url)
        self.assertEqual(project["urls"]["Documentation"], SUPPORT.documentation_url)

    def test_project_and_docs_manifests_match_appconfig(self):
        project = json.loads((ROOT / "vibproject.ygit").read_text(encoding="utf-8"))
        docs = json.loads((ROOT / "docs/docs.manifest.ygit").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["displayName"], APP.display_name)
        self.assertEqual(project["project"]["version"], APP.version)
        self.assertEqual(project["organization"]["company"], APP.owner_name)
        self.assertEqual(project["license"]["spdx"], APP.license_identifier)
        self.assertEqual(docs["documentation"]["version"], APP.version)

    def test_citation_matches_appconfig(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn(f"version: {APP.version}", citation)
        self.assertIn(f"license: {APP.license_identifier}", citation)
        self.assertIn(f'- name: "{APP.owner_name}"', citation)


if __name__ == "__main__":
    unittest.main()
