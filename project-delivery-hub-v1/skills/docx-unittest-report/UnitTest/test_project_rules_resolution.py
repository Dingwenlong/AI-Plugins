from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_rules import resolve_agent_root, resolve_asset_path, resolve_rules_root


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectRulesResolutionTests(unittest.TestCase):
    def test_rules_root_from_config_is_resolved_relative_to_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-rules-") as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            config = {
                "defaultWorkspace": "LOCAL",
                "workspaces": {
                    "LOCAL": {
                        "workspaceRoot": workspace_root.as_posix(),
                        "rulesRoot": ".agent/project-rules/LOCAL",
                    }
                },
            }

            with patch("project_rules.load_workspace_config", return_value=(config, Path(temp_dir) / "local-workspaces.json")):
                self.assertEqual(
                    resolve_rules_root(workspace_key="LOCAL"),
                    (workspace_root / ".agent" / "project-rules" / "LOCAL").resolve(),
                )

    def test_asset_path_uses_configured_rules_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-rules-") as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            rules_root = workspace_root / ".agent" / "project-rules" / "LOCAL"
            asset_path = rules_root / "assets" / "template.docx"
            asset_path.parent.mkdir(parents=True)
            asset_path.write_text("fixture", encoding="utf-8")
            write_json(rules_root / "catalog.json", {"assets": {"utReportTemplate": "assets/template.docx"}})

            config = {
                "defaultWorkspace": "LOCAL",
                "workspaces": {
                    "LOCAL": {
                        "workspaceRoot": workspace_root.as_posix(),
                        "rulesRoot": ".agent/project-rules/LOCAL",
                    }
                },
            }

            with patch("project_rules.load_workspace_config", return_value=(config, Path(temp_dir) / "local-workspaces.json")):
                self.assertEqual(resolve_asset_path("utReportTemplate", workspace_key="LOCAL"), asset_path.resolve())

    def test_feature_tester_map_prefers_workspace_agent_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-rules-") as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            rules_root = workspace_root / ".agent" / "project-rules" / "LOCAL"
            catalog_asset = rules_root / "assets" / "docx" / "feature-tester-map.json"
            agent_asset = workspace_root / ".agent" / "config" / "feature-tester-map.json"
            write_json(catalog_asset, {"mapping": {"B.003": "Catalog"}})
            write_json(agent_asset, {"mapping": {"B.003": "AgentConfig"}})
            write_json(rules_root / "catalog.json", {"assets": {"featureTesterMap": "assets/docx/feature-tester-map.json"}})
            config = {
                "defaultWorkspace": "LOCAL",
                "workspaces": {
                    "LOCAL": {
                        "workspaceRoot": workspace_root.as_posix(),
                        "agentRoot": ".agent",
                        "rulesRoot": ".agent/project-rules/LOCAL",
                    }
                },
            }

            with patch("project_rules.load_workspace_config", return_value=(config, Path(temp_dir) / "local-workspaces.json")):
                self.assertEqual(resolve_agent_root(workspace_key="LOCAL"), (workspace_root / ".agent").resolve())
                self.assertEqual(resolve_asset_path("featureTesterMap", workspace_key="LOCAL"), agent_asset.resolve())

    def test_feature_tester_map_does_not_fall_back_to_project_rules_asset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-rules-") as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            rules_root = workspace_root / ".agent" / "project-rules" / "LOCAL"
            catalog_asset = rules_root / "assets" / "docx" / "feature-tester-map.json"
            write_json(catalog_asset, {"mapping": {"B.003": "Catalog"}})
            write_json(rules_root / "catalog.json", {"assets": {"featureTesterMap": "assets/docx/feature-tester-map.json"}})
            config = {
                "defaultWorkspace": "LOCAL",
                "workspaces": {
                    "LOCAL": {
                        "workspaceRoot": workspace_root.as_posix(),
                        "agentRoot": ".agent",
                        "rulesRoot": ".agent/project-rules/LOCAL",
                    }
                },
            }

            with patch("project_rules.load_workspace_config", return_value=(config, Path(temp_dir) / "local-workspaces.json")):
                self.assertIsNone(resolve_asset_path("featureTesterMap", workspace_key="LOCAL"))


if __name__ == "__main__":
    unittest.main()
