# Embodied software assistant — Preview

Yoshino and Rem are presentation identities for the existing SoftwareAssistant, not independent planners or autonomous pets. Both expose identical application capabilities. The original roleplay workbench remains available separately.

## Execution and isolation

The single existing AssistantCenter, typed Action Registry, confirmations, TaskManager and frontend receipts remain authoritative. The visual shortcut endpoint has an explicit subset of navigation, query, theme/font, literary review and revision-candidate Actions. It does not expose all registered actions or add MCP tools. Review and candidate shortcuts always require confirmation. Character-specific model and context preferences are stored beside the existing assistant settings. Thread reuse and discussion context require the same project, persona, model and permissions. Local audit history is separated by project and persona and retains operation summaries, not full prompts. In-memory conversations are distinct; full chat replay after restart is not implemented.

Selected-text review reuses ReviewCenter, validates the exact UTF-16 range and revision, sends only that passage by default, and anchors returned evidence against the source document. A queued review is tracked as a separate existing task; submission is not review success. Rejected or cancelled proposals do not write prose or Canon. Character presentation never bypasses model/provider data consent.

## Visual events

Task/pending/step receipts drive thinking, searching, execution, approval, result, success, error, rejection and cancellation. AI wording is not a success signal. There are no autonomous model calls. A character click or context menu opens actions; the full assistant supports bounded tasks, confirmation cards, evidence links, stop and reviewed retry. Hidden characters release their iframe/WebGL runtime while existing tasks remain in the assistant.

The floating model docks inside the assistant panel when it is open. Focus mode hides the model. Position, size, local model and synthetic voice settings reuse the companion preferences.

## Assets and truthful capabilities

Runtime: existing l2d 2.1.1 / Cubism, private local resources. New private v5 copies contain six task-oriented motion3 clips (Read, Search, Execute, Confirm, Present, Error) in addition to the twelve existing clips and seven expression files. Curves use only existing head, eye and body parameters. These are basic frontal meshes built from private AI artwork, not official models or production-quality faithful character rigs. No unrigged hand/finger motion is claimed. Editable layered art, limb topology and original-style authoring still require specialist asset work.

Private Core, textures and MOC3 files remain outside public ZIPs. Local validation permission is not public SDK/character redistribution clearance. Project license decision remains with the author.

## Speech

Existing local SAPI5 synthesis and actual viseme events drive mouth movement. Voice playback is explicit and independently configurable; original actors’ voices are not cloned. Browser speech recognition is optional and may be unavailable in WebView2. It requires an explicit notice before starting and only fills the input for user review. No microphone model is downloaded. Codex exposes actual incremental reply events; the ordinary custom-API tool loop still returns turn-level text.

## Mature implementations reviewed

- [Cubism Web SDK](https://docs.live2d.com/en/cubism-sdk-manual/cubism-sdk-for-web/) and [motion blending](https://docs.live2d.com/en/cubism-sdk-manual/motion/): runtime owns mesh deformation and interpolation.
- [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber): bounded emotion mapping and audio/avatar separation; no second server installed.
- [VTube Studio API](https://github.com/DenchiSoft/VTubeStudio): explicit parameter/motion capabilities and authentic execution events.
- [CopilotKit frontend tools](https://docs.copilotkit.ai/frontend-tools): frontend tools and human confirmation; reused Novel Studio’s equivalent registry instead of adding another runtime.
- [SpeechRecognition compatibility](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition) and [Live2D license](https://www.live2d.com/en/sdk/license/).

## Verification boundaries

See the local delivery report for actual checks. A successful local shortcut is not a Codex reasoning test; a fixed SAPI utterance is not an AI voice dialogue; browser checks are not native desktop checks. No real novel data belongs in demo evidence or public assets.

## This delivery's observed checks

- Browser: local menu action, actual character source, Yoshino-to-Rem model switch, rejected revision leaves text unchanged, pending review cancellation, denied reference permission, and editing/saving/undo with avatar disabled. No page errors in this focused check.
- A single iframe stays mounted while opening/closing the assistant panel; no extra model-ready events. The former panel stacking-context bug and redundant-character selection ready-state bug were fixed.
- Real Codex MCP: theme action completed with a frontend receipt in 35.06 seconds. This is one measured call, not a general latency guarantee.
- Real Codex selected-text review: the existing literary review task completed and saved a selection-scoped report with observed model gpt-6.1-sol. The tiny demo passage correctly resulted in insufficient wider context rather than fabricated character findings.
- Native Windows EXE: launched in the isolated demo, displayed the basic private MOC3 model, opened its menu, completed an actual local font-size Action, showed the docked model and execution receipt, then exited normally. The broader native A-H matrix is not fully verified.
- Local SAPI fixed-text validation produced 106 real viseme events. Microphone-to-AI-to-TTS desktop interaction remains unverified; no remote TTS or actor voice was used.
- Relevant backend tests: latest embodied tests 10 passed; earlier focused Live2D 24 and creative-boundary 14 checks passed. Production TypeScript/Vite build passed. No full historical suite was run.

Remaining limits: basic character art/rig fidelity, limited head/eye/body gestures, no complete chat replay after process restart, custom-provider tool conversation still turn-level text, optional ASR platform support, and no precise CPU/GPU/memory comparison. A solver/tool receipt is the source of execution success, not the model's wording.
