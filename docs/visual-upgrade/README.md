# Novel Studio 2.10.2 — Visual direction and local resources

This pass changes presentation only. It keeps the existing editor, navigation, Actions,
project isolation, saving, revisions, backups and on-demand AI initialization.

## Design decisions

- Obsidian: switch skins independently of the underlying workspace and documents.
  https://help.obsidian.md/themes
- Typora: use shared CSS variables for colors and surfaces; scope editor styling carefully.
  https://theme.typora.io/doc/Write-Custom-Theme/
- iA Writer: keep the prose and focus layout visually quiet.
  https://ia.net/writer/support/editor/focus-mode
- SillyTavern: use the distinction between customizable visual identity and actual chat behavior.
  https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/User_Settings/uicustomization.md

The implemented design is our own: layered paper surfaces, a readable book cover,
soft borders, restrained gold accents, consistent rounded controls and compact companion cards.
No product screenshot, proprietary theme stylesheet or external character illustration was copied.

## Skins

The existing six presets remain. Added: Yoshino / Sakura Paper, Rem / Blue & White,
and Rem / Quiet Blue Night. The last preset is dark throughout the UI and editor.
The existing light/dark shortcut switches between the two Rem variants when either is selected.
Other existing presets retain the old moon/night toggle behavior.

Choose Settings → Appearance → Theme. Existing font controls remain separate.
Turn off decorative art to hide companion cards and marks. Focus mode also hides them.
The desk companion is small, placed inside navigation, and can be dismissed for the current session.
It has no audio, animation loop, AI request or background model.

## Local personal portraits

The portrait-first supplement supersedes the earlier motif-only fallback. Named
standing portrait slots now appear in the welcome area, writing navigation,
assistant and roleplay; missing artwork is clearly labelled. See PORTRAITS.md for
resource paths, the manifest, reload controls and public packaging guards.

Personal artwork loads from the user data directory's `companion/` folder;
public source and executable resources carry an empty manifest. The two named
read-only image routes preserve the existing loopback security boundary.

## Compatibility and performance

No dependencies or database structures were added. Appearance is the existing preference field;
only its accepted values and matching assistant theme schema were extended. Old theme values remain valid.
New labels use the existing i18next settings namespace in Simplified Chinese and English;
other languages use the existing honest fallback. CSS uses logical inline/block properties for RTL.

Only the small local resource manifest is requested on a companion theme. Portraits load lazily.
No whole-window blur, large bitmap background, downloaded font or permanent animation was added.

The default global theme stays unchanged. Actual runtime evidence and limitations are recorded
in the accompanying version report rather than inferred from successful builds.
