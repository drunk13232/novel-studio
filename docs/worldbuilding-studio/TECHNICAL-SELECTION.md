# 2.15 technical choices

Reviewed against the actual 2.14.0 source, not old feature prompts. Existing Bible already supplied category fields, stable entity IDs, project-scoped links, images, writer confirmation, revision snapshots and Data Center backup. Existing World Logic Lab already supplied Z3, NetworkX, SymPy, Pint and bounded tasks. Existing AICenter and TaskManager already supplied Codex/API routing, privacy approval, cancellation and history.

Design references inspected on 2026-10-17:

- [World Anvil templates](https://www.worldanvil.com/features/worldbuilding-templates): guided entity-specific questions and flexible entry detail. The local design uses original prompts and existing Novel Studio entities, without copying its templates or assets.
- [Kanka features](https://kanka.io/features): modular entry categories, references, timelines and private knowledge views. Novel Studio retains its own project and Writer isolation boundaries.
- [Obsidian Templates](https://obsidian.md/help/plugins/templates): reusable content separated from concrete notes. Novel Studio exports template definitions separately from world entries.
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12): existing `jsonschema` 4.26.0 validates a schema built from a restricted Pydantic model. No arbitrary executable schema extensions.

No additional packages are installed. React, ordinary semantic controls, existing styling/i18next, Pydantic, jsonschema, Bible storage/history, TaskManager, Codex, Provider routing, and the existing World Logic Lab are reused. The installed NovelForge worldbuilding phase is loaded through the existing professional-method loader with source hashes. Its genre examples are advisory, not author facts or permission to write files. The existing distribution notices and optional-resource boundary remain in force. No new third-party resources or public license decision are introduced.

Native acceptance uses the installed computer-use skill and the existing PyInstaller/WebView2 binary. Browser checks and native checks are recorded independently. Do not count a simulated adapter result as real AI or desktop proof.
