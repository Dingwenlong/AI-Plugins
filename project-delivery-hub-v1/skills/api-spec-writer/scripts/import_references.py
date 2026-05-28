#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def find_plugin_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return None


def main() -> int:
    plugin_root = find_plugin_root()
    if plugin_root is None:
        raise SystemExit(
            "无法定位 project-delivery-hub-v1 插件根目录；"
            "请从已安装插件目录运行，或直接调用 reference-index-importer。"
        )

    target = plugin_root / "skills" / "reference-index-importer" / "scripts" / "import_reference_indexes.py"
    if not target.exists():
        raise SystemExit(f"reference-index-importer 导入脚本不存在：{target.as_posix()}")

    print(
        "提示：api-spec-writer/scripts/import_references.py 仅保留旧入口兼容；"
        "全局 external API / DB Schema reference 导入职责属于 reference-index-importer。",
        file=sys.stderr,
    )
    target_scripts_dir = str(target.parent)
    if target_scripts_dir not in sys.path:
        sys.path.insert(0, target_scripts_dir)
    sys.argv = [str(target), *sys.argv[1:]]
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code is None:
            return 0
        print(exc.code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
