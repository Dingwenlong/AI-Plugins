from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


TEXT_RE = re.compile(r"<text\b[^>]*>.*?</text>", re.S)
REF_ENHANCEMENT_RE = re.compile(
    r'<g data-project-ref-enhancement="(?:arrow|pointer-bg)">.*?</g>',
    re.S,
)
COMMON_REF_DISPLAY_RE = re.compile(
    r"(?:循序圖請參考[:：]\s*)?\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+(?:\s*[\u3400-\u9fff].*)?"
)
COMMON_REF_SELF_CALL_RE = re.compile(r"(?:CommonFunc\.[A-Za-z0-9_]+|CommonUtil/[A-Za-z0-9_]+)")


def attr(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{name}="([^"]+)"', tag)
    return match.group(1) if match else None


def text_content(text_tag: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text_tag))


def participant_lifeline_x(svg: str, anchors: list[str]) -> float | None:
    lifelines = re.finditer(
        r'<g class="participant-lifeline"(?P<attrs>[^>]*)>.*?'
        r'<line\b(?P<line_attrs>[^>]*)',
        svg,
        re.S,
    )
    for lifeline in lifelines:
        attrs = lifeline.group("attrs")
        uid = attr(attrs, "data-entity-uid") or ""
        qualified_name = attr(attrs, "data-qualified-name") or ""
        if uid in anchors or qualified_name in anchors:
            x1 = attr(lifeline.group("line_attrs"), "x1")
            return float(x1) if x1 is not None else None
    return None


def find_ref_frame(svg: str, pos: int) -> tuple[float, float, float, float, int, int, str] | None:
    window_start = max(0, pos - 2500)
    window = svg[window_start:pos]
    candidates: list[tuple[float, float, float, float, int, int, str]] = []
    for match in re.finditer(r"<rect\b[^>]*/>", window):
        tag = match.group(0)
        style = attr(tag, "style") or ""
        try:
            x = float(attr(tag, "x") or "")
            y = float(attr(tag, "y") or "")
            width = float(attr(tag, "width") or "")
            height = float(attr(tag, "height") or "")
        except ValueError:
            continue
        if width > 100 and height > 80 and "stroke:#1E5054" in style:
            candidates.append(
                (
                    x,
                    y,
                    width,
                    height,
                    window_start + match.start(),
                    window_start + match.end(),
                    tag,
                )
            )
    return candidates[-1] if candidates else None


def compact_ref_arrow(
    frame: tuple[float, float, float, float, int, int, str],
    anchor_x: float,
    method_y: float,
) -> str:
    frame_x, frame_y, frame_width, frame_height, _, _, _ = frame
    x1 = min(max(anchor_x, frame_x + 16.0), frame_x + frame_width - 76.0)
    x2 = min(frame_x + frame_width - 18.0, x1 + 66.0)
    y1 = min(max(frame_y + 34.0, method_y + 47.0), frame_y + frame_height - 72.0)
    y2 = y1 + 16.0
    stroke = "#B01513"
    return f'''<g data-project-ref-enhancement="arrow">
<line style="stroke:{stroke};stroke-width:1.5625;" x1="{x1:.4f}" x2="{x2:.4f}" y1="{y1:.4f}" y2="{y1:.4f}"/>
<line style="stroke:{stroke};stroke-width:1.5625;" x1="{x2:.4f}" x2="{x2:.4f}" y1="{y1:.4f}" y2="{y2:.4f}"/>
<line style="stroke:{stroke};stroke-width:1.5625;" x1="{x1:.4f}" x2="{x2:.4f}" y1="{y2:.4f}" y2="{y2:.4f}"/>
<polygon fill="{stroke}" points="{x1:.4f},{y2:.4f} {x1 + 12.0:.4f},{y2 - 5.0:.4f} {x1 + 12.0:.4f},{y2 + 5.0:.4f}" style="stroke:{stroke};stroke-width:1.5625;"/>
</g>'''


def pointer_background(
    pointer_tag: str,
    file_tag: str,
    frame: tuple[float, float, float, float, int, int, str],
) -> str:
    frame_x, _, frame_width, _, _, _, _ = frame
    px = float(attr(pointer_tag, "x") or "0")
    py = float(attr(pointer_tag, "y") or "0")
    plen = float(attr(pointer_tag, "textLength") or "0")
    fx = float(attr(file_tag, "x") or "0")
    fy = float(attr(file_tag, "y") or f"{py + 23.0}")
    flen = float(attr(file_tag, "textLength") or "0")
    x = max(frame_x + 4.0, min(px, fx) - 14.0)
    right = min(frame_x + frame_width - 4.0, max(px + plen, fx + flen) + 14.0)
    y = py - 19.0
    height = max(24.0, fy - py + 25.0)
    return (
        '<g data-project-ref-enhancement="pointer-bg">'
        f'<rect fill="#F4A100" height="{height:.4f}" style="stroke:none;" '
        f'width="{right - x:.4f}" x="{x:.4f}" y="{y:.4f}"/>'
        "</g>"
    )


def transparent_frame_tag(frame_tag: str) -> str:
    cleaned = re.sub(r'\s+\bfill="[^"]*"', "", frame_tag)
    return cleaned.replace("<rect", '<rect fill="none"', 1)


def replace_user_head(svg: str) -> str:
    match = re.search(
        r'<g class="participant participant-head"(?=[^>]*data-qualified-name="User")[^>]*>.*?</g>',
        svg,
        re.S,
    )
    if not match:
        return svg

    group = match.group(0)
    if 'data-style="project-task-icon"' in group and "<circle" in group and "<rect" in group and "<path" in group:
        return svg

    ellipse = re.search(r'<ellipse[^>]*cx="([0-9.]+)"', group)
    rect = re.search(r'<rect[^>]*width="([0-9.]+)"[^>]*x="([0-9.]+)"', group)
    circle = re.search(r'<circle[^>]*cx="([0-9.]+)"', group)
    if ellipse:
        center_x = float(ellipse.group(1))
    elif rect:
        center_x = float(rect.group(2)) + float(rect.group(1)) / 2
    elif circle:
        center_x = float(circle.group(1))
    else:
        return svg

    label_width = 58.3221
    label_height = 43.4357
    label_x = center_x - label_width / 2
    label_y = 81.5033
    text_len = 36.4471
    text_x = center_x - text_len / 2
    text_y = label_y + 28.4424
    stroke = "#1E5054"
    stroke_width = 3.125

    scale = 1.35
    source_head_center_y = 1123.94
    source_circle_top = source_head_center_y - 3.40157
    source_bottom = 1154.55
    icon_height = (source_bottom - source_circle_top) * scale
    icon_top = label_y - 8.0 - icon_height
    icon_x = center_x - (17.01 * scale) / 2

    def xy(x: float, y: float) -> tuple[float, float]:
        return icon_x + x * scale, icon_top + (y - source_circle_top) * scale

    body_points = [
        (3.4, 1154.55),
        (3.4, 1137.54),
        (3.4, 1144.35),
        (0, 1144.35),
        (0, 1130.74),
        (1.7, 1129.04),
        (15.31, 1129.04),
        (17.01, 1130.74),
        (17.01, 1144.35),
        (13.61, 1144.35),
        (13.61, 1137.54),
        (13.61, 1154.55),
        (8.5, 1154.55),
        (8.5, 1140.94),
        (8.5, 1154.55),
        (3.4, 1154.55),
    ]
    body_path = "M" + " L".join(f"{x:.4f},{y:.4f}" for x, y in (xy(px, py) for px, py in body_points)) + " Z"
    head_cx, head_cy = xy(8.505, source_head_center_y)
    entity_uid = attr(group, "data-entity-uid")
    group_id = attr(group, "id")
    identity_attrs = ""
    if entity_uid:
        identity_attrs += f' data-entity-uid="{entity_uid}"'
    identity_attrs += ' data-qualified-name="User" data-style="project-task-icon"'
    if group_id:
        identity_attrs += f' id="{group_id}"'

    replacement = f'''<g class="participant participant-head"{identity_attrs}>
<circle cx="{head_cx:.4f}" cy="{head_cy:.4f}" r="{3.40157 * scale:.4f}" fill="#FFFFFF" style="stroke:{stroke};stroke-width:{stroke_width:.3f};"/>
<path d="{body_path}" fill="#FFFFFF" style="stroke:{stroke};stroke-width:{stroke_width:.3f};stroke-linecap:round;stroke-linejoin:round;"/>
<rect fill="#FFFFFF" height="{label_height:.4f}" style="stroke:{stroke};stroke-width:{stroke_width:.3f};" width="{label_width:.4f}" x="{label_x:.4f}" y="{label_y:.4f}"/>
<text fill="#000000" font-family="'Times New Roman'" font-size="18.75" font-weight="bold" lengthAdjust="spacing" textLength="{text_len:.4f}" x="{text_x:.4f}" y="{text_y:.4f}">User</text>
</g>'''
    return svg[: match.start()] + replacement + svg[match.end() :]


def enhance_common_refs(svg: str, anchors: list[str]) -> str:
    svg = REF_ENHANCEMENT_RE.sub("", svg)
    texts = list(TEXT_RE.finditer(svg))
    edits: list[tuple[int, int, str]] = []
    anchor_x = participant_lifeline_x(svg, anchors)

    for index, text in enumerate(texts):
        content = text_content(text.group(0))
        if not COMMON_REF_SELF_CALL_RE.search(content):
            continue

        frame = find_ref_frame(svg, text.start())
        if frame is None:
            continue

        try:
            method_y = float(attr(text.group(0), "y") or "")
        except ValueError:
            continue

        frame_x, _, frame_width, _, frame_start, frame_end, frame_tag = frame
        arrow_anchor_x = anchor_x if anchor_x is not None else frame_x + frame_width / 2.0
        edits.append((text.start(), text.start(), compact_ref_arrow(frame, arrow_anchor_x, method_y)))
        edits.append((frame_start, frame_end, transparent_frame_tag(frame_tag)))

        pointer = None
        file_text = None
        for later in texts[index + 1 : min(index + 8, len(texts))]:
            later_content = text_content(later.group(0))
            if COMMON_REF_DISPLAY_RE.search(later_content):
                pointer = later
                file_text = later
                break
            if "循序圖請參考" in later_content:
                pointer = later
                continue
            if pointer is not None and COMMON_REF_DISPLAY_RE.search(later_content):
                file_text = later
                break
        if pointer is not None and file_text is not None:
            edits.append((pointer.start(), pointer.start(), pointer_background(pointer.group(0), file_text.group(0), frame)))

    for start, end, replacement in sorted(set(edits), key=lambda item: item[0], reverse=True):
        svg = svg[:start] + replacement + svg[end:]
    return svg


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-process project PlantUML SVG ref blocks.")
    parser.add_argument("--svg", required=True, type=Path, help="SVG file to update in place.")
    parser.add_argument(
        "--anchor",
        action="append",
        default=None,
        help="Participant uid or qualified name used as the CommonFunc/CommonUtil self-call anchor. Can be repeated.",
    )
    args = parser.parse_args()

    anchors = args.anchor or ["Ent", "Enterprise", "part3"]
    svg = args.svg.read_text(encoding="utf-8")
    svg = replace_user_head(svg)
    updated = enhance_common_refs(svg, anchors)
    args.svg.write_text(updated, encoding="utf-8")
    print(f"postprocessed {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
