# Director Console Preview 2.24.1

Local delivery only. Previous 2.24.0 and its published artifacts remain available; this update does not publish to GitHub or change shortcuts.

## Completed local verification

- 51 distinct related backend checks passed across the final scoped suite and targeted reruns. One fixture referenced a missing demo file and was fixed to its own isolated draft. A second setup raced the frontend build's temporary dist removal; static resources were isolated from backend fixtures and that check passed on rerun.
- Actual OpenAI Python SDK requests serialized distinct planner/writer temperature, reasoning effort and output limits against an in-memory compatible transport. This is MOCK PROTOCOL PASS, not remote AI.
- Actual CPython/WASI obtained only the explicitly handed-off candidate through existing Action permissions. Missing grants and changed candidate versions were rejected. Legacy role-control compatibility, cancellation and stale-record checks passed.
- Production TypeScript/Vite build passed. Existing large-chunk warnings remain; this update adds no dependency or background model loop.
- Headless Edge with the real local backend passed 9 scenarios: demo chapter, history search/empty state, candidate save, TaskManager stream/completion with a MOCK model, load without execution, real WASI analysis, return to the same saved candidate, private JSON export, and no dialog horizontal overflow at 1366/960/600 widths with reduced motion. No page errors or external requests were observed.
- Fast consecutive editing exposed a save-receipt race. The form now prevents edits during its short save/load requests; generation still permits author intervention. Fully completed plans no longer advertise another whole-plan run.
- The packaged EXE ran its real offline WASI worker successfully. This is a packaged runtime check, not native desktop clicking.
- All 1,213 protected real-data baseline files remained byte-identical; zero missing files. Tests used isolated copies of the public demo.

## Boundaries

REAL REMOTE AI: UNVERIFIED for this update. Native WebView window interaction, physical Chinese IME and Windows DPI: UNVERIFIED. These are not established by local fixtures or a headless browser. Project history retains the existing recent-80-record display bound. The Python handoff is read-only analysis, not automatic adoption of script output into prose.

No global Codex configuration, formal manuscript, Canon, State or Knowledge was modified. No new dependency, Agent, database migration or permission bypass was added. Private author/character resources remain outside distributable archives. The earlier 2.24.0 public Allowlist is not silently promoted to cover these new files; any future public update needs its usual review.
