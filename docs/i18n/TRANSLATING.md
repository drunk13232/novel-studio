# Translating Novel Studio

This International Preview adds i18next UI localization to the current World Logic Lab codebase. Language availability is not a claim of complete translation or native review. See LANGUAGE-STATUS.md for measured coverage and remaining work.

## Scope

Translate application labels, instructions, accessible names and confirmations only. Never translate user manuscripts, character names, world entries, reference excerpts, filenames, API routes, model IDs, Canon/State enums or credentials. UI language, project writing language and AI explanation language are separate settings. Existing projects retain their declared language; missing legacy language remains zh-CN.

## Resource files

Offline catalogs live in web/frontend/public/locales/<BCP-47 locale>/<namespace>.json. Simplified Chinese is the source, English is the international reference. Region variants use their own files; pt-PT does not fall back to pt-BR. Supported languages are listed in src/i18n-locales.ts. Fallback is the exact supported locale → English → Simplified Chinese. Unsupported browser region variants are matched to a supported base locale at first launch. An explicit saved choice wins on later launches.

## Keys and placeholders

Use stable semantic lowerCamelCase keys, such as editor:save or assistant:waitingApproval. Do not use source sentences, hashes or line numbers as keys. Preserve {{variable}} names exactly; do not translate parameter names. React escapes inserted text. Do not insert HTML or scripts into a translation; use react-i18next Trans for explicitly reviewed rich text.

## Plurals and formatting

Use i18next count and JSON v4 suffixes (_one, _few, _many, _other, etc.). Required categories come from Intl.PluralRules for the locale. Do not append an English s or invent plural rules. Numbers and dates use JavaScript Intl. Story dates retain the declared offset and ISO Gregorian calendar; locale changes do not silently change the calendar year. Date-only records do not gain a displayed time. Content counts still distinguish Han characters from all non-whitespace characters; this UI update does not redefine stored writing metrics.

## New languages

1. Add the supported BCP-47 code, native name and direction to i18n-locales.ts.
2. Add offline namespace JSON files. Use empty objects for unfinished namespaces, not copied Chinese text or invented translations.
3. Translate and review the intended keys. Keep missing keys as explicit fallback and report PARTIAL.
4. Check interpolation, grammatical plurals, privacy warnings, technical terms and long labels.
5. Verify representative views, language switching while editing, persistence and RTL where applicable.
6. Update measured status. COMPLETE requires complete UI adaptation, key checks and representative interaction evidence; machine-assisted translation still needs a native-review notice.

## Local commands

From the engine directory:

    npm --prefix web/frontend ci
    npm --prefix web/frontend run i18n:extract
    npm --prefix web/frontend run i18n:status
    npm --prefix web/frontend run i18n:lint
    npm --prefix web/frontend run i18n:quality
    npm --prefix web/frontend run build

Extract defaults to dry-run. Review changes before writing or using instrument. Keep source literals used as IDs, conditions, user content or AI input out of automatic replacement. Dynamic keys must be registered in the explicit resource catalog and documented by the quality report.

## Review

Translations in this release are machine-assisted and have no documented native translator review. Verify terminology, tone, grammar, script shaping, keyboard navigation, screen readers, layout at small desktop sizes, and safety confirmations. English and Simplified Chinese currently have a broader registered catalog; advanced untranslated interfaces remain a release limitation. Do not silently raise completeness to make a percentage look better.

No public repository URL exists yet. This bundled guide is the contribution entry point until the owner authorizes publication. The project license and copyright holder remain pending; software licensing does not cover authors’ manuscripts or uploaded materials.
