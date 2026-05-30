#!/usr/bin/env python3
"""One-time onboarding scaffolder for project-delivery-hub-v1.

Copies the shipped `.example` config templates into their real locations so a
fresh install can be configured. NEVER overwrites an existing real config
(idempotent / safe to re-run). Fill in the placeholder values afterwards
(see the printed next steps and skills/workspace-onboarding/SKILL.md).

Usage:
  python init_workspace_config.py --workspace-root D:\\Path\\To\\MyProject [--workspace-key KEY] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# scripts -> workspace-onboarding -> skills -> plugin root
PLUGIN_ROOT = SCRIPT_DIR.parent.parent.parent
REFERENCES = PLUGIN_ROOT / "references"


def build_plan(workspace_root: Path) -> list[tuple[str, Path, Path]]:
    cfg = workspace_root / ".agent" / "config"
    return [
        ("local-workspaces", REFERENCES / "local-workspaces.example.json", REFERENCES / "local-workspaces.json"),
        ("design-source-registry", REFERENCES / "design-source-registry.example.json", cfg / "design-source-registry.json"),
        ("feature-tester-map", REFERENCES / "feature-tester-map.example.json", cfg / "feature-tester-map.json"),
        ("wedoc-smartsheet-targets", REFERENCES / "wedoc-smartsheet-targets.example.json", cfg / "wedoc-smartsheet-targets.json"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold real configs from shipped .example templates (never overwrites existing files)."
    )
    parser.add_argument("--workspace-root", required=True, help="Workspace root, e.g. D:\\Path\\To\\MyProject")
    parser.add_argument("--workspace-key", help="Workspace key (informational; set it in local-workspaces.json afterwards)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not write any file")
    parser.add_argument(
        "--rule-pack",
        default="generic",
        help="Rule pack to scaffold into <workspaceRoot>/.agent/project-rules/<key>: 'generic' (default, project-agnostic template), '<workspaceKey>' (copy the bundled .agent snapshot's real pack), or 'none'.",
    )
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    created: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    for label, example, dest in build_plan(workspace_root):
        if not example.exists():
            missing.append(f"{label}: 模板缺失 {example}")
            continue
        if dest.exists():
            skipped.append(f"{label}: 已存在，跳过 -> {dest}")
            continue
        if args.dry_run:
            created.append(f"{label}: [dry-run] 将创建 -> {dest}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(example, dest)
            created.append(f"{label}: 已创建 -> {dest}")

    # Rule pack: copy a template into <workspaceRoot>/.agent/project-rules/<key> (never overwrite).
    rule_pack = (args.rule_pack or "").strip()
    if rule_pack.lower() != "none":
        key = (args.workspace_key or "").strip() or "MYPROJECT"
        dest_rp = workspace_root / ".agent" / "project-rules" / key
        if rule_pack.lower() == "generic":
            src_rp = PLUGIN_ROOT / "references" / "rule-pack-templates" / "generic"
        else:
            src_rp = PLUGIN_ROOT / ".agent" / "project-rules" / rule_pack
        label = f"rule-pack({rule_pack})"
        if not src_rp.exists():
            missing.append(f"{label}: 模板/快照缺失 {src_rp}（非 generic 时需包内已带 .agent bundle）")
        elif dest_rp.exists():
            skipped.append(f"{label}: 已存在，跳过 -> {dest_rp}")
        elif args.dry_run:
            created.append(f"{label}: [dry-run] 将复制 {src_rp} -> {dest_rp}")
        else:
            shutil.copytree(src_rp, dest_rp)
            created.append(f"{label}: 已复制 -> {dest_rp}")

    title = "=== 脚手架结果（dry-run，未写入） ===" if args.dry_run else "=== 脚手架结果 ==="
    print(title)
    for line in created:
        print("  +", line)
    for line in skipped:
        print("  =", line)
    for line in missing:
        print("  !", line)
    if not (created or skipped or missing):
        print("  (无可处理项)")

    cfg = workspace_root / ".agent" / "config"
    key_hint = f"（workspaceKey 用 '{args.workspace_key}'）" if args.workspace_key else ""
    print("\n=== 下一步：填占位值（详见 skills/workspace-onboarding/SKILL.md） ===")
    print(f"  1. {REFERENCES / 'local-workspaces.json'}: 把 workspaceRoot/agentRoot/rulesRoot/defaultCodeRoot 改成本机绝对路径{key_hint}")
    print(f"  2. {cfg / 'design-source-registry.json'}: 填 PRD/TSD/API Detail/Common/IT SPEC/旧项目目录与各 functionCode")
    print(f"  3. {cfg / 'feature-tester-map.json'}: 填 featureId -> 测试人员")
    print(f"  4. {cfg / 'wedoc-smartsheet-targets.json'}: 仅用企业微信异动记录时填真实 webhook/user_id（私有，勿提交）")
    print("  5. SQL fixture（如需第 03 步）: 按 api-sql-fixture-preparer 文档建 .agent/config/sql-fixture-targets.local.json（私有、无密码勿提交）")
    print("  6. 开发规范: 用 project-rule-analyzer 写入 <rulesRoot> 并生成 catalog.json + rule packs")
    print("\n提示：chain-workspace.json 由 chain_workspace.py 自动生成，无需手抄；本脚本不覆盖已存在配置，可安全重复运行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
