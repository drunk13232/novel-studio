# Internationalization selection

Installed: i18next 26.4.3 (MIT), react-i18next 17.0.16 (MIT), i18next-http-backend 4.0.2 (MIT). Development-only: i18next-cli 1.75.2 (MIT), Playwright 1.64.0 (Apache-2.0).

react-i18next requires React >=16.8, i18next >=26.2 and TypeScript 5/6/7; the installed React 19.3 and TypeScript 5.9.3 satisfy this. CLI requires Node >=22; installed Node 24.14 satisfies this. The existing Vite 7.3.7 build copies offline public/locales catalogs. Only required namespaces are fetched from the owned loopback service. No CDN, paid translation platform, extra server, database or font download is introduced.

References: https://www.i18next.com/overview/configuration-options ; https://www.i18next.com/principles/fallback ; https://react.i18next.com/latest/usetranslation-hook ; https://github.com/i18next/i18next-cli ; https://cldr.unicode.org/ ; https://playwright.dev/docs/library .

The owner explicitly approved sending a reviewed UI-only id/text dataset to the existing OpenAI Codex login. Real SDK results and current-conversation translations are validated by stable IDs and placeholders before integration. A text-only capsule uses ephemeral threads with closed filesystem permissions, no MCP, no shell, no Skills discovery and process-scoped overrides instead of global configuration writes. Failed and incomplete batches are recorded privately and excluded; native expert review remains pending. The private job is not shipped as a product translation engine.

The existing vis-timeline 8.5.4 format callbacks use Intl to display tick labels while preserving the declared story offset; its zoom/scale algorithms are unchanged. CodeMirror uses its official Compartment reconfiguration for accessible editor labels, preserving the live editing instance and undo history. No font files are copied; selected fonts retain priority with script-capable system fallbacks.

Security check: the installed Moment 2.30.1 was upgraded to official 2.31.0 (MIT) to address npm's locale-name path traversal advisory. It retains the existing timeline dependency rather than replacing its engine. Monaco 0.57.0 includes DOMPurify 3.4.15; remaining low-severity advisories are disclosed. No third-party source edit or editor downgrade was performed.

A global config hash drift was observed during the pass. Its source is unresolved, and it is excluded from candidates. This does not establish that all user-level settings stayed byte-identical.
