from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def normalize_manifest_target(path: Path) -> Path:
    name = path.name
    if ".autofixed" in name:
        name = name.replace(".autofixed", "")
    return path.with_name(name)


def normalize_results_target(path: Path) -> Path:
    name = path.name
    if ".autofixed" in name:
        name = name.replace(".autofixed", "")
    return path.with_name(name)


def move_or_replace(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == target.resolve():
        return
    if target.exists():
        target.unlink()
    shutil.move(str(source), str(target))


def delete_if_exists(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def report_base_name(path: Path) -> str:
    name = path.name
    for suffix in (".job.json", ".results.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def debug_sidecar_candidates(final_manifest: Path) -> list[Path]:
    base_name = report_base_name(final_manifest)
    return [
        final_manifest.with_name(f"{base_name}.coverage-gap.json"),
        final_manifest.with_name(f"{base_name}.test-improvement-plan.md"),
        final_manifest.with_name(f"{base_name}.autofix-report.json"),
        final_manifest.with_name(f"{base_name}.autofixed.coverage-gap.json"),
        final_manifest.with_name(f"{base_name}.autofixed.test-improvement-plan.md"),
        final_manifest.with_name(f"{base_name}.autofix-report.strong.json"),
        final_manifest.with_name("coverage-gap.json"),
        final_manifest.with_name("module-scope.json"),
        final_manifest.with_name("template-classification.json"),
        final_manifest.with_name("report-job.autofix-report.json"),
    ]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Compact DOCX UnitTest report outputs while preserving Postman MCP evidence artifacts.",
    )
    parser.add_argument("manifest_path", help="Final manifest path, usually *.autofixed.job.json")
    parser.add_argument("results_path", help="Final results path, usually *.autofixed.results.json")
    parser.add_argument(
        "--keep-debug",
        action="store_true",
        help="Keep coverage-gap, improvement-plan, and autofix-report sidecars.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path).expanduser().resolve()
    results_path = Path(args.results_path).expanduser().resolve()
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path.as_posix()}")
    if not results_path.exists():
        raise SystemExit(f"results not found: {results_path.as_posix()}")

    final_manifest = normalize_manifest_target(manifest_path)
    final_results = normalize_results_target(results_path)
    move_or_replace(manifest_path, final_manifest)
    move_or_replace(results_path, final_results)

    removed: list[str] = []
    if not args.keep_debug:
        for candidate in debug_sidecar_candidates(final_manifest):
            if delete_if_exists(candidate):
                removed.append(candidate.as_posix())

    print(f"Final manifest: {final_manifest.as_posix()}")
    print(f"Final results: {final_results.as_posix()}")
    print(f"Removed debug sidecars: {len(removed)}")
    for item in removed:
        print(f"- {item}")


if __name__ == "__main__":
    main()
