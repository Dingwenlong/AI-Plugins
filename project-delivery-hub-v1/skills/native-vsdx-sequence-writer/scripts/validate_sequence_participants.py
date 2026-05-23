from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


COMMON_REF_DISPLAY_RE = re.compile(
    r"(?:循序圖請參考[:：]\s*)?\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+(?:\s*[\u3400-\u9fff].*)?"
)
COMMON_REF_SELF_CALL_RE = re.compile(r"(?:CommonFunc\.[A-Za-z0-9_]+|CommonUtil/[A-Za-z0-9_]+)")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_puml(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if re.search(r"(?m)^\s*(?:ref\s+over\s+\w+\s*:\s*)?CommonFunc/[A-Za-z0-9_]+", text):
        fail(errors, f"{path}: CommonFunc references must use dot notation, e.g. CommonFunc.MethodName")
    if re.search(r"(?m)^\s*(?:ref\s+over\s+\w+\s*:\s*)?CommonUtil\.[A-Za-z0-9_]+", text):
        fail(errors, f"{path}: CommonUtil references must keep slash notation, e.g. CommonUtil/MethodName")
    for name in ("DB", "Redis"):
        bad = re.search(
            rf"(?im)^\s*(database|collections|queue)\s+['\"]?{re.escape(name)}\b",
            text,
        )
        if bad:
            fail(errors, f"{path}: {name} uses non-boxed PlantUML keyword `{bad.group(1)}`")


def participant_head(svg: str, uid_or_name: str, name: str | None = None) -> str | None:
    if name is None:
        pattern = (
            r'<g class="participant participant-head"[^>]*data-qualified-name="'
            + re.escape(uid_or_name)
            + r'"[^>]*>(.*?)</g>'
        )
    else:
        pattern = (
            r'<g class="participant participant-head"[^>]*data-entity-uid="'
            + re.escape(uid_or_name)
            + r'"[^>]*data-qualified-name="'
            + re.escape(name)
            + r'"[^>]*>(.*?)</g>'
        )
    match = re.search(pattern, svg, re.S)
    return match.group(0) if match else None


def attr(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{name}="([^"]+)"', tag)
    return match.group(1) if match else None


def text_content(text_tag: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text_tag))


def validate_svg(path: Path, errors: list[str]) -> None:
    svg = path.read_text(encoding="utf-8")

    user = participant_head(svg, "User")
    app = participant_head(svg, "APP")
    if user is None:
        fail(errors, f"{path}: User participant head not found")
    elif "<ellipse" in user or "<rect" not in user or "<path" not in user:
        fail(errors, f"{path}: User is not project task-icon boxed style")
    elif 'data-style="project-task-icon"' not in user and 'fill="none"' in user:
        fail(errors, f"{path}: User still looks like a stick actor, not the project Visio task icon")
    elif app is not None:
        user_widths = {float(v) for v in re.findall(r"stroke-width:([0-9.]+)", user)}
        app_widths = {float(v) for v in re.findall(r"stroke-width:([0-9.]+)", app)}
        if app_widths and user_widths and max(user_widths) < max(app_widths) - 0.01:
            fail(errors, f"{path}: User border stroke is thinner than APP participant border")

    for name in ("DB", "Redis"):
        head = participant_head(svg, name)
        if head is None:
            continue
        if "<rect" not in head or "<ellipse" in head or "<path" in head:
            fail(errors, f"{path}: {name} is not boxed participant style")

    text_re = re.compile(r"<text\b[^>]*>.*?</text>", re.S)
    common_ref_count = 0
    for text in text_re.finditer(svg):
        content = text_content(text.group(0))
        if not COMMON_REF_SELF_CALL_RE.search(content):
            continue
        preceding = svg[max(0, text.start() - 1200) : text.start()]
        if re.search(r">\s*ref\s*</text>", preceding) and "<rect" in preceding:
            common_ref_count += 1
    if common_ref_count:
        arrow_count = svg.count('data-project-ref-enhancement="arrow"')
        pointer_bg_count = svg.count('data-project-ref-enhancement="pointer-bg"')
        if arrow_count < common_ref_count:
            fail(errors, f"{path}: CommonFunc/CommonUtil refs are missing red self-call arrows")
        if pointer_bg_count < common_ref_count or "#F4A100" not in svg:
            fail(errors, f"{path}: CommonFunc/CommonUtil refs are missing orange SVG pointer backgrounds")

        lifeline_xs = [
            float(x)
            for x in re.findall(
                r'<g class="participant-lifeline"[^>]*>.*?<line\b[^>]*x1="([0-9.]+)"',
                svg,
                re.S,
            )
        ]
        for arrow in re.finditer(r'<g data-project-ref-enhancement="arrow">(.*?)</g>', svg, re.S):
            first_line = re.search(r"<line\b[^>]*/>", arrow.group(1))
            if first_line is None:
                fail(errors, f"{path}: CommonFunc/CommonUtil ref arrow has no folded line geometry")
                continue
            try:
                x1 = float(attr(first_line.group(0), "x1") or "")
            except ValueError:
                fail(errors, f"{path}: CommonFunc/CommonUtil ref arrow is missing an anchor x1")
                continue
            if lifeline_xs and min(abs(x1 - x) for x in lifeline_xs) > 2.0:
                fail(errors, f"{path}: CommonFunc/CommonUtil ref arrow is not anchored to a participant lifeline")

        for bg in re.finditer(r'<g data-project-ref-enhancement="pointer-bg"><rect\b([^>]*)/></g>', svg):
            bg_attrs = bg.group(1)
            try:
                bg_x = float(attr(bg_attrs, "x") or "")
                bg_right = bg_x + float(attr(bg_attrs, "width") or "")
            except ValueError:
                fail(errors, f"{path}: orange SVG pointer background is missing x/width")
                continue

            following = list(text_re.finditer(svg, bg.end(), min(len(svg), bg.end() + 1200)))
            pointer = None
            file_text = None
            for text in following[:4]:
                content = text_content(text.group(0))
                if COMMON_REF_DISPLAY_RE.search(content):
                    pointer = text
                    file_text = text
                    break
                if "循序圖請參考" in content:
                    pointer = text
                elif pointer is not None and COMMON_REF_DISPLAY_RE.search(content):
                    file_text = text
                    break
            if pointer is None or file_text is None:
                continue
            file_content = text_content(file_text.group(0))
            if ".svg" in file_content:
                fail(errors, f"{path}: CommonFunc/CommonUtil ref display name still includes .svg")
            if "SVG" in file_content:
                fail(errors, f"{path}: CommonFunc/CommonUtil ref display name still includes the legacy SVG folder wording")
            if not re.search(r"循序圖請參考[:：]\s*\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+\s*[\u3400-\u9fff]", file_content):
                fail(errors, f"{path}: CommonFunc/CommonUtil ref display name must use `循序圖請參考：basename 中文說明`")
            try:
                min_x = min(float(attr(pointer.group(0), "x") or ""), float(attr(file_text.group(0), "x") or ""))
                max_right = max(
                    float(attr(pointer.group(0), "x") or "") + float(attr(pointer.group(0), "textLength") or "0"),
                    float(attr(file_text.group(0), "x") or "") + float(attr(file_text.group(0), "textLength") or "0"),
                )
            except ValueError:
                continue
            if bg_x > min_x + 0.5 or bg_right < max_right - 0.5:
                fail(errors, f"{path}: orange SVG pointer background does not fully cover the pointer text")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate project sequence participant styles for PUML/SVG outputs."
    )
    parser.add_argument("--puml", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()

    if not args.puml and not args.svg:
        parser.error("provide --puml and/or --svg")

    errors: list[str] = []
    if args.puml:
        validate_puml(args.puml, errors)
    if args.svg:
        validate_svg(args.svg, errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("project participant style validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
