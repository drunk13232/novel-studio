# Public source review — 2.25.2 Preview

The owner authorized updating the existing public repository and Preview Release. The refreshed explicit Allowlist includes this module, its integrations, Chinese/English strings and synthetic tests. Source export includes no parent Git objects, private author data, credentials, machine locator, audit logs or private character resources. The private Developer ZIP and personal launch helpers are not public release assets.

New source: data_organization.py, data-organization.tsx/css, organization-data.ts, quantity-field.tsx and world-data-table.tsx. Existing Bible templates, field rendering, world studio, model controls, task and confirmation services are reused. There are no new application dependencies or data migrations.

Source and binary scanner findings require fingerprint-level review. Previously owner-reviewed upstream/test false positives can be retained only when the fingerprint and original source are unchanged. Any new unresolved sensitive finding blocks publication. The artifact-side publication record contains actual scan, runtime, installer, CI and remote-hash evidence; no development result is promoted to native or real-provider acceptance.
