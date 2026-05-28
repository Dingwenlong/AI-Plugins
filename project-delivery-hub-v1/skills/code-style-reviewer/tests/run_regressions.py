from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_code_style.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_rules_root(root: Path) -> Path:
    rules_root = root / "rules-root"
    common = rules_root / "rules" / "code-guidelines" / "p240301-v6.2" / "rules" / "common-style.md"
    data = rules_root / "rules" / "code-guidelines" / "p240301-v6.2" / "rules" / "data-access.md"
    catalog = rules_root / "rules" / "code-guidelines" / "p240301-v6.2" / "catalog.json"
    write(common, "# common-style\n")
    write(data, "# data-access\n")
    write(catalog, "{}\n")
    write(
        rules_root / "catalog.json",
        json.dumps(
            {
                "schemaVersion": "1.0.0",
                "workspaceKey": "TEST",
                "activeReviewStatuses": ["approved", "active"],
                "rulePacks": {
                    "apiCodeWriter": {
                        "strict": True,
                        "requiredRuleIds": [
                            "p240301-v6.2-common-style",
                            "p240301-v6.2-data-access",
                        ],
                        "requiredAssets": [],
                        "optionalAssets": [],
                    }
                },
                "rules": [
                    {
                        "ruleId": "p240301-v6.2-common-style",
                        "category": "code-guidelines",
                        "title": "common-style",
                        "path": "rules/code-guidelines/p240301-v6.2/rules/common-style.md",
                        "reviewStatus": "approved",
                    },
                    {
                        "ruleId": "p240301-v6.2-data-access",
                        "category": "code-guidelines",
                        "title": "data-access",
                        "path": "rules/code-guidelines/p240301-v6.2/rules/data-access.md",
                        "reviewStatus": "approved",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    return rules_root


def make_fixture(root: Path) -> tuple[Path, Path, Path]:
    project = root / "project"
    agent = root / "agent"
    rules_root = make_rules_root(root)
    source = project / "FooService.cs"
    write(
        source,
        """/*
 * 文件说明: Foo service
 * 新增人员: AI
 */
using System.Collections.Generic;
namespace Demo
{
    public class FooService
    {
        private readonly IBarService BarService;

        public FooService(IBarService barService)
        {
            BarService = barService;
        }

        public async Task<Foo> GetAsync(int id)
        {
            Foo item = new Foo();
            List<string> names = new List<string> { "a" };
            if (item == null)
            {
                return new Foo();
            }
            var rows = await _sql.QueryAsync<Foo>("SELECT Id FROM Foo", commandParameters: [new SqlParameter("@Id", id)]);
            return rows.FirstOrDefault();
        }

        private SqlParameter BuildSqlParameter(string name, object value)
        {
            return new SqlParameter(name, value);
        }
    }
}
""",
    )
    write(project / "stale.bak", "old")
    api_dir = agent / "context" / "Common" / "apis" / "COMMON.test"
    write(
        api_dir / "change-plan.json",
        json.dumps(
            {
                "analysis": {
                    "targetFile": "FooService.cs",
                    "serviceFiles": ["FooService.cs"],
                    "codeTargetFiles": ["FooService.cs"],
                    "queryContractsSelected": [{"sql": "SELECT Id FROM Foo"}],
                    "devGuidelineLoadHints": [
                        {"ruleId": "common-style", "loadPath": "rules/code-guidelines/p240301-v6.2/rules/common-style.md"},
                        {"ruleId": "data-access", "loadPath": "rules/code-guidelines/p240301-v6.2/rules/data-access.md"},
                    ],
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    return project, agent, rules_root


def run_reviewer(project: Path, agent: Path, rules_root: Path, *extra: str) -> dict:
    command = [
        sys.executable,
        str(SCRIPT),
        "--project-root",
        str(project),
        "--agent-root",
        str(agent),
        "--context-root",
        str(agent / "context"),
        "--rules-root",
        str(rules_root),
        "--workspace-key",
        "TEST",
        "--function-code",
        "Common",
        *extra,
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def assert_category(payload: dict, category: str) -> None:
    categories = {finding["category"] for finding in payload["findings"]}
    assert category in categories, f"missing category {category}: {categories}"


def test_context_review_finds_style_issues() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project, agent, rules_root = make_fixture(Path(tmp))
        result = run_reviewer(project, agent, rules_root, "--api-id", "COMMON.test")
        assert result["findingCount"] >= 8
        report = read_json(agent / "context" / "Common" / "apis" / "COMMON.test" / "code-style-review.json")
        assert report["scope"] == "context"
        assert report["apiId"] == "COMMON.test"
        assert report["targetFiles"] == ["FooService.cs"]
        for category in [
            "namespace_style",
            "object_creation",
            "collection_initialization",
            "tagged_comment",
            "dependency_injection",
            "data_access",
            "header_author",
            "header_update_record",
            "repository_hygiene",
        ]:
            assert_category(report, category)
        assert any(source["ruleId"] == "api-code-writer" for source in report["ruleSources"])
        assert any(source["ruleId"] == "data-access" for source in report["ruleSources"])


def test_scope_files_uses_explicit_file_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project, agent, rules_root = make_fixture(Path(tmp))
        run_reviewer(project, agent, rules_root, "--scope", "files", "--file", "FooService.cs")
        report = read_json(agent / "context" / "Common" / "code-style-review.json")
        assert report["targetFiles"] == ["FooService.cs"]
        assert report["scope"] == "files"
        assert report["summary"]["findingCount"] > 0


def main() -> int:
    test_context_review_finds_style_issues()
    print("[pass] test_context_review_finds_style_issues")
    test_scope_files_uses_explicit_file_only()
    print("[pass] test_scope_files_uses_explicit_file_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
