# Native Shape Library

This folder stores small, stable native-shape templates used by `scripts/build_native_visio_sequence.ps1`.

The current DAWHO native VSDX visual standard is `references/standard-examples/E001_native_reference.vsdx`, copied from project `v1.x Reference/E.001_01.vsdx`. When template behavior is ambiguous, match the E.001 reference.

The goal is to keep visual design decisions out of the generator code:

- one template file per visual component;
- `manifest.json` is the runtime registry;
- the generator loads the library first and falls back to built-in drawing only when a template is missing;
- recurring visual fixes should update the relevant template file whenever possible.

Current templates:

- `page-title`: top page title style modeled after project reference sequence diagrams such as `v1.x Reference/E.001_01.vsdx`.
- `user-participant-head`: composite User participant rule; drops the native `Actor lifeline / User` master and keeps its built-in lifeline/style as the connector target.
- `actor-head`: diagnostic fallback `User` icon; formal native delivery should use `Actor lifeline`.
- `participant-head-box`: fallback participant label box for non-UML/manual paths.
- `object-participant-lifeline`: composite object participant rule for `APP`, `Enterprise`, and other non-User UML object lifelines; drops native masters and preserves native master style.
- `uml-fragment-frame`: native UML fragment mapping for `alt`, `opt`, `loop`, `ref`, and business `group`; `ref` / `group` use `Other fragment` when no dedicated reference master exists. `alt` operands are normalized after layout so the first condition has no extra top line, later `else` operands provide the branch separators, and the final operand bottom stays tight to the frame bottom.
- `clipped-header-tab`: manual fallback group / alt / ref / loop clipped-corner header tab.
- `section-divider`: double-line stage divider with centered title box.
- `orange-pointer-strip`: Common SVG / supporting sequence orange reference strip.
- `alt-condition-label`: branch condition labels inside `alt` / `else` frames.
- `note-card`: yellow explanatory note card.
- `ref-common-svg-block`: CommonFunc/CommonUtil method text plus orange SVG pointer layout.

Native self-call label rule:

- `Self Message` labels default to a left-aligned text block immediately to the right of the folded arrow. Keep small technical parameter snippets in the same character color/style as the surrounding Chinese label.
- A normal self-message consumes one participant connection-point interval for the folded arrow and reserves one connection-point interval to the next message arrow; ref-only CommonFunc/CommonUtil self-calls keep the compact ref layout.

Default message style profile:

- Formal native specs should declare `messageStyle.policy = "e001-reference"` unless the user explicitly asks for another style.
- `e001-reference` means preserve the Visio native master/theme appearance from the E.001 standard and use per-message overrides for explicit DAWHO emphasis.
- Use `dawho-red` only when all message arrows and labels should be red.
- Use `preserve-native` only when raw Visio master defaults are explicitly requested.

Validation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_native_shape_library.ps1
```
