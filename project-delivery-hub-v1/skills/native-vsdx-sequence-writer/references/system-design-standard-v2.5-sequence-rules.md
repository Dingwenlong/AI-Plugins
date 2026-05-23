# System Design Standard v2.5 - Sequence Diagram Rules

Source: `P240301_永豐商銀新大戶_系統設計規範 v2.5 20260514.docx`.

Use this reference only when generating, checking, repairing, or handing off 既有专案 sequence diagrams. Keep `SKILL.md` as the light entry; load this file for system-design-standard details.

## Delivery Contract

- Formal project delivery is a Visio source diagram. Normal output should be native editable VSDX, not an SVG image imported into Visio.
- Source files must be delivered together with exported visual files when visual files are requested.
- Customer Visio compatibility target is Visio 2013; the team may use Visio 2021 while authoring, but final delivery should be saved/exported in Visio 2013-2016 compatible form when the environment supports it.
- PlantUML and SVG remain content drafts or visual references unless the user explicitly asks for a non-standard fallback.
- When a TSD version changes, archive the original TSD and sequence diagram before editing the new version.

## Naming And File Rules

- Diagram file naming follows `{PRDNumber}_{sequenceNo}.svg` for SVG references, for example `D.001.001_01.svg`.
- For native VSDX delivery in this skill, continue using the plugin contract: one `{functionCode}_01.vsdx` under `output/sequence_diagram/{functionCode}/vsdx/`, with tabs inside the VSDX when needed.
- Do not copy generated diagrams back to `v1.x Reference/` unless the user explicitly asks for that delivery exception.

## Standard Participants

Use participants only when they are directly involved in the visible flow.

- Frontend UI: `APP`
- System maintenance/background content source: `後台`
- Session/content source: `Redis`
- Backend API: `Enterprise`
- Red envelope API: `RedEnvelope`
- API Gateway: `Gateway`
- JWT signing/authorization: `JWT`
- DB and Redis must appear as plain boxed participants in formal delivery, not cylinder/storage icons.
- User only initiates actions. Do not draw `APP -> User` or return arrows to User; user prompts, page display, refresh, and popup text are APP self-actions.

Default participant order remains `User -> APP -> Enterprise -> IRIS -> DB -> Redis` unless the actual flow requires a narrower participant set or an explicit project standard says otherwise.

## Message Content

- Participants should have visible spacing; lifelines should align cleanly and not stick together.
- Request arrows and backend-related messages must have readable labels. When a message depends on backend data, show the DB table/API/source name in the message label or nearby note.
- Response arrows must describe the returned result. Do not leave a bare `return` or unlabeled arrow.
- APP popup/reminder content should be written as text, not pasted as a screenshot.
- Do not place full request/response field lists on arrows. Use business-readable labels and keep full field contracts in API Detail.

## Fragment Rules

- `alt` represents IF/ELSE and must have at least two branches.
- A single conditional block should use `opt`, not `alt`.
- `group` represents a business stage or readable block.
- `loop` represents repeated work.
- `ref` represents an external reference only. For new deliveries, keep the ref body concise and pointing to the referenced location; do not put process flow inside the ref block or in a lower `[]` area.
- New ref-only rules do not force retroactive repair of already-delivered diagrams unless the user asks.
- All borders and fragment lines must avoid overlap. Message labels, fragment headers, orange pointer strips, and lifelines need enough spacing to remain readable.

## Common Method References

- CommonFunc/CommonUtil references should be modeled as `ref` blocks, not as ordinary main-flow self-calls or standalone participants.
- The visible reference self-call notation is fixed by layer: internal CommonFunc uses `CommonFunc.MethodName`; outward CommonUtil keeps `CommonUtil/MethodName`.
- The visible ref should identify the common method and Chinese description, while the real file name or path can stay in the landing note / trace list.
- In native VSDX, the ref block may contain the compact reference self-call that identifies the CommonFunc/CommonUtil target plus the pointer strip. It must not contain actual main-flow request, response, return, APP display, or Enterprise business-processing messages.
- If a normal message or self-call begins with `CommonFunc.` / `CommonFunc/` / `CommonUtil.` / `CommonUtil/`, rewrite it as a ref before delivery.

## Special Standard Patterns

- Member type, member identity, or online-banking qualification validation should be shown near the functional entry only when PRD/API Detail requires it. Do not add generic validation without evidence.
- City/county list acquisition should use API + MMA SQL/local memory cache style when that project rule applies, not frontend-only JSON lookup.
- Network-password secondary validation should follow the project standard drawing pattern when the feature requires it.
- APP direct access to New DAWHO backend data does not need extra sequence labeling; Enterprise access to backend data must clearly show the backend data source.

## Validation Checklist

Before handoff:

- Every tab has a clear user entry, normally `User -> APP`.
- Request/response labels are present and business-readable.
- Backend-related arrows state the backend data source/API where needed.
- `alt`, `opt`, `ref`, and CommonFunc/CommonUtil usage matches this reference.
- User, DB, and Redis visual styles match the project native baseline.
- Formal VSDX exists or the blocker is explicitly reported; normal delivery must not say VSDX is only a future optional step.
