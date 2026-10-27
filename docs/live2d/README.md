# Dynamic Companion Preview

An already configured local character appears as a transparent floating pet inside Novel Studio. Drag the character or its name bar to move it; arrow keys on the name bar also work. Click the character or chat button to open conversation, actions and settings in a small adjacent panel. Closing the conversation leaves the character visible. The size slider and reset are in Settings. Position, size, click-through and character selection persist through the existing local companion settings.

The pointer button enables click-through and dims the character so the writing underneath stays usable. The name bar remains interactive. The minus button hides the pet; the top-bar **Live2D Companion** button restores it. Focus mode hides and releases the renderer. The pet does not reserve an editor column and is bounded by the app window; it is not an operating-system-wide always-on-top window. Hiding the pet removes the iframe/WebGL renderer. Merely showing it never starts AI generation.

## Current delivery boundary

Yoshino (朝武芳乃) and Rem have separate character cards, conversations, visible memory, lore, model mapping and voice settings. The personal installation currently selects full-body `yoshino_coherent_v3` and `rem_coherent_v3` Cubism 3 models, based on locally generated fan art. Their frontal breathing, blink, restrained head/hair/clothing motion and expression parameters render through the existing Live2D runtime. They are not official character assets or fully painted, professional Cubism Editor rigs; large limb rotations and unseen-body poses are not delivered. The public Windows ZIP contains no character art, private models, SDK runtime or credentials. Official Haru remains a separately named technical sample.

## Private model import

Use a complete Cubism 3 runtime ZIP: one `.model3.json`, its `.moc3`, referenced textures, optional `.physics3.json`, `.pose3.json`, `.exp3.json`, `.motion3.json` and license notes. Select the correct character, enter source/permission notes and confirm local use rights. Runtime JSON must reference only files inside the package. No scripts, sound recordings or editor projects are accepted. All imported models live in the user-data `companion/live2d/models` directory, outside the installation and public ZIP.

Choose real motion IDs and expressions; the app does not infer what a model's F01 means. Map emotions and click intent only after viewing them. An unmapped expression or motion is visibly unassigned. Model framing uses the mature runtime APIs. Pet placement is a separate, bounded UI position; click-through and focus mode protect writing interactions.

## Runtime licensing and local setup

The MIT l2d wrapper embeds proprietary Live2D Core. MIT does not grant unrestricted Core redistribution. Public packages contain only our frame adapter and no SDK/model assets. The expandable-model AI application release license remains a separate review with Live2D.

For an authorized local developer installation, install the pinned development dependency using `npm ci --ignore-scripts`. After reading and accepting the SDK terms yourself, copy `node_modules/l2d/dist/index.js` unmodified into the private data directory as `companion/live2d/runtime/l2d.js`. The current loader checks its SHA-256. The old-Core script embedded in this exact bundle also needs a standalone pre-load because of its script insertion order; developer setup instructions are in TECHNICAL-SELECTION.md. Do not download untrusted runtime scripts or change the whitelist to accept arbitrary JavaScript.

## Personal Yoshino and Rem rigs

Private authoring sources, textures and model files remain under the user-data `companion` directory, outside source and public releases. Earlier model iterations are retained. The floating presentation reuses these models without creating a second renderer or changing character sessions. No Cubism Editor `.cmo3` project is included. A professional layered-art revision and binding pass remain necessary for broad hand or body poses.

## Dialogue, voice and actions

The model selector reuses existing Codex login or configured AI Provider. Only the private card, current scoped transcript and author-provided lore/memory are sent. The companion does not read whole novels, Canon or references implicitly. Dialogue completion includes restrained emotion and whitelisted intent; actual model capabilities decide what runs.

Voice is opt-in, using installed Windows SAPI5 voices, with separate voice/rate/volume per character. Enable automatic reading for new replies or read the latest reply manually. Pause, resume and stop affect only the owned speech. Mouth values come from real SAPI viseme events. No original actor voice cloning is included. Microphone/ASR is not implemented in this preview.

A request to open a chapter or find a character becomes a visible candidate. Clicking it calls the existing controlled Action Registry and requires the actual frontend receipt. The companion has no Shell, SQL, API-key or raw filesystem tools. Canon/State/Final remain protected.

## Persistence and sharing

Settings and the original Roleplay session structure are stored only in user data. Character and novel scopes are distinct; reopening restores history without automatically calling AI or replaying old speech. No public license choice is made for the whole Novel Studio project. Do not publish private character rigs, SDK assets or voice material without the respective rights.



## Dynamic behavior preview

See [DYNAMIC-COMPANION.md](DYNAMIC-COMPANION.md) for actual behavior capabilities, the separate shared scene, resource limitations and Cubism authoring requirements. This preview does not supply complete production character rigs.
