# Novel Studio 2.12.2 — Literary Study Design System

## Direction and references

The owner supplied three concept boards: overall literary studio, components, and writing plus evaluation. The implementation uses their ivory / ink-teal / navy / antique-gold direction and editorial book / plant motifs. The boards are visual references, never sliced into UI controls or bundled as product assets.

Primary rules: real controls first; decorative art at welcoming/empty/heading edges; clean manuscript surface; truthful task and evaluation states; keyboard and RTL compatibility. Existing information architecture, editor, model routing and data formats remain authoritative.

## Tokens

The existing `--paper`, `--canvas`, `--surface`, `--ink`, `--muted`, `--line`, `--accent`, `--wash`, `--gold` and `--on-accent` remain the theme interface. `--text`, `--panel`, `--bg` and `--border` alias those tokens for older workbench components.

The Moon theme is refined into an ivory study: paper #faf9f4, surface #fffefa, ink #253c4c, accent #1f6363, gold #b08e52. Other theme palettes stay intact. Do not hardcode light card surfaces into shared components.

Controls use 6px corners, cards 7–12px. Shadows appear only for floating dialogs, shelf cards and small elevation, rather than every content block. Typography: existing user-selected UI font for controls, system serif fallback for editorial headings, existing author-selected writing font for manuscript. No downloaded or redistributed fonts.

## Component families

| Family | Implementation | Required states |
| --- | --- | --- |
| Buttons and inputs | Existing native/React controls in study-design.css | normal, hover, active, keyboard focus, disabled, aria-invalid |
| Choice and tags | Existing checkbox/radio/select, semantic accent | chosen state plus label; no color-only errors |
| Book cards | Existing actions and real cover; CoverArtwork only when no cover exists | no source cover write, stable candidate mapping |
| Tabs and navigation | Existing DeskTabs / Sidebar / quality tabs | active, focus, keyboard controls, scrollable groups |
| Paper workspace | Existing CodeMirror container and saved positions | no bitmap below body text, clean focus mode |
| Evidence and entities | Existing review/literary/world/reference cards | source links and uncertainty remain present |
| Scores | ScoreMedallion and lazy EvaluationCharts | actual score, null/insufficient, stale; no invented grades |
| Dialog and settings | Existing StudioDialog and SettingsCenter | bounded height, independent scrolling, close/save actions |
| Matrix and timeline | Existing matrix / vis-timeline / React Flow | existing plans versus facts, selection and zoom retained |
| Empty and loading | LiteraryArt / existing Empty / status feedback | decorative image accessible-hidden, useful actual message |

Shared visual rules live in `web/frontend/src/study-design.css`; new small presentation components in `study-components.tsx`. Charts are lazy loaded only when an evaluation result is displayed. Native element semantics and existing event handlers are retained. Avoid adding overlapping page-specific theme overrides.

## Data and semantic integrity

Score graphics use stored actual results, 0–100 axes, null for unavailable values, and real chapter numbers. A curve compares selected local chapter judgments, not a longitudinal scientific quality measure. Missing judgments are not joined or assigned zero. Stale reports remain visibly stale. Partial coverage still suppresses complete-range total scores.

The art is not Canon, a novel cover replacement, or a character resource. Existing private Yoshino/Rem models and SDK assets stay outside source and public packages. Decorations can be hidden by the existing setting; focus mode retains a clean editor.

## Responsive and international layout

Use logical inline/block properties for new spacing and alignment. Existing graph/chart coordinate canvases remain LTR where required. Viewport emulation, browser zoom and real Windows system DPI are different evidence categories. Never change system DPI unattended.

## Development sequence and verification

Foundation and shelf → actual page check → writing and evaluation → actual component interaction → complex existing workbenches → final packaged WebView screenshots. The stage run found a fixed-height review heading overlapping tabs; it was changed to grow with translated text rather than forcing the click.

The final delivery report records actual screenshots and interaction results. This specification is not itself an acceptance result.
