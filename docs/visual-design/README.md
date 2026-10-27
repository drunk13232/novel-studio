# Novel Studio 2.12.2 Visual Design Upgrade Preview

This is a visual upgrade of the existing desktop application. It retains the previous editor, project data model, AI workflow, permissions, backups and private companion configuration.

Read DESIGN-SYSTEM.md for component rules and ASSETS.md for independent art sources. Core files: study-design.css, study-components.tsx, evaluation-charts.tsx, literary-art.tsx and the existing study/review components. Runtime resources are small SVG/WebP files bundled by Vite; no image service, extra model or external font is needed at runtime.

The Moon theme receives the primary ivory literary-study treatment; existing other themes remain selectable. The existing decoration switch hides atmosphere art, and focus mode keeps the manuscript area clean. No image is placed underneath manuscript text.

Evaluation graphics use stored real results only. This version does not generate scores or call a remote model merely to display the page. Evidence, uncertainty, missing coverage and expired source versions remain explicit.

Windows build: use desktop/build.ps1 -Preview. Developer packaging checks the exact visual asset manifest. The public ZIP uses first-run data configuration, while a local installed copy may point to an existing user data directory. Do not package personal novels, reports, models, credentials or reference libraries.

See DELIVERY-REPORT.md for actual checks, EXE screenshots and limitations. Preview does not imply full native IME, system DPI or all remote AI-provider acceptance.
