from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ENTERPRISE_FRAMEWORK_PROFILE = "enterpriseapi"
PRIMARY_FRAMEWORK_GUIDELINE = "project framework guideline"


@dataclass(frozen=True)
class FrameworkProfile:
    profile_name: str
    repo_root: Path
    api_project_path: Path
    business_interface_project_path: Path
    business_project_path: Path
    entity_project_path: Path
    unit_test_project_path: Path
    integration_test_project_path: Path
    controller_dir: Path
    business_interface_dir: Path
    business_dir: Path
    entity_dir: Path
    unit_test_dir: Path
    integration_test_dir: Path
    root_namespace: str
    registration_strategy: str


@dataclass(frozen=True)
class FrameworkPlan:
    framework_profile: str
    module_name: str
    controller_file: str
    interface_file: str
    service_files: tuple[str, ...]
    entity_files: tuple[str, ...]
    unit_test_files: tuple[str, ...]
    integration_test_files: tuple[str, ...]
    creation_mode: str
    target_file: str
    target_method: str
    request_type: str | None
    response_type: str
    source_candidates: tuple[str, ...]
    registration_strategy: str


def dedupe_paths(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def collect_code_target_files(plan: FrameworkPlan) -> list[str]:
    return dedupe_paths(
        [
            plan.controller_file,
            plan.interface_file,
            plan.target_file,
            *plan.service_files,
            *plan.entity_files,
        ]
    )


def collect_test_handoff_files(plan: FrameworkPlan) -> tuple[list[str], list[str], list[str]]:
    unit_test_target_files = list(plan.unit_test_files)
    integration_test_target_files = list(plan.integration_test_files)
    return unit_test_target_files, integration_test_target_files, dedupe_paths(
        [*unit_test_target_files, *integration_test_target_files]
    )
