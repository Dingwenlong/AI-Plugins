from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable
from zipfile import BadZipFile, ZipFile


SEQUENCE_EXTENSIONS = {".json", ".puml", ".vsdx", ".svg"}
FORMAT_PRIORITY = {
    "native_visio_spec": 0,
    "plantuml": 1,
    "vsdx": 2,
    "svg": 3,
}
SYSTEM_KEYWORDS = {
    "app",
    "api",
    "backend",
    "commonfunc",
    "commonutil",
    "db",
    "enterprise",
    "iris",
    "jwt",
    "redis",
    "request",
    "response",
    "user",
}
FIELD_STOPWORDS = {
    "addexchangedepositinit",
    "commonfunc",
    "commonutil",
    "deposit",
    "enterprise",
    "false",
    "iris",
    "null",
    "request",
    "response",
    "true",
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_token(value: object) -> str:
    text = clean_text(value).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def split_identifier(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return [part for part in re.split(r"[^A-Za-z0-9]+", spaced) if len(part) >= 3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def function_variants(function_code: str | None) -> set[str]:
    text = clean_text(function_code).upper()
    if not text:
        return set()
    variants = {text, text.replace(".", "_"), text.replace(".", ""), text.replace("_", ".")}
    variants.add(normalize_token(text))
    return {value for value in variants if value}


def registry_tokens(agent_dir: Path, function_code: str | None) -> set[str]:
    tokens = function_variants(function_code)
    registry_path = agent_dir / "config" / "design-source-registry.json"
    registry = load_json_file(registry_path) or {}
    functions = registry.get("functions") if isinstance(registry.get("functions"), dict) else {}
    normalized_function = normalize_token(function_code)
    for key, payload in functions.items():
        if not isinstance(payload, dict):
            continue
        values: list[str] = [str(key)]
        for field in ("aliases", "prdCodes", "tsdCodes"):
            values.extend(str(item) for item in list(payload.get(field) or []))
        normalized_values = {normalize_token(value) for value in values if clean_text(value)}
        if normalized_function and normalized_function not in normalized_values and normalized_function != normalize_token(key):
            continue
        for value in values:
            tokens.update(function_variants(value))
    return {value for value in tokens if value}


def registry_sequence_roots(agent_dir: Path) -> list[Path]:
    registry_path = agent_dir / "config" / "design-source-registry.json"
    registry = load_json_file(registry_path) or {}
    directories = registry.get("directories") if isinstance(registry.get("directories"), dict) else {}
    roots: list[Path] = []
    for key in ("sequenceDiagram", "sequenceDiagrams"):
        value = directories.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            text = clean_text(item)
            if not text:
                continue
            path = Path(text).expanduser()
            if not path.is_absolute():
                path = agent_dir.parent / path
            if path.exists():
                roots.append(path.resolve())
    return roots


def sequence_kind(path: Path) -> str | None:
    suffix = path.suffix.casefold()
    name = path.name.casefold()
    if suffix == ".json" and ("native_visio_spec" in name or "sequence" in name):
        return "native_visio_spec"
    if suffix == ".puml":
        return "plantuml"
    if suffix == ".vsdx":
        return "vsdx"
    if suffix == ".svg":
        return "svg"
    return None


def path_matches_function(path: Path, tokens: set[str]) -> bool:
    if not tokens:
        return False
    normalized_path = normalize_token(path.as_posix())
    normalized_name = normalize_token(path.name)
    for token in tokens:
        normalized_token = normalize_token(token)
        if normalized_token and (normalized_token in normalized_path or normalized_token in normalized_name):
            return True
    return False


def find_sequence_files(root: Path, tokens: set[str], *, authority: str, matched_by: str) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    candidates: list[dict[str, Any]] = []
    roots = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
    for path in roots:
        if path.suffix.casefold() not in SEQUENCE_EXTENSIONS:
            continue
        if ".bak" in path.name.casefold():
            continue
        kind = sequence_kind(path)
        if kind is None:
            continue
        if not path_matches_function(path, tokens):
            continue
        candidates.append(
            {
                "path": path.resolve(),
                "kind": kind,
                "authority": authority,
                "matchedBy": matched_by,
            }
        )
    return candidates


def walk_handoff_paths(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = clean_text(key).casefold()
            if any(marker in key_text for marker in ("sequence", "时序", "時序", "循序", "vsdx", "svg", "puml")):
                text = clean_text(item)
                if text:
                    yield text
            yield from walk_handoff_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_handoff_paths(item)
    else:
        text = clean_text(value)
        if re.search(r"\.(?:vsdx|svg|puml|json)$", text, re.IGNORECASE) and any(
            marker in text.casefold() for marker in ("sequence", "时序", "時序", "循序", "vsdx", "svg", "puml", "native_visio")
        ):
            yield text


def handoff_sequence_files(agent_dir: Path, function_code: str | None, tokens: set[str]) -> list[dict[str, Any]]:
    if not function_code:
        return []
    handoff_path = agent_dir / "functions" / function_code / "handoff" / "development-handoff.json"
    handoff = load_json_file(handoff_path)
    if not handoff:
        return []
    candidates: list[dict[str, Any]] = []
    for raw_path in walk_handoff_paths(handoff):
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = agent_dir / path
        if not path.exists() or not path.is_file():
            continue
        kind = sequence_kind(path)
        if kind is None:
            continue
        if tokens and not path_matches_function(path, tokens):
            continue
        candidates.append(
            {
                "path": path.resolve(),
                "kind": kind,
                "authority": "design_handoff",
                "matchedBy": "development_handoff",
            }
        )
    return candidates


def discover_sequence_files(agent_dir: Path, function_code: str | None, sequence_root: Path | None = None) -> list[dict[str, Any]]:
    tokens = registry_tokens(agent_dir, function_code)
    sources: list[dict[str, Any]] = []
    local_root = agent_dir / "functions" / clean_text(function_code) / "analysis" / "sequence-diagrams"
    sources.extend(find_sequence_files(local_root, tokens, authority="agent_function_sequence", matched_by="function_analysis"))
    sources.extend(handoff_sequence_files(agent_dir, function_code, tokens))
    if sequence_root is not None:
        sources.extend(find_sequence_files(sequence_root, tokens, authority="cli_sequence_root", matched_by="sequence_root"))
    for root in registry_sequence_roots(agent_dir):
        sources.extend(find_sequence_files(root, tokens, authority="design_source_registry", matched_by="registry_sequence_directory"))

    deduped: dict[Path, dict[str, Any]] = {}
    for source in sources:
        path = source["path"].resolve()
        existing = deduped.get(path)
        if existing is None or FORMAT_PRIORITY[source["kind"]] < FORMAT_PRIORITY[existing["kind"]]:
            deduped[path] = source
    return sorted(
        deduped.values(),
        key=lambda item: (FORMAT_PRIORITY[item["kind"]], item["path"].as_posix().casefold()),
    )


def parse_native_json(path: Path) -> dict[str, Any]:
    payload = load_json_file(path) or {}
    participants = [clean_text(item.get("label") or item.get("id")) for item in list(payload.get("participants") or []) if isinstance(item, dict)]
    sections = [clean_text(item.get("label")) for item in list(payload.get("sections") or []) if isinstance(item, dict)]
    messages = [clean_text(item.get("text")) for item in list(payload.get("messages") or []) if isinstance(item, dict)]
    frames = [
        clean_text(item.get("condition") or item.get("label") or item.get("kind"))
        for item in list(payload.get("frames") or [])
        if isinstance(item, dict)
    ]
    pointers = [clean_text(item.get("text")) for item in list(payload.get("orangePointers") or []) if isinstance(item, dict)]
    text_blocks = [clean_text(item.get("text")) for item in list(payload.get("texts") or []) if isinstance(item, dict)]
    return {
        "participants": [item for item in participants if item],
        "sections": [item for item in sections if item],
        "messages": [item for item in messages if item],
        "frames": [item for item in frames if item],
        "references": [item for item in pointers if item],
        "textBlocks": [item for item in text_blocks if item],
    }


def parse_plantuml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    participants: list[str] = []
    sections: list[str] = []
    messages: list[str] = []
    frames: list[str] = []
    references: list[str] = []
    for line in text.splitlines():
        stripped = clean_text(re.sub(r"<[^>]+>", "", line))
        if not stripped or stripped.startswith(("'", "skinparam", "@")):
            continue
        participant_match = re.match(r'^(?:actor|participant)\s+"?([^"]+)"?', stripped, re.IGNORECASE)
        if participant_match:
            participants.append(clean_text(participant_match.group(1)))
            continue
        section_match = re.match(r"^==\s*(.+?)\s*==$", stripped)
        if section_match:
            sections.append(clean_text(section_match.group(1)))
            continue
        frame_match = re.match(r"^(alt|else|opt|loop|group)\s+(.+)$", stripped, re.IGNORECASE)
        if frame_match:
            frames.append(clean_text(frame_match.group(2)))
            continue
        if stripped.casefold().startswith("ref "):
            references.append(stripped)
            continue
        if "->" in stripped or "-->" in stripped:
            messages.append(stripped.split(":", 1)[-1].replace("\\n", " ").strip())
    return {
        "participants": participants,
        "sections": sections,
        "messages": [item for item in messages if item],
        "frames": frames,
        "references": references,
        "textBlocks": [],
    }


def parse_xml_text(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
    except ET.ParseError:
        return {"participants": [], "sections": [], "messages": [], "frames": [], "references": [], "textBlocks": []}
    texts = [clean_text(html.unescape(item)) for item in root.itertext() if clean_text(item)]
    titles: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].casefold()
        if tag in {"title", "desc"}:
            value = clean_text(" ".join(element.itertext()))
            if value:
                titles.append(value)
    return {
        "participants": [],
        "sections": titles,
        "messages": texts[:80],
        "frames": [item for item in texts if item.startswith("[") and item.endswith("]")][:30],
        "references": [item for item in texts if "循序圖請參考" in item or ".svg" in item.casefold()][:30],
        "textBlocks": [],
    }


def parse_vsdx(path: Path) -> dict[str, Any]:
    texts: list[str] = []
    try:
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if not (name.startswith("visio/pages/") and name.endswith(".xml")):
                    continue
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError:
                    continue
                texts.extend(clean_text(html.unescape(item)) for item in root.itertext() if clean_text(item))
    except (BadZipFile, OSError):
        return {"participants": [], "sections": [], "messages": [], "frames": [], "references": [], "textBlocks": []}
    return {
        "participants": [],
        "sections": [],
        "messages": texts[:120],
        "frames": [item for item in texts if item.startswith("[") and item.endswith("]")][:30],
        "references": [item for item in texts if "循序圖請參考" in item or ".svg" in item.casefold()][:30],
        "textBlocks": [],
    }


def parse_sequence_file(path: Path, kind: str) -> dict[str, Any]:
    if kind == "native_visio_spec":
        return parse_native_json(path)
    if kind == "plantuml":
        return parse_plantuml(path)
    if kind == "vsdx":
        return parse_vsdx(path)
    if kind == "svg":
        return parse_xml_text(path, kind=kind)
    return {"participants": [], "sections": [], "messages": [], "frames": [], "references": [], "textBlocks": []}


def joined_extract_text(extract: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("participants", "sections", "messages", "frames", "references", "textBlocks"):
        parts.extend(clean_text(item) for item in list(extract.get(key) or []) if clean_text(item))
    return "\n".join(parts)


def api_tokens(api_name: str) -> set[str]:
    tokens = {normalize_token(api_name)}
    tokens.update(normalize_token(part) for part in split_identifier(api_name))
    return {token for token in tokens if len(token) >= 4}


def extract_applies_to_api(extract: dict[str, Any], api_name: str) -> bool:
    tokens = api_tokens(api_name)
    if not tokens:
        return False
    normalized = normalize_token(joined_extract_text(extract))
    return any(token in normalized for token in tokens)


def extract_symbols(text: str) -> list[str]:
    symbols: list[str] = []
    for pattern in (
        r"\b(?:IRIS\.)?[A-Z]{2}\d{4}\b",
        r"\b(?:CommonFunc|CommonUtil|Backend|DepositCommonUtil)[./][A-Za-z_][A-Za-z0-9_]*\b",
        r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(",
    ):
        for match in re.finditer(pattern, text):
            symbol = clean_text(match.group(0)).rstrip("(")
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols[:20]


def extract_dependencies(text: str, evidence_id: str) -> list[dict[str, Any]]:
    dependencies: dict[str, dict[str, Any]] = {}

    def remember(kind: str, target: str, description: str) -> None:
        cleaned_target = clean_text(target).strip("/.")
        if not cleaned_target:
            return
        dependency_id = normalize_token(f"{kind}.{cleaned_target}") or kind.casefold()
        dependencies.setdefault(
            dependency_id,
            {
                "id": dependency_id,
                "type": kind,
                "description": description,
                "evidenceIds": [evidence_id],
            },
        )

    for system in ("IRIS", "CommonFunc", "CommonUtil", "Backend", "DB", "Redis"):
        pattern = re.compile(rf"\b{system}\s*(?:[./>:-]+)\s*(?P<target>[A-Za-z0-9_./-]+)", re.IGNORECASE)
        for match in pattern.finditer(text):
            remember(system, match.group("target"), match.group(0))
    for match in re.finditer(r"\b(?P<owner>CommonFunc|CommonUtil|DepositCommonUtil)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)", text, re.IGNORECASE):
        remember(match.group("owner"), f"{match.group('method')}()", match.group(0))
    for match in re.finditer(r"\b(?P<code>[A-Z]{2}\d{4})\b", text):
        remember("IRIS", match.group("code"), match.group(0))
    return list(dependencies.values())


def field_names(fields: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()

    def walk(items: list[dict[str, Any]]) -> None:
        for item in items:
            name = clean_text(item.get("fieldName") or item.get("field") or item.get("name"))
            if name:
                names.add(normalize_token(name))
            children = item.get("children")
            if isinstance(children, list):
                walk([child for child in children if isinstance(child, dict)])

    walk(fields)
    return names


def extract_field_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(r"\b[a-z][A-Za-z0-9_]{2,}\b", text):
        token = match.group(0)
        normalized = normalize_token(token)
        if normalized in FIELD_STOPWORDS or normalized in SYSTEM_KEYWORDS:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens[:40]


def extract_response_codes(text: str) -> list[str]:
    codes: list[str] = []
    for match in re.finditer(r"\b\d{4}\b", text):
        code = match.group(0)
        if code not in codes:
            codes.append(code)
    return codes[:20]


def build_sequence_context(
    *,
    agent_dir: Path,
    function_code: str | None,
    api_name: str,
    request_fields: list[dict[str, Any]],
    response_fields: list[dict[str, Any]],
    known_response_codes: Iterable[str],
    sequence_root: Path | None = None,
) -> dict[str, Any]:
    sources = discover_sequence_files(agent_dir, function_code, sequence_root=sequence_root)
    source_entries: list[dict[str, Any]] = []
    extracts: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    legacy_references: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    notes: list[str] = []

    if not sources:
        notes.append("未找到匹配目前 functionCode 的時序圖；本次 API Spec 不以時序圖補強業務邏輯。")
        return {
            "sourceEntries": [],
            "extracts": [],
            "steps": [],
            "legacyReferences": [],
            "runtimeDependencies": [],
            "constraints": [],
            "unresolved": [],
            "notes": notes,
        }

    known_fields = field_names(request_fields + response_fields)
    known_codes = {clean_text(code) for code in known_response_codes if clean_text(code)}
    seen_dependency_ids: set[str] = set()

    for index, source in enumerate(sources, start=1):
        path = source["path"]
        kind = source["kind"]
        parsed = parse_sequence_file(path, kind)
        text = joined_extract_text(parsed)
        applies = extract_applies_to_api(parsed, api_name)
        evidence_id = f"sequence_{index}_{normalize_token(path.stem)[:36] or 'diagram'}"
        source_entries.append(
            {
                "path": relative_or_absolute(path, agent_dir),
                "kind": kind,
                "sha256": sha256_file(path),
                "matchedBy": source["matchedBy"],
                "authority": source["authority"],
            }
        )
        extracts.append(
            {
                "evidenceId": evidence_id,
                "path": relative_or_absolute(path, agent_dir),
                "kind": kind,
                "appliedToApi": applies,
                "participants": list(parsed.get("participants") or [])[:20],
                "sections": list(parsed.get("sections") or [])[:30],
                "messages": list(parsed.get("messages") or [])[:80],
                "frames": list(parsed.get("frames") or [])[:40],
                "references": list(parsed.get("references") or [])[:40],
            }
        )
        if not applies:
            continue

        snippet_parts = []
        for label, key in (("sections", "sections"), ("frames", "frames"), ("messages", "messages"), ("references", "references")):
            values = [clean_text(item) for item in list(parsed.get(key) or []) if clean_text(item)]
            if values:
                snippet_parts.append(f"{label}: " + " | ".join(values[:12]))
        snippet = "\n".join(snippet_parts) or text[:1000]
        legacy_references.append(
            {
                "id": evidence_id,
                "kind": "sequenceDiagram",
                "title": path.name,
                "origin": relative_or_absolute(path, agent_dir),
                "authority": source["authority"],
                "symbols": extract_symbols(text),
                "summary": clean_text("；".join(list(parsed.get("sections") or [])[:3])) or path.name,
                "snippet": snippet[:4000],
            }
        )

        for step_index, message in enumerate(list(parsed.get("messages") or [])[:20], start=1):
            steps.append(
                {
                    "step": f"sequence-{index}-{step_index}",
                    "title": f"時序圖：{clean_text(message)[:80]}",
                    "details": clean_text(message),
                    "evidenceIds": [evidence_id],
                }
            )
        for frame in list(parsed.get("frames") or [])[:20]:
            constraints.append(
                {
                    "constraintType": "sequence_branch",
                    "rule": clean_text(frame),
                    "severity": "warning",
                    "evidenceIds": [evidence_id],
                }
            )
        for dependency in extract_dependencies(text, evidence_id):
            dependency_id = dependency["id"]
            if dependency_id in seen_dependency_ids:
                continue
            seen_dependency_ids.add(dependency_id)
            dependencies.append(dependency)

        unknown_fields = [field for field in extract_field_tokens(text) if normalize_token(field) not in known_fields]
        if unknown_fields:
            unresolved.append(
                {
                    "topic": "sequenceDiagram.fieldContract",
                    "reason": "時序圖出現 API Detail/TSD 請求或回應契約未宣告的欄位候選。",
                    "blocking": True,
                    "blockedReason": "sequence diagram field contract mismatch",
                    "missingFacts": unknown_fields[:12],
                    "suggestedOwner": "spec",
                    "nextDecisionNeeded": "確認這些欄位是否應補入 API Detail/TSD，或從時序圖中排除為非介面欄位。",
                }
            )
        unknown_codes = [code for code in extract_response_codes(text) if known_codes and code not in known_codes]
        if unknown_codes:
            unresolved.append(
                {
                    "topic": "sequenceDiagram.responseCodeContract",
                    "reason": "時序圖出現 API Detail/TSD 未交接的 responseCode。",
                    "blocking": True,
                    "blockedReason": "sequence diagram response code mismatch",
                    "missingFacts": unknown_codes[:12],
                    "suggestedOwner": "spec",
                    "nextDecisionNeeded": "確認 responseCode catalog 歸屬與 API Detail/TSD 範例或錯誤碼規則是否需要補齊。",
                }
            )

    if source_entries and not legacy_references:
        notes.append("已找到目前 functionCode 的時序圖，但未命中目前 apiName；僅記錄為 artifact 證據，不補強此 API 的業務邏輯。")

    return {
        "sourceEntries": source_entries,
        "extracts": extracts,
        "steps": steps,
        "legacyReferences": legacy_references,
        "runtimeDependencies": dependencies,
        "constraints": constraints,
        "unresolved": unresolved,
        "notes": notes,
    }
