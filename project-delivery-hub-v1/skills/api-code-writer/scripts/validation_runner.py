from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Iterable


VALIDATION_RETRYABLE_REASON = "assembly_locked"
VALIDATION_MAX_ATTEMPTS = 3
VALIDATION_RETRY_BACKOFF_SECONDS = (2, 5)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [segment.strip() for segment in text.split("\n")]
    return "\n".join(segment for segment in lines if segment)


def execute_validation_command(project_root: Path, command: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=project_root,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def cleanup_retryable_validation_lock_state(project_root: Path) -> None:
    recovery_commands = [
        "dotnet build-server shutdown",
        "taskkill /F /IM dotnet.exe",
        "taskkill /F /IM VBCSCompiler.exe",
        "taskkill /F /IM testhost.exe",
    ]
    for command in recovery_commands:
        subprocess.run(
            command,
            cwd=project_root,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )


def classify_validation_result(result: dict[str, Any]) -> dict[str, str]:
    combined = "\n".join(
        [
            clean_text(result.get("stdout")),
            clean_text(result.get("stderr")),
        ]
    ).lower()
    if "msb3248" in combined or "being used by another process" in combined or "file is locked" in combined:
        return {"kind": "environment", "reason": "assembly_locked"}
    if "nu1301" in combined or "unable to load the service index" in combined or "timed out" in combined:
        return {"kind": "environment", "reason": "external_dependency_unavailable"}
    if "access to the path" in combined or "permission denied" in combined:
        return {"kind": "environment", "reason": "filesystem_access_denied"}
    return {"kind": "code", "reason": "build_or_test_failure"}


def run_validation_command_with_retry(project_root: Path, command: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, VALIDATION_MAX_ATTEMPTS + 1):
        result = execute_validation_command(project_root, command)
        result["attempt"] = attempt
        attempts.append(result)
        if result["passed"]:
            final_result = dict(result)
            if len(attempts) > 1:
                final_result["retryCount"] = len(attempts) - 1
                final_result["recoveredByRetry"] = True
                final_result["attempts"] = attempts
            return final_result
        classification = classify_validation_result(result)
        if classification["reason"] != VALIDATION_RETRYABLE_REASON or attempt >= VALIDATION_MAX_ATTEMPTS:
            final_result = dict(result)
            if len(attempts) > 1:
                final_result["retryCount"] = len(attempts) - 1
                final_result["attempts"] = attempts
            return final_result
        cleanup_retryable_validation_lock_state(project_root)
        backoff_index = min(attempt - 1, len(VALIDATION_RETRY_BACKOFF_SECONDS) - 1)
        time.sleep(VALIDATION_RETRY_BACKOFF_SECONDS[backoff_index])
    return attempts[-1]


def run_validation_checks(project_root: Path, commands: Iterable[str]) -> list[dict[str, Any]]:
    cleanup_retryable_validation_lock_state(project_root)
    return [run_validation_command_with_retry(project_root, command) for command in commands]


def summarize_validation_failure(validation_results: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [result for result in validation_results if not result.get("passed")]
    classifications = []
    for failure in failures:
        classification = classify_validation_result(failure)
        classifications.append(
            {
                "command": failure.get("command"),
                "kind": classification["kind"],
                "reason": classification["reason"],
            }
        )
    overall_kind = "environment" if failures and all(entry["kind"] == "environment" for entry in classifications) else "code"
    return {
        "kind": overall_kind,
        "classifications": classifications,
    }


def evaluate_validation_outcome(validation_results: list[dict[str, Any]]) -> dict[str, Any]:
    all_passed = all(result["passed"] for result in validation_results)
    if all_passed:
        return {
            "effectivePassed": True,
            "status": "tests_passed",
            "phase": "validated",
            "degraded": False,
            "validationFailure": None,
            "note": "",
        }

    validation_failure = summarize_validation_failure(validation_results)
    failed_results = [result for result in validation_results if not result.get("passed")]
    build_failures = [
        result
        for result in failed_results
        if clean_text(result.get("command")).lower().startswith("dotnet build ")
    ]
    non_build_failures = [
        result
        for result in failed_results
        if not clean_text(result.get("command")).lower().startswith("dotnet build ")
    ]
    unit_passed = any(
        result.get("passed") and "enterpriseapiunit.csproj" in clean_text(result.get("command")).lower()
        for result in validation_results
    )
    integration_passed = any(
        result.get("passed") and "enterpriseapiintegration.csproj" in clean_text(result.get("command")).lower()
        for result in validation_results
    )
    only_retryable_build_lock = (
        bool(build_failures)
        and not non_build_failures
        and validation_failure["kind"] == "environment"
        and all(entry["reason"] == VALIDATION_RETRYABLE_REASON for entry in validation_failure["classifications"])
    )
    degraded_pass = only_retryable_build_lock and unit_passed and integration_passed
    note = ""
    if degraded_pass:
        note = "dotnet build 僅因可恢復文件鎖失敗，且 Unit/Integration 測試皆通過；依技能規則視為降級通過。"

    return {
        "effectivePassed": all_passed or degraded_pass,
        "status": "tests_passed" if all_passed or degraded_pass else "tests_failed",
        "phase": "validated" if all_passed or degraded_pass else "validation_failed",
        "degraded": degraded_pass,
        "validationFailure": validation_failure,
        "note": note,
    }


def build_validation_summary(validation_results: list[dict[str, Any]]) -> str:
    if not validation_results:
        return "Validation not executed."
    passed = sum(1 for result in validation_results if result.get("passed"))
    return f"{passed}/{len(validation_results)} validation check(s) passed."


def summarize_validation_retries(validation_results: list[dict[str, Any]]) -> str:
    if not validation_results:
        return "none"
    total_retries = sum(int(result.get("retryCount") or 0) for result in validation_results)
    recovered = [
        clean_text(result.get("command"))
        for result in validation_results
        if result.get("recoveredByRetry") and clean_text(result.get("command"))
    ]
    if total_retries <= 0:
        return "none"
    recovered_text = ", ".join(recovered) if recovered else "none"
    return f"totalRetries={total_retries}; recoveredCommands={recovered_text}"
