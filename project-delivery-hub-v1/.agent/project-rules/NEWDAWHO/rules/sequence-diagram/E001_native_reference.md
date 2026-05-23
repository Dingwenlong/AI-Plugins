# E.001 Native VSDX Reference Standard

Source snapshot:

- Project reference: `v1.x Reference/E.001_01.vsdx`
- Built-in copy: `references/standard-examples/E001_native_reference.vsdx`
- Preview: `references/standard-examples/E001_native_reference_preview.png`

Use this file as the current DAWHO native VSDX style baseline when generating formal sequence diagrams. E.001 is the preferred baseline for native Visio structure and layout.

The built-in copy is also the skill's bundled DAWHO project Visio theme template. It must retain `visio/theme/theme1.xml` and the document theme relationship; `scripts/build_native_visio_sequence.ps1` uses it as the automatic fallback when the caller-provided `-TemplateVsdx` is missing the DAWHO project theme.

Observed native structure:

- `TopLevelShapes=91`
- `Page.Connects=52`
- `visio/media=0`
- `visio/embeddings=0`
- `ForeignDataXmlEntries=0`
- Masters include `Actor lifeline`, `Object lifeline`, `Message`, `Self Message`, `Return Message`, `Alternative fragment`, `Optional fragment`, `Loop fragment`, `Other fragment`, and `Interaction operand`.

Style and layout rules to preserve:

- User is a native `Actor lifeline`; APP and Enterprise are native `Object lifeline` shapes.
- Message labels live on `Message` / `Self Message` / `Return Message` shapes, not detached text boxes.
- Self Message labels are left-aligned text blocks placed immediately to the right of the folded self-call arrow. Technical parameter snippets inside the label keep the same text color/style as the surrounding Chinese label.
- `alt` uses `Alternative fragment`; `opt` uses `Optional fragment`; `loop` uses `Loop fragment`; `ref` and business `group` use `Other fragment` when no dedicated reference/group master exists.
- Branch conditions use native `Interaction operand` regions. The first `if` condition does not show an extra line above the condition text; `else` operands provide the visible branch separator and extend to the next operand or to the frame bottom.
- `alt` frames should fully contain the content that belongs to each branch, including nested `ref` frames, response arrows, orange pointer strips, and follow-up APP self-calls, with Visio container membership repaired after geometry changes.
- The top title is a separate centered title band with clear vertical breathing room above participants.
- Section dividers sit below participant heads with enough space; they must not crowd the participant label boxes.
- Orange reference strips are used only for `循序圖請參考...` supporting SVG/sequence references and stay inset inside `ref` frames.
- Default native style policy is `messageStyle.policy = "e001-reference"`: preserve Visio master/theme appearance and use per-message overrides only for explicit DAWHO emphasis.
- Use `messageStyle.policy = "dawho-red"` only when the user explicitly wants all message arrows and labels red.

Mandatory QA:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_native_visio_output.ps1 -VsdxPath <output.vsdx>
```

The gate must pass before handoff.
