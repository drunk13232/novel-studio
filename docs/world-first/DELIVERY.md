# Novel Studio 2.23.1 · World-First Creation Preview

Status: PARTIAL / Preview. This hotfix removes story and character prerequisites from worldbuilding; it does not certify every feature or external AI service.

## Delivered

- Bookshelf world-first entry reuses the existing creation wizard and persists its focus.
- World-only editable fields and bounded context; existing story history and character/theme inputs are excluded from world-first requests.
- Actual world task routing, existing model controls and explicit author adoption. Missing or invented conditions remain proposals.
- Creation of confirmed world settings without placeholder protagonist, character State, story proposal, long-form outline materialization or prose.
- Existing World Studio defaults to one simple editable overview. Advanced modes remain available.
- Version fencing prevents stale reads from rolling the draft backward. Only stage and model-control metadata can safely merge across a newer draft revision; stale content edits and adoption remain rejected.
- Cancelled partial world replies retain their world-history scope rather than disappearing after reload.
- No new dependency, framework, global configuration change or user-data migration.

## Verification completed before packaging

- LOCAL PASS: 52 targeted creation, project, world-studio and AI-control cases. One pre-existing Pydantic serialization warning remains in a world-relation test fixture.
- BUILD PASS: TypeScript/Vite production build. Existing large lazy-loaded editor/PDF chunks still produce size warnings.
- BROWSER PASS: headless Edge against the actual isolated backend and a clearly identified local mock OpenAI-compatible model. Verified direct world entry, seven world-only fields, generation, explicit adoption, project creation, saved overview navigation, no placeholder cast, existing starter design and no automatic adoption. No JavaScript errors, business error notifications or external requests in the final run.
- An earlier browser run found a genuine draft-version race immediately after AI completion. It was fixed; the final run includes error-notification assertions rather than silently retrying a failed content mutation.

## Not claimed

- The fixture model is MOCK, not real Codex or remote AI. No paid calls or private-fiction transmission took place.
- Native Windows clicks, physical Chinese IME and broad regression of every writing feature were not performed in this hotfix. The previous release's native checks are not reused as proof for this version.
- The Windows installer/archives are separately checked after construction. Release-side SHA256SUMS.txt and WORLD-FIRST-VERIFICATION.json record their actual results without rewriting this source snapshot after sealing.
- Licensing and public publication remain owner decisions. Private checks, user data and private companion assets are excluded from developer and Windows archives.
