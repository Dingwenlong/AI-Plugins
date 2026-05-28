from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from chain_workspace import resolve_chain_workspace


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ChainWorkspaceResolutionTests(unittest.TestCase):
    def test_plugin_config_resolves_relative_agent_and_rules_roots_from_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="api-spec-workspace-") as temp_dir:
            temp_root = Path(temp_dir)
            plugin_root = temp_root / "plugin"
            write_json(plugin_root / ".codex-plugin" / "plugin.json", {"id": "project-delivery-hub-v1"})

            workspace_root = temp_root / "workspace"
            project_root = workspace_root / "feature_branch" / "P240301Git"
            project_root.mkdir(parents=True)
            config_path = plugin_root / "references" / "local-workspaces.json"
            write_json(
                config_path,
                {
                    "schemaVersion": "1.0.0",
                    "defaultWorkspace": "LOCAL",
                    "workspaces": {
                        "LOCAL": {
                            "workspaceRoot": workspace_root.as_posix(),
                            "agentRoot": ".agent",
                            "rulesRoot": ".agent/project-rules/LOCAL",
                        }
                    },
                },
            )

            workspace = resolve_chain_workspace(
                project_root=project_root,
                workspace_key_arg="LOCAL",
                start_path=plugin_root / "skills" / "api-spec-writer",
            )

            self.assertEqual(workspace.config_source, config_path.resolve())
            self.assertEqual(workspace.resolution_source, "config")
            self.assertEqual(workspace.agent_root, (workspace_root / ".agent").resolve())
            self.assertEqual(workspace.project_rules_root, (workspace_root / ".agent" / "project-rules" / "LOCAL").resolve())


if __name__ == "__main__":
    unittest.main()
