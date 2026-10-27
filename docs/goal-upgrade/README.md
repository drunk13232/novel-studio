# Goal-Driven Creative Preview (2.10.0)

This is a Preview. New UI is translated into Simplified Chinese and English. Other languages use the established fallback; they are not counted as translated coverage.

## Author workflows

1. **Characters → roleplay**: open a character and select “与这个人物对话”. Choose your Persona, NPCs, chapter/time/place and a scene. A Persona may use an existing character, but that character cannot also be an NPC. Each actor can use a separate configured model. At most four NPCs reply in one turn.
2. **Roleplay → material**: tick actual messages, then save as inspiration, scene candidate, or editable chapter material. Short stories use an independent revision of their existing single manuscript. Anthologies retain material as notes; open an individual story for prose. No simulation becomes Canon or State automatically.
3. **Memory**: choose “整理个人记忆候选”, inspect its source turns and epistemic status, edit it, select the actors allowed to see it, and confirm. Manual memory is also supported. Saved proposals and confirmed memory survive restart. A suspicion remains a suspicion.
4. **Branches**: edits and regeneration create branches. Counterfactual scenes preserve the Baseline. Changing the knowledge chapter requires an empty dialogue branch. Comparisons show actual inputs and dialogue, not invented numerical predictions.
5. **Literary review**: choose a prose version, one of twelve dimensions, model, criteria and optional specific characters/references/style profiles. Reader mode receives public prose and criteria only. Evidence buttons locate verbatim quotes. Ambiguous quotes show multiple locations for author choice. Keep, reject or create a revision todo.
6. **Revision**: a verified quote can request a Writer-safe candidate in the existing Monaco Diff. Full Checker feedback is not forwarded. Reject leaves prose unchanged. Accepting a protected Final creates an independent manual revision, never overwrites Final.
7. **Behavior → experiment**: choose the behavior reviewer model, ask a conditional question, inspect premises, alternatives and uncertainty, and transfer the proposed quantitative question to the existing World Logic Lab. Design, challenge and explanation have separate model routes. Edit and freeze rules before local execution.
8. **Settings → model assignments**: set global or project task routes and per-request overrides. Provider model IDs/capabilities remain user-configured. API budgets can notify or block; unknown prices/output limits block when strict mode requires a request estimate. These are local estimates, not provider bills. Codex login quotas are independent.

## Deliberate limits

- Character-card JSON supports a documented v2/v3 subset, not PNG cards or all tavern plugins. Privileged prompts, scripts, extensions and remote resources are ignored.
- Source-backed knowledge needs committed receipts. Missing safe wording/history is UNKNOWN, not reconstructed from current author truth.
- Lorebook activates only after actor-audience filtering and keyword matching. Imported lore and temporary assumptions are not Canon.
- Secret-string checks are a backstop, not proof that every paraphrase or literary implication is safe. Authors must review disclosures and imported card wording.
- Multi-model references and same-model roles do not establish independent scientific or human consensus.
- Social and psychological output is conditional opinion. Only declared mathematical models can yield numeric results.
- Invalid AI expressions remain editable proposals and cannot be run or frozen until validation passes. Rules are never loosened automatically after failure.
- Manual writing remains available without AI/network access. A failed model does not trigger cross-provider fallback.

## Implementation boundaries

Existing AICenter, keyring, CodexAdapter, TaskManager, controlled Actions, CharacterService, references, workbench notes, checkpoints, DataCenter, ReviewerReport and Monaco Diff are reused. World Logic Lab and its solvers are retained. No new Agent framework, model gateway, task scheduler, credential store or literary scoring engine is installed.

The software assistant has registered scoped entry actions for roleplay sessions and reviews. The Codex MCP whitelist is unchanged; it does not automatically expose every new Action. Ordinary LLM roleplay/review requests are text-only and have no file or application tools.

See TECHNICAL-DECISIONS.md and AI-SAFETY.md. Verification and unresolved items are recorded separately in UPGRADE-REPORT.md. Private check fixtures, logs, downloaded research source, credentials and real novels are excluded from developer packages.
