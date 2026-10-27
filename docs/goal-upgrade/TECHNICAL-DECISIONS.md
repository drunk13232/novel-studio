# Creative collaboration technical decisions

Research date: 2026-10-13. This is a design decision record, not completion evidence.

|Requirement|Chosen existing technology|Reason|
|---|---|---|
|Task-specific models|AICenter/Provider/keyring and existing TaskManager|Retain project/request overrides, credentials, consent and usage records|
|NPC response|Text-only LLM adapter or existing restricted Codex capsule|Each actor receives a separate evidence-backed view; no application tools|
|Cards and Lorebook|Pydantic data contracts plus existing character/state sources|Imports are data; filter audiences before keyword activation and apply a context budget|
|Dialogue history|Existing safe JSON write/checkpoint helpers|Original nodes and branches survive restart without another database or task framework|
|Behavior/world reasoning|Conditional AI opinions plus existing World Logic Lab|Actual formulas and constraints remain in mature local solvers|
|Literary review|Existing Reviewer routes, ReviewReport and revision Diff|Bind evidence to the actual text and keep author acceptance/non-destructive candidates|

Inspected [SillyTavern lore](https://github.com/SillyTavern/SillyTavern/blob/release/public/scripts/world-info.js), [group chat](https://github.com/SillyTavern/SillyTavern/blob/release/public/scripts/group-chats.js), [RisuAI lore](https://github.com/risuai/risuai/blob/main/src/ts/process/lorebook.svelte.ts), [memory](https://github.com/risuai/risuai/blob/main/src/ts/process/memory/hypav3.ts), [Promptfoo assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/), [LangGraph checkpoints](https://docs.langchain.com/oss/python/langgraph/persistence), and the official Z3 Python API implementation.

SillyTavern uses AGPL-3.0 and RisuAI's license text is GPL v3. Their code/assets are not copied or distributed. Promptfoo/LangGraph use MIT, but a second evaluator or orchestration runtime is not needed. Promptfoo [safe mode](https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/) is not a general sandbox for untrusted configurations; LangGraph [security advisories](https://github.com/langchain-ai/langgraph/security/advisories) also support explicit trust-boundary review rather than assuming that installing a framework solves safety.

No new runtime dependency or Agent framework is selected. Project Apache-2.0 and copyright decisions remain with the owner. Other-language UI may explicitly fall back; actual language quality is not certified by adding a catalog entry.
